"""准备原500+新增250工况的650/100训练数据；只检查前向接口，不训练。"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from scipy.io import loadmat

from prepare_residual_labels import FEATURE_NAMES, _metadata_value, prepare_file, write_dataset
from ndp_tcn.data import read_case_metadata, load_case, load_splits, Scalers

ROOT = Path(__file__).resolve().parent
SOURCE_ID_FIELDS = ('batch_id', 'batch_case_id', 'case_id', 'case_group', 'paired_nominal_id', 'split_group')
PARAMETER_FIELDS = ('frequency_Hz', 'high_duty_fraction', 'low_power_W_at_12V', 'high_power_W_at_12V',
    'load_mode', 'output_C_factor', 'output_C_uF', 'input_C_unchanged_uF', 'L_factors', 'phase_L_uH',
    'controller_parameters_unchanged', 'complete_cycles', 'event_type', 'initial_power_W_at_12V',
    'final_power_W_at_12V', 'pulse_start_s', 'stop_time_s', 'slew_A_per_us',
    'transition_duration_s', 'reference_voltage_V', 'input_voltage_V')


def now():
    return datetime.now(timezone(timedelta(hours=8)))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def decorate_metadata(stats, meta, origin, global_id, source_hash, reused_from=None):
    from make_split_750 import family_key, LOAD_FAMILY_SCOPE
    result = dict(stats)
    result['case_parameters'] = {k: _metadata_value(meta[k]) for k in PARAMETER_FIELDS if k in meta}
    result['source_identity'] = {k: _metadata_value(meta[k]) for k in SOURCE_ID_FIELDS if k in meta}
    result['source_batch_case_id'] = int(meta['batch_case_id'])
    result['case_id'] = result['batch_case_id'] = int(global_id)
    result['source_case_id'] = int(meta['case_id'])
    result['case_id_field'] = 'collection global ID: old1..500, S501..700, T701..750'
    result['collection_id'] = 'ndp_training750_v1'
    result['origin_dataset'] = origin
    result['collection_prepared_at'] = now().isoformat()
    result['collection_builder_sha256'] = digest(__file__)
    result['source_sha256'] = source_hash
    result['load_family_scope'] = LOAD_FAMILY_SCOPE
    result['load_family_key'] = family_key(result)
    result['label_reuse'] = {'reused': reused_from is not None,
        'original_npz': str(reused_from) if reused_from is not None else None,
        'original_npz_sha256': digest(reused_from) if reused_from is not None else None,
        'numeric_arrays_unchanged': reused_from is not None}
    return result


def scan_sources(old_labels, old_sources, new_sources):
    old_files = sorted(old_labels.glob('*.npz'))
    added_files = sorted(p for p in new_sources.iterdir() if p.is_file() and p.suffix.lower()=='.mat')
    if len(old_files) != 500 or len(added_files) != 250:
        raise ValueError(f'Expected old500 labels and top-level new250 MAT, got {len(old_files)}/{len(added_files)}.')
    rows = []
    for file in old_files:
        stats = read_case_metadata(file)
        if stats['history_steps'] != 8 or stats['horizon_steps_to_target_interval_start'] != 1:
            raise ValueError('Existing500 must use L8/h1.')
        source = old_sources / Path(stats['source_file']).name
        if not source.is_file() or source.stem[0] not in 'NV':
            raise ValueError(f'Missing or unexpected old MAT: {source}')
        meta = loadmat(source, simplify_cells=True, variable_names=['meta'])['meta']
        source_hash = digest(source)
        if source_hash != stats['source_sha256']:
            raise ValueError(f'Old label/source SHA mismatch: {file.name}')
        rows.append(dict(source=source, old_npz=file, stats=stats, meta=meta, origin='old500',
                         global_id=int(stats['case_id']), source_hash=source_hash, filename=file.name))
    counts = Counter()
    for source in added_files:
        prefix = source.stem[:1]
        if prefix not in ('S', 'T'):
            raise ValueError(f'Unexpected top-level MAT; do not include support files: {source.name}')
        meta = loadmat(source, simplify_cells=True, variable_names=['meta'])['meta']
        local_id = int(meta['batch_case_id'])
        if not source.stem.startswith(f'{prefix}{local_id:03d}_'):
            raise ValueError(f'Filename and metadata ID disagree: {source.name}')
        if not 1 <= local_id <= (200 if prefix=='S' else 50):
            raise ValueError('New batch ID outside expected range.')
        counts[prefix] += 1
        rows.append(dict(source=source, old_npz=None, stats=None, meta=meta,
            origin='supplement200' if prefix=='S' else 'step50',
            global_id=local_id+(500 if prefix=='S' else 700),source_hash=digest(source),
            filename=source.stem+'_L8_h1_residual.npz'))
    if counts != {'S':200,'T':50}:
        raise ValueError(f'Expected S200/T50, got {dict(counts)}')
    if {r['global_id'] for r in rows} != set(range(1,751)):
        raise ValueError('Global IDs must be unique1..750.')
    if len({r['source_hash'] for r in rows}) != 750:
        raise ValueError('Byte-identical source MAT duplicates found.')
    if len({r['filename'].casefold() for r in rows}) != 750:
        raise ValueError('Duplicate destination filename.')
    for r in rows:
        m=r['meta']
        if not bool(m.get('all_checks_pass',False)):
            raise ValueError(f"Source audit not passed: {r['source'].name}")
        for field, expected in [('sample_frequency_Hz',30000),('switching_frequency_Hz',30000),
                                ('b0',20000),('wc',5000),('wo',14000)]:
            if float(m[field]) != expected:
                raise ValueError(f"Incompatible {field}: {r['source'].name}")
    return sorted(rows,key=lambda r:r['global_id'])


def verify_source_arrays(values, source, stats):
    raw = loadmat(source, simplify_cells=True, variable_names=['data','meta'])
    data, meta = raw['data'], raw['meta']
    x=np.asarray(data['features'],dtype=np.float64);t=np.asarray(data['time'],dtype=np.float64).reshape(-1)
    if tuple(data['feature_names']) != FEATURE_NAMES or x.shape != (len(t),9):
        raise ValueError(f'Wrong source shape/channels: {source.name}')
    if not np.isfinite(x).all() or not np.isfinite(t).all() or not np.allclose(np.diff(t),1/30000,rtol=1e-5,atol=1e-12):
        raise ValueError(f'Invalid source arrays: {source.name}')
    k=np.asarray(values['source_index']);j=k+1
    eligible=np.arange(7,len(t)-2,dtype=np.int64)
    valid=np.asarray(data['valid'],dtype=bool).reshape(-1)
    eligible=eligible[(t[eligible]>=stats['minimum_source_time_s']) & valid[eligible]]
    if not np.array_equal(k,eligible):
        raise ValueError(f'Missing or extra eligible windows: {source.name}')
    expected_x=x[k[:,None]+np.arange(-7,1)].astype(np.float32)
    interval=(x[j+1,0]-x[j,0])/(t[j+1]-t[j])-float(meta['b0'])*x[j,6]
    expected_y=(interval-x[k,7]).astype(np.float32)[:,None]
    pairs=[(values['X'],expected_x),(values['y'],expected_y),(values['target_interval_index'],j),
           (values['source_time_s'],t[k]),(values['target_start_time_s'],t[j]),
           (values['target_end_time_s'],t[j+1]),(values['source_z2_V_per_s'],x[k,7]),
           (values['target_disturbance_V_per_s'],interval)]
    if any(not np.array_equal(a,b) for a,b in pairs):
        raise ValueError(f'Exact raw-source label/index verification failed: {source.name}')
    return dict(source_arrays_verified=True,label_formula_exact=True,all_eligible_windows_present=True,
                samples=len(k),minimum_source_time_s=stats['minimum_source_time_s'])


def readiness_check(data_dir, split_path, report_dir):
    import torch
    from ndp_tcn.model import TiNpuConfig, build_model
    torch.set_num_threads(2);torch.manual_seed(2026)
    splits=load_splits(data_dir,split_path,include_test=True)
    if [len(splits[k]) for k in ('train','val','test')] != [650,0,100]:
        raise ValueError('Expected650 train/0val/100 selection cases.')
    scalers=Scalers.fit(splits['train'])
    assert set(scalers.fit_case_ids)=={c.case_id for c in splits['train']}
    assert not set(scalers.fit_case_ids)&{c.case_id for c in splits['test']}
    batch=np.stack([cases[0].X[0] for cases in (splits['train'],splits['test'])])
    inputs=torch.from_numpy(scalers.transform_x(batch))
    model=build_model(TiNpuConfig(),'ti_npu');model.eval()
    before={k:v.clone() for k,v in model.state_dict().items()}
    with torch.inference_mode():
        output=model(inputs)
    assert tuple(output.shape)==(2,1) and torch.isfinite(output).all()
    assert all(torch.equal(before[k],v) for k,v in model.state_dict().items())
    assert all(p.grad is None for p in model.parameters())
    report=dict(status='passed',created_at=now().isoformat(),training_started=False,
        optimizer_created=False,optimizer_steps=0,forward_only=True,checkpoint_written=False,
        backend='ti_npu',python=sys.version,python_executable=sys.executable,torch_version=torch.__version__,
        file_counts={k:len(v) for k,v in splits.items()},
        window_counts={k:sum(len(c.X) for c in v) for k,v in splits.items()},
        input_shape=list(inputs.shape),output_shape=list(output.shape),network_parameters=sum(p.numel() for p in model.parameters()),
        scaler_fit_case_ids=list(scalers.fit_case_ids),
        scaler_note='只为检查数据和前向接口临时拟合，未保存为训练scaler；正式训练重新仅用train拟合。')
    save_json(report_dir/'training_readiness.json',report)
    return report


def prepare(args):
    from make_split_750 import create_split
    old_labels=args.old_labels.resolve();old_sources=args.old_sources.resolve();new_sources=args.new_sources.resolve()
    output=args.output_dir.resolve();split_path=args.split.resolve()
    if output.exists() or split_path.exists() or split_path.with_suffix('.README_CN.md').exists():
        raise FileExistsError('Refusing to overwrite existing750 labels or split. Select new output paths for regeneration.')
    report_dir=(args.report_dir or ROOT/'ndp_tcn/results'/('prepare_750_'+now().strftime('%Y%m%d_%H%M%S'))).resolve()
    report_dir.mkdir(parents=True,exist_ok=True)
    if (report_dir/'dataset_preparation.json').exists():
        raise FileExistsError('Preparation report already exists; use a new report directory.')
    report=dict(created_at=now().isoformat(),status='preflight',training_started=False,
        old_labels=str(old_labels),old_sources=str(old_sources),new_sources=str(new_sources),
        output_dir=str(output),split=str(split_path),test_count=100,train_count=650,
        preparation_script_sha256=digest(__file__),label_generator_sha256=digest(ROOT/'prepare_residual_labels.py'))
    save_json(report_dir/'dataset_preparation.json',report)
    try:
        rows=scan_sources(old_labels,old_sources,new_sources)
        save_json(report_dir/'source_inventory.json',[dict(source=str(r['source']),source_sha256=r['source_hash'],
            origin_dataset=r['origin'],global_case_id=r['global_id'],target_filename=r['filename'],
            source_identity={k:_metadata_value(r['meta'][k]) for k in SOURCE_ID_FIELDS}) for r in rows])
        output.mkdir(parents=True,exist_ok=False)
        prepared=[];verifications=[]
        for index,row in enumerate(rows,1):
            if row['old_npz'] is not None:
                with np.load(row['old_npz'],allow_pickle=False) as archive:
                    values={k:archive[k] for k in archive.files if k not in ('metadata_json','feature_names')}
                stats=dict(row['stats'])
            else:
                # 单次阶跃在40~100ms，保留40ms到阶跃之间的正常段；不使用pulse_region筛选。
                values,stats=prepare_file(row['source'],history=8,horizon=1,
                    start_time=.04 if row['origin']=='step50' else None)
            stats=decorate_metadata(stats,row['meta'],row['origin'],row['global_id'],row['source_hash'],row['old_npz'])
            stats['source_file']=str(row['source'])
            verified=verify_source_arrays(values,row['source'],stats)
            if digest(row['source']) != row['source_hash']:
                raise ValueError(f"Source changed while preparing: {row['source']}")
            target=output/row['filename'];write_dataset(target,values,stats)
            loaded=load_case(target)
            if not np.array_equal(loaded.X,values['X']) or not np.array_equal(loaded.y,values['y']):
                raise ValueError(f'Written dataset differs: {target.name}')
            if row['old_npz'] and digest(row['old_npz'])!=stats['label_reuse']['original_npz_sha256']:
                raise ValueError('Old label was changed during reuse.')
            prepared.append(dict(filename=target.name,case_id=row['global_id'],origin_dataset=row['origin'],
                source_file=str(row['source']),source_sha256=row['source_hash'],samples=len(values['X']),
                load_family_key=stats['load_family_key'],source_batch_case_id=stats['source_batch_case_id']))
            verifications.append(dict(filename=target.name,case_id=row['global_id'],**verified))
            del loaded,values
            if index%25==0 or index==750:
                print(f'PREPARED {index}/750, cumulative_windows={sum(r["samples"] for r in prepared)}',flush=True)
        summary=dict(created_at=now().isoformat(),file_count=750,total_samples=sum(r['samples'] for r in prepared),
            source_counts=dict(Counter(r['origin_dataset'] for r in prepared)),history_steps=8,horizon_steps=1,
            feature_names=FEATURE_NAMES,files=prepared,training_started=False)
        save_json(output/'batch_summary.json',summary)
        validation=dict(status='passed',created_at=now().isoformat(),source_count=750,
            source_files_unchanged=True,old500_numeric_labels_reused_without_change=True,files=verifications)
        save_json(output/'validation_report.json',validation)
        manifest=create_split(output,split_path,args.old_split.resolve(),seed=args.seed,test_count=100)
        readiness=readiness_check(output,split_path,report_dir)
        report.update(status='ready_not_trained',finished_at=now().isoformat(),files=750,
            samples=summary['total_samples'],split_counts=readiness['file_counts'],window_counts=readiness['window_counts'])
        save_json(report_dir/'dataset_preparation.json',report)
        save_json(report_dir/'split_summary.json',manifest.get('summary',{}))
        (output/'README_CN.md').write_text(
            '# 750工况训练数据\n\n原500+新增S200/T50，共750份，'+str(summary['total_samples'])+'个窗口。\n'
            '已准备650训练/100验证选优，尚未训练。各窗口为[8,9]、目标[1]，残差单位V/s。\n'
            '旧500标签数值未改；S/T新增标签采用同一L8/h1定义。原MAT、旧标签与权重保持不变。\n'
            '批次内ID冲突已转换为全局1..750，source_identity保留源编号与配对关系。\n'
            '按跨批次负载族完整划分，不随机拆窗口；部分长恒定负载包含旧DC相同前缀，保留且同侧。\n'
            '详情见项目根README_BATCH750_CN.md、configs/ndp_tcn_split_750.README_CN.md。\n'
            'batch_summary.json列来源与窗口数；validation_report.json记录全部源公式/索引逐元素验证。\n',encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
        return report
    except Exception as error:
        report.update(status='failed',error=str(error),finished_at=now().isoformat())
        save_json(report_dir/'dataset_preparation.json',report)
        raise


def main():
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8',errors='replace')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old-labels',type=Path,default=ROOT/'data/train_500_labeled')
    parser.add_argument('--old-sources',type=Path,default=ROOT/'data/train_500')
    parser.add_argument('--new-sources',type=Path,default=ROOT/'data/数据集新')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'data/train_750_labeled')
    parser.add_argument('--split',type=Path,default=ROOT/'configs/ndp_tcn_split_750.json')
    parser.add_argument('--old-split',type=Path,default=ROOT/'configs/ndp_tcn_split_500.json')
    parser.add_argument('--report-dir',type=Path)
    parser.add_argument('--seed',type=int,default=2026)
    prepare(parser.parse_args())


if __name__=='__main__':
    main()
