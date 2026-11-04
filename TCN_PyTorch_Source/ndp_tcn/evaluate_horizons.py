"""按相同源窗口及相同目标区间比较多步长模型；测试集不参与选优。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from scipy.io import loadmat

from .data import load_case, read_case_metadata, paired_group_key, load_family_key
from .metrics import predict_array
from .outputs import create_run_directory, now_singapore
from .predict import ResidualPredictor
from .predict_onnx import OnnxResidualPredictor


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def error_metrics(error):
    error = np.asarray(error, dtype=np.float64).reshape(-1)
    if not len(error) or not np.isfinite(error).all():
        raise ValueError("Metrics require nonempty finite errors.")
    return {"sample_count": len(error), "rmse_V_per_s": float(np.sqrt(np.mean(error**2))),
            "mae_V_per_s": float(np.mean(np.abs(error))),
            "max_abs_error_V_per_s": float(np.max(np.abs(error))),
            "bias_V_per_s": float(np.mean(error))}


def aggregate_metrics(records):
    if not records:
        return {"sample_count": 0, "case_count": 0}
    n = sum(item["sample_count"] for item in records)
    return {"sample_count": n, "case_count": len(records),
            "rmse_V_per_s": float(np.sqrt(sum(item["sample_count"] * item["rmse_V_per_s"]**2 for item in records) / n)),
            "macro_rmse_V_per_s": float(np.mean([item["rmse_V_per_s"] for item in records])),
            "mae_V_per_s": sum(item["sample_count"] * item["mae_V_per_s"] for item in records) / n,
            "max_abs_error_V_per_s": max(item["max_abs_error_V_per_s"] for item in records),
            "bias_V_per_s": sum(item["sample_count"] * item["bias_V_per_s"] for item in records) / n}


def common_indices(arrays):
    """返回每个工况索引数组中的对齐位置；禁止悄悄用截断长度代替时刻对齐。"""
    common = np.asarray(arrays[0])
    for array in arrays:
        if np.asarray(array).ndim != 1 or np.any(np.diff(array) <= 0):
            raise ValueError("Alignment indices must be one-dimensional and strictly increasing.")
        common = np.intersect1d(common, array, assume_unique=True)
    if not len(common):
        raise ValueError("Candidates have no common evaluation indices.")
    return common, [np.searchsorted(array, common) for array in arrays]


def task_transition_index(command, sample_times, task_start_time_s=None):
    """匹配声明任务起点附近的采样边沿，排除上电初始化斜坡。

    返回变化区间j而非变化后样本j+1。元数据时刻可位于区间内部，故连续变化段
    起点允许相差1.5Ts；无匹配则返回None，不能用启动或远处周期边沿替代。
    """
    command = np.asarray(command, dtype=np.float64).reshape(-1)
    times = np.asarray(sample_times, dtype=np.float64).reshape(-1)
    if (times.shape != command.shape or len(times) < 2 or not np.isfinite(times).all()
            or not np.isfinite(command).all() or np.any(np.diff(times) <= 0)):
        raise ValueError("Invalid samples for task-transition matching.")
    tolerance = max(1e-7, float(np.ptp(command)) * 1e-6)
    changes = np.flatnonzero(np.abs(np.diff(command)) > tolerance)
    if not len(changes):
        return None
    starts = changes[np.r_[True, np.diff(changes) > 1]]
    if task_start_time_s is None:
        return int(starts[0])
    if not np.isfinite(task_start_time_s):
        raise ValueError("Task start time must be finite.")
    closest = int(starts[np.argmin(np.abs(times[starts] - task_start_time_s))])
    dt = float(np.median(np.diff(times)))
    return closest if abs(times[closest] - task_start_time_s) <= 1.5 * dt + 1e-12 else None


def event_masks(command, source_indices, target_indices, dt, transient_window_s,
                task_start_time_s=None, sample_times=None):
    """仅离线分组使用仿真负载命令，不将命令或未来信息送入模型。

    变化区间j来自 command[j+1]-command[j]，瞬态窗口从变化区间延续到
    transient_window_s 后。首次任务边沿按声明pulse_start_s匹配，排除启动斜坡；
    未出现在输入的分组采用严格source<edge，边沿区间内的源样本不计入。
    """
    command = np.asarray(command, dtype=np.float64).reshape(-1)
    if not np.isfinite(command).all() or dt <= 0 or transient_window_s < 0:
        raise ValueError("Invalid offline load command or transient window.")
    changes = np.diff(command)
    tolerance = max(1e-7, float(np.ptp(command)) * 1e-6)
    rise = np.flatnonzero(changes > tolerance)
    fall = np.flatnonzero(changes < -tolerance)
    edges = np.sort(np.concatenate([rise, fall]))

    def near(indices):
        if not len(indices):
            return np.zeros(len(target_indices), dtype=bool)
        positions = np.searchsorted(indices, target_indices, side="right") - 1
        previous = indices[np.maximum(positions, 0)]
        return (positions >= 0) & ((target_indices - previous) * dt <= transient_window_s + 1e-12)

    transient = near(edges)
    unseen_first = np.zeros(len(target_indices), dtype=bool)
    times = np.arange(len(command)) * dt if sample_times is None else sample_times
    first = task_transition_index(command, times, task_start_time_s)
    if first is not None:
        unseen_first = ((source_indices < first) & (target_indices >= first)
                        & ((target_indices - first) * dt <= transient_window_s + 1e-12))
    return {"target_transient": transient, "target_steady": ~transient,
            "target_rise_transient": near(rise), "target_fall_transient": near(fall),
            "first_transition_not_yet_in_source": unseen_first}


def case_kind(metadata):
    params = metadata.get("case_parameters", {})
    event = str(params.get("event_type", ""))
    if event.startswith("step"):
        return "single_step"
    if float(params.get("frequency_Hz", 0) or 0) > 0:
        return "periodic_pulse"
    return "constant_load"


def validate_manifest(data_dir, predictor, split):
    run = predictor.checkpoint["run"]
    manifest = run["split_manifest"]
    if split == "test" and (run.get("test_used_for_selection") or run.get("selection_split") == "test"):
        raise ValueError("The named test split was used for selection; it is not independent.")
    used, owners, identities, chosen = set(), {}, {}, {}
    for role in ("train", "val", "test"):
        identities[role] = set()
        for filename in manifest.get(role, []):
            if filename in used:
                raise ValueError("A case filename appears in multiple splits.")
            used.add(filename)
            path = data_dir / filename
            meta = read_case_metadata(path)
            expected = run["data_identity"][filename]
            if meta["case_id"] != expected["case_id"] or meta["source_sha256"] != expected["source_sha256"]:
                raise ValueError(f"Saved case identity differs: {filename}")
            predictor.validate_schema(meta)
            identities[role].add((meta["case_id"], meta["source_sha256"]))
            for kind, key in (("source", meta["source_sha256"]), ("paired", paired_group_key(meta)),
                              ("family", load_family_key(meta))):
                if key is not None:
                    group = (kind, key)
                    if group in owners and owners[group] != role:
                        raise ValueError(f"{kind} leakage between {owners[group]} and {role}.")
                    owners[group] = role
            if role == split:
                if meta["case_id"] in chosen:
                    raise ValueError("Duplicate case IDs in evaluation split.")
                chosen[meta["case_id"]] = path
    if not chosen:
        raise ValueError(f"No cases in {split}.")
    return chosen, identities


def read_physical_reference(case):
    path = Path(case.metadata["source_file"])
    if sha256(path) != case.metadata["source_sha256"]:
        raise ValueError(f"Original MAT hash differs: {path}")
    data = loadmat(path, simplify_cells=True, variable_names=["data"])["data"]
    features = np.asarray(data["features"], dtype=np.float64)
    time = np.asarray(data["time"], dtype=np.float64).reshape(-1)
    command = np.asarray(data["load_current_command_A"], dtype=np.float64).reshape(-1)
    if features.shape != (len(time), 9) or command.shape != time.shape:
        raise ValueError("Original MAT feature/load-command dimensions disagree.")
    f = np.diff(features[:, 0]) / np.diff(time) - case.metadata["b0_per_phase"] * features[:-1, 6]
    return features, time, command, f


def run_comparison(config, directory, split="test", batch_size=512, threads=2, transient_window_ms=1.0):
    torch.set_num_threads(threads)
    specs = config["candidates"]
    if not specs or len({item["name"] for item in specs}) != len(specs):
        raise ValueError("Provide uniquely named candidates.")
    contexts, identities = [], None
    report = {"created_at": now_singapore().isoformat(timespec="seconds"), "split": split,
              "evaluator_source_sha256": sha256(__file__),
              "role": "independent_test" if split == "test" else "validation_comparison",
              "independent_test_result": split == "test", "horizon_choice_performed": False,
              "board_execution_verified": False, "compiled_c_numeric_execution_verified": False,
              "timing_verified": False, "units": "V/s", "transient_window_ms": transient_window_ms,
              "event_mask_version": "declared_task_transition_v2",
              "event_mask_definitions": {
                  "target_transient": "unchanged: within configured window after any sampled load-command change interval, including startup if within evaluation range",
                  "first_transition_not_yet_in_source": "first_task_event selects declared pulse_start_s instead of startup; contiguous command-change segment start within 1.5 Ts; strict source_index < task_edge_interval <= target_index and target within transient window",
                  "source_inside_edge_interval": "excluded conservatively even if exact declared event time is later within that sample interval",
                  "missing_task_edge": "empty subset; never substitute startup or a distant later edge",
                  "correction_scope": "scoring-mask correction only; no model, training, split or horizon selection changed"},
              "alignment_definitions": {
                  "common_target_intervals": "same case and reconstructed target interval j; source k=j-H differs across H",
                  "common_source_windows": "same case and source k/input; each H predicts its own target interval k+H"},
              "baseline_definitions": {
                  "source_eso_hold": "predict residual=0, equivalently f_pred=z2[source]",
                  "target_eso_diagnostic": "recorded z2[target]; available at future application time, NOT a source-time predictor",
                  "quantization_delta": "TI-QAT ONNX prediction minus the selected FP32 prediction, not label error"},
              "limitations": ["TI-QAT ONNX is the numerical reference supplied to the compiler; it is not measured compiled-C/NPU output.",
                              "Labels are reconstructed interval disturbances, not physical ground truth.",
                              "Offline command-based masks are evaluation-only; commands/future measurements are never model inputs.",
                              "An empty first-transition-before-source subset means that capability was not measured, not zero error.",
                              "No closed-loop performance or worst-case board latency is inferred from these errors."],
              "candidates": {}}
    for spec in specs:
        checkpoint = Path(spec["checkpoint"]).resolve()
        predictor = ResidualPredictor(checkpoint)
        data_dir = Path(spec["data_dir"]).resolve()
        paths, membership = validate_manifest(data_dir, predictor, split)
        if identities is not None and membership != identities:
            raise ValueError("Candidate train/val/test source-case memberships differ.")
        identities = membership
        onnx = None
        if spec.get("quantized_dir"):
            qdir = Path(spec["quantized_dir"]).resolve()
            qreport = json.loads((qdir / "quantization_report.json").read_text(encoding="utf-8"))
            if qreport.get("status") != "qat_export_verified_on_selection_samples":
                raise ValueError("QAT export verification did not pass.")
            if split == "test" and qreport.get("test_used_for_selection"):
                raise ValueError("QAT selected on test; independent testing is invalid.")
            onnx = OnnxResidualPredictor(qdir / "model_int8.onnx", threads=threads)
            if sha256(onnx.model_path) != qreport.get("onnx_sha256"):
                raise ValueError("QAT ONNX hash differs from the verified export report.")
            if onnx.contract["checkpoint_sha256"] != sha256(checkpoint):
                raise ValueError("FP32 checkpoint and QAT model are not from the same run.")
            if onnx.contract["scalers"] != predictor.scalers.to_dict() or onnx.schema != predictor.schema:
                raise ValueError("FP32 and QAT schema/scaler identities differ.")
        name = spec["name"]
        if any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in name):
            raise ValueError("Candidate names must be filename-safe ASCII names.")
        report["candidates"][name] = {"horizon_steps": predictor.schema["horizon_steps_to_target_interval_start"],
            "checkpoint": str(checkpoint), "checkpoint_sha256": sha256(checkpoint), "data_dir": str(data_dir),
            "quantized_onnx_sha256": sha256(onnx.model_path) if onnx else None,
            "selection_split": predictor.checkpoint["run"].get("selection_split"),
            "alignments": {kind: {"cases": []} for kind in report["alignment_definitions"]}}
        contexts.append({"name": name, "predictor": predictor, "onnx": onnx, "paths": paths, "saved": []})
    for case_id in sorted(contexts[0]["paths"]):
        cases, loaded = [], []
        for ctx in contexts:
            case = load_case(ctx["paths"][case_id])
            with np.load(case.path, allow_pickle=False) as a:
                k, j = a["source_index"].copy(), a["target_interval_index"].copy()
            ctx["predictor"].validate_schema(case.metadata)
            fp32 = predict_array(ctx["predictor"].model, ctx["predictor"].scalers, case.X, batch_size, "cpu")[:, 0]
            quantized = ctx["onnx"].predict_array(case.X)[:, 0] if ctx["onnx"] else None
            loaded.append({"k": k, "j": j, "fp32": fp32, "ti_qat_onnx": quantized})
            cases.append(case)
        features, time, command, true_f = read_physical_reference(cases[0])
        for case, values in zip(cases, loaded):
            k, j = values["k"], values["j"]
            expected_x = features[k[:, None] + np.arange(-case.seq_len + 1, 1)].astype(np.float32)
            if not np.array_equal(case.X, expected_x):
                raise ValueError("Case windows are not consecutive raw MAT samples.")
            if not np.allclose(case.y[:, 0], true_f[j] - features[k, 7], rtol=1e-6, atol=1e-3):
                raise ValueError("Case label does not reconstruct the declared target interval.")
        for alignment, key in (("common_target_intervals", "j"), ("common_source_windows", "k")):
            common, positions = common_indices([values[key] for values in loaded])
            for ctx, case, values, pos in zip(contexts, cases, loaded, positions):
                k, j = values["k"][pos], values["j"][pos]
                target = case.y[pos, 0].astype(np.float64)
                pred = {"fp32": values["fp32"][pos], "source_eso_hold": np.zeros(len(pos)),
                        "target_eso_diagnostic": features[j, 7] - features[k, 7]}
                if values["ti_qat_onnx"] is not None:
                    pred["ti_qat_onnx"] = values["ti_qat_onnx"][pos]
                errors = {name: array - target for name, array in pred.items()}
                if "ti_qat_onnx" in pred:
                    errors["quantization_delta"] = pred["ti_qat_onnx"] - pred["fp32"]
                task_start = case.metadata.get("case_parameters", {}).get("pulse_start_s")
                masks = event_masks(command, k, j, case.sample_interval, transient_window_ms / 1000,
                                    task_start_time_s=task_start, sample_times=time)
                masks[case_kind(case.metadata)] = np.ones(len(pos), dtype=bool)
                record = {"case_id": case_id, "filename": case.path.name, "case_kind": case_kind(case.metadata),
                          "sample_count": len(pos), "overall": {name: error_metrics(err) for name, err in errors.items()},
                          "groups": {group: {name: error_metrics(err[mask]) for name, err in errors.items()}
                                     for group, mask in masks.items() if np.any(mask)}}
                report["candidates"][ctx["name"]]["alignments"][alignment]["cases"].append(record)
                if alignment == "common_target_intervals":
                    ctx["saved"].append({"case_id": np.full(len(pos), case_id, dtype=np.int64),
                        "source_index": k, "target_interval_index": j,
                        "source_time_s": time[k], "target_start_time_s": time[j],
                        "source_z2_V_per_s": features[k, 7], "target_z2_V_per_s": features[j, 7],
                        "target_disturbance_V_per_s": true_f[j], "target_residual_V_per_s": target,
                        "fp32_residual_V_per_s": pred["fp32"],
                        **({"ti_qat_onnx_residual_V_per_s": pred["ti_qat_onnx"]} if "ti_qat_onnx" in pred else {}),
                        **{name: mask for name, mask in masks.items() if name.startswith("target_") or name.startswith("first_")}})
        print(f"evaluated {split} case {case_id}: " + ", ".join(f"{ctx['name']}={len(case.X)}" for ctx, case in zip(contexts, cases)), flush=True)
    group_names = ("constant_load", "single_step", "periodic_pulse", "target_transient", "target_steady",
                   "target_rise_transient", "target_fall_transient", "first_transition_not_yet_in_source")
    for ctx in contexts:
        candidate = report["candidates"][ctx["name"]]
        for alignment in candidate["alignments"].values():
            records = alignment["cases"]
            variants = list(records[0]["overall"])
            alignment["overall"] = {name: aggregate_metrics([r["overall"][name] for r in records]) for name in variants}
            alignment["groups"] = {group: {name: aggregate_metrics([r["groups"][group][name] for r in records if group in r["groups"]])
                                                   for name in variants} for group in group_names}
        arrays = {key: np.concatenate([part[key] for part in ctx["saved"]]) for key in ctx["saved"][0]}
        path = directory / f"predictions_{ctx['name']}.npz"
        np.savez_compressed(path, **arrays)
        candidate["predictions_file"] = path.name
        candidate["predictions_sha256"] = sha256(path)
    (directory / "evaluation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    lines = ["# 多步长独立评价记录", "", f"时间：{report['created_at']}；集合：{split}；角色：{report['role']}。", "",
             "同一工况/目标区间用于主比较（不同H的输入末拍不同）；另报告同源窗口比较（不同H的目标不同）。",
             "训练、验证、测试工况按MAT来源/配对组/负载族隔离。测试不选checkpoint、QAT轮次或H；此脚本不自动选择H。",
             "TI-QAT ONNX是提供给编译器的数值参考，不是板上编译C或NPU实测。所有误差单位V/s。", "",
             "| 候选 | H | FP32 macro RMSE | TI-QAT ONNX macro RMSE | TI-QAT最大绝对误差 |", "|---|---:|---:|---:|---:|"]
    for name, candidate in report["candidates"].items():
        overall = candidate["alignments"]["common_target_intervals"]["overall"]
        q = overall.get("ti_qat_onnx", {})
        lines.append(f"| {name} | {candidate['horizon_steps']} | {overall['fp32']['macro_rmse_V_per_s']:.6f} | {q.get('macro_rmse_V_per_s', '未运行')} | {q.get('max_abs_error_V_per_s', '未运行')} |")
    lines += ["", f"瞬态掩码：目标区间距仿真负载命令变化区间不超过{transient_window_ms}ms；这些命令仅用于离线分组。",
              "source_eso_hold为零残差/保持源拍z2；target_eso_diagnostic使用未来应用时刻实录z2，只是当期ESO对照，不是源拍可用预测。",
              "predictions_*.npz保留主比较中的每点预测、源/目标索引及时间、真值和分组掩码；evaluation_report.json有完整分组/每工况指标。",
              "首次任务跳变分组按元数据pulse_start_s匹配真实负载命令变化段起点（容差1.5Ts），排除0秒启动斜坡；严格要求source_index<变化区间索引，落在同一变化区间内的源样本保守排除。",
              "该分组若样本数为0，表示没有测到该能力，不能解释为误差为0。整体/稳态/瞬态指标仍按原定义；此次仅修正首次任务边沿评分掩码，没有重新训练、选模型或改划分。",
              "没有运行板端延迟测量、闭环补偿或稳定性验证。"]
    (directory / "README_CN.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="JSON candidates: name/checkpoint/data_dir/optional quantized_dir")
    parser.add_argument("--split", choices=("val", "test"), default="test")
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--transient-window-ms", type=float, default=1.0)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.batch_size < 1 or args.threads < 1 or not np.isfinite(args.transient_window_ms) or args.transient_window_ms < 0:
        parser.error("Invalid batch size, thread count or transient window.")
    config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    directory = create_run_directory(args.output_dir, prefix=f"evaluate_horizons_{args.split}")
    (directory / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    run_comparison(config, directory, args.split, args.batch_size, args.threads, args.transient_window_ms)
    print(f"Saved horizon comparison: {directory}")


if __name__ == "__main__":
    main()
