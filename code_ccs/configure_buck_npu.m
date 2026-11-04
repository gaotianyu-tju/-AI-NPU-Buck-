function configure_buck_npu
% Restore ONLY the v15 build configuration. Does not replace chart algorithms.
folder=fileparts(mfilename('fullpath'));
addpath(folder);
model='buck_ADRC_MBD_NPU_24b';
load_system(fullfile(folder,[model '.slx']));
assert(strcmp(get_param(model,'FileName'),fullfile(folder,[model '.slx'])), ...
    'A same-name model from another folder is open; close it before configuring.');
buck_npu_configure_paths(model);
set_param(model,'InitFcn', ...
    'run(fullfile(fileparts(get_param(bdroot,''FileName'')),''buck_npu_load_workspace.m''));');
save_system(model);
fprintf('v15 MBD build paths saved: %s\n',get_param(model,'FileName'));
end
