"""Read-only checks of the final MBD-generated release; Python standard library only.
Run: python verification/verify_delivery.py
No device access, no flashing, no control parameter writes.
"""
from pathlib import Path
import hashlib, json, re, zipfile

P=Path(__file__).resolve().parents[1]
G=P/'buck_ADRC_MBD_NPU_24b_ert_rtw'
NAME='buck_ADRC_MBD_NPU_24b'
def read(p): return p.read_text(encoding='utf-8',errors='replace')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

R={'version':16,'validation_scope':'Local delivery build and static verification; no new DSP flash/load test.'}
baseline=json.loads(read(P/'verification'/'source_equivalence.json'))
checks={}
for name,row in baseline.items():
    if name.endswith('.slx'): continue  # Build saves relocated absolute CustomInclude/Library paths.
    checks[name]=sha(P/name)==row['delivery_sha256']
assert all(checks.values()), checks
R['delivered_sources_match_annotated_manifest']=checks
controller=read(G/(NAME+'.c'))
order=['buck_npu_begin(','buck_npu_apply_prediction(','buck_npu_commit(',
       'EPwm1Regs.CMPA.bit.CMPA =','EPwm10Regs.CMPA.bit.CMPA =',
       'EPwm2Regs.CMPA.bit.CMPA =','EPwm7Regs.CMPA.bit.CMPA =']
positions=[controller.index(x) for x in order]
assert positions==sorted(positions)
assert controller.index('GpioDataRegs.GPACLEAR.bit.GPIO22 =',positions[-1])>positions[-1]
for call in order[:3]: assert controller.count(call)==1,call
assert 'tvmgen_default_run(' not in controller and 'buck_npu_service(' not in controller
assert read(G/'ert_main.c').count('buck_npu_service();')==1
R['control_order']=order+['GPIO22 low']
R['inference_worker_in_main_only']=True
assert 'buck_npu_io_revision=16U' in read(P/'buck_npu.c')
make=read(G/(NAME+'.mk'))
objects=re.search(r'^OBJS\s*=\s*(.+)$',make,re.M).group(1).split()
assert len(objects)==len(set(objects))
for n in ('buck_npu','buck_load_observer','buck_npu_compensation'):
    assert n+'.obj' not in objects
    assert n+'_v15_o2.obj' in make
    assert (G/(n+'_v15_o2.obj')).stat().st_mtime >= (P/(n+'.c')).stat().st_mtime
assert 'ndp_model_io_strict.obj' in make and 'ndp_model_io.obj' not in objects
assert 'Desktop/buck_LADRC_NPU' not in make.replace('\\','/')
R['current_optimized_objects_without_duplicates']=True
mt=read(G/(NAME+'.map'))
def region(n):
    m=re.search(r'^\s*'+n+r'\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)',mt,re.M)
    assert m,n
    x=dict(zip(['origin','length','used','unused'],[int(v,16) for v in m.groups()]))
    assert x['used']<=x['length'] and x['used']+x['unused']==x['length']
    return x
R['memory_in_C28_words']={n:region(n) for n in ('FLASH_BANK0_SEC0','RAMGS_DATA','RAMM0M1')}
R['model_sections']={}
for sec,reg in [('.rodata.tvm','FLASH_BANK0_SEC0'),('.bss.noinit.tvm','RAMGS_DATA'),('.bss.noinit.buck_npu','RAMGS_DATA')]:
    m=re.search('^'+re.escape(sec)+r'\s*\n\*\s+\d\s+([0-9a-f]+)\s+([0-9a-f]+)',mt,re.M)
    assert m,sec
    addr,size=[int(v,16) for v in m.groups()];r=R['memory_in_C28_words'][reg]
    assert r['origin']<=addr and addr+size<=r['origin']+r['length'] and addr%8==0
    R['model_sections'][sec]={'address':addr,'length':size,'region':reg}
R['outputs']={ext:sha(P/(NAME+ext)) for ext in ('.slx','.out','.elf','.hex')}
assert R['outputs']['.out']==R['outputs']['.elf']
# Before annotation, original final v16 firmware had this exact Intel HEX image.
R['hex_identical_to_original_final_v16']=R['outputs']['.hex']=='4d2dc669501953e1eccccffefcd9a59dff5eae60cd1544323ae453e612c5e198'
assert R['hex_identical_to_original_final_v16']
assert 'Successful completion of build procedure' in read(P/'NPU_build_log.txt')
R['full_build_pass']=True
print(json.dumps(R,ensure_ascii=False,indent=2))
