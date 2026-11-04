function buck_npu_compile_v15_objects(buildInfo,projectFolder)
% Preserve the working CCS v15 per-file O2 settings. The MBD controller and
% hardware support files keep their existing compiler options.
cgt='D:/ti/ccs1281/ccs/tools/compiler/ti-cgt-c2000_22.6.1.LTS';
assert(isfile([cgt '/bin/cl2000.exe']), ...
    'BuckNPU:CompilerMissing','The v15 CCS C2000 compiler was not found: %s',cgt);
names={'buck_npu','buck_load_observer','buck_npu_compensation'};
includes=buildInfo.getIncludePaths(true);
includes=[{projectFolder,pwd,'D:/ti/ti-cgt-c2000_22.6.0.LTS/include'}, ...
    includes(:)',{[cgt '/include']}];
includeFlags=strjoin(cellfun(@(p)sprintf('--include_path="%s"',p), ...
    includes,'UniformOutput',false),' ');
defineFlags=strjoin(buildInfo.getDefines(),' ');
for k=1:numel(names)
    sourceName=[names{k} '.c'];
    objectName=[names{k} '_v15_o2.obj'];
    command=sprintf(['"%s/bin/cl2000.exe" --compile_only --abi=eabi ' ...
        '-v28 -ml -mt --cla_support=cla2 --float_support=fpu32 ' ...
        '--tmu_support=tmu1 --vcu_support=vcrc --fp_mode=relaxed ' ...
        '--opt_level=2 %s %s --output_file="%s" "%s"'], ...
        cgt,includeFlags,defineFlags,fullfile(pwd,objectName), ...
        fullfile(projectFolder,sourceName));
    [status,compilerOutput]=system(command);
    assert(status==0,'BuckNPU:V15ObjectBuild', ...
        'v15 optimized source failed: %s\n%s',sourceName,compilerOutput);
    if ~isempty(strtrim(compilerOutput)), fprintf('%s\n',compilerOutput); end
    % Prevent a second, unoptimized copy in the ordinary source list.
    remove=false(size(buildInfo.Src.Files));
    for j=1:numel(buildInfo.Src.Files)
        remove(j)=strcmp(buildInfo.Src.Files(j).FileName,sourceName);
    end
    buildInfo.Src.Files=buildInfo.Src.Files(~remove);
    found=[];
    for j=1:numel(buildInfo.LinkObj)
        if strcmp(buildInfo.LinkObj(j).Name,objectName), found(end+1)=j; end %#ok<AGROW>
    end
    assert(numel(found)<=1,'BuckNPU:DuplicateV15Object', ...
        'Duplicate v15 optimized object: %s',objectName);
    if isempty(found)
        buildInfo.addLinkObjects(objectName,pwd,1000,true,true);
    else
        obj=buildInfo.LinkObj(found);
        obj.Path=pwd; obj.Precompiled=true; obj.LinkOnly=true; obj.LinkPriority=1000;
    end
    fprintf('Buck NPU: v15 O2 / CGT 22.6.1 preserved for %s\n',sourceName);
end
end
