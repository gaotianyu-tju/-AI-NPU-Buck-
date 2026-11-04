"""TI 1.5 官方 PTQ：先检查依赖，只用 checkpoint 的训练工况校准。"""
from __future__ import annotations

import argparse
from copy import deepcopy
from email.parser import Parser
import hashlib
from importlib import metadata as import_metadata
import json
from pathlib import Path
import platform
import sys
import traceback
import zipfile

from .outputs import create_run_directory, now_singapore


ROOT = Path(__file__).resolve().parents[1]
TI_VERSION = "1.5.0"
DEFAULT_WHEEL = ROOT / "tmp/ti_wheels/tinyml_torchmodelopt-1.5.0-py3-none-any.whl"
QUANTIZATION_DOC = "https://software-dl.ti.com/C2000/esd/mcu_ai/user_guide/features/quantization.html"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _installed_version(name):
    try:
        return import_metadata.version(name)
    except import_metadata.PackageNotFoundError:
        return None


def check_environment(wheel_path=None, *, version_lookup=None, marker_environment=None):
    """只检查发行包元数据；不会导入 torch/TI 包，更不会安装或修改依赖。"""
    version_lookup = version_lookup or _installed_version
    env = {"python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
           "python_full_version": platform.python_version()}
    if marker_environment is not None:
        env.update(marker_environment)
    report = {
        "created_at": now_singapore().isoformat(timespec="seconds"),
        "python_executable": sys.executable, "python_version": env["python_full_version"],
        "platform": platform.platform(), "required_ti_version": TI_VERSION,
        "metadata_source": None, "dependencies": [], "errors": [],
        "source_import_dependencies": [],
        "ptq_environment_ready": False, "ti_npu_ready": False,
        "nnc_python_compatible": env["python_version"] == "3.10",
        "nnc_note": "本项目已核对的 TI NNC wheel 为 cp310；此项不是 PTQ 的 Python 限制，也不代表 NNC 已安装或编译通过。",
        "environment_modified": False, "documentation": QUANTIZATION_DOC,
    }
    try:
        from packaging.markers import default_environment
        from packaging.requirements import Requirement
        from packaging.specifiers import SpecifierSet
        from packaging.utils import canonicalize_name

        env = {**default_environment(), **env}
        selected_wheel = Path(wheel_path) if wheel_path is not None else DEFAULT_WHEEL
        if selected_wheel.is_file():
            with zipfile.ZipFile(selected_wheel) as archive:
                names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
                if len(names) != 1:
                    raise ValueError("TI wheel must contain exactly one distribution METADATA.")
                package_metadata = Parser().parsestr(archive.read(names[0]).decode("utf-8"))
            report["metadata_source"] = str(selected_wheel.resolve())
            report["metadata_sha256"] = _sha256(selected_wheel)
        elif wheel_path is not None:
            raise FileNotFoundError(f"Metadata wheel does not exist: {selected_wheel}")
        else:
            package_metadata = import_metadata.metadata("tinyml_torchmodelopt")
            report["metadata_source"] = "installed:tinyml_torchmodelopt"
        if (canonicalize_name(package_metadata.get("Name", "")) != "tinyml-torchmodelopt"
                or package_metadata.get("Version") != TI_VERSION):
            raise ValueError("This entry supports official tinyml_torchmodelopt 1.5.0 metadata only.")
        requires_python = package_metadata.get("Requires-Python")
        requirements = package_metadata.get_all("Requires-Dist") or []
        if not requires_python or not requirements:
            raise ValueError("TI metadata is missing Requires-Python or Requires-Dist.")
        report["requires_python"] = requires_python
        if not SpecifierSet(requires_python).contains(env["python_full_version"], prereleases=True):
            report["errors"].append(f"Python {env['python_full_version']} does not satisfy {requires_python}.")
        package_version = version_lookup("tinyml_torchmodelopt")
        report["installed_ti_version"] = package_version
        if package_version != TI_VERSION:
            report["errors"].append(f"tinyml_torchmodelopt requires {TI_VERSION}; installed: {package_version or 'missing'}.")
        for text in requirements:
            requirement = Requirement(text)
            active = requirement.marker is None or requirement.marker.evaluate(env)
            installed = version_lookup(requirement.name) if active else None
            matches = active and installed is not None and requirement.specifier.contains(installed, prereleases=True)
            status = "matched" if matches else ("inactive_marker" if not active else ("missing" if installed is None else "incompatible"))
            report["dependencies"].append({"requirement": text, "name": requirement.name,
                                           "installed": installed, "status": status})
            if active and not matches:
                report["errors"].append(f"{requirement.name}{requirement.specifier}; installed: {installed or 'missing'}.")
        # 1.5.0 METADATA 漏列 tabulate；真实源码 auto_quantization.py 在导入时直接使用它。
        tabulate_version = version_lookup("tabulate")
        report["source_import_dependencies"].append({"name": "tabulate", "installed": tabulate_version,
            "status": "present" if tabulate_version else "missing",
            "source": "tinyml_torchmodelopt/quantization/base/fx/auto_quantization.py: from tabulate import tabulate",
            "version_pin_declared_by_ti_metadata": False})
        if tabulate_version is None:
            report["errors"].append("tabulate is missing; TI 1.5.0 source imports it but its METADATA omits the dependency.")
    except Exception as exc:
        report["errors"].append(f"Metadata inspection failed: {type(exc).__name__}: {exc}")
    report["ptq_environment_ready"] = not report["errors"]
    return report


