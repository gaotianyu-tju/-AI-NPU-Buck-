"""从已有 TI CNN 权重进行官方 8-bit QAT，用转换后的模型逐轮选优。"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import random
import sys
import time
import traceback

from .outputs import create_run_directory, now_singapore
from .ti_quantize import ROOT, _json, _sha256, check_environment, load_calibration_cases


def _write_readme(directory, environment, report):
    settings = report.get("training", {})
    checkpoint = report.get("checkpoint") or "ndp_tcn/results/<TI训练目录>/best.pt"
    data_directory = report.get("data_directory") or "<本次标签目录>"
    lines = ["# TI 8-bit QAT 实验记录", "", f"生成时间：{report['created_at']}（UTC+08:00）。",
             f"状态：`{report['status']}`。", "", "## 方法与数据", "",
             f"从已有 `{report.get('model_backend', 'ti_npu / ti_npu_fullconv')}` FP32 checkpoint 初始化，沿用其结构和源码身份。",
             "使用 TI 1.5 `TINPUTinyMLQATFxModule`，权重/激活均为 8-bit，auto_quantization=False。",
             "只用保存清单的 train 工况进行梯度更新、observer 量化范围更新和 BN 训练；复用原 scaler，不重新拟合。",
             "每轮仅在训练 wrapper 的副本上 eval/convert，然后按选优工况的物理 macro RMSE 选择最佳量化模型。",
             "若使用名为 test 的划分，此处按用户约定作为选优集，不能称为独立测试集；实际工况以本次清单为准。",
             "选优工况不参与梯度、BN 或 observer 校准。每轮调用一次原 wrapper.train()，使 TI 的冻结日程正常推进。", "",
             f"- 初始化来源：`{report.get('checkpoint', '')}`。",
             f"- 训练/observer 工况：`{report.get('training_case_ids', [])}`。",
             f"- 选优工况：`{report.get('selection_case_ids', [])}`。",
             f"- 配置：`{json.dumps(settings, ensure_ascii=False)}`。",
             f"- 已完成轮次：`{report.get('epochs_completed', 0)}`；最佳轮次：`{report.get('best_epoch', None)}`。",
             f"- 最佳量化模型 macro RMSE：`{report.get('best_macro_rmse_V_per_s', None)}` V/s。",
             f"- 初始化 FP32 macro RMSE：`{report.get('source_fp32_macro_rmse_V_per_s', None)}` V/s。", "",
             "## 输入输出与产物", "",
             "9 通道依次为 Vo、ILA、ILB、ILC、ILD、VREF、IREF、z2、Vin；窗口 `[B,L,9]` 标准化后转 `[B,12,L,1]`，后三通道为标准化的 0。",
             "`output_int=False` 输出归一化浮点残差；只计算一次 `normalized*y_scale+y_mean` 得到 V/s。",
             "全卷积后端的导出核心直接输出 `[B,4,1,1]`，有效通道为0；四通道用相同目标训练，PC指标只读取通道0。选择输出通道仅在训练/评价适配器中进行，不导出 Slice/Gather。",
             "QAT开始前仅在模型副本上把有效通道0的权重/偏置复制到冗余通道1..3，避免从头FP32训练后未监督槽的随机损失影响共享主干；来源checkpoint和有效通道0不变。",
             "窗口时序、预测目标区间、b0 和单位沿用来源 checkpoint 的 data_schema，写入 deployment.json。",
             "未来扰动为原始末拍 z2 加残差；QAT 入口不修改 ADRC 或生成控制指令。",
             "- `history.json`：每轮训练损失、选优指标、冻结日程计数和耗时。",
             "- `best_qat_state.pt`：独立的官方 QAT wrapper 状态与配置；不能作为原 ResidualPredictor 的 best.pt 加载。",
             "- `model_int8.onnx`：最佳轮转换后的 TI 量化表达图。",
             "- `deployment.json`：与 ONNX 内嵌 metadata 一致的输入输出约定，包含 FP32 来源和 QAT 状态文件哈希。",
             "- `golden_vectors.npz`：选优集全部样本的规范化输入及量化预测。",
             "- `quantization_report.json`：来源、实际配置、验证状态与物理指标。",
             "- `environment.json`：TI 依赖检查；此脚本不会自行修改 Python 环境。", ""]
    if environment.get("errors"):
        lines += ["## 环境阻塞", ""] + [f"- {error}" for error in environment["errors"]] + [""]
    if report.get("error"):
        lines += ["## 本次失败", "", report["error"], "未完成运行留下的候选文件不能视为已验证部署产物。", ""]
    if report["status"] == "qat_export_verified_on_selection_samples":
        lines += ["本次已完成真实 QAT、全部选优样本的 ONNX checker/Runtime 验证；具体误差见报告。", ""]
    lines += ["## 使用与限制", "", "在 E:\\bisai 的 VS Code Python 终端执行：", "", "```text",
              f'python -m ndp_tcn.ti_qat --checkpoint "{checkpoint}" --data-dir "{data_directory}"', "```", "",
              "默认 epochs=10、lr=0.0001、batch-size=128、weight-decay=0.0001、seed=2026、threads=2、MSE 损失、工况平衡有放回采样。",
              "每轮抽样数等于全部训练窗口数。输出默认 results/ti_qat_时间戳；显式 --output-dir 必须是新目录。",
              "量化验证成功不等于板上验证：本入口不运行 NNC，也不确认闭环稳定性或 ISR 耗时，ti_npu_ready 始终为 false。",
              "2026-10-31：自动说明改为实际选优集合，并在复现命令中显式指定标签目录。",
              "本次说明生成代码的修改前备份为 backups/20261031_220015_before_ti500_delivery；原网络适配备份为 backups/20261031_204055_before_ti_npu_network。",
              "恢复旧代码前先备份当前版本；恢复源码不会恢复训练/量化结果。原始 MAT 数据不受影响。", ""]
    if report.get("model_backend") == "ti_npu_fullconv":
        lines += ["2026-11-01：支持全卷积 core / contract v3。修改前备份：backups/20261101_210628_before_ti_npu_fullconv。",
                  "TI1.5默认将无ReLU的1×1卷积输出裁剪到[-512,511]；项目在每次转换副本中显式改为硬件signed8的[-128,127]，之后才选优和导出。依赖包文件未修改。",
                  "官方QAT末层observer的中心化端点可能与硬件端点相差一码；不能宣称训练假量化与部署逐位相同，最终指标以适配后的转换模型为准。",
                  "QAT成功不证明硬件映射；下一步必须通过全卷积专用NNC审计，任何CPU网络层回退均失败。输入输出转换和运行库调度开销单列，不能声称CPU零占用。", ""]
    (directory / "README_CN.md").write_text("\n".join(lines), encoding="utf-8")


def constrain_fullconv_output_int8(converted):
    """TI 1.5 将无 ReLU 的 1x1 卷积按残差分支生成10位输出，显式约束为硬件signed8。

    这是项目内、可审计的部署量化适配，不修改第三方包。必须在每轮转换选优前应用，
    不能仅修改最终ONNX，或把改写后的输出宣称与TI默认10位裁剪始终等价。
    """
    from torch import nn
    from tinyml_torchmodelopt.quantization.tinpu.quant_modules import TINPUOffsetScaleShift

    head = getattr(converted.module, "output", None)
    if (not isinstance(head, nn.Sequential) or len(head) != 2
            or not isinstance(head[0], nn.Conv2d) or head[0].kernel_size != (1, 1)
            or head[0].out_channels != 4 or not isinstance(head[1], TINPUOffsetScaleShift)):
        raise ValueError("Unexpected TI fullconv output conversion; signed-int8 adapter refuses unknown graph.")
    if (head[1].quant_min, head[1].quant_max) not in ((-512, 511), (-128, 127)):
        raise ValueError("Unexpected TI output clipping range; re-audit the quantization adapter.")
    head[1].quant_min, head[1].quant_max = -128, 127
    return converted


def converted_copy(wrapper, fullconv=False):
    """只转换副本；不能冻结或替换下一轮还要训练的原 wrapper。"""
    candidate = deepcopy(wrapper).eval().convert().eval()
    return constrain_fullconv_output_int8(candidate) if fullconv else candidate


def initialize_qat_core(core, fullconv=False):
    """复制来源核心，并让硬件对齐的冗余输出从有效通道0初始化。

    FP32 包装器只监督通道0，1..3不是独立任务；从头训练后这些槽可能仍是
    未训练参数。QAT对四槽使用同一个标签，故在副本上同步它们，避免无效槽
    的随机损失影响共享主干。来源权重与有效通道0的FP32函数均保持不变。
    """
    import torch
    from torch import nn

    result = deepcopy(core).cpu().eval()
    if fullconv:
        head = getattr(result, "output", None)
        if (not isinstance(head, nn.Conv2d) or head.out_channels != 4
                or head.kernel_size != (1, 1) or head.bias is None):
            raise ValueError("Unexpected fullconv core output; refusing QAT head synchronization.")
        with torch.no_grad():
            head.weight[1:].copy_(head.weight[:1].expand_as(head.weight[1:]))
            head.bias[1:].copy_(head.bias[:1].expand_as(head.bias[1:]))
    return result


def run_qat(args, directory, report, environment):
    import numpy as np
    import onnx
    import onnxruntime as ort
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, WeightedRandomSampler
    from tinyml_torchmodelopt.quantization import TINPUTinyMLQATFxModule
    from tinyml_torchmodelopt.quantization.common import TinyMLQConfigType
    from .data import NPZWindows, load_case
    from .metrics import evaluate_model
    from .predict import ResidualPredictor
    from .ti_npu_model import pack_input_tensor
    from .export_onnx import deployment_timing_metadata

    class WindowAdapter(nn.Module):
        def __init__(self, core, fullconv=False):
            super().__init__()
            self.core = core
            self.fullconv = fullconv

        def forward(self, x):
            output = self.core(pack_input_tensor(x))
            return output[:, 0, 0, 0].unsqueeze(1) if self.fullconv else output

    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)
    predictor = ResidualPredictor(args.checkpoint, device="cpu")
    fullconv = predictor.backend == "ti_npu_fullconv"
    train_cases = load_calibration_cases(predictor, args.data_dir)
    source_run = predictor.checkpoint["run"]
    manifest = source_run["split_manifest"]
    selection_split = source_run.get("selection_split") or manifest.get("selection_split") or "test"
    if selection_split not in ("val", "test") or not manifest.get(selection_split):
        raise ValueError("QAT requires a nonempty saved val/test split for converted-model selection.")
    selection_cases = [load_case(args.data_dir / name) for name in manifest[selection_split]]
    for case in selection_cases:
        predictor.validate_schema(case.metadata)
    baseline = evaluate_model(predictor.model, selection_cases, predictor.scalers, args.batch_size, "cpu")
    base = NPZWindows(train_cases, predictor.scalers)
    generator = torch.Generator().manual_seed(args.seed)
    sampler = WeightedRandomSampler(torch.as_tensor(base.sample_weights, dtype=torch.double),
                                    len(base), replacement=True, generator=generator)
    loader = DataLoader(base, batch_size=args.batch_size, sampler=sampler, num_workers=0, generator=generator)
    example = pack_input_tensor(torch.from_numpy(predictor.scalers.transform_x(train_cases[0].X[:1])))
    qconfig = TinyMLQConfigType(weight_bitwidth=8, activation_bitwidth=8, auto_quantization=False)
    wrapper = TINPUTinyMLQATFxModule(initialize_qat_core(predictor.model.core, fullconv), example_inputs=example,
                                    qconfig_type=qconfig, total_epochs=args.epochs,
                                    output_int=False, verbose=False)
    optimizer = torch.optim.AdamW(wrapper.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    criterion = nn.MSELoss()
    checkpoint = args.checkpoint.resolve()
    report.update({"checkpoint": str(checkpoint), "checkpoint_sha256": _sha256(checkpoint),
                   "model_source_sha256": source_run["model_source_sha256"], "qat_script_sha256": _sha256(__file__),
                   "model_backend": predictor.backend, "method": "QAT", "quantization": "TI_TINPU_QAT_8bit",
                   "weight_bits": 8, "activation_bits": 8, "auto_quantization": False, "output_int": False,
                   "redundant_output_initialization": ("copy_effective_channel_0_on_qat_clone" if fullconv else "not_applicable"),
                   "source_checkpoint_modified": False,
                   "scalers_refit": False, "training_case_ids": [case.case_id for case in train_cases],
                   "calibration_case_ids": [case.case_id for case in train_cases], "calibration_only": False,
                   "calibration_samples": len(base), "training_samples_per_epoch": len(base),
                   "heldout_arrays_loaded": True, "heldout_used_for_training": False,
                   "heldout_used_for_calibration": False, "selection_case_ids": [case.case_id for case in selection_cases],
                   "selection_split": selection_split, "test_used_for_selection": selection_split == "test",
                   "independent_test_result": False, "source_fp32_selection_metrics": baseline,
                   "source_fp32_macro_rmse_V_per_s": baseline["macro_rmse_V_per_s"],
                   "training": {"epochs": args.epochs, "lr": args.lr, "batch_size": args.batch_size,
                                "weight_decay": args.weight_decay, "seed": args.seed, "threads": args.threads,
                                "loss": "mse", "sampling": "case_balanced_with_replacement", "gradient_clip_norm": 1.0},
                   "train_files": [{"name": case.path.name, "sha256": _sha256(case.path), "samples": len(case.X)} for case in train_cases],
                   "selection_files": [{"name": case.path.name, "sha256": _sha256(case.path), "samples": len(case.X)} for case in selection_cases]})
    _json(directory / "config.json", report)
    _write_readme(directory, environment, report)
    history, best_score, best_converted = [], float("inf"), None
    best_state_path = directory / "best_qat_state.pt"
    for epoch in range(1, args.epochs + 1):
        start_time = time.perf_counter()
        wrapper.train()
        loss_sum, sample_count = 0.0, 0
        for x, y, _ in loader:
            optimizer.zero_grad(set_to_none=True)
            prediction = wrapper(pack_input_tensor(x))
            target = y[:, :, None, None].expand(-1, 4, 1, 1) if fullconv else y
            loss = criterion(prediction, target)
            if not torch.isfinite(loss):
                raise RuntimeError("Nonfinite QAT training loss.")
            loss.backward()
            nn.utils.clip_grad_norm_(wrapper.parameters(), 1.0, error_if_nonfinite=True)
            optimizer.step()
            loss_sum += float(loss.detach()) * len(x)
            sample_count += len(x)
        candidate = converted_copy(wrapper, fullconv)
        selection = evaluate_model(WindowAdapter(candidate, fullconv), selection_cases, predictor.scalers, args.batch_size, "cpu")
        selection.update({"split": selection_split, "role": "converted_quantized_model_selection",
                          "used_for_checkpoint_selection": True, "independent_test_result": False})
        score = selection["macro_rmse_V_per_s"]
        if not np.isfinite(score):
            raise RuntimeError("Nonfinite converted QAT selection score.")
        record = {"epoch": epoch, "train_loss_normalized": loss_sum / sample_count,
                  "sample_draws": sample_count, "selection_metrics": selection,
                  "ti_num_epochs_tracked": int(wrapper.num_epochs_tracked),
                  "seconds": time.perf_counter() - start_time}
        history.append(record)
        report["epochs_completed"] = epoch
        if score < best_score:
            best_score, best_converted = score, candidate
            report.update({"best_epoch": epoch, "best_macro_rmse_V_per_s": score,
                           "selection_metrics": selection})
            # 独立格式，明确这是官方 QAT wrapper 状态，不伪装原 FP32 checkpoint。
            torch.save({"qat_checkpoint_version": 1, "checkpoint_kind": "TI_TINPU_QAT_WRAPPER_STATE",
                        "qat_wrapper_state_dict": wrapper.state_dict(), "epoch": epoch,
                        "model_config": predictor.checkpoint["model_config"], "model_backend": predictor.backend,
                        "scalers": predictor.scalers.to_dict(), "data_schema": predictor.schema,
                        "training": report["training"], "selection_metrics": selection,
                        "source_checkpoint": str(checkpoint), "source_checkpoint_sha256": report["checkpoint_sha256"],
                        "model_source_sha256": report["model_source_sha256"], "ti_version": "1.5.0"}, best_state_path)
        _json(directory / "history.json", history)
        _json(directory / "quantization_report.json", report)
        print(f"epoch={epoch} loss={record['train_loss_normalized']:.6f} converted_selection_macro_RMSE={score:.3f} V/s elapsed={record['seconds']:.2f}s", flush=True)
    report.update({"qat_checkpoint": str(best_state_path.resolve()), "qat_checkpoint_sha256": _sha256(best_state_path)})
    if fullconv:
        report["terminal_quantization_adapter"] = {
            "version": "fullconv_signed_int8_v1", "ti_default_clip": [-512, 511],
            "deployment_clip": [-128, 127], "applied_before_each_selection_and_export": True,
            "third_party_files_modified": False,
            "note": "TI1.5 residual-branch 1x1 default is10-bit; project constrains regression head to hardware signed8. Accuracy is evaluated after this change."}
    contract = {"contract_version": 3 if fullconv else 2, "model_backend": predictor.backend, "input_name": "normalized_window",
                "output_name": "normalized_residual", "input_shape": [1, 12, predictor.config.seq_len, 1],
                "output_shape": [1, 4, 1, 1] if fullconv else [1, 1], "input_dtype": "float32", "output_dtype": "float32", "input_layout": "NCHW",
                "raw_window_shape": [predictor.config.seq_len, 9], "padded_channels": 12,
                "input_is_normalized": True, "output_is_normalized": True, "output_int": False,
                "scalers": predictor.scalers.to_dict(), "data_schema": predictor.schema,
                "checkpoint": str(checkpoint), "checkpoint_sha256": report["checkpoint_sha256"],
                "model_source_sha256": report["model_source_sha256"], "qat_checkpoint": report["qat_checkpoint"],
                "qat_checkpoint_sha256": report["qat_checkpoint_sha256"], "quantization": "TI_TINPU_QAT_8bit",
                "target_board": "LAUNCHXL-F28P55X", "ti_npu_ready": False}
    contract.update(deployment_timing_metadata(predictor.schema))
    if fullconv:
        contract.update({"effective_output_channel": 0, "packed_output_channels": 4, "output_layout": "NCHW",
                         "network_execution_requirement": "all_layers_on_npu",
                         "terminal_quantization_adapter": "fullconv_signed_int8_v1",
                         "terminal_quantized_range": [-128, 127]})
    model_path = directory / "model_int8.onnx"
    best_converted.export(example, str(model_path), input_names=[contract["input_name"]],
                          output_names=[contract["output_name"]], opset_version=17)
    graph = onnx.load(model_path)
    if fullconv:
        forbidden = {node.op_type for node in graph.graph.node} & {"Gemm", "MatMul", "Flatten", "Slice", "Gather"}
        if forbidden:
            raise ValueError(f"Full-convolution QAT core contains forbidden operators: {sorted(forbidden)}")
    onnx.helper.set_model_props(graph, {"ndp_tcn_contract": json.dumps(contract, ensure_ascii=False)})
    onnx.checker.check_model(graph)
    onnx.save(graph, model_path)
    _json(directory / "deployment.json", contract)
    options = ort.SessionOptions()
    options.intra_op_num_threads = args.threads
    session = ort.InferenceSession(str(model_path), sess_options=options, providers=["CPUExecutionProvider"])
    inputs, outputs = session.get_inputs(), session.get_outputs()
    if (len(inputs) != 1 or inputs[0].shape != contract["input_shape"] or inputs[0].type != "tensor(float)"
            or inputs[0].name != contract["input_name"] or len(outputs) != 1 or outputs[0].shape != contract["output_shape"]
            or outputs[0].type != "tensor(float)" or outputs[0].name != contract["output_name"]):
        raise ValueError("QAT ONNX does not match the declared fixed float32 I/O contract.")
    normalized = predictor.scalers.transform_x(np.concatenate([case.X for case in selection_cases]))
    packed = pack_input_tensor(torch.from_numpy(normalized))
    with torch.no_grad():
        torch_output = np.concatenate([best_converted(batch).numpy() for batch in packed.split(args.batch_size)])
    ort_output = np.concatenate([session.run([contract["output_name"]],
                                 {contract["input_name"]: value[None]})[0] for value in packed.numpy()])
    if not np.isfinite(ort_output).all() or not np.allclose(torch_output, ort_output, atol=1e-4, rtol=1e-4):
        raise ValueError("Converted QAT torch and ONNX outputs differ beyond normalized atol/rtol=1e-4.")
    scalar_output = ort_output[:, 0, 0, 0, None] if fullconv else ort_output
    residual = predictor.scalers.inverse_y(scalar_output)
    targets = np.concatenate([case.y for case in selection_cases]).astype(np.float64)
    case_ids = np.concatenate([np.full(len(case.X), case.case_id, dtype=np.int64) for case in selection_cases])
    case_metrics = [{"case_id": case.case_id, "sample_count": len(case.X),
                     "rmse_V_per_s": float(np.sqrt(np.mean((residual[case_ids == case.case_id] - case.y)**2)))}
                    for case in selection_cases]
    report.update({"status": "qat_export_verified_on_selection_samples", "onnx_checker_passed": True,
                   "onnx_runtime_verified": True, "verification_samples": len(packed),
                   "verification_scope": "all selection samples; not independent test",
                   "converted_torch_vs_onnx_max_abs_normalized": float(np.max(np.abs(torch_output - ort_output))),
                   "onnx_selection_metrics": {"cases": case_metrics,
                       "macro_rmse_V_per_s": float(np.mean([case["rmse_V_per_s"] for case in case_metrics])),
                       "rmse_V_per_s": float(np.sqrt(np.mean((residual - targets)**2)))},
                   "onnx_sha256": _sha256(model_path), "onnx_nodes": sorted({node.op_type for node in graph.graph.node}),
                   "ti_npu_ready": False, "nnc_compilation_executed": False, "board_execution_verified": False})
    golden = {"normalized_input_nchw": packed.numpy(), "normalized_residual": scalar_output,
              "residual_V_per_s": residual, "target_residual_V_per_s": targets, "case_ids": case_ids}
    if fullconv:
        golden["normalized_output_nchw"] = ort_output
        report["output_contract"] = {"shape": contract["output_shape"], "effective_output_channel": 0,
                                     "training_targets": "same scalar target on all four channels"}
    np.savez_compressed(directory / "golden_vectors.npz", **golden)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--checkpoint", type=Path, required=True)
    result.add_argument("--data-dir", type=Path, default=ROOT / "data/train_example_labeled")
    result.add_argument("--epochs", type=int, default=10)
    result.add_argument("--lr", type=float, default=1e-4)
    result.add_argument("--batch-size", type=int, default=128)
    result.add_argument("--weight-decay", type=float, default=1e-4)
    result.add_argument("--seed", type=int, default=2026)
    result.add_argument("--threads", type=int, default=2)
    result.add_argument("--ti-wheel", type=Path)
    result.add_argument("--output-dir", type=Path, default=None)
    return result


def main(argv=None):
    import math

    argument_parser = parser()
    args = argument_parser.parse_args(argv)
    if (min(args.epochs, args.batch_size, args.threads) < 1 or not math.isfinite(args.lr) or args.lr <= 0
            or not math.isfinite(args.weight_decay) or args.weight_decay < 0):
        argument_parser.error("epochs, batch-size, threads, lr must be positive; weight-decay finite and nonnegative.")
    environment = check_environment(args.ti_wheel)
    directory = create_run_directory(args.output_dir, prefix="ti_qat")
    report = {"created_at": now_singapore().isoformat(timespec="seconds"), "ti_npu_ready": False,
              "data_directory": str(args.data_dir.resolve()),
              "status": "qat_in_progress" if environment["ptq_environment_ready"] else "blocked_environment"}
    _json(directory / "environment.json", environment)
    _json(directory / "quantization_report.json", report)
    _write_readme(directory, environment, report)
    print(f"Output directory: {directory}", flush=True)
    if not environment["ptq_environment_ready"]:
        print("TI QAT dependency check failed; no training started.")
        return 2
    try:
        run_qat(args, directory, report, environment)
    except Exception as exc:
        report.update({"status": "qat_failed", "error": f"{type(exc).__name__}: {exc}",
                       "error_traceback": traceback.format_exc()})
        print(report["error"], file=sys.stderr)
        code = 1
    else:
        print(f"Saved best QAT epoch {report['best_epoch']}; selection macro RMSE={report['best_macro_rmse_V_per_s']:.3f} V/s.")
        code = 0
    _json(directory / "quantization_report.json", report)
    _write_readme(directory, environment, report)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
