"""将旧 TI CNN 的两层全连接等价转换为卷积；不重新训练、不修改原数据。"""
import argparse
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from .export_onnx import _verification_cases, comparison_metrics
from .model import model_source
from .outputs import create_run_directory, now_singapore
from .predict import ResidualPredictor
from .ti_npu_fullconv_model import convert_legacy_model


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def convert(args):
    if (args.batch_size < 1 or args.threads < 1 or not np.isfinite(args.atol)
            or not np.isfinite(args.rtol) or min(args.atol, args.rtol) < 0):
        raise ValueError("Positive batch-size/threads and finite nonnegative tolerances are required.")
    torch.set_num_threads(args.threads)
    predictor = ResidualPredictor(args.checkpoint, device="cpu")
    if predictor.backend != "ti_npu":
        raise ValueError("Only an original ti_npu FP32 checkpoint can be converted.")
    selection, cases = _verification_cases(predictor, args)
    candidate = convert_legacy_model(predictor.model).eval()
    directory = create_run_directory(args.output_dir, prefix="convert_ti_npu_fullconv")
    print(f"Output directory: {directory}", flush=True)
    source = args.checkpoint.resolve()
    report = {"created_at": now_singapore().isoformat(timespec="seconds"), "status": "in_progress",
        "operation": "FP32 equivalent FC-to-Conv weight conversion; no retraining",
        "model_backend": "ti_npu_fullconv", "source_checkpoint": str(source),
        "source_checkpoint_sha256": _sha256(source),
        "source_model_sha256": predictor.checkpoint["run"]["model_source_sha256"],
        "model_source_sha256": _sha256(model_source("ti_npu_fullconv")),
        "conversion_script_sha256": _sha256(__file__), "source_epoch": predictor.checkpoint.get("epoch"),
        "epochs_trained": 0, "scalers_refit": False, "physical_features_changed": False,
        "verification_split": selection, "verification_samples": sum(len(c.X) for c in cases),
        "independent_test_result": False, "atol_V_per_s": args.atol, "rtol": args.rtol,
        "core_input_shape": [1, 12, candidate.config.seq_len, 1], "core_output_shape": [1, 4, 1, 1],
        "effective_output_channel": 0, "output_channel_initialization": "four copies of original scalar output",
        "npu_hardware_mapping_verified": False, "board_execution_verified": False, "ti_npu_ready": False,
        "verification_files": [{"path": str(c.path), "sha256": _sha256(c.path), "case_id": c.case_id,
                                "sample_count": len(c.X)} for c in cases]}
    _json(directory / "conversion_report.json", report)
    try:
        references, converted, case_metrics = [], [], []
        with torch.inference_mode():
            for case in cases:
                inputs = predictor.scalers.transform_x(case.X)
                old_parts, new_parts = [], []
                for start in range(0, len(inputs), args.batch_size):
                    tensor = torch.from_numpy(inputs[start:start+args.batch_size])
                    old_parts.append(predictor.model(tensor).numpy())
                    new_parts.append(candidate(tensor).numpy())
                old = predictor.scalers.inverse_y(np.concatenate(old_parts))
                new = predictor.scalers.inverse_y(np.concatenate(new_parts))
                references.append(old)
                converted.append(new)
                case_metrics.append({"case_id": case.case_id, "sample_count": len(old),
                    "source_rmse_V_per_s": float(np.sqrt(np.mean((old-case.y)**2))),
                    "converted_rmse_V_per_s": float(np.sqrt(np.mean((new-case.y)**2))),
                    "comparison": comparison_metrics(old, new, args.atol, args.rtol)})
        check = comparison_metrics(np.concatenate(references), np.concatenate(converted), args.atol, args.rtol)
        report.update({"comparison": check, "cases": case_metrics,
            "source_macro_rmse_V_per_s": float(np.mean([c["source_rmse_V_per_s"] for c in case_metrics])),
            "converted_macro_rmse_V_per_s": float(np.mean([c["converted_rmse_V_per_s"] for c in case_metrics]))})
        if not check["passed"]:
            raise ValueError("FC-to-Conv conversion exceeded the physical-unit equivalence tolerance.")
        checkpoint = deepcopy(predictor.checkpoint)
        run = checkpoint["run"]
        # Keep source training provenance and data identity; this directory is a conversion, not a training run.
        source_run = deepcopy(run)
        run.update({"created_at": report["created_at"], "output_timezone": "Asia/Singapore",
            "output_directory": str(directory), "model_backend": "ti_npu_fullconv",
            "model_config": asdict(candidate.config), "model_source_sha256": report["model_source_sha256"],
            "parameter_count": sum(p.numel() for p in candidate.parameters()), "operation": report["operation"],
            "epochs_trained_in_this_run": 0, "source_training_created_at": source_run.get("created_at"),
            "source_checkpoint": str(source), "source_checkpoint_sha256": report["source_checkpoint_sha256"],
            "source_training_run": source_run, "conversion_report": "conversion_report.json"})
        checkpoint.update({"model_backend": "ti_npu_fullconv", "model_config": asdict(candidate.config),
            "model_state_dict": candidate.state_dict(), "conversion": {"operation": report["operation"],
                "source_checkpoint": str(source), "source_checkpoint_sha256": report["source_checkpoint_sha256"],
                "created_at": report["created_at"]}})
        target = directory / "best.pt"
        torch.save(checkpoint, target)
        # Exercise the public hash/schema/state loader before declaring success.
        reloaded = ResidualPredictor(target)
        with torch.inference_mode():
            sample = torch.from_numpy(predictor.scalers.transform_x(cases[0].X[:args.batch_size]))
            torch.testing.assert_close(candidate(sample), reloaded.model(sample), rtol=0, atol=0)
        _json(directory / "config.json", run)
        _json(directory / "scalers.json", predictor.scalers.to_dict())
        report.update({"status": "fp32_equivalence_verified", "checkpoint": str(target),
                       "checkpoint_sha256": _sha256(target), "public_predictor_reload_verified": True})
    except Exception as exc:
        report.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
        raise
    finally:
        _json(directory / "conversion_report.json", report)
        lines = ["# TI 全卷积权重转换记录", "", f"时间：{report['created_at']}（Asia/Singapore）。",
            f"状态：`{report['status']}`。", "本目录执行等价权重转换，没有重新训练；转换时间不是原训练时间。",
            f"原始权重：`{source}`；原始训练轮次：{report['source_epoch']}。", "",
            "## 网络与输入输出", "",
            "保留原始九路 Vo、ILA、ILB、ILC、ILD、VREF、IREF、z2、Vin；没有新增物理特征。",
            f"历史长度 {candidate.config.seq_len}；标签、每相 IREF、b0、预测步长和 scaler 沿用原 checkpoint。",
            "原 Flatten/FC 隐藏层改为覆盖剩余时间位置的卷积，末层改为 1×1 卷积。",
            "部署 core 接收 [1,12,L,1]，输出 [1,4,1,1]；四通道初始均复制原输出，有效通道为0。",
            "PC 训练/推理包装层读取通道0，部署图直接输出全部四路，不包含 Slice/Gather/Flatten。",
            "其他输出槽仅用于满足通道对齐，后续训练不保证其与第0路相同；使用时只读有效通道。", "",
            "## 验证与限制", "",
            f"验证集合：{selection}；真实窗口数：{report['verification_samples']}。",
            f"物理量容差：atol={args.atol} V/s，rtol={args.rtol}。",
            f"等价性结果：`{json.dumps(report.get('comparison', {}), ensure_ascii=False)}`。",
            "验证沿用原选优集合，不属于独立测试。保留了原数据身份、划分、scaler 和源 checkpoint 哈希。",
            "FP32 等价不证明 INT8 等价、NPU 全层硬件映射或板端实时性；必须在本部署结构上量化并检查生成代码。", "",
            "## 复现", "", "在 E:/bisai 的 TCN 环境中执行：", "", "```text",
            f'python -m ndp_tcn.convert_fullconv --checkpoint "{source.as_posix()}" --data-dir "{args.data_dir.resolve().as_posix()}"',
            "```", "默认 batch-size=256、threads=2、atol=0.05 V/s、rtol=1e-5；输出自动创建 UTC+08 时间戳目录。",
            "源权重、MAT 和历史结果均未覆盖；代码备份和恢复说明见根 README_CN.md。",
            "2026-11-01：新增全卷积等价转换与原始九通道兼容接口。", ""]
        if report.get("error"):
            lines += [f"本次失败：{report['error']}"]
        (directory / "README_CN.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Converted {report['verification_samples']} windows; max abs difference="
          f"{report['comparison']['max_abs_difference_V_per_s']:.9g} V/s; checkpoint={target}", flush=True)
    return target


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--checkpoint", type=Path, required=True)
    result.add_argument("--data-dir", type=Path, required=True)
    result.add_argument("--verify-npz", type=Path, nargs="+")
    result.add_argument("--output-dir", type=Path, default=None)
    result.add_argument("--batch-size", type=int, default=256)
    result.add_argument("--threads", type=int, default=2)
    result.add_argument("--atol", type=float, default=.05)
    result.add_argument("--rtol", type=float, default=1e-5)
    return result


if __name__ == "__main__":
    convert(parser().parse_args())
