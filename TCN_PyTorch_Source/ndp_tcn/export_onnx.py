"""导出固定窗口 FP32 ONNX 并在 PC 核对数值；不是 TI NPU 编译器。"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import torch

from .data import load_case
from .outputs import create_run_directory, now_singapore
from .predict import ResidualPredictor
from .predict_onnx import pack_normalized_numpy


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_KEY = "ndp_tcn_contract"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def deployment_timing_metadata(schema):
    """同一标签定义的显式板端时序；H是调度元数据，不是第十路特征。"""
    h = schema["horizon_steps_to_target_interval_start"]
    length = schema["history_steps"]
    dt = float(schema["sample_interval_s"])
    if (isinstance(h, bool) or not isinstance(h, (int, np.integer)) or h < 0
            or isinstance(length, bool) or not isinstance(length, (int, np.integer)) or length < 1
            or not np.isfinite(dt) or dt <= 0):
        raise ValueError("Invalid deployment horizon/history/sample interval.")
    frequency = 1.0 / dt
    if np.isclose(frequency, round(frequency), rtol=1e-10, atol=1e-8):
        frequency = float(round(frequency))
    return {
        "H": int(h), "horizon_steps_to_target_interval_start": int(h),
        "history_steps": int(length), "sample_interval_s": dt,
        "control_frequency_Hz": frequency, "prediction_lead_time_s": int(h) * dt,
        "feature_names": list(schema["feature_names"]),
        "feature_units": ["V", "A", "A", "A", "A", "V", "A", "V/s", "V"],
        "IREF_definition": "common per-phase current reference; do not multiply by four",
        "b0_per_phase": float(schema["b0_per_phase"]),
        "label_formula": "label[k,H]=((Vo[k+H+1]-Vo[k+H])/dt[k+H]-b0*IREF[k+H])-z2[k]",
        "output_restore_formula": "residual_V_per_s=normalized_output*y_scale+y_mean",
        "disturbance_reconstruction": "f_pred[k+H]=z2[k]+residual_V_per_s",
        "target_interval_definition": "[t[k+H],t[k+H+1])",
        "runtime_scheduling": {
            "source_tick": "k: endpoint of the continuous input window k-L+1...k",
            "target_tick": "k+H", "history_requires_consecutive_control_ticks": True,
            "update_raw_history_when_npu_busy": True,
            "input_endpoint": "after current IREF[k] and z2[k] have been calculated",
            "source_z2": "capture z2[k] with the submitted window; never replace it by completion-time z2",
            "early_result": "cache until the matching target control ISR",
            "late_result": "discard if not available at the target control ISR entry; use baseline LADRC",
            "consume_once": True,
            "control_correction": "delta_I=clamp(-alpha*(f_pred-z2_current)/b0,-delta_I_max,+delta_I_max)",
            "horizon_is_tensor_input": False,
        },
    }


def _verification_cases(predictor, args):
    run = predictor.checkpoint["run"]
    if args.verify_npz:
        paths = [Path(path).resolve() for path in args.verify_npz]
        selection = "explicit_verification_files"
    else:
        manifest = run["split_manifest"]
        selection = run.get("selection_split") or manifest.get("selection_split") or "test"
        if selection not in ("train", "val", "test") or not manifest.get(selection):
            raise ValueError("No verification cases; specify --verify-npz.")
        root = args.data_dir.resolve()
        paths = [(root / name).resolve() for name in manifest[selection]]
        if any(not path.is_relative_to(root) for path in paths):
            raise ValueError("Verification manifest paths must remain inside data-dir.")
    identities = list(run.get("data_identity", {}).values())
    cases, seen = [], set()
    for path in paths:
        case = load_case(path)
        predictor.validate_schema(case.metadata)
        identity = (case.case_id, case.metadata["source_sha256"].lower())
        if identity in seen:
            raise ValueError("Duplicate verification case/source identity.")
        if not any((item["case_id"], item["source_sha256"].lower()) == identity
                   for item in identities):
            raise ValueError(f"Verification case identity was not recorded in checkpoint: {path.name}")
        seen.add(identity)
        cases.append(case)
    if not cases:
        raise ValueError("Verification requires at least one nonempty case.")
    return selection, cases


def comparison_metrics(reference, candidate, atol, rtol):
    reference = np.asarray(reference, dtype=np.float64)
    candidate = np.asarray(candidate, dtype=np.float64)
    if reference.shape != candidate.shape or reference.size == 0:
        raise ValueError("Comparison arrays must have the same nonempty shape.")
    if not np.isfinite(reference).all() or not np.isfinite(candidate).all():
        raise ValueError("Nonfinite ONNX verification output.")
    absolute = np.abs(candidate-reference)
    limits = atol + rtol*np.abs(reference)
    return {"passed": bool(np.all(absolute <= limits)),
            "max_abs_difference_V_per_s": float(absolute.max()),
            "mean_abs_difference_V_per_s": float(absolute.mean()),
            "rmse_difference_V_per_s": float(np.sqrt(np.mean(absolute**2))),
            "outside_tolerance_count": int(np.count_nonzero(absolute > limits))}


def audit_ti_operator_profile(graph):
    """只审核本项目 FP32 core 的结构约束，不替代 TI 量化器/编译器认证。"""
    import onnx
    from onnx import numpy_helper

    allowed = {"Conv", "Relu", "Flatten", "Reshape", "Gemm", "MatMul", "Add", "Constant", "Identity"}
    failures, convs, dense = [], [], []
    constants = {value.name: numpy_helper.to_array(value) for value in graph.graph.initializer}
    for node in graph.graph.node:
        if node.op_type == "Constant":
            for attr in node.attribute:
                if attr.name == "value":
                    constants[node.output[0]] = numpy_helper.to_array(attr.t)
    try:
        inferred = onnx.shape_inference.infer_shapes(graph, strict_mode=True)
    except Exception as exc:
        failures.append(f"Static shape inference failed: {type(exc).__name__}: {exc}")
        inferred = graph
    shapes = {value.name: [dim.dim_value if dim.HasField("dim_value") else None
                          for dim in value.type.tensor_type.shape.dim]
              for value in [*inferred.graph.input, *inferred.graph.value_info, *inferred.graph.output]}
    producer = {output: node for node in graph.graph.node for output in node.output}
    graph_inputs = list(graph.graph.input)
    if (len(graph_inputs) != 1 or len(shapes.get(graph_inputs[0].name, [])) != 4
            or shapes[graph_inputs[0].name][0:2] != [1, 12]
            or shapes[graph_inputs[0].name][-1] != 1):
        failures.append("Graph input must have static NCHW [1,12,L,1] shape.")
    for node in graph.graph.node:
        attrs = {attr.name: onnx.helper.get_attribute_value(attr) for attr in node.attribute}
        if node.domain not in ("", "ai.onnx") or node.op_type not in allowed:
            failures.append(f"Unsupported core operator: {node.domain}::{node.op_type}.")
            continue
        if node.op_type == "Conv":
            weights = constants.get(node.input[1])
            if weights is None or weights.ndim != 4:
                failures.append("Convolution must have constant 2D kernel weights.")
                continue
            out_channels, in_channels, kh, kw = weights.shape
            groups = attrs.get("group", 1)
            kernel = list(attrs.get("kernel_shape", [kh, kw]))
            good = (groups == 1 and in_channels % 4 == 0 and out_channels % 4 == 0
                    and kh >= 2 and kw == 1 and kernel == [kh, kw]
                    and list(attrs.get("strides", [1, 1])) == [1, 1]
                    and list(attrs.get("dilations", [1, 1])) == [1, 1]
                    and list(attrs.get("pads", [0, 0, 0, 0])) == [0, 0, 0, 0]
                    and attrs.get("auto_pad", b"NOTSET") in (b"NOTSET", b"VALID", "NOTSET", "VALID"))
            if not good:
                failures.append("Conv requires groups=1, multiple-of-4 channels, kH>=2, kW=1, unit stride/dilation and no padding.")
            if len(node.input) > 2 and node.input[2] and node.input[2] not in constants:
                failures.append("Convolution bias must be constant.")
            convs.append({"in_channels": int(in_channels), "out_channels": int(out_channels),
                          "kernel": [int(kh), int(kw)], "groups": int(groups)})
        elif node.op_type in ("Gemm", "MatMul"):
            weights = constants.get(node.input[1])
            if weights is None or weights.ndim != 2:
                failures.append("Fully connected layers require constant rank-2 weights.")
                continue
            transposed = node.op_type == "Gemm" and attrs.get("transB", 0) == 1
            in_features, out_features = (weights.shape[1], weights.shape[0]) if transposed else weights.shape
            if (in_features < 16 or attrs.get("transA", 0) != 0 or attrs.get("transB", 0) not in (0, 1)
                    or attrs.get("alpha", 1.0) != 1.0 or attrs.get("beta", 1.0) != 1.0):
                failures.append("Fully connected input count must be >=16, with ordinary unscaled matrix multiplication.")
            if node.op_type == "Gemm" and len(node.input) > 2 and node.input[2] and node.input[2] not in constants:
                failures.append("Fully connected bias must be constant.")
            dense.append({"in_features": int(in_features), "out_features": int(out_features)})
        elif node.op_type == "Add":
            biases = [constants[name] for name in node.input if name in constants]
            if len(biases) != 1 or biases[0].ndim > 2 or (biases[0].ndim == 2 and biases[0].shape[0] != 1):
                failures.append("Add is allowed only for a constant scalar/vector fully-connected bias.")
        elif node.op_type == "Reshape":
            if len(node.input) < 2 or node.input[1] not in constants:
                failures.append("Reshape must use a constant target shape.")
            elif shapes.get(node.output[0], [])[:1] != [1] or len(shapes.get(node.output[0], [])) != 2:
                failures.append("Core Reshape must flatten to a static batch-one matrix.")
        elif node.op_type == "Flatten" and attrs.get("axis", 1) != 1:
            failures.append("Core Flatten must preserve batch with axis=1.")
    if not convs or len(dense) != 2:
        failures.append("Expected at least one temporal Conv and exactly two fully connected layers.")
    if convs and convs[0]["in_channels"] != 12:
        failures.append("The first convolution must consume all 12 packed channels.")
    if sum(node.op_type == "Relu" for node in graph.graph.node) != len(convs)+1:
        failures.append("Expected one ReLU per convolution and one after the hidden fully connected layer.")
    final = producer.get(graph.graph.output[0].name) if len(graph.graph.output) == 1 else None
    while final is not None and final.op_type in ("Identity", "Reshape"):
        final = producer.get(final.input[0])
    if final is not None and final.op_type == "Add":
        variable = [name for name in final.input if name not in constants]
        final = producer.get(variable[0]) if len(variable) == 1 else None
    signed_output = final is not None and final.op_type in ("Gemm", "MatMul")
    if not signed_output or not dense or dense[-1]["out_features"] != 1:
        failures.append("Final output must be a signed one-unit fully connected layer without activation.")
    return {"profile": "ti_npu_fp32_core_v1", "applicable": True, "passed": not failures,
            "failures": failures, "convolutions": convs, "fully_connected": dense,
            "signed_output": signed_output, "ti_npu_ready": False,
            "note": "FP32 structural audit only; TI quantization, compiler acceptance and board timing remain unverified."}


def audit_ti_fullconv_operator_profile(graph):
    """严格审查全卷积 core；没有输出切片、全连接、展平或动态重排。"""
    import onnx
    from onnx import numpy_helper

    failures, convs = [], []
    constants = {value.name: numpy_helper.to_array(value) for value in graph.graph.initializer}
    producers = {name: node for node in graph.graph.node for name in node.output}
    shapes = lambda value: [dim.dim_value if dim.HasField("dim_value") else None
                            for dim in value.type.tensor_type.shape.dim]
    if (len(graph.graph.input) != 1 or len(shapes(graph.graph.input[0])) != 4
            or shapes(graph.graph.input[0])[:2] != [1, 12]
            or shapes(graph.graph.input[0])[-1] != 1):
        failures.append("Full-convolution input must be static NCHW [1,12,L,1].")
    if len(graph.graph.output) != 1 or shapes(graph.graph.output[0]) != [1, 4, 1, 1]:
        failures.append("Full-convolution output must retain all four channels [1,4,1,1].")
    for node in graph.graph.node:
        if node.domain not in ("", "ai.onnx") or node.op_type not in {"Conv", "Relu", "Identity"}:
            failures.append(f"Forbidden full-convolution core operator: {node.domain}::{node.op_type}.")
        if node.op_type == "Identity" and node.input[0] in constants:
            constants[node.output[0]] = constants[node.input[0]]
        if node.op_type != "Conv":
            continue
        attrs = {a.name: onnx.helper.get_attribute_value(a) for a in node.attribute}
        weight = constants.get(node.input[1])
        if weight is None or weight.ndim != 4:
            failures.append("Conv requires constant rank-four weights.")
            continue
        cout, cin, kh, kw = weight.shape
        if (cin % 4 or cout % 4 or attrs.get("group", 1) != 1 or kw != 1 or kh < 1
                or list(attrs.get("kernel_shape", [kh, kw])) != [kh, kw]
                or list(attrs.get("strides", [1, 1])) != [1, 1]
                or list(attrs.get("dilations", [1, 1])) != [1, 1]
                or list(attrs.get("pads", [0, 0, 0, 0])) != [0, 0, 0, 0]
                or attrs.get("auto_pad", b"NOTSET") not in (b"NOTSET", b"VALID", "NOTSET", "VALID")):
            failures.append("Conv requires m4 channels, groups=1, kW=1, valid unit-stride/dilation.")
        if len(node.input) > 2 and node.input[2] and node.input[2] not in constants:
            failures.append("Conv bias must be constant.")
        convs.append({"in_channels": int(cin), "out_channels": int(cout), "kernel": [int(kh), int(kw)]})
    if (len(convs) < 3 or convs[0]["in_channels"] != 12
            or convs[-1]["out_channels"] != 4 or convs[-1]["kernel"] != [1, 1]):
        failures.append("Expected temporal convolution trunk, full-window convolution and four-channel 1x1 head.")
    if sum(n.op_type == "Relu" for n in graph.graph.node) != len(convs)-1:
        failures.append("Only the final signed convolution may omit ReLU.")
    final = producers.get(graph.graph.output[0].name) if len(graph.graph.output) == 1 else None
    while final is not None and final.op_type == "Identity":
        final = producers.get(final.input[0])
    signed = final is not None and final.op_type == "Conv"
    if not signed:
        failures.append("Final output must be a signed convolution without activation or output selection.")
    return {"profile": "ti_npu_fullconv_fp32_core_v1", "applicable": True, "passed": not failures,
            "failures": failures, "convolutions": convs, "fully_connected": [], "signed_output": signed,
            "ti_npu_ready": False,
            "note": "FP32 structural audit only; all-layer NPU hardware placement must be proven by NNC generated code."}


def _write_readme(directory, contract, report):
    passed = report["status"] == "passed"
    ti_profile = contract.get("model_backend") in ("ti_npu", "ti_npu_fullconv")
    fullconv = contract.get("model_backend") == "ti_npu_fullconv"
    lines = ["# 本次 ONNX 导出与数值验证", "",
             f"状态：**{'PC 数值验证通过' if passed else '未通过，不能作为已验证模型使用'}**。", "",
             "此产物为通用 FP32 ONNX，目标用途是 PC 对照与后续工具链评估。",
             "**尚未完成 TMS320F28P55x NPU 量化、TI MCU NNC 编译、固件集成或板端时延验证。**", "",
             f"时间：{report['created_at']}（UTC+08）。",
             f"原 checkpoint：`{contract['checkpoint']}`。",
             f"原 checkpoint SHA-256：`{contract['checkpoint_sha256']}`。",
             f"原 checkpoint 轮次：{report.get('checkpoint_epoch', '未记录')}。", "",
             "## 输入与输出", "",
             f"- 输入：`normalized_window`，float32，固定形状 `{contract['input_shape']}`。",
             "- 时间维度按从旧到新排列；通道顺序为 Vo、ILA、ILB、ILC、ILD、VREF、IREF、z2、Vin。",
             "- ONNX 图外先计算 `(raw_window - x_mean) / x_scale`，再转 float32。",
             ("- 在 CPU 上再把 [B,L,9] 转为 [B,12,L,1]：前九通道按原顺序重排，后三通道填标准化零；ONNX 只包含 core。"
              if ti_profile else "- 此 original 图直接接收 [B,L,9] 标准化窗口。"),
             f"- 输出：`normalized_residual`，float32，固定形状 `{contract['output_shape']}`。",
             ("- 全卷积图完整输出四路，图外读取有效通道0；其他输出槽不用于控制。" if fullconv else
              "- 图输出单个有符号残差。"),
             "- 图外计算 `normalized_residual * y_scale + y_mean` 得到物理残差 V/s。",
             "- `future_disturbance = source_z2 + residual`；保持原 h 和采样间隔，不改变预测目标时间。",
             "- scaler 和数据约定同时写入 ONNX 元数据 `ndp_tcn_contract` 与 deployment.json。",
             "- 不要把原始九通道信号直接送入归一化图，也不要对恢复后的残差重复反标准化。", "",
             "## 导出和检查", "",
             ("在内存中的 TI 模型副本上执行 eval 和 structural_reparam，融合 Conv2d/BN，然后只导出 core。"
              if ti_profile else "在内存中的模型副本上执行 eval 和 structural_reparam，合并可重参数化的大/小核卷积。"),
             ("全卷积 core 仅包含卷积与 ReLU（允许静态 Identity）；禁止 FC/Flatten/Slice/Gather，执行独立严格审查。" if fullconv else
              "TI core 使用普通二维卷积、ReLU、Flatten/Reshape 和全连接；执行额外的算子/层配置审查。"
              if ti_profile else "保持原 GELU 和分组结构，不改写训练权重或模型源码。"),
             "使用 dynamo 导出器和单文件权重；结构审查通过不等于 TI NPU 已经编译通过。",
             f"请求 opset：{report['requested_opset']}；实际导入版本：`{report.get('opset_imports', {})}`。",
             f"验证样本数：{report.get('sample_count', 0)}，验证来源：`{report.get('verification_split')}`。",
             "每个窗口使用 batch=1，分别计算未融合 PyTorch、融合 PyTorch、ONNX Runtime CPU 输出，",
             "统一恢复为 V/s 后比较。判据为 `abs(candidate-reference) <= atol + rtol*abs(reference)`。",
             f"atol={report['atol_V_per_s']} V/s，rtol={report['rtol']}；不通过时程序报错并保留失败记录。", ""]
    if passed:
        for key, title in (("fusion_vs_original", "融合与原 PyTorch"),
                           ("onnx_vs_fused", "ONNX 与融合 PyTorch"),
                           ("onnx_vs_original", "ONNX 与原 PyTorch")):
            item = report[key]
            lines.append(f"- {title}：最大绝对差 {item['max_abs_difference_V_per_s']:.9g} V/s，"
                         f"平均绝对差 {item['mean_abs_difference_V_per_s']:.9g} V/s。")
        lines += ["", "对比的是同一模型的数值等价性，不是新的模型精度或独立测试成绩。"]
    elif report.get("error"):
        lines += [f"错误：`{report['error']}`。"]
    lines += ["", "## 文件与操作", "",
              "- model.onnx：固定 batch=1 的 FP32 网络与嵌入的输入输出约定。",
              "- deployment.json：同一输入输出约定的可读副本。",
              "- verification.json：验证状态、误差、各工况标签 RMSE、版本、算子和哈希。", "",
              "- golden_vectors.npz：原始窗口、归一化窗口、原 PyTorch 期望输出、工况与源时刻；仅供移植后数值回放。",
              "  normalized_window 使用 ONNX 图输入布局；normalized_raw_window 保留标准化后的 [B,L,9] 窗口。",
              "这些选优/验证窗口不能作为量化校准集；量化校准仍只能使用训练工况。", "",
              f"在 VS Code 项目根目录 {ROOT} 中执行（选择 TCN 环境）：", "", "```text",
              f'python -m ndp_tcn.predict_onnx --model "{(directory / "model.onnx").as_posix()}" '
              f'--input-npz "{report["verification_files"][0]["path"]}"', "```", "",
              "ONNX Runtime 仅用于 PC 回放；F28P55x 固件应走 TI 量化/编译及 C2000Ware/CCS 流程。",
              "本图包含的算子及分组方式是否可编译为 TI NPU，须按对应工具链约束另行确认。",
              "本次修改前备份见项目中文说明；此目录为新产物，不覆盖历史实验。", ""]
    (directory / "README_CN.md").write_text("\n".join(lines), encoding="utf-8")


def export(args):
    if (args.threads < 1 or args.opset < 13 or not np.isfinite(args.atol)
            or not np.isfinite(args.rtol) or args.atol < 0 or args.rtol < 0):
        raise ValueError("threads must be positive, opset >= 13, and tolerances finite/nonnegative.")
    try:
        import onnx
        import onnxruntime as ort
        import onnxscript
    except ImportError as exc:
        raise ImportError("Install export dependencies: python -m pip install -r ndp_tcn/requirements_onnx.txt") from exc
    torch.set_num_threads(args.threads)
    predictor = ResidualPredictor(args.checkpoint, device="cpu")
    if predictor.backend not in ("original", "ti_npu", "ti_npu_fullconv"):
        raise ValueError("This export workflow supports original, ti_npu and ti_npu_fullconv checkpoints.")
    ti_profile = predictor.backend in ("ti_npu", "ti_npu_fullconv")
    fullconv = predictor.backend == "ti_npu_fullconv"
    selection, cases = _verification_cases(predictor, args)
    fused = deepcopy(predictor.model).eval()
    fused.structural_reparam()
    checkpoint = args.checkpoint.resolve()
    contract = {"contract_version": 1, "input_name": "normalized_window",
                "output_name": "normalized_residual", "input_shape": [1, predictor.config.seq_len, 9],
                "output_shape": [1, 1], "input_dtype": "float32", "output_dtype": "float32",
                "input_is_normalized": True, "output_is_normalized": True,
                "scalers": predictor.scalers.to_dict(), "data_schema": predictor.schema,
                "checkpoint": str(checkpoint), "checkpoint_sha256": _sha256(checkpoint),
                "target_board": "TMS320F28P55x", "ti_npu_ready": False,
                "model_backend": predictor.backend}
    contract.update(deployment_timing_metadata(predictor.schema))
    if ti_profile:
        contract.update({"contract_version": 2, "input_shape": [1, 12, predictor.config.seq_len, 1],
                         "input_layout": "NCHW", "raw_window_shape": [predictor.config.seq_len, 9],
                         "padded_channels": 12})
    if fullconv:
        contract.update({"contract_version": 3, "output_shape": [1, 4, 1, 1], "output_layout": "NCHW",
                         "effective_output_channel": 0, "packed_output_channels": 4})
    directory = create_run_directory(args.output_dir, prefix=f"onnx_{predictor.backend}" if ti_profile else "onnx")
    print(f"Output directory: {directory}", flush=True)
    report = {"created_at": now_singapore().isoformat(timespec="seconds"), "status": "in_progress",
              "target_board": "TMS320F28P55x", "ti_npu_ready": False, "model_backend": predictor.backend,
              "checkpoint": str(checkpoint), "checkpoint_sha256": contract["checkpoint_sha256"],
              "checkpoint_epoch": predictor.checkpoint.get("epoch"),
              "model_source_sha256": predictor.checkpoint["run"]["model_source_sha256"],
              "export_script_sha256": _sha256(__file__), "requested_opset": args.opset,
              "exporter": "dynamo", "structural_reparameterization": True,
              "atol_V_per_s": args.atol, "rtol": args.rtol, "verification_split": selection,
              "sample_count": sum(len(case.X) for case in cases),
              "verification_files": [{"path": str(case.path), "sha256": _sha256(case.path),
                                      "case_id": case.case_id, "sample_count": len(case.X),
                                      "source_sha256": case.metadata["source_sha256"]} for case in cases],
              "environment": {"python": platform.python_version(), "torch": str(torch.__version__),
                              "onnx": onnx.__version__, "onnxruntime": ort.__version__,
                              "onnxscript": onnxscript.__version__, "numpy": np.__version__},
              "onnx_checker_passed": False, "independent_test_result": False}
    _json(directory / "deployment.json", contract)
    _json(directory / "verification.json", report)
    _write_readme(directory, contract, report)
    try:
        model_path = directory / "model.onnx"
        normalized_sample = predictor.scalers.transform_x(cases[0].X[:1])
        sample = torch.from_numpy(pack_normalized_numpy(normalized_sample) if ti_profile else normalized_sample)
        torch.onnx.export(fused.core if ti_profile else fused, (sample,), str(model_path), input_names=[contract["input_name"]],
                          output_names=[contract["output_name"]], opset_version=args.opset,
                          dynamo=True, external_data=False, verbose=False)
        graph = onnx.load(str(model_path))
        onnx.helper.set_model_props(graph, {CONTRACT_KEY: json.dumps(contract, ensure_ascii=False)})
        onnx.checker.check_model(graph, full_check=True)
        onnx.save_model(graph, str(model_path), save_as_external_data=False)
        report["onnx_checker_passed"] = True
        report["opset_imports"] = {item.domain or "ai.onnx": item.version for item in graph.opset_import}
        if report["opset_imports"].get("ai.onnx") != args.opset:
            raise RuntimeError(f"Exported ONNX opset {report['opset_imports'].get('ai.onnx')} "
                               f"does not match requested opset {args.opset}; the graph is not verified "
                               "for the requested target version.")
        report["operators"] = sorted({f"{node.domain or 'ai.onnx'}::{node.op_type}" for node in graph.graph.node})
        report["operator_profile_check"] = (audit_ti_fullconv_operator_profile(graph) if fullconv else
                                            audit_ti_operator_profile(graph) if ti_profile else
                                            {"applicable": False, "passed": False,
                                             "note": "Original ModernTCN is not the TI-specific core profile."})
        if ti_profile and not report["operator_profile_check"]["passed"]:
            raise RuntimeError("TI FP32 operator-profile check failed: " +
                               "; ".join(report["operator_profile_check"]["failures"]))
        report["convolution_groups"] = sorted({int(attr.i) for node in graph.graph.node
                                               if node.op_type == "Conv" for attr in node.attribute
                                               if attr.name == "group"})
        report["onnx_sha256"] = _sha256(model_path)
        report["onnx_file_bytes"] = model_path.stat().st_size
        options = ort.SessionOptions()
        options.intra_op_num_threads = args.threads
        options.inter_op_num_threads = 1
        session = ort.InferenceSession(str(model_path), sess_options=options, providers=["CPUExecutionProvider"])
        inputs, outputs = session.get_inputs(), session.get_outputs()
        if (len(inputs) != 1 or inputs[0].name != contract["input_name"]
                or inputs[0].shape != contract["input_shape"] or inputs[0].type != "tensor(float)"
                or len(outputs) != 1 or outputs[0].name != contract["output_name"]
                or outputs[0].shape != contract["output_shape"] or outputs[0].type != "tensor(float)"):
            raise ValueError("Exported graph does not have the declared fixed float32 input/output contract.")
        original_all, fused_all, ort_all, case_metrics = [], [], [], []
        normalized_all, normalized_raw_all, original_normalized_all = [], [], []
        core_reference_all, core_ort_all = [], []
        for case in cases:
            normalized = predictor.scalers.transform_x(case.X)
            graph_windows = pack_normalized_numpy(normalized) if ti_profile else normalized
            values = [[], [], []]
            original_normalized = []
            with torch.inference_mode():
                for index in range(len(normalized)):
                    window = np.ascontiguousarray(normalized[index:index+1])
                    tensor = torch.from_numpy(window)
                    graph_input = np.ascontiguousarray(graph_windows[index:index+1])
                    ort_output = session.run([contract["output_name"]], {contract["input_name"]: graph_input})[0]
                    if fullconv:
                        if ort_output.shape != (1, 4, 1, 1) or not np.isfinite(ort_output).all():
                            raise ValueError("Invalid full-convolution core output.")
                        core_reference_all.append(fused.core(torch.from_numpy(graph_input)).cpu().numpy())
                        core_ort_all.append(ort_output)
                        ort_output = ort_output[:, 0, 0, 0].reshape(1, 1)
                    outputs = (predictor.model(tensor).cpu().numpy(), fused(tensor).cpu().numpy(), ort_output)
                    original_normalized.append(outputs[0])
                    for target, value in zip(values, outputs):
                        if value.shape != (1, 1) or not np.isfinite(value).all():
                            raise ValueError("Nonfinite or malformed verification output.")
                        target.append(predictor.scalers.inverse_y(value))
            original, merged, converted = [np.concatenate(value).astype(np.float64) for value in values]
            original_all.append(original)
            fused_all.append(merged)
            ort_all.append(converted)
            normalized_all.append(graph_windows)
            normalized_raw_all.append(normalized)
            original_normalized_all.append(np.concatenate(original_normalized))
            target = case.y.astype(np.float64)
            case_metrics.append({"case_id": case.case_id, "sample_count": len(target),
                                 "original_torch_rmse_V_per_s": float(np.sqrt(np.mean((original-target)**2))),
                                 "onnx_rmse_V_per_s": float(np.sqrt(np.mean((converted-target)**2))),
                                 "onnx_vs_original": comparison_metrics(original, converted, args.atol, args.rtol)})
        original, merged, converted = [np.concatenate(values) for values in (original_all, fused_all, ort_all)]
        report.update({"fusion_vs_original": comparison_metrics(original, merged, args.atol, args.rtol),
                       "onnx_vs_fused": comparison_metrics(merged, converted, args.atol, args.rtol),
                       "onnx_vs_original": comparison_metrics(original, converted, args.atol, args.rtol),
                       "cases": case_metrics,
                       "original_torch_macro_rmse_V_per_s": float(np.mean([r["original_torch_rmse_V_per_s"] for r in case_metrics])),
                       "onnx_macro_rmse_V_per_s": float(np.mean([r["onnx_rmse_V_per_s"] for r in case_metrics]))})
        if fullconv:
            reference4 = predictor.scalers.inverse_y(np.concatenate(core_reference_all).reshape(-1, 1))
            output4 = predictor.scalers.inverse_y(np.concatenate(core_ort_all).reshape(-1, 1))
            report["all_four_core_outputs_vs_fused"] = comparison_metrics(reference4, output4, args.atol, args.rtol)
            if not report["all_four_core_outputs_vs_fused"]["passed"]:
                raise RuntimeError("Full-convolution four-channel ONNX outputs exceed tolerance.")
        if not all(report[key]["passed"] for key in ("fusion_vs_original", "onnx_vs_fused", "onnx_vs_original")):
            raise RuntimeError("ONNX/fusion numerical verification exceeded the specified physical-unit tolerances.")
        vectors_path = directory / "golden_vectors.npz"
        np.savez_compressed(vectors_path,
                            raw_window=np.concatenate([case.X for case in cases]),
                            normalized_window=np.concatenate(normalized_all),
                            normalized_raw_window=np.concatenate(normalized_raw_all),
                            expected_normalized_residual=np.concatenate(original_normalized_all),
                            expected_residual_V_per_s=original,
                            case_id=np.concatenate([np.full(len(case.X), case.case_id, dtype=np.int64) for case in cases]),
                            source_time_s=np.concatenate([case.source_time for case in cases]),
                            **({"expected_normalized_core_output": np.concatenate(core_ort_all)} if fullconv else {}))
        report["golden_vectors_sha256"] = _sha256(vectors_path)
        report["golden_vectors_purpose"] = "porting verification only; do not use selection/test cases for quantization calibration"
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = f"{type(exc).__name__}: {exc}"
        _json(directory / "verification.json", report)
        _write_readme(directory, contract, report)
        raise
    _json(directory / "verification.json", report)
    _write_readme(directory, contract, report)
    print(f"Verified {report['sample_count']} windows; ONNX vs PyTorch maximum difference="
          f"{report['onnx_vs_original']['max_abs_difference_V_per_s']:.9g} V/s; saved {directory / 'model.onnx'}", flush=True)
    return directory


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--data-dir", type=Path, default=ROOT / "data" / "train_example_labeled")
    p.add_argument("--verify-npz", type=Path, nargs="+", help="覆盖默认选优集合，文件必须匹配 checkpoint 记录的数据身份")
    p.add_argument("--output-dir", type=Path, default=None, help="省略时在 ndp_tcn/results 自动创建按后端命名的 onnx 时间戳目录")
    p.add_argument("--opset", type=int, default=18)
    p.add_argument("--atol", type=float, default=.5, help="转换差值绝对容差，单位 V/s")
    p.add_argument("--rtol", type=float, default=1e-5)
    p.add_argument("--threads", type=int, default=2)
    return p


def main():
    return export(parser().parse_args())


if __name__ == "__main__":
    main()
