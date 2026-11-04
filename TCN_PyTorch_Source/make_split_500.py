"""仅读取 NPZ 元数据，将本批 500 工况按配对组划分为 400/100。"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import random

from ndp_tcn.data import FEATURE_NAMES, read_case_metadata


ROOT = Path(__file__).resolve().parent
LOAD_FIELDS = ("frequency_Hz", "high_duty_fraction", "low_power_W_at_12V",
               "high_power_W_at_12V", "load_mode")


def _integer(value, name, minimum=1):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"Invalid {name}: {value!r}.")
    return value


def _finite(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Invalid {name}: {value!r}.")
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f"Invalid {name}: {value!r}.")
    return value


def _parameters(metadata):
    parameters = metadata.get("case_parameters")
    if not isinstance(parameters, dict) or any(key not in parameters for key in LOAD_FIELDS):
        raise ValueError("case_parameters must contain the load trajectory fields.")
    frequency = _finite(parameters["frequency_Hz"], "frequency_Hz")
    duty = parameters["high_duty_fraction"]
    # DC 没有脉冲占空比；原 MAT 的 NaN 在标签元数据中记为 null。
    if duty is not None or frequency != 0:
        if not 0 < _finite(duty, "high_duty_fraction") < 1:
            raise ValueError("Pulse high_duty_fraction must lie in (0, 1).")
    low = _finite(parameters["low_power_W_at_12V"], "low_power_W_at_12V")
    high = _finite(parameters["high_power_W_at_12V"], "high_power_W_at_12V")
    if high < low or not isinstance(parameters["load_mode"], str) or not parameters["load_mode"]:
        raise ValueError("Invalid load mode or high/low power.")
    c = _finite(parameters.get("output_C_factor"), "output_C_factor")
    inductors = parameters.get("L_factors")
    if (c <= 0 or not isinstance(inductors, list) or len(inductors) != 4
            or any(_finite(value, "L_factor") <= 0 for value in inductors)):
        raise ValueError("Expected positive C factor and four positive L factors.")
    return parameters


def build_manifest(records, seed=2026):
    """records 是 (文件名, 已校验的 NPZ 元数据)；不会读取 X/y 大数组。"""
    if len(records) != 500:
        raise ValueError(f"Expected exactly 500 new NPZ cases, found {len(records)}; do not mix pilot10.")
    _integer(seed, "seed", minimum=0)
    grouped = defaultdict(list)
    case_ids, source_hashes, names, batches = set(), set(), set(), set()
    reference = None
    for name, metadata in records:
        if Path(name).name != name or Path(name).suffix.lower() != ".npz" or name.casefold() in names:
            raise ValueError(f"Duplicate or invalid NPZ filename: {name}.")
        names.add(name.casefold())
        case_id = _integer(metadata.get("case_id"), "case_id")
        if case_id != _integer(metadata.get("batch_case_id"), "batch_case_id"):
            raise ValueError("case_id must equal the globally unique batch_case_id.")
        source_hash = str(metadata["source_sha256"]).lower()
        if case_id in case_ids or source_hash in source_hashes:
            raise ValueError(f"Duplicate source/case identity: {name}.")
        case_ids.add(case_id)
        source_hashes.add(source_hash)
        batch = metadata.get("batch_id")
        if not isinstance(batch, str) or not batch.strip():
            raise ValueError("A nonempty batch_id is required.")
        batches.add(batch)
        pair_id = _integer(metadata.get("paired_nominal_id"), "paired_nominal_id")
        group = metadata.get("split_group")
        if not 1 <= pair_id <= 300 or group != f"N{pair_id:03d}":
            raise ValueError(f"Invalid paired_nominal_id/split_group in {name}.")
        kind = metadata.get("case_group")
        local_id = _integer(metadata.get("source_case_id"), "source_case_id")
        if kind == "nominal":
            if case_id > 300 or case_id != pair_id or local_id != case_id:
                raise ValueError(f"Invalid nominal identity/pair: {name}.")
        elif kind == "variation":
            if not 301 <= case_id <= 500 or local_id != case_id - 300:
                raise ValueError(f"Invalid variation identity: {name}.")
        else:
            raise ValueError(f"Invalid case_group in {name}.")
        _parameters(metadata)
        shape, yshape = metadata.get("X_shape"), metadata.get("y_shape")
        if not isinstance(shape, list) or len(shape) != 3:
            raise ValueError(f"Invalid X_shape in {name}.")
        n = _integer(shape[0], "sample_count")
        if shape[1:] != [metadata["history_steps"], len(FEATURE_NAMES)] or yshape != [n, 1]:
            raise ValueError(f"Invalid metadata sample shapes in {name}.")
        signature = (metadata["history_steps"], metadata["horizon_steps_to_target_interval_start"],
                     metadata["sample_interval_s"], metadata["b0_per_phase"], metadata["label_definition"],
                     metadata.get("minimum_source_time_s"))
        if reference is None:
            reference = signature
        elif (signature[:2] != reference[:2] or signature[4:] != reference[4:]
              or not math.isclose(signature[2], reference[2], rel_tol=1e-6, abs_tol=1e-12)
              or not math.isclose(signature[3], reference[3], rel_tol=1e-9, abs_tol=1e-12)):
            raise ValueError("All cases must use the same label settings and sampling interval.")
        grouped[group].append((name, metadata))
    if len(batches) != 1 or case_ids != set(range(1, 501)):
        raise ValueError("Expected a single batch with unique case_id 1..500.")
    if Counter(len(members) for members in grouped.values()) != {1: 100, 2: 200}:
        raise ValueError("Expected 100 single groups and 200 nominal/variation pairs.")
    for group, members in grouped.items():
        nominal = [metadata for _, metadata in members if metadata["case_group"] == "nominal"]
        if len(nominal) != 1:
            raise ValueError(f"Paired nominal case missing or repeated in {group}.")
        expected = tuple(nominal[0]["case_parameters"][key] for key in LOAD_FIELDS)
        if any(tuple(metadata["case_parameters"][key] for key in LOAD_FIELDS) != expected
               for _, metadata in members):
            raise ValueError(f"Paired cases have inconsistent load trajectory in {group}.")
    rng = random.Random(seed)
    test_groups = set()
    for size, held_out in ((1, 20), (2, 40)):
        pool = sorted(group for group, members in grouped.items() if len(members) == size)
        test_groups.update(rng.sample(pool, held_out))
    split_names = {"train": [], "val": [], "test": []}
    group_rows = []
    summaries = {}
    for group in sorted(grouped):
        split = "test" if group in test_groups else "train"
        members = sorted(grouped[group], key=lambda item: item[1]["case_id"])
        filenames = [name for name, _ in members]
        split_names[split].extend(filenames)
        group_rows.append({"batch_id": next(iter(batches)), "split_group": group, "split": split,
                           "case_ids": [metadata["case_id"] for _, metadata in members],
                           "files": filenames})
    for split in split_names:
        selected = [metadata for name, metadata in records if name in set(split_names[split])]
        modes = Counter()
        for metadata in selected:
            parameters = metadata["case_parameters"]
            c_changed = not math.isclose(parameters["output_C_factor"], 1.0)
            l_changed = any(not math.isclose(value, 1.0) for value in parameters["L_factors"])
            modes["C_and_L" if c_changed and l_changed else "C_only" if c_changed
                  else "L_only" if l_changed else "nominal_parameters"] += 1
        summaries[split] = {
            "files": len(selected), "groups": sum(row["split"] == split for row in group_rows),
            "samples": sum(metadata["X_shape"][0] for metadata in selected),
            "nominal": sum(metadata["case_group"] == "nominal" for metadata in selected),
            "variation": sum(metadata["case_group"] == "variation" for metadata in selected),
            "dc_cases": sum(metadata["case_parameters"]["frequency_Hz"] == 0 for metadata in selected),
            "parameter_modes": dict(sorted(modes.items())),
        }
    return {
        "description_zh": "本批500工况按配对组划分400/100；同一标称轨迹及其参数扰动样本保留在同一集合。test按用户要求用于每轮验证和最佳checkpoint选优，不是独立测试集。",
        "selection_split": "test", "seed": seed, "batch_id": next(iter(batches)),
        "strategy": {"unit": ["batch_id", "split_group"], "algorithm": "random.Random(seed).sample",
                     "ordering": "sorted split_group; sample size-1 stratum before size-2 stratum",
                     "test_fraction": 0.2, "strata": [
                         {"group_size": 1, "total_groups": 100, "test_groups": 20},
                         {"group_size": 2, "total_groups": 200, "test_groups": 40}],
                     "parameters_and_dc": "recorded only; no extra balancing/optimization"},
        **split_names, "summary": summaries, "groups": group_rows,
        "source_cases": [{"file": name, "case_id": metadata["case_id"],
                          "source_case_id": metadata["source_case_id"],
                          "source_sha256": metadata["source_sha256"],
                          "generator_sha256": metadata.get("generator_sha256")}
                         for name, metadata in sorted(records)],
        "label_configuration": dict(zip(("history_steps", "horizon_steps_to_target_interval_start",
                                          "sample_interval_s", "b0_per_phase", "label_definition",
                                          "minimum_source_time_s"), reference)),
    }


def create_split(data_dir, output, seed=2026):
    data_dir, output = Path(data_dir).resolve(), Path(output).resolve()
    report = output.with_suffix(".README_CN.md")
    if output.suffix.lower() != ".json":
        raise ValueError("Split output must use the .json extension.")
    if output.exists() or report.exists():
        raise FileExistsError(f"Refusing to overwrite an existing split/report: {output} / {report}")
    if not data_dir.is_dir():
        raise ValueError(f"Data directory does not exist: {data_dir}")
    files = sorted(path for path in data_dir.iterdir() if path.is_file() and path.suffix.lower() == ".npz")
    records = [(path.name, read_case_metadata(path)) for path in files]
    manifest = build_manifest(records, seed)
    manifest["created_at"] = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
    manifest["data_dir"] = str(data_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    train, test = manifest["summary"]["train"], manifest["summary"]["test"]
    text = f"""# 本批 500 工况划分记录

