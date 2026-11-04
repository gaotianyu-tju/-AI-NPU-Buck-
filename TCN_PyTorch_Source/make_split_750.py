"""750工况按跨批次负载族划分；固定100组用于验证选优，不训练模型。"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import random

from ndp_tcn.data import FEATURE_NAMES, LABEL_DEFINITION, read_case_metadata

ROOT = Path(__file__).resolve().parent
LOAD_FAMILY_SCOPE = "ndp_load_family_v1"
BACKUP = "backups/20261031_235640_before_batch750_prepare"
EVENT_TYPES = ("pulse", "step_up", "step_down", "constant")
NEW_CATEGORIES = ("supplement_nominal", "supplement_variation", "step_up", "step_down", "constant")


def _number(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"Invalid finite number for {name}: {value!r}.")
    value = float(format(value, ".12g"))
    if (positive and value <= 0) or (not positive and value < 0):
        raise ValueError(f"Invalid nonnegative/positive number for {name}: {value!r}.")
    return value


def family_key(metadata):
    """返回规范JSON族键；C/L、起始时间和批次不分族，单次阶跃保留方向。

    旧500标签未保存ref/Vin/slew时，使用本项目已核验的12V/48V/0.1A/us。
    新准备入口会从原MAT补齐这些字段，因此默认值仅为旧元数据兼容。
    """
    p = metadata.get("case_parameters")
    if not isinstance(p, dict):
        raise ValueError("case_parameters must be an object.")
    mode = p.get("load_mode")
    if not isinstance(mode, str) or not mode.strip():
        raise ValueError("load_mode is required.")
    f = _number(p.get("frequency_Hz"), "frequency_Hz")
    low = _number(p.get("low_power_W_at_12V"), "low_power_W_at_12V")
    high = _number(p.get("high_power_W_at_12V"), "high_power_W_at_12V")
    if high < low:
        raise ValueError("high_power_W_at_12V must be >= low_power_W_at_12V.")
    event = p.get("event_type")
    if not event:
        event = "pulse" if f > 0 else "constant"
    if event not in EVENT_TYPES:
        raise ValueError(f"Unsupported event_type: {event!r}.")
    payload = {"scope": LOAD_FAMILY_SCOPE, "event_type": event, "load_mode": mode.strip().upper(),
               "reference_voltage_V": _number(p.get("reference_voltage_V", 12), "reference_voltage_V", positive=True),
               "input_voltage_V": _number(p.get("input_voltage_V", 48), "input_voltage_V", positive=True),
               "slew_A_per_us": _number(p.get("slew_A_per_us", 0.1), "slew_A_per_us", positive=True)}
    if event == "pulse":
        duty = _number(p.get("high_duty_fraction"), "high_duty_fraction", positive=True)
        if f <= 0 or duty >= 1:
            raise ValueError("Pulse family requires frequency>0 and duty in (0,1).")
        payload.update(frequency_Hz=f, high_duty_fraction=duty,
                       low_power_W_at_12V=low, high_power_W_at_12V=high)
    elif event == "constant":
        initial = _number(p.get("initial_power_W_at_12V", low), "initial_power_W_at_12V")
        final = _number(p.get("final_power_W_at_12V", high), "final_power_W_at_12V")
        if f != 0 or not (initial == final == low == high):
            raise ValueError("Constant family requires f=0 and identical powers.")
        payload["power_W_at_12V"] = initial
    else:
        initial = _number(p.get("initial_power_W_at_12V"), "initial_power_W_at_12V")
        final = _number(p.get("final_power_W_at_12V"), "final_power_W_at_12V")
        direction = "step_up" if final > initial else "step_down" if final < initial else "constant"
        if f != 0 or direction != event or min(initial, final) != low or max(initial, final) != high:
            raise ValueError("Step direction or sorted low/high powers are inconsistent.")
        payload.update(initial_power_W_at_12V=initial, final_power_W_at_12V=final)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _integer(value, name, *, zero=False):
    if isinstance(value, bool) or not isinstance(value, int) or value < (0 if zero else 1):
        raise ValueError(f"Invalid {name}: {value!r}.")
    return value


def _old_sides(old_manifest):
    sides = {}
    for split, expected in (("train", 400), ("test", 100)):
        names = old_manifest.get(split)
        if not isinstance(names, list) or len(names) != expected:
            raise ValueError("Original manifest must contain exactly400train/100test.")
        for name in names:
            if not isinstance(name, str) or Path(name).name != name or name in sides:
                raise ValueError("Invalid or repeated filename in original manifest.")
            sides[name] = split
    if old_manifest.get("val") != []:
        raise ValueError("Original manifest val must be empty.")
    return sides


def _new_category(metadata):
    case_id = metadata["case_id"]
    if 501 <= case_id <= 700:
        kind = metadata.get("case_group")
        if kind not in ("nominal", "variation"):
            raise ValueError("Supplement200 must preserve nominal/variation case_group.")
        return "supplement_"+kind
    if 701 <= case_id <= 750:
        event = json.loads(family_key(metadata))["event_type"]
        if event not in ("step_up", "step_down", "constant"):
            raise ValueError("Step50 must preserve step_up/step_down/constant event_type.")
        return event
    raise ValueError("New case_id must lie in501..750.")


def _select_groups(groups, old_sides, test_count, seed, required_new_categories):
    """按完整族的大小做0/1动态规划；在覆盖条件下严格按旧归属变化数量选优。"""
    ordered = sorted(groups)
    random.Random(seed).shuffle(ordered)
    categories = tuple(required_new_categories)
    category_bits = {category: 1 << i for i, category in enumerate(categories)}
    wanted = (1 << len(categories))-1
    # state=(test文件数,新数据类别覆盖mask)；score=(-保留旧test数,移入旧train数)。
    # 相同score保留首个，排序后固定seed保证确定性，不按标签/预测指标选集合。
    states = {(0, 0): ((0, 0), ())}
    for index, key in enumerate(ordered):
        members = groups[key]
        size = len(members)
        old_test = sum(old_sides.get(name) == "test" for name, _ in members)
        old_train = sum(old_sides.get(name) == "train" for name, _ in members)
        mask = 0
        for name, metadata in members:
            if name not in old_sides:
                category = _new_category(metadata)
                mask |= category_bits.get(category, 0)
        for (count, covered), (score, selected) in list(states.items()):
            if count+size > test_count:
                continue
            target = (count+size, covered | mask)
            candidate = (score[0]-old_test, score[1]+old_train)
            if target not in states or candidate < states[target][0]:
                states[target] = (candidate, selected+(index,))
    if (test_count, wanted) not in states:
        raise ValueError("No exact family-isolated split satisfies test_count and new-category coverage.")
    score, indices = states[(test_count, wanted)]
    return {ordered[i] for i in indices}, {"old_test_moved_to_train": sum(s == "test" for s in old_sides.values())+score[0],
                                         "old_train_moved_to_test": score[1]}


def build_manifest(records, old_manifest, seed=2026, test_count=100, *,
                   required_new_categories=NEW_CATEGORIES):
    """records为(文件名,NPZ元数据)；不读取X/y，也不依据标签幅值划分。"""
    if len(records) != 750:
        raise ValueError(f"Expected exactly750 cases; found {len(records)}.")
    _integer(seed, "seed", zero=True)
    _integer(test_count, "test_count")
    if test_count != 100:
        raise ValueError("This experiment requires exactly100 validation/selection cases.")
    required_new_categories = tuple(required_new_categories)
    if len(set(required_new_categories)) != len(required_new_categories) or any(x not in NEW_CATEGORIES for x in required_new_categories):
        raise ValueError("Invalid new-category coverage requirements.")
    old_sides = _old_sides(old_manifest)
    old_sources = {row["file"]: row for row in old_manifest.get("source_cases", [])}
    groups = defaultdict(list)
    names, ids, hashes = set(), set(), set()
    group_keys, positive_pairs = {}, {}
    reference = None
    canonical = []
    for name, metadata in sorted(records):
        if not isinstance(name, str) or Path(name).name != name or Path(name).suffix.lower() != ".npz" or name.casefold() in names:
            raise ValueError(f"Invalid/duplicate NPZ filename: {name!r}.")
        names.add(name.casefold())
        case_id = _integer(metadata.get("case_id"), "case_id")
        if case_id != _integer(metadata.get("batch_case_id"), "batch_case_id"):
            raise ValueError("case_id must equal remapped batch_case_id.")
        digest = metadata.get("source_sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
            raise ValueError("Invalid source_sha256.")
        if case_id in ids or digest.lower() in hashes:
            raise ValueError("Duplicate source/case identity.")
        ids.add(case_id);hashes.add(digest.lower())
        if (name in old_sides) != (case_id <= 500):
            raise ValueError("Original500 membership does not match case_id1..500.")
        if name in old_sources:
            old_source = old_sources[name]
            if old_source.get("case_id") != case_id or str(old_source.get("source_sha256", "")).lower() != digest.lower():
                raise ValueError("Original500 identity/source hash differs from original split.")
        expected_origin = "old500" if case_id <= 500 else "supplement200" if case_id <= 700 else "step50"
        if "origin_dataset" in metadata and metadata["origin_dataset"] != expected_origin:
            raise ValueError("origin_dataset conflicts with remapped case_id.")
        if tuple(metadata.get("feature_names", [])) != FEATURE_NAMES or metadata.get("label_definition") != LABEL_DEFINITION:
            raise ValueError("Incompatible features/label definition.")
        history = _integer(metadata.get("history_steps"), "history_steps")
        horizon = _integer(metadata.get("horizon_steps_to_target_interval_start"), "horizon", zero=True)
        dt = _number(metadata.get("sample_interval_s"), "sample_interval_s", positive=True)
        b0 = _number(metadata.get("b0_per_phase"), "b0_per_phase", positive=True)
        if history != 8 or horizon != 1 or not math.isclose(dt, 1/30000, rel_tol=1e-6) or b0 != 20000:
            raise ValueError("Expected L8/h1/30kHz/b0=20000 labels.")
        signature = (history, horizon, dt, b0, metadata["label_definition"])
        if reference is None:reference = signature
        shape, yshape = metadata.get("X_shape"), metadata.get("y_shape")
        if not isinstance(shape, list) or len(shape) != 3 or shape[1:] != [8, 9] or yshape != [shape[0], 1]:
            raise ValueError("Invalid X/y metadata shapes.")
        _integer(shape[0], "sample_count")
        key = family_key(metadata)
        if metadata.get("load_family_scope") != LOAD_FAMILY_SCOPE or metadata.get("load_family_key") != key:
            raise ValueError("Missing or inconsistent canonical load_family_scope/key.")
        batch, local_group = metadata.get("batch_id"), metadata.get("split_group")
        if not isinstance(batch, str) or not batch or not isinstance(local_group, str) or not local_group:
            raise ValueError("Source batch/group identity is required.")
        pair = _integer(metadata.get("paired_nominal_id"), "paired_nominal_id", zero=True)
        source_group = (batch, local_group)
        if source_group in group_keys and group_keys[source_group] != key:
            raise ValueError("A source paired/split group has conflicting load families.")
        group_keys[source_group] = key
        if pair:
            pair_key = (batch, pair)
            if pair_key in positive_pairs and positive_pairs[pair_key] != source_group:
                raise ValueError("A positive paired_nominal_id has inconsistent split_group.")
            positive_pairs[pair_key] = source_group
        groups[key].append((name, metadata))
        canonical.append((name, metadata))
    if ids != set(range(1, 751)) or not set(old_sides).issubset({name for name, _ in records}):
        raise ValueError("Expected original500 plus remapped new501..750, with no missing IDs.")
    selected, objective = _select_groups(groups, old_sides, test_count, seed, required_new_categories)
    split_names = {"train": [], "val": [], "test": []}
    rows = []
    for key in sorted(groups):
        split = "test" if key in selected else "train"
        members = sorted(groups[key])
        filenames = [name for name, _ in members]
        split_names[split].extend(filenames)
        rows.append({"load_family_scope": LOAD_FAMILY_SCOPE, "load_family_key": key,
                     "family_id": "F_"+hashlib.sha256(key.encode()).hexdigest()[:16], "split": split,
                     "files": filenames, "case_ids": [m["case_id"] for _, m in members],
                     "source_batches": sorted({m["batch_id"] for _, m in members})})
    for split in split_names:split_names[split].sort()
    if (len(split_names["train"]), len(split_names["test"])) != (650, 100):
        raise RuntimeError("Internal exact-count failure.")
    actual_side = {name: split for split in split_names for name in split_names[split]}
    changed = [{"file": name, "old_split": old_sides[name], "new_split": actual_side[name]}
               for name in sorted(old_sides) if old_sides[name] != actual_side[name]]
    summary = {}
    for split, files in split_names.items():
        nameset = set(files)
        chosen = [(name, m) for name, m in canonical if name in nameset]
        summary[split] = {"files": len(chosen), "groups": sum(row["split"] == split for row in rows),
                          "samples": sum(m["X_shape"][0] for _, m in chosen),
                          "old500_files": sum(name in old_sides for name, _ in chosen),
                          "new250_files": sum(name not in old_sides for name, _ in chosen),
                          "event_types": dict(sorted(Counter(json.loads(family_key(m))["event_type"] for _, m in chosen).items())),
                          "source_batches": dict(sorted(Counter(m["batch_id"] for _, m in chosen).items())),
                          "new_event_types": dict(sorted(Counter(json.loads(family_key(m))["event_type"] for name, m in chosen if name not in old_sides).items())),
                          "new_categories": dict(sorted(Counter(_new_category(m) for name, m in chosen if name not in old_sides).items()))}
    return {"description_zh": "750完整工况按跨批次负载族划分650训练/100验证选优；test是验证槽位，不是独立测试。",
            "selection_split": "test", "seed": seed, "test_count": test_count, **split_names,
            "summary": summary, "groups": rows, "changed_membership": changed,
            "strategy": {"unit": ["load_family_scope", "load_family_key"],
                         "scope": LOAD_FAMILY_SCOPE, "required_new_categories": list(required_new_categories),
                         "algorithm": "exact0/1dynamic_programming_with_coverage_bitmask",
                         "objective_order": ["min_old_test_moved_to_train", "min_old_train_moved_to_test", "seeded_group_order_tie_break"],
                         "objective": objective, "group_size_counts": {str(k): v for k, v in sorted(Counter(len(m) for m in groups.values()).items())},
                         "cross_batch_families": sum(len(row["source_batches"]) > 1 for row in rows),
                         "ignored_for_family": ["source_batch", "C/L_parameters", "start_time", "sampling_phase", "record_duration"],
                         "legacy_defaults": {"reference_voltage_V": 12, "input_voltage_V": 48, "slew_A_per_us": 0.1}},
            "label_configuration": dict(zip(("history_steps", "horizon_steps_to_target_interval_start", "sample_interval_s", "b0_per_phase", "label_definition"), reference)),
            "source_cases": [{"file": name, "case_id": m["case_id"], "batch_id": m["batch_id"],
                              "source_sha256": m["source_sha256"], "source_batch_case_id": m.get("source_batch_case_id"),
                              "load_family_key": family_key(m)} for name, m in canonical]}


def create_split(data_dir, output, old_split, seed=2026, test_count=100, *,
                 required_new_categories=NEW_CATEGORIES):
    data_dir, output = Path(data_dir).resolve(), Path(output).resolve()
    old_split = Path(old_split).resolve()
    report = output.with_suffix(".README_CN.md")
    if output.suffix.lower() != ".json":raise ValueError("Split output must use .json extension.")
    if output.exists() or report.exists():raise FileExistsError(f"Refusing to overwrite split/README: {output}")
    files = sorted(data_dir.glob("*.npz"))
    records = [(path.name, read_case_metadata(path)) for path in files]
    old_bytes = old_split.read_bytes()
    old_manifest = json.loads(old_bytes.decode("utf-8-sig"))
    manifest = build_manifest(records, old_manifest, seed, test_count, required_new_categories=required_new_categories)
    manifest.update(created_at=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
                    data_dir=str(data_dir), original_split=str(old_split),
                    original_split_sha256=hashlib.sha256(old_bytes).hexdigest())
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, allow_nan=False);f.write("\n")
    train, test = manifest["summary"]["train"], manifest["summary"]["test"]
    text = f"""# 750工况划分记录：650训练 / 100验证选优