def load_calibration_cases(predictor, data_dir):
    """校验完整清单身份，但只解压 train 的数组，绝不把 val/test 用于校准。"""
    from .data import load_splits, read_case_metadata

    if predictor.backend not in ("ti_npu", "ti_npu_fullconv"):
        raise ValueError("TI calibration requires backend=ti_npu or backend=ti_npu_fullconv.")
    run = predictor.checkpoint.get("run", {})
    manifest = run.get("split_manifest")
    identities = run.get("data_identity")
    if not isinstance(manifest, dict) or not isinstance(identities, dict):
        raise ValueError("Checkpoint must contain the original split manifest and data identities.")
    for split in ("train", "val", "test"):
        if not isinstance(manifest.get(split), list):
            raise ValueError(f"Missing checkpoint split: {split}.")
    # load_splits 平时也读取 val；这里将所有留出工况放入仅检查元数据的 test 槽。
    calibration_manifest = {"train": list(manifest["train"]), "val": [],
                            "test": list(manifest["val"]) + list(manifest["test"])}
    cases = load_splits(data_dir, calibration_manifest, include_test=False)["train"]
    root = Path(data_dir).resolve()
    for name in manifest["train"] + manifest["val"] + manifest["test"]:
        current = read_case_metadata(root / name)
        predictor.validate_schema(current)
        expected = identities.get(name)
        if expected != {"case_id": current["case_id"], "source_sha256": current["source_sha256"]}:
            raise ValueError(f"Calibration source differs from checkpoint identity: {name}.")
    case_ids = [case.case_id for case in cases]
    if sorted(case_ids) != sorted(predictor.scalers.fit_case_ids):
        raise ValueError("Calibration cases must exactly match the training cases used to fit saved scalers.")
    return cases


