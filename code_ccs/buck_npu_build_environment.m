function buck_npu_build_environment
% Work around the existing generated batch-file drive-map helper returning
% an empty mlEnv. Use the user's EXISTING E: MATLAB mapping, never create it.
% Set only this MATLAB process's child-build environment (not Windows globals).
if contains(matlabroot,' ') && isempty(getenv('MATLAB_ROOT'))
    mappedRoot='E:';
    localInfo=fullfile(matlabroot,'VersionInfo.xml');
    mappedInfo=fullfile([mappedRoot filesep],'VersionInfo.xml');
    assert(isfile(mappedInfo) && isfile(fullfile([mappedRoot filesep],'bin','matlab.exe')), ...
        'BuckNPU:MatlabMapping','The existing E: MATLAB mapping is unavailable. Restore the mapping to this MATLAB installation before building.');
    assert(strcmp(fileread(localInfo),fileread(mappedInfo)), ...
        'BuckNPU:MatlabVersion','E: points to a different MATLAB version. Check the existing mapping.');
    setenv('MATLAB_ROOT',mappedRoot);
    setenv('ALT_MATLAB_ROOT',mappedRoot);
    setenv('MATLAB_BIN',[mappedRoot '\bin']);
    setenv('ALT_MATLAB_BIN',[mappedRoot '\bin']);
end
end