生成时间：{manifest['created_at']}（UTC+08:00）；批次：`{manifest['batch_id']}`。
数据目录：`{data_dir}`；划分文件：`{output.name}`。

本次只生成清单，未训练模型。读取每个 NPZ 的 `metadata_json` 并与旁 JSON 核对，不解压 X/y。
校验全局 `case_id=batch_case_id` 为 1..500，原组内编号保存在 `source_case_id`；来源 SHA-256 不得重复。
300 个 nominal 与 200 个 variation 组成 300 组，其中 200 组各含 2 个文件、100 组各含 1 个文件。
同一 `(batch_id, split_group)` 的完整工况始终同组，训练读取器也会拒绝跨集合的配对泄漏。

| 集合 | 文件 | 配对组 | nominal | variation | 窗口 | DC工况 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | {train['files']} | {train['groups']} | {train['nominal']} | {train['variation']} | {train['samples']} | {train['dc_cases']} |
| test | {test['files']} | {test['groups']} | {test['nominal']} | {test['variation']} | {test['samples']} | {test['dc_cases']} |

`val=[]`，`selection_split=test`：100 个 test 工况用于每轮验证和挑选 checkpoint，因此指标不代表独立测试结果。
随机种子为 `{seed}`。对组名排序，先从 100 个单文件组抽取 20 组，再从 200 个双文件组抽取 40 组进入 test。
分层只保证组大小和 4:1 文件数；C/L 模式及 DC 分布记录在 JSON 的 summary，不做额外平衡。
每组实际归属在 groups，每个 MAT 来源哈希在 source_cases，标签时间配置在 label_configuration。