def _write_readme(directory, environment, report):
    lines = ["# TI PTQ / 环境诊断记录", "", f"生成时间：{report['created_at']}（UTC+08:00）。",
             f"状态：`{report['status']}`。", "", "## 本次行为", "",
             "先按 TI 1.5.0 wheel 或已安装发行包的 METADATA 检查 Python 和所有当前适用依赖。",
             "本入口不安装、卸载或降级环境。诊断失败时不会加载 checkpoint、校准或导出 INT8 模型。",
             "另检查 TI 1.5 源码直接导入、但其 METADATA 漏列的 tabulate；官方未提供该项版本约束。",
             "`environment.json` 保存解释器、依赖条件、安装版本及失败原因。", "",
             f"- Python：`{environment['python_executable']}` / `{environment['python_version']}`。",
             f"- PTQ 依赖满足：`{environment['ptq_environment_ready']}`。",
             "- `ti_npu_ready=false`：本入口不运行 TI NNC 编译，也不代表板上已运行。", ""]
    if environment["errors"]:
        lines += ["## 尚未满足的条件", ""] + [f"- {error}" for error in environment["errors"]] + [""]
    lines += ["## 量化约定", "",
              "仅接受 `ti_npu` checkpoint。使用其中保存的 train 清单和 scaler，校准只读训练工况数组；",
              "val/test 只读元数据检查身份，不参与 observer 校准，也不重新拟合标准化。",
              "9 通道顺序为 Vo、ILA、ILB、ILC、ILD、VREF、IREF、z2、Vin。",
              "原始窗口 `[B,L,9]` 先标准化，再转 `[B,12,L,1]`；后三通道为标准化后的 0。",
              "TI PTQ 使用 8-bit 权重、8-bit 激活，auto_quantization=False；eval/no_grad 校准后 convert/export。",
              "`output_int=False` 使 ONNX 输出归一化浮点残差；物理残差只计算一次 `y*y_scale+y_mean`（V/s）。",
              "未来扰动为末拍原始 z2 加物理残差；本入口不生成控制指令。",
              "量化后的 PC 数值验证只比较训练工况抽样，不是独立测试性能或板端时序验证。", ""]
    if report.get("checkpoint"):
        lines += [f"来源 checkpoint：`{report['checkpoint']}`。",
                  f"校准工况：`{report.get('calibration_case_ids', [])}`；样本数：`{report.get('calibration_samples', 0)}`。", ""]
    if report.get("error"):
        lines += [f"本次错误：`{report['error']}`。中断后的候选文件不视为已验证模型。", ""]
    if report["status"] == "ptq_export_verified_on_calibration_samples":
        lines += ["本次已完成官方 PTQ、ONNX checker 和 ONNX Runtime 数值验证；详见 `quantization_report.json`。",
                  "`model_int8.onnx` 是 TI 量化表达图，仍需 TI NNC 编译、检查 CPU 回退以及板上数值/耗时验证。",
                  "`deployment.json` 保存输入输出约定，`golden_vectors.npz` 保存 PC 抽样验证向量。", ""]
    else:
        lines += ["本次尚未完成 TI PTQ 导出/编译/板上运行；环境诊断成功也只表示可以尝试运行。", ""]
    lines += ["## 可复制命令", "", "在 E:\\bisai 的 VS Code Python 环境终端执行：", "", "```text",
              "python -m ndp_tcn.ti_quantize --check-environment",
              "python -m ndp_tcn.ti_quantize --checkpoint ndp_tcn/results/<本次训练目录>/best.pt", "```", "",
              "默认 data-dir=data/train_example_labeled，batch-size=128，threads=2，verification-samples=256。",
              "默认结果使用 results/ti_environment_时间戳 或 results/ti_ptq_时间戳；显式 --output-dir 必须是新目录。",
              f"API 来源：[TI 官方 1.5 量化文档]({QUANTIZATION_DOC}) 及本次 environment.json 指定的 wheel 源码。",
              "代码备份：`backups/20261031_204055_before_ti_npu_network`；该入口为首次新增，旧代码备份清单中记录为新增文件。",
              "恢复前先备份当前代码，再按原备份清单恢复；恢复源码不恢复训练权重或量化结果。", ""]
    (directory / "README_CN.md").write_text("\n".join(lines), encoding="utf-8")


