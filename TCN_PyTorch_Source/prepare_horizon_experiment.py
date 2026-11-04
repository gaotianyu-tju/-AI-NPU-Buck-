"""从原始750份MAT重新生成多步标签及整负载族隔离的train/val/test。"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import sys

import numpy as np
from scipy.io import loadmat

from make_split_750 import family_key, LOAD_FAMILY_SCOPE
from ndp_tcn.data import load_case, load_splits
from prepare_residual_labels import FEATURE_NAMES, prepare_file, write_dataset
from prepare_training_750 import decorate_metadata, digest, now, save_json, scan_sources

ROOT = Path(__file__).resolve().parent


def group_assignments(records, seed=2026):
    """仅按工况元数据分层，不读取标签或预测；同负载的C/L变体永不同侧。"""
    groups = defaultdict(list)
    ids, hashes, source_groups = set(), set(), {}
    for record in records:
        case_id, source_hash = int(record['case_id']), record['source_sha256']
        if case_id in ids or source_hash in hashes:
            raise ValueError('Duplicate case/source in split inventory.')
        ids.add(case_id); hashes.add(source_hash)
        key = family_key(record)
        if record.get('load_family_key', key) != key:
            raise ValueError('Canonical load family mismatch.')
        source_group = (record['batch_id'], record['split_group'])
        if source_group in source_groups and source_groups[source_group] != key:
            raise ValueError('Source paired group has conflicting load families.')
        source_groups[source_group] = key
        groups[key].append(case_id)
    strata = defaultdict(list)
    for key in sorted(groups):
        p = json.loads(key)
        event = p['event_type']
        if event == 'pulse':
            frequency = p['frequency_Hz']
            event += '_low' if frequency <= 70 else '_mid' if frequency <= 140 else '_high'
        strata[event].append(key)
    assignment, group_rows = {}, []
    rng = random.Random(seed)
    for stratum in sorted(strata):
        keys = list(strata[stratum]); rng.shuffle(keys)
        if len(keys) < 3:
            raise ValueError(f'Stratum {stratum} has fewer than three independent families.')
        held = max(1, int(len(keys) * .1 + .5))
        if 2 * held >= len(keys):
            raise ValueError('Insufficient training families after holdout allocation.')
        for index, key in enumerate(keys):
            side = 'test' if index < held else 'val' if index < 2 * held else 'train'
            members = sorted(groups[key])
            for case_id in members:
                assignment[case_id] = side
            group_rows.append(dict(family_id='F_' + hashlib.sha256(key.encode()).hexdigest()[:16],
                load_family_scope=LOAD_FAMILY_SCOPE, load_family_key=key,
                stratum=stratum, split=side, case_ids=members))
    return assignment, sorted(group_rows, key=lambda row: row['family_id'])


def verify_source_arrays(values, source, stats, horizon):
    """独立用MAT逐元素核验窗口、索引和区间残差，不调用标签构造函数。"""
    raw = loadmat(source, simplify_cells=True, variable_names=['data', 'meta'])
    data, meta = raw['data'], raw['meta']
    x = np.asarray(data['features'], dtype=np.float64)
    t = np.asarray(data['time'], dtype=np.float64).reshape(-1)
    if tuple(data['feature_names']) != FEATURE_NAMES or x.shape != (len(t), 9):
        raise ValueError('Wrong source shape/channels.')
    if not np.isfinite(x).all() or not np.allclose(np.diff(t), 1 / 30000, rtol=1e-5, atol=1e-12):
        raise ValueError('Nonfinite or nonuniform source samples.')
    eligible = np.arange(7, len(t) - horizon - 1, dtype=np.int64)
    valid = np.asarray(data.get('valid', np.ones(len(t))), dtype=bool).reshape(-1)
    eligible = eligible[(t[eligible] >= stats['minimum_source_time_s']) & valid[eligible]]
    k = np.asarray(values['source_index']); j = k + horizon
    expected_x = x[k[:, None] + np.arange(-7, 1)].astype(np.float32)
    interval = (x[j + 1, 0] - x[j, 0]) / (t[j + 1] - t[j]) - float(meta['b0']) * x[j, 6]
    expected_y = (interval - x[k, 7]).astype(np.float32)[:, None]
    pairs = [(k, eligible), (values['X'], expected_x), (values['y'], expected_y),
        (values['target_interval_index'], j), (values['source_time_s'], t[k]),
        (values['target_start_time_s'], t[j]), (values['target_end_time_s'], t[j + 1]),
        (values['source_z2_V_per_s'], x[k, 7]), (values['target_disturbance_V_per_s'], interval)]
    if any(not np.array_equal(a, b) for a, b in pairs):
        raise ValueError(f'Exact source label/index verification failed: {source.name}')
    return dict(source_arrays_verified=True, label_formula_exact=True,
        all_eligible_windows_present=True, samples=len(k), source_point_count=len(t),
        source_index_first=int(k[0]), source_index_last=int(k[-1]))


def make_manifest(records, assignments, groups, horizon, seed, data_dir):
    sides = {side: [] for side in ('train', 'val', 'test')}
    summary = {}
    for record in records:
        sides[assignments[record['case_id']]].append(record['file'])
    for side in sides:
        sides[side].sort()
        chosen = [r for r in records if assignments[r['case_id']] == side]
        summary[side] = dict(files=len(chosen), samples=sum(r['samples'] for r in chosen),
            groups=sum(row['split'] == side for row in groups),
            event_types=dict(sorted(Counter(r['event_type'] for r in chosen).items())),
            origin_datasets=dict(sorted(Counter(r['origin_dataset'] for r in chosen).items())))
    return dict(created_at=now().isoformat(), description_zh='全新训练；跨批次负载族隔离，val选优，test仅作最终独立评价。',
        selection_split='val', seed=seed, data_dir=str(data_dir), **sides, summary=summary,
        groups=groups, source_cases=records,
        label_configuration=dict(history_steps=8, horizon_steps_to_target_interval_start=horizon,
            sample_interval_s=1/30000, b0_per_phase=20000, label_definition='interval_residual_v1'),
        strategy=dict(unit=['load_family_scope', 'load_family_key'], scope=LOAD_FAMILY_SCOPE,
            algorithm='seeded_shuffle_within_event_and_pulse_frequency_stratum',
            fractions=[.8, .1, .1], rounding='round each 10% holdout family count, at least one',
            strata='constant,step_up,step_down,pulse_<=70Hz,pulse_70to140Hz,pulse_>140Hz',
            ignores=['C/L variations', 'source batch', 'start phase', 'record duration'],
            uses_labels=False, same_family_membership_for_all_horizons=True),
        independence_note='相对本次从头训练及QAT独立；这些历史数据曾参与旧H1探索，非全新采集的外部测试集。')


def prepare(args):
    horizons = sorted(set(args.horizons))
    if not horizons or any(h < 1 for h in horizons):
        raise ValueError('Horizons must be positive integers.')
    output = (args.output_dir or ROOT/'ndp_tcn/results'/('prepare_horizons_'+now().strftime('%Y%m%d_%H%M%S'))).resolve()
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite preparation directory: {output}')
    output.mkdir(parents=True)
    report = dict(created_at=now().isoformat(), status='preflight', horizons=horizons,
        output_dir=str(output), script_sha256=digest(__file__),
        label_generator_sha256=digest(ROOT/'prepare_residual_labels.py'), runs={})
    save_json(output/'preparation_report.json', report)
    try:
        rows = scan_sources(args.old_labels.resolve(), args.old_sources.resolve(), args.new_sources.resolve())
        base_metadata = [decorate_metadata({name: r['meta'][name] for name in
            ('batch_id', 'split_group', 'paired_nominal_id')},
            r['meta'], r['origin'], r['global_id'], r['source_hash']) for r in rows]
        assignment, groups = group_assignments(base_metadata, args.seed)
        save_json(output/'source_inventory.json', [dict(source=str(r['source']), source_sha256=r['source_hash'],
            case_id=r['global_id'], origin_dataset=r['origin'], split=assignment[r['global_id']]) for r in rows])
        save_json(output/'family_assignment.json', dict(seed=args.seed, groups=groups,
            case_assignment={str(k): v for k, v in sorted(assignment.items())}))
        print('SPLIT '+json.dumps(dict(Counter(assignment.values())), ensure_ascii=False), flush=True)
        for horizon in horizons:
            directory = output/f'h{horizon}'
            directory.mkdir()
            records, checks = [], []
            for index, row in enumerate(rows, 1):
                # T单次阶跃保留40ms至事件前的历史正常段，不以事件时刻裁断。
                values, stats = prepare_file(row['source'], history=8, horizon=horizon,
                    start_time=.04 if row['origin'] == 'step50' else None)
                stats = decorate_metadata(stats, row['meta'], row['origin'], row['global_id'], row['source_hash'])
                stats.update(horizon_experiment_builder_sha256=digest(__file__),
                    horizon_experiment_created_at=report['created_at'],
                    comparison_horizons=horizons, split_role=assignment[row['global_id']],
                    label_reuse=dict(reused=False, reason='Rebuilt from original MAT at requested horizon.'))
                checked = verify_source_arrays(values, row['source'], stats, horizon)
                common_max = checked['source_point_count'] - max(horizons) - 2
                values['comparison_common_source_mask'] = values['source_index'] <= common_max
                stats['comparison_common_max_source_index'] = common_max
                stats['comparison_common_source_samples'] = int(values['comparison_common_source_mask'].sum())
                target = directory/f"{row['source'].stem}_L8_h{horizon}_residual.npz"
                write_dataset(target, values, stats)
                loaded = load_case(target)
                if not np.array_equal(loaded.X, values['X']) or not np.array_equal(loaded.y, values['y']):
                    raise ValueError(f'Written arrays changed: {target}')
                if digest(row['source']) != row['source_hash']:
                    raise ValueError(f'Original MAT changed: {row["source"]}')
                records.append(dict(file=target.name, case_id=row['global_id'], source_file=str(row['source']),
                    source_sha256=row['source_hash'], npz_sha256=digest(target), samples=len(values['y']),
                    common_source_samples=stats['comparison_common_source_samples'],
                    event_type=json.loads(stats['load_family_key'])['event_type'],
                    origin_dataset=row['origin'], load_family_key=stats['load_family_key']))
                checks.append(dict(file=target.name, **checked))
                del values, loaded
                if index % 50 == 0 or index == len(rows):
                    print(f'H{horizon} PREPARED {index}/{len(rows)}', flush=True)
            manifest = make_manifest(records, assignment, groups, horizon, args.seed, directory)
            split = output/f'split_h{horizon}.json'
            save_json(split, manifest)
            # Existing loader also checks source-pair/family isolation and shared timing contract.
            loaded_splits = load_splits(directory, split, include_test=False)
            del loaded_splits
            save_json(directory/'batch_summary.json', dict(created_at=now().isoformat(),
                history_steps=8, horizon_steps_to_target_interval_start=horizon,
                file_count=len(records), total_samples=sum(r['samples'] for r in records),
                feature_names=FEATURE_NAMES, files=records))
            save_json(directory/'validation_report.json', dict(status='passed', source_files_unchanged=True,
                all_labels_rebuilt_from_original_mat=True, files=checks))
            (directory/'README_CN.md').write_text(
                f'# H={horizon} 连续8点九通道数据\n\n生成时间：{now().isoformat()}，Asia/Singapore。\n'
                f'750份MAT重新生成，horizon={horizon}，history=8，30kHz，b0=20000。\n'
                '输入Vo,ILA,ILB,ILC,ILD,VREF,IREF,z2,Vin；IREF为每相值。\n'
                '标签 f_interval[k+H]-z2[k]，未来样本仅用于监督。没有复用H1标签或scaler。\n'
                'train拟合scaler及权重，val选优，test仅最终评价；同负载C/L变体与跨批次相同负载整族隔离。\n'
                f'划分：{json.dumps(manifest["summary"], ensure_ascii=False)}\n'
                f'清单：../{split.name}；common_source_mask按最大H={max(horizons)}限定共同源时刻。\n'
                '独立性相对于本次从头训练，不是新采集外部测试；所有原MAT和旧结果未改动。\n'
                'validation_report.json为逐元素源MAT/公式/时间索引验证。标签数据不代表闭环稳定性。\n', encoding='utf-8')
            report['runs'][str(horizon)] = dict(status='ready', data_dir=str(directory), split=str(split),
                summary=manifest['summary'], split_sha256=digest(split))
            save_json(output/'preparation_report.json', report)
            print('READY '+json.dumps(report['runs'][str(horizon)], ensure_ascii=False), flush=True)
        report.update(status='passed', finished_at=now().isoformat())
        save_json(output/'preparation_report.json', report)
        (output/'README_CN.md').write_text(
            '# 多预测步长实验数据\n\n'+json.dumps(report, ensure_ascii=False, indent=2)+'\n\n'
            '所有H使用同一整族划分；固定种子2026，不按预测/标签误差挑选测试集。\n'
            'comparison_common_source_mask用于H间同源时刻比较；各H训练保留所有有效标签。\n'
            '重建命令（E:/bisai、TCN）：`python prepare_horizon_experiment.py --horizons 15 16 20`。\n'
            '脚本首次新增，无旧文件可恢复；项目修改前备份见root README。\n', encoding='utf-8')
        return report
    except Exception as error:
        report.update(status='failed', error=str(error), finished_at=now().isoformat())
        save_json(output/'preparation_report.json', report)
        raise


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--horizons', type=int, nargs='+', default=[15, 16, 20])
    parser.add_argument('--old-labels', type=Path, default=ROOT/'data/train_500_labeled',
        help='仅用于核对原500来源及SHA，不读取其X/y作为新训练数据')
    parser.add_argument('--old-sources', type=Path, default=ROOT/'data/train_500')
    parser.add_argument('--new-sources', type=Path, default=ROOT/'data/数据集新')
    parser.add_argument('--output-dir', type=Path, help='精确覆盖默认路径选择，但已有目录拒绝覆盖')
    parser.add_argument('--seed', type=int, default=2026)
    result = prepare(parser.parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