输入通道顺序：`Vo, ILA, ILB, ILC, ILD, VREF, IREF, z2, Vin`；电压单位 V，电流单位 A，z2 与残差单位 V/s。
具体窗口长度、预测区间、采样周期以 JSON 的 label_configuration 为准；DC 没有占空比，元数据以 null 表示。

在 E:/bisai、TCN 环境的 VS Code 终端执行以下命令可生成默认清单（已经生成时会拒绝覆盖）：

```text
python make_split_500.py
```

另存不同随机种子的划分时，显式指定新路径；保留旧清单以追溯实验：

```text
python make_split_500.py --data-dir data/train_500_labeled --output configs/ndp_tcn_split_500_seed2027.json --seed 2027
```

训练时必须同时指定这批标签目录和本清单。训练、评价、推理完整命令见项目根目录 README_BATCH500_CN.md。
本记录的生成前检查只涉及元数据和分组；实际数组一致性验证与训练结果以项目执行记录为准。
代码修改前备份：backups/20261031_213143_before_batch500_labels；本清单和生成脚本为首次新增，无旧版本可备份。
恢复旧代码前先保存当前改动，再按备份 manifest 恢复受影响源文件；恢复代码不删除新数据、不恢复模型权重。

2026-10-31：新增 500 工况按组随机划分、配对防泄漏及独立清单记录，旧 10 工况清单保持原样。
"""
    with report.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/train_500_labeled")
    parser.add_argument("--output", type=Path, default=ROOT / "configs/ndp_tcn_split_500.json")
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    manifest = create_split(args.data_dir, args.output, args.seed)
    print(json.dumps({"output": str(args.output), "summary": manifest["summary"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