def run_ptq(args, directory, report):
    """仅在严格依赖检查通过后进入。此处使用官方 TI wrapper，不替代或仿造量化。"""
    import numpy as np
    import onnx
    import onnxruntime as ort
    import torch
    from tinyml_torchmodelopt.quantization import TINPUTinyMLPTQFxModule
    from tinyml_torchmodelopt.quantization.common import TinyMLQConfigType
    from .predict import ResidualPredictor
    from .ti_npu_model import pack_input_tensor

    torch.set_num_threads(args.threads)
    predictor = ResidualPredictor(args.checkpoint, device="cpu")
    if predictor.backend != "ti_npu":
        raise ValueError("For ti_npu_fullconv use ndp_tcn.ti_qat; this legacy PTQ export has a scalar output contract.")
    cases = load_calibration_cases(predictor, args.data_dir)
    checkpoint = args.checkpoint.resolve()
    report.update({"checkpoint": str(checkpoint), "checkpoint_sha256": _sha256(checkpoint),
                   "model_source_sha256": predictor.checkpoint["run"]["model_source_sha256"],
                   "quantize_script_sha256": _sha256(__file__), "model_backend": "ti_npu",
                   "calibration_case_ids": [case.case_id for case in cases],
                   "calibration_samples": sum(len(case.X) for case in cases),
                   "calibration_files": [{"name": case.path.name, "sha256": _sha256(case.path),
                                          "samples": len(case.X)} for case in cases],
                   "weight_bits": 8, "activation_bits": 8, "auto_quantization": False,
                   "output_int": False, "scalers_refit": False, "heldout_arrays_loaded": False})
    normalized_cases = [torch.from_numpy(predictor.scalers.transform_x(case.X)) for case in cases]
    example = pack_input_tensor(normalized_cases[0][:1])
    # 保留训练得到的 BN，由官方 FX prepare 完成卷积/BN 融合。
    fp32_core = deepcopy(predictor.model.core).cpu().eval()
    qconfig = TinyMLQConfigType(weight_bitwidth=8, activation_bitwidth=8, auto_quantization=False)
    quantized = TINPUTinyMLPTQFxModule(deepcopy(fp32_core), example_inputs=example,
                    qconfig_type=qconfig, total_epochs=1, output_int=False, verbose=False)
    quantized.eval()
    with torch.no_grad():
        for values in normalized_cases:
            for start in range(0, len(values), args.batch_size):
                quantized(pack_input_tensor(values[start:start + args.batch_size]))
    quantized = quantized.convert().eval()
    contract = {"contract_version": 2, "model_backend": "ti_npu", "input_name": "normalized_window",
                "output_name": "normalized_residual", "input_shape": [1, 12, predictor.config.seq_len, 1],
                "output_shape": [1, 1], "input_dtype": "float32", "output_dtype": "float32",
                "input_layout": "NCHW", "raw_window_shape": [predictor.config.seq_len, 9],
                "padded_channels": 12, "input_is_normalized": True, "output_is_normalized": True,
                "scalers": predictor.scalers.to_dict(), "data_schema": predictor.schema,
                "checkpoint": str(checkpoint), "checkpoint_sha256": report["checkpoint_sha256"],
                "model_source_sha256": report["model_source_sha256"],
                "target_board": "LAUNCHXL-F28P55X", "ti_npu_ready": False,
                "quantization": "TI_TINPU_PTQ_8bit", "output_int": False}
    model_path = directory / "model_int8.onnx"
    quantized.export(example, str(model_path), input_names=[contract["input_name"]],
                     output_names=[contract["output_name"]], opset_version=17)
    graph = onnx.load(model_path)
    onnx.helper.set_model_props(graph, {"ndp_tcn_contract": json.dumps(contract, ensure_ascii=False)})
    onnx.checker.check_model(graph)
    onnx.save(graph, model_path)
    _json(directory / "deployment.json", contract)
    options = ort.SessionOptions()
    options.intra_op_num_threads = args.threads
    session = ort.InferenceSession(str(model_path), sess_options=options, providers=["CPUExecutionProvider"])
    inputs, outputs = session.get_inputs(), session.get_outputs()
    if (len(inputs) != 1 or inputs[0].shape != contract["input_shape"] or inputs[0].type != "tensor(float)"
            or inputs[0].name != contract["input_name"] or len(outputs) != 1
            or outputs[0].shape != [1, 1] or outputs[0].type != "tensor(float)"
            or outputs[0].name != contract["output_name"]):
        raise ValueError("TI quantized export does not match the fixed float input/output contract.")
    all_windows = torch.cat(normalized_cases)
    count = min(args.verification_samples, len(all_windows))
    selected_indices = np.unique(np.linspace(0, len(all_windows) - 1, count, dtype=np.int64))
    packed = pack_input_tensor(all_windows[selected_indices])
    with torch.no_grad():
        fp32_normalized = fp32_core(packed).numpy()
        quantized_normalized = quantized(packed).numpy()
    onnx_normalized = np.concatenate([session.run([contract["output_name"]],
                         {contract["input_name"]: value[None]})[0] for value in packed.numpy()])
    if not all(np.isfinite(values).all() for values in (fp32_normalized, quantized_normalized, onnx_normalized)):
        raise ValueError("Nonfinite output during TI PTQ verification.")
    if not np.allclose(quantized_normalized, onnx_normalized, rtol=1e-4, atol=1e-4):
        raise ValueError("Converted TI torch and ONNX outputs disagree beyond normalized atol/rtol=1e-4.")
    # output_int=False 已还原量化尺度，这里只还原一次训练标签标准化。
    fp32_physical = predictor.scalers.inverse_y(fp32_normalized)
    onnx_physical = predictor.scalers.inverse_y(onnx_normalized)
    difference = onnx_physical - fp32_physical
    report.update({"status": "ptq_export_verified_on_calibration_samples", "onnx_checker_passed": True,
                   "onnx_runtime_verified": True, "verification_samples": len(selected_indices),
                   "verification_scope": "training calibration samples only; not heldout evaluation",
                   "converted_torch_vs_onnx_max_abs_normalized": float(np.max(np.abs(quantized_normalized-onnx_normalized))),
                   "ptq_vs_fp32_rmse_V_per_s": float(np.sqrt(np.mean(difference**2))),
                   "ptq_vs_fp32_max_abs_V_per_s": float(np.max(np.abs(difference))),
                   "onnx_sha256": _sha256(model_path), "onnx_nodes": sorted({node.op_type for node in graph.graph.node}),
                   "ti_npu_ready": False, "nnc_compilation_executed": False, "board_execution_verified": False})
    np.savez_compressed(directory / "golden_vectors.npz", normalized_input_nchw=packed.numpy(),
                        normalized_residual=onnx_normalized, residual_V_per_s=onnx_physical,
                        fp32_residual_V_per_s=fp32_physical, calibration_indices=selected_indices)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--check-environment", action="store_true", help="只检查依赖；无需 checkpoint；不匹配退出码 2")
    result.add_argument("--checkpoint", type=Path)
    result.add_argument("--data-dir", type=Path, default=ROOT / "data/train_example_labeled")
    result.add_argument("--ti-wheel", type=Path, help="用于核对 METADATA 的官方 1.5.0 wheel；不会安装")
    result.add_argument("--batch-size", type=int, default=128)
    result.add_argument("--threads", type=int, default=2)
    result.add_argument("--verification-samples", type=int, default=256)
    result.add_argument("--output-dir", type=Path, default=None)
    return result