生成时间：{manifest['created_at']}（Asia/Singapore）。未训练模型。
数据目录：`{data_dir}`；清单：`{output.name}`。

本次按用户最新要求固定100个完整工况用于逐轮验证和checkpoint选优，其余650训练。
`selection_split=test`、`val=[]`仅沿用现有接口命名，没有独立测试集，不是旧的600/150方案。

| 集合 | 文件 | 负载族 | 窗口 | 原500文件 | 新250文件 |
|---|---:|---:|---:|---:|---:|
| train | {train['files']} | {train['groups']} | {train['samples']} | {train['old500_files']} | {train['new250_files']} |
| test（验证选优） | {test['files']} | {test['groups']} | {test['samples']} | {test['old500_files']} | {test['new250_files']} |

保留各MAT原批次、组内编号及配对含义，仅合并标签的全局case_id为1..750。
跨批次按规范负载族分组：周期脉冲使用频率/占空比/低高功率；单次阶跃使用方向及初终功率；
恒载使用功率。共同参考电压、输入电压、负载模式和斜率进入族键。
忽略C/L偏差、起始时间、采样相位和记录长度，使相同负载的近邻版本始终同组。
旧元数据未保存ref/Vin/slew时兼容12V/48V/0.1A/us；本次准备入口会从原MAT补齐实际值。
共有{len(manifest['groups'])}个族，其中{manifest['strategy']['cross_batch_families']}族跨原/新增批次。

