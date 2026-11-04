function build_buck_npu
% Rebuild this model from generated code; do not flash or start the board.
% Force regeneration because the original hardware support package still
% remembers SDK 5.02, whereas this project's post-codegen hook selects 26.02.
% Reusing its incremental buildInfo can otherwise merge both SDK source lists.
folder=fileparts(mfilename('fullpath'));
previousFolder=pwd;
restoreFolder=onCleanup(@()cd(previousFolder));
cd(folder);
addpath(folder);
buck_npu_build_environment;
model='buck_ADRC_MBD_NPU_24b';
load_system(fullfile(folder,[model '.slx']));
buildFailure=[];
logText=evalc('try; slbuild(model,''ForceTopModelBuild'',true); catch buildFailure; disp(getReport(buildFailure,''extended'',''hyperlinks'',''off'')); end');
logFile=fopen(fullfile(folder,'NPU_build_log.txt'),'w','n','UTF-8');
assert(logFile>=0,'Cannot write build log');
fprintf(logFile,'%s',logText);
fclose(logFile);
if ~isempty(buildFailure)
    fprintf('%s\n',logText(max(1,end-5000):end));
    rethrow(buildFailure);
end
save_system(model);
fprintf('%s\n',logText(max(1,end-1800):end));
fprintf('NPU model build passed. Full log: %s\n',fullfile(folder,'NPU_build_log.txt'));
end