def main(argv=None):
    argument_parser = parser()
    args = argument_parser.parse_args(argv)
    if not args.check_environment and args.checkpoint is None:
        argument_parser.error("--checkpoint is required unless --check-environment is specified.")
    if min(args.batch_size, args.threads, args.verification_samples) < 1:
        argument_parser.error("batch-size, threads and verification-samples must be positive.")
    environment = check_environment(args.ti_wheel)
    directory = create_run_directory(args.output_dir, prefix="ti_environment" if args.check_environment else "ti_ptq")
    report = {"created_at": now_singapore().isoformat(timespec="seconds"), "ti_npu_ready": False,
              "status": "environment_ready" if environment["ptq_environment_ready"] else "blocked_environment"}
    _json(directory / "environment.json", environment)
    _json(directory / "quantization_report.json", report)
    _write_readme(directory, environment, report)
    print(f"Output directory: {directory}", flush=True)
    if not environment["ptq_environment_ready"]:
        print("TI PTQ dependency check failed. No checkpoint loaded or quantized model generated.")
        for error in environment["errors"]:
            print(f"- {error}")
        return 2
    if args.check_environment:
        print("TI PTQ dependency metadata matches. Compilation and board execution are not verified.")
        return 0
    try:
        report["status"] = "ptq_in_progress"
        _json(directory / "quantization_report.json", report)
        run_ptq(args, directory, report)
    except Exception as exc:
        report.update({"status": "ptq_failed", "error": f"{type(exc).__name__}: {exc}",
                       "error_traceback": traceback.format_exc()})
        print(report["error"], file=sys.stderr)
        return_code = 1
    else:
        print("TI PTQ ONNX exported and checked on PC; TI NNC/board validation remains required.")
        return_code = 0
    _json(directory / "quantization_report.json", report)
    _write_readme(directory, environment, report)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
