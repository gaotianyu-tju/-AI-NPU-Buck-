function buck_npu_post_codegen(buildInfo)
% Model-local SDK selection: no change to MATLAB's global TI preferences.
% Keep all source, header and library paths in this build on SDK 26.02.
sdk = 'D:/ti/c2000/C2000Ware_26_02_00_00';
assert(isfolder(sdk),'C2000Ware 26.02 not found: %s',sdk);
mods = {buildInfo.Inc,buildInfo.Src,buildInfo.Other,buildInfo.SysLib};
for k=1:numel(mods)
    v=mods{k};
    for j=1:numel(v.Paths)
        v.Paths(j).Value = replaceSDK(v.Paths(j).Value,sdk);
    end
    for j=1:numel(v.Files)
        v.Files(j).Path = replaceSDK(v.Files(j).Path,sdk);
    end
end
for j=1:numel(buildInfo.LinkObj)
    buildInfo.LinkObj(j).Path=replaceSDK(buildInfo.LinkObj(j).Path,sdk);
end
collections={buildInfo.Tokens,buildInfo.BuildArgs,buildInfo.MakeVars};
for k=1:numel(collections)
    v=collections{k};
    for j=1:numel(v)
        v(j).Value=replaceSDK(v(j).Value,sdk);
    end
end
% Incremental builds may merge old-SDK dependencies with cached new-SDK
% dependencies. After path replacement they are the SAME source file.
% Remove only identical full paths; never hide different same-name sources.
srcFiles=buildInfo.Src.Files;
sourceKeys=cell(numel(srcFiles),1);
for j=1:numel(srcFiles)
    sourceKeys{j}=lower(strrep(fullfile(srcFiles(j).Path,srcFiles(j).FileName),'\','/'));
end
[~,keep]=unique(sourceKeys,'stable');
removed=numel(srcFiles)-numel(keep);
buildInfo.Src.Files=srcFiles(sort(keep));
fprintf('Buck NPU: removed %d duplicate source entries after SDK path normalization.\n',removed);
fprintf('Buck NPU: build dependencies selected from %s\n',sdk);
% H15 FPU32 split-mean preprocessing uses strict FP, unlike the unchanged MBD
% controller build flags. Compile just this file with its own options each build.
projectFolder=fileparts(mfilename('fullpath'));
cgt='D:/ti/ti-cgt-c2000_22.6.0.LTS';
objectName='ndp_model_io_strict.obj';
objectPath=fullfile(pwd,objectName);
command=sprintf('"%s/bin/cl2000.exe" --compile_only --abi=eabi --float_support=fpu32 -v28 -ml --c99 --opt_level=2 --fp_mode=strict --include_path="%s/include" --include_path="%s" --output_file="%s" "%s"', ...
    cgt,cgt,projectFolder,objectPath,fullfile(projectFolder,'ndp_model_io.c'));
[status,compilerOutput]=system(command);
assert(status==0,'BuckNPU:StrictIOBuild','H15 strict preprocessing compile failed: %s',compilerOutput);
% LinkObj is a read-only collection. Reuse its existing handle on incremental
% builds; only add a new object when absent. Never delete/assign the collection.
existingObject=[];
for j=1:numel(buildInfo.LinkObj)
    if strcmp(buildInfo.LinkObj(j).Name,objectName)
        existingObject(end+1)=j; %#ok<AGROW>
    end
end
assert(numel(existingObject)<=1,'BuckNPU:DuplicateStrictIO', ...
    'Multiple H15 strict IO objects found in cached build information.');
if isempty(existingObject)
    buildInfo.addLinkObjects(objectName,pwd,1000,true,true);
else
    linkObject=buildInfo.LinkObj(existingObject);
    linkObject.Path=pwd;
    linkObject.Precompiled=true;
    linkObject.LinkOnly=true;
    linkObject.LinkPriority=1000;
end
fprintf('Buck NPU: H15 FPU32 preprocessing compiled separately with strict FP.\n');
buck_npu_compile_v15_objects(buildInfo,projectFolder);
% Refuse to build an old chart accidentally paired with the v15 C runtime.
controllerFile=fullfile(pwd,'buck_ADRC_MBD_NPU_24b.c');
controllerText=fileread(controllerFile);
assert(count(controllerText,'buck_npu_apply_prediction(')==1, ...
    'BuckNPU:WrongChart','Expected exactly one v15 prediction handoff call.');
assert(count(controllerText,'buck_npu_begin(')==1 && ...
       count(controllerText,'buck_npu_commit(')==1, ...
    'BuckNPU:WrongChart','Expected exactly one begin/commit per control step.');
assert(~contains(controllerText,'buck_npu_service(') && ...
       ~contains(controllerText,'tvmgen_default_run('), ...
    'BuckNPU:InferenceInISR','Background inference must not enter the control ISR.');
% The original v15 board code restores these six analog inputs after the
% support package clears AMSEL. Keep that initialization on EVERY generation.
boardFile=fullfile(pwd,'MW_c28xx_board.c');
boardText=fileread(boardFile);
analogNeedle='  GpioCtrlRegs.GPHAMSEL.all = 0U;';
assert(count(boardText,analogNeedle)==1,'BuckNPU:BoardSignature', ...
    'Expected one AMSEL initialization; inspect new support-package output.');
if ~contains(boardText,'GpioCtrlRegs.GPHAMSEL.bit.GPIO225 = 1U;')
    analogRestore=sprintf(['\n  /* Restore ADC analog inputs (v15 MBD build hook) */\n' ...
        '  GpioCtrlRegs.GPHAMSEL.bit.GPIO225 = 1U; /* A4 */\n' ...
        '  GpioCtrlRegs.GPHAMSEL.bit.GPIO249 = 1U; /* A5 */\n' ...
        '  GpioCtrlRegs.GPHAMSEL.bit.GPIO253 = 1U; /* C11 */\n' ...
        '  GpioCtrlRegs.GPHAMSEL.bit.GPIO230 = 1U; /* C10 */\n' ...
        '  GpioCtrlRegs.GPHAMSEL.bit.GPIO226 = 1U; /* B2 */\n' ...
        '  GpioCtrlRegs.GPHAMSEL.bit.GPIO237 = 1U; /* B10 */']);
    boardText=strrep(boardText,analogNeedle,[analogNeedle analogRestore]);
    fh=fopen(boardFile,'w'); assert(fh>=0,'Cannot write generated board source');
    fprintf(fh,'%s',boardText); fclose(fh);
end
pins=[225 249 253 230 226 237];
for pin=pins
    assert(count(boardText,sprintf('GpioCtrlRegs.GPHAMSEL.bit.GPIO%d = 1U;',pin))==1, ...
        'BuckNPU:AnalogPin','Missing/duplicate v15 analog input GPIO%d',pin);
end
% Inject the background worker into the generated main loop. Code generation
% recreates ert_main.c, so this runs on every build before compilation.
mainFile=fullfile(pwd,'ert_main.c');
assert(isfile(mainFile),'Buck NPU: generated ert_main.c not found: %s',mainFile);
mainText=fileread(mainFile);
needle='  while (runModel) {';
assert(count(mainText,needle)==1,'Buck NPU: main-loop signature changed');
if ~contains(mainText,'buck_npu_service();')
    mainText=strrep(mainText,needle,sprintf('%s\n    buck_npu_service();',needle));
    mainText=strrep(mainText,'#include "rtwtypes.h"', ...
        sprintf('#include "rtwtypes.h"\n#include "buck_npu.h"'));
    fh=fopen(mainFile,'w');
    assert(fh>=0,'Buck NPU: cannot patch generated main');
    fprintf(fh,'%s',mainText);
    fclose(fh);
end
assert(count(mainText,'buck_npu_service();')==1, ...
    'BuckNPU:DuplicateWorker','Expected exactly one main-loop worker.');
end

function out=replaceSDK(in,sdk)
out=in;
if ischar(in)
    old={'D:/ti/c2000/C2000Ware_5_02_00_00', ...
         'D:\ti\c2000\C2000Ware_5_02_00_00'};
    for j=1:numel(old), out=strrep(out,old{j},sdk); end
end
end