先满足验证集100文件与整族隔离、新类别最低覆盖：{', '.join(required_new_categories)}。
在这些条件下，动态规划优先最少移出旧test，再最少移入旧train；完全同分时按固定种子{seed}打乱后的族顺序选取。
本次旧test移到train {manifest['strategy']['objective']['old_test_moved_to_train']}个，旧train移到test {manifest['strategy']['objective']['old_train_moved_to_test']}个。
全部变化见JSON的changed_membership，新旧及类别分布见summary。保留原500清单未修改。
这是在有限验证预算下最小改动的折中；S nominal、S variation、T step_up、T step_down、T constant各至少一族成员进入验证。
不是各新类别按样本量比例分层，不保证频率、功率或参数偏差全面均衡；新增类别的验证覆盖可能很小。
由于验证清单发生变化，新指标不能与旧500工况报告直接作同一验证集上的优劣比较。
不得把原100test再加上同族新样本，却仍声称只有100；也不得拆开同族凑整。

通道顺序：Vo、ILA、ILB、ILC、ILD、VREF、IREF、z2、Vin；X[N,8,9]、y[N,1]。
电压V、电流A、z2和扰动残差V/s。L8/h1、30kHz、b0=20000；各文件单独构造窗口。
minimum_source_time_s可随实际事件起点变化，不能用其不同作为拆分负载族的依据。
标准化仍只在训练入口由650个训练工况拟合，未复用旧scaler。

