"""生成单文件或目录内各工况的九通道扰动残差标签。"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.io import loadmat

FEATURE_NAMES = ("Vo", "ILA", "ILB", "ILC", "ILD", "VREF", "IREF", "z2", "Vin")


def _metadata_value(value):
    """描述性参数可含 MATLAB 数组；0 Hz 工况的 NaN 占空比写成 JSON null。"""
    if isinstance(value, np.ndarray):
        return _metadata_value(value.tolist())
    if isinstance(value, np.generic):
        return _metadata_value(value.item())
    if isinstance(value, (tuple, list)):
        return [_metadata_value(item) for item in value]
    if isinstance(value, float) and np.isnan(value):
        return None
    return value


def _case_identity(meta):
    """批次编号唯一；保留 N/V 各组内部原编号及配对关系，不改原始 MAT。"""
    def positive_id(name, allow_zero=False):
        value = meta[name]
        if (isinstance(value, (bool, np.bool_)) or not np.isscalar(value)
                or not np.isfinite(float(value)) or float(value) < (0 if allow_zero else 1)
                or float(value) != int(value)):
            raise ValueError(f"meta.{name} must be an {'nonnegative' if allow_zero else 'positive'} integer.")
        return int(value)

    source_id = positive_id("case_id")
    result = {"case_id": source_id, "source_case_id": source_id,
              "case_id_field": "meta.case_id"}
    batch_fields = ("batch_id", "batch_case_id", "case_group", "paired_nominal_id", "split_group")
    if any(name in meta for name in batch_fields):
        missing = [name for name in batch_fields if name not in meta]
        if missing:
            raise ValueError(f"Incomplete batch/group metadata: {missing}.")
        for name in ("batch_id", "case_group", "split_group"):
            value = meta[name]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"meta.{name} must be a nonempty string.")
            result[name] = value
        result["batch_case_id"] = positive_id("batch_case_id")
        # 补充S/T工况以0明确表示未配对，不能把它当作某个共同的标称工况。
        result["paired_nominal_id"] = positive_id("paired_nominal_id", allow_zero=True)
        result["case_id"] = result["batch_case_id"]
        result["case_id_field"] = "meta.batch_case_id"
    return result


def build_samples(features, time, b0, history=8, horizon=1, start_time=0.0,
                  source_valid=None):
    x = np.asarray(features, dtype=np.float64)
    t = np.asarray(time, dtype=np.float64).reshape(-1)
    if x.shape != (len(t), 9):
        raise ValueError("Expected [number of time points, 9] features.")
    if history < 1 or horizon < 0:
        raise ValueError("history must be positive; horizon must be nonnegative.")
    dt = np.diff(t)
    if not np.isfinite(t).all() or np.any(dt <= 0):
        raise ValueError("Timestamps must be finite and strictly increasing.")
    if not np.isfinite(b0) or b0 == 0:
        raise ValueError("b0 must be finite and nonzero.")
    if not np.allclose(dt, np.median(dt), rtol=1e-5, atol=1e-12):
        raise ValueError("Uniformly sampled input is required for these windows.")

    # IREF is already the common per-phase reference: do NOT multiply by four.
    f_interval = np.diff(x[:, 0]) / dt - float(b0) * x[:-1, 6]
    # k+horizon+1 must still exist, because the target uses an interval endpoint.
    k = np.arange(history - 1, len(t) - horizon - 1, dtype=np.int64)
    if not len(k):
        raise ValueError("Not enough data for the chosen history and horizon.")
    windows = k[:, None] + np.arange(-history + 1, 1, dtype=np.int64)
    j = k + horizon
    target = f_interval[j] - x[k, 7]
    keep = ((t[k] >= start_time) & np.isfinite(x[windows]).all(axis=(1, 2))
            & np.isfinite(target))
    if source_valid is not None:
        source_valid = np.asarray(source_valid, dtype=bool).reshape(-1)
        if source_valid.shape != t.shape:
            raise ValueError("Source valid mask has the wrong length.")
        keep &= source_valid[k]
    k, j, windows, target = k[keep], j[keep], windows[keep], target[keep]
    if not len(k):
        raise ValueError("No eligible windows remain.")

    return {
        "X": x[windows].astype(np.float32),
        "y": target.astype(np.float32)[:, None],
        "source_index": k,
        "target_interval_index": j,
        "source_time_s": t[k],
        "target_start_time_s": t[j],
        "target_end_time_s": t[j + 1],
        "target_disturbance_V_per_s": f_interval[j],
        "source_z2_V_per_s": x[k, 7],
    }


def audit_eso(features, time, meta, start_time):
    """Cross-check the supplied controller equations away from saturation/reset."""
    x = np.asarray(features, dtype=np.float64)
    t = np.asarray(time, dtype=np.float64)
    b0, wc, wo = [float(meta[key]) for key in ("b0", "wc", "wo")]
    dt = 1.0 / float(meta["sample_frequency_Hz"])
    v, vref, u, z2 = x[:, 0], x[:, 5], x[:, 6], x[:, 7]
    z1 = vref - (b0 * u + z2) / wc
    # The supplied controller clips at +/-40 A; inversion is invalid at clipping.
    keep = ((t[1:] >= start_time) & (np.abs(u[1:]) < 39.9)
            & (np.abs(u[:-1]) < 39.9))
    if not keep.any():
        return {"checked_pairs": 0}
    z2_pred = z2[:-1] + dt * wo**2 * (v[1:] - z1[:-1])
    z1_pred = z1[:-1] + dt * (z2[:-1] + b0*u[:-1]
                             + 2*wo*(v[1:] - z1[:-1]))
    return {
        "checked_pairs": int(keep.sum()),
        "z2_replay_rmse_V_per_s": float(np.sqrt(np.mean((z2[1:][keep]-z2_pred[keep])**2))),
        "z1_replay_rmse_V": float(np.sqrt(np.mean((z1[1:][keep]-z1_pred[keep])**2))),
        "limitation": "Evidence of recorded timing; not proof of downstream actuation timing. Reset samples require an enable log in future exports.",
    }


def timestamp():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def prepare_file(mat_file, history=8, horizon=1, start_time=None):
    """逐工况读取自己的参数，完成计算与检查；此函数不写文件。"""
    mat_file = Path(mat_file)
    mat = loadmat(mat_file, simplify_cells=True, variable_names=["data", "meta"])
    data, meta = mat["data"], mat["meta"]
    identity = _case_identity(meta)
    if tuple(data["feature_names"]) != FEATURE_NAMES:
        raise ValueError("Unexpected column order: map columns explicitly first.")
    if "per-phase" not in str(meta.get("IREF_definition", "")):
        raise ValueError("Confirm the per-phase IREF definition before applying b0.")
    start = float(meta.get("pulse_start_s", 0.0) if start_time is None else start_time)
    values = build_samples(data["features"], data["time"], meta["b0"],
                           history, horizon, start, data.get("valid"))
    stats = {
        "created_at": timestamp(),
        "label_definition": "interval_residual_v1",
        "source_file": str(mat_file.resolve()),
        "source_sha256": hashlib.sha256(mat_file.read_bytes()).hexdigest(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        **identity,
        "case_parameters": {key: _metadata_value(meta[key]) for key in (
            "frequency_Hz", "high_duty_fraction", "low_power_W_at_12V",
            "high_power_W_at_12V", "load_mode", "output_C_factor", "output_C_uF",
            "input_C_unchanged_uF", "L_factors", "phase_L_uH",
            "controller_parameters_unchanged", "complete_cycles", "event_type",
            "initial_power_W_at_12V", "final_power_W_at_12V", "pulse_start_s",
            "stop_time_s", "slew_A_per_us", "transition_duration_s",
            "reference_voltage_V", "input_voltage_V") if key in meta},
        "feature_names": FEATURE_NAMES,
        "b0_per_phase": float(meta["b0"]),
        "history_steps": history,
        "horizon_steps_to_target_interval_start": horizon,
        "sample_interval_s": float(np.median(np.diff(data["time"]))),
        "minimum_source_time_s": start,
        "X_shape": list(values["X"].shape),
        "y_shape": list(values["y"].shape),
        "first_source_time_s": float(values["source_time_s"][0]),
        "last_source_time_s": float(values["source_time_s"][-1]),
        "target_min_V_per_s": float(values["y"].min()),
        "target_max_V_per_s": float(values["y"].max()),
        "zero_residual_baseline_rmse_V_per_s": float(np.sqrt(np.mean(values["y"].astype(float)**2))),
        "eso_replay": audit_eso(data["features"], data["time"], meta, start),
        "assumptions": [
            "IREF[j] is applied with zero-order hold over [t[j],t[j+1]); no extra command delay.",
            "Inputs end after source IREF and z2 have been calculated; inference is for a subsequent interval.",
            "The target is an interval-averaged reconstruction from control-rate Vo, not physical ground truth.",
            "No filtering, normalization, or training/validation/test split has been applied.",
            "Historical context before minimum_source_time_s is allowed when available and finite; this preserves the first pulse edge.",
            "The source valid mask describes initialized history, not operating safety or successful settling.",
        ],
    }
    return values, stats


def check_output_path(output):
    output = Path(output)
    # 用显式后缀和独占创建避免 NumPy 自动补后缀造成覆盖检查失效。
    if output.suffix.lower() != ".npz":
        raise ValueError("Output filename must end with .npz.")
    for path in (output, output.with_suffix(".json")):
        if path.exists():
            raise FileExistsError(f"Output already exists; choose a new name/directory: {path}")


def write_dataset(output, values, stats):
    output = Path(output)
    check_output_path(output)
    metadata = json.dumps(stats, ensure_ascii=False, indent=2, allow_nan=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        np.savez_compressed(stream, **values,
                            feature_names=np.asarray(FEATURE_NAMES),
                            metadata_json=np.asarray(metadata))
    with output.with_suffix(".json").open("x", encoding="utf-8") as stream:
        stream.write(metadata)


def process_directory(input_dir, output_dir, history=8, horizon=1,
                      start_time=None, pattern="pulse_*.mat"):
    """只扫描当前目录，各工况独立构建窗口，全部预检通过后才开始写出。"""
    input_dir, output_dir = Path(input_dir), Path(output_dir)
    if "/" in pattern or "\\" in pattern or "**" in pattern:
        raise ValueError("Use a non-recursive filename pattern, for example pulse_*.mat.")
    sources = sorted(path for path in input_dir.glob(pattern) if path.is_file())
    if not sources:
        raise ValueError(f"No files match {pattern!r} in {input_dir}.")
    top_level_mats = [path for path in input_dir.iterdir()
                      if path.is_file() and path.suffix.lower() == ".mat"]
    print(f"Selected {len(sources)} files with pattern {pattern!r}; "
          f"top-level MAT files: {len(top_level_mats)}; recursive=False.", flush=True)
    if len(sources) < len(top_level_mats):
        print("Other top-level MAT files were not selected. For the N/V batch use "
              "--pattern \"[NV]*.mat\"; support subdirectories are not scanned.", flush=True)
    outputs = [output_dir / f"{path.stem}_L{history}_h{horizon}_residual.npz"
               for path in sources]
    summary_path = output_dir / "batch_summary.json"
    if summary_path.exists():
        raise FileExistsError(f"Batch summary already exists; choose a new directory: {summary_path}")
    for output in outputs:
        check_output_path(output)

    # 先检查全部工况；不把前一个文件的末尾和后一个文件的开头拼成窗口。
    prepared = []
    seen_ids, seen_sources = set(), set()
    for source, output in zip(sources, outputs):
        try:
            values, stats = prepare_file(source, history, horizon, start_time)
        except Exception as exc:
            raise ValueError(f"Failed to prepare {source.name}: {exc}") from exc
        if stats["case_id"] in seen_ids or stats["source_sha256"] in seen_sources:
            raise ValueError(f"Duplicate source/case identity in batch: {source.name}. "
                             "Keep separate batches/pilot files in separate labeled directories.")
        # 预检序列化，避免大量文件已写出后才发现某个 MATLAB 参数无法写 JSON。
        json.dumps(stats, ensure_ascii=False, allow_nan=False)
        seen_ids.add(stats["case_id"])
        seen_sources.add(stats["source_sha256"])
        prepared.append((output, values, stats))

    records = []
    for output, values, stats in prepared:
        write_dataset(output, values, stats)
        records.append({
            "source_file": stats["source_file"],
            "source_sha256": stats["source_sha256"],
            "case_id": stats["case_id"],
            **{key: stats[key] for key in ("source_case_id", "case_id_field", "batch_id",
                                          "batch_case_id", "case_group", "paired_nominal_id",
                                          "split_group") if key in stats},
            "case_parameters": stats["case_parameters"],
            "npz_file": str(output.resolve()),
            "metadata_file": str(output.with_suffix(".json").resolve()),
            "X_shape": stats["X_shape"],
            "y_shape": stats["y_shape"],
            "sample_count": len(values["y"]),
            "minimum_source_time_s": stats["minimum_source_time_s"],
            "sample_interval_s": stats["sample_interval_s"],
            "b0_per_phase": stats["b0_per_phase"],
            "zero_residual_baseline_rmse_V_per_s": stats["zero_residual_baseline_rmse_V_per_s"],
            "eso_replay": stats["eso_replay"],
        })
        print(f"OK {output.name}: X={values['X'].shape}, y={values['y'].shape}")

    summary = {
        "created_at": timestamp(),
        "input_directory": str(input_dir.resolve()),
        "output_directory": str(output_dir.resolve()),
        "pattern": pattern,
        "recursive": False,
        "top_level_mat_count": len(top_level_mats),
        "unselected_top_level_mat_count": len(top_level_mats)-len(sources),
        "history_steps": history,
        "horizon_steps_to_target_interval_start": horizon,
        "start_time_override_s": start_time,
        "feature_names": FEATURE_NAMES,
        "generator_sha256": prepared[0][2]["generator_sha256"],
        "file_count": len(records),
        "total_samples": sum(record["sample_count"] for record in records),
        "dataset_split": "Not assigned. Keep complete cases/runs together; do not randomly split overlapping windows.",
        "files": records,
    }
    with summary_path.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(f"Completed {len(records)} cases, {summary['total_samples']} samples. Summary: {summary_path}")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_path", type=Path, help="单个 MAT 文件或包含工况 MAT 的目录")
    destinations = parser.add_mutually_exclusive_group(required=True)
    destinations.add_argument("--output", type=Path, help="单文件输出路径，必须以 .npz 结尾")
    destinations.add_argument("--output-dir", type=Path, help="批量输出目录，不覆盖已有结果")
    parser.add_argument("--pattern", default="pulse_*.mat", help="批量文件名匹配规则，不递归扫描")
    parser.add_argument("--history", type=int, default=8)
    parser.add_argument("--horizon", type=int, default=1)
    parser.add_argument("--start-time", type=float, default=None,
                        help="最早源时刻；未指定时使用每个文件自己的 meta.pulse_start_s")
    args = parser.parse_args()
    try:
        if args.input_path.is_dir():
            if args.output_dir is None:
                parser.error("Directory input requires --output-dir.")
            process_directory(args.input_path, args.output_dir, args.history,
                              args.horizon, args.start_time, args.pattern)
        else:
            if not args.input_path.is_file():
                parser.error(f"Input does not exist: {args.input_path}")
            if args.output is None:
                parser.error("Single-file input requires --output.")
            check_output_path(args.output)
            values, stats = prepare_file(args.input_path, args.history,
                                         args.horizon, args.start_time)
            write_dataset(args.output, values, stats)
            print(json.dumps(stats, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