在E:/bisai、TCN的VS Code终端中使用：

```text
python make_split_750.py
python -m ndp_tcn.train --backend ti_npu --data-dir data/train_750_labeled --split configs/ndp_tcn_split_750.json --epochs 50 --batch-size 128 --lr 0.001 --patience 10
```

第一条在清单已生成时会拒绝覆盖；第二条由用户自行启动，本准备过程未执行训练。
划分阶段只核验元数据及分组；X/y数组核验由750准备入口执行，其报告与状态见README_BATCH750_CN.md。
模型/量化/CCS后续必须使用这次训练的新权重及scaler，不能与旧500结果混用。

修改前备份：`{BACKUP}`。本脚本、测试和本清单属于新增文件，没有旧版本。
恢复前先保存当前代码，再按备份manifest恢复；不删除原MAT、原500标签或历史结果。
2026-11-01：新增跨批次负载族、精确650/100、旧归属变化审计和新类别覆盖约束。
"""
    with report.open("x", encoding="utf-8", newline="\n") as f:f.write(text)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT/"data/train_750_labeled")
    parser.add_argument("--output", type=Path, default=ROOT/"configs/ndp_tcn_split_750.json")
    parser.add_argument("--old-split", type=Path, default=ROOT/"configs/ndp_tcn_split_500.json")
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    manifest = create_split(args.data_dir, args.output, args.old_split, args.seed)
    print(json.dumps({"output": str(args.output), "summary": manifest["summary"],
                      "old_membership_changes": manifest["changed_membership"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
