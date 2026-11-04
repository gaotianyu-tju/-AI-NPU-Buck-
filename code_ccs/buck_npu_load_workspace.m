% Load the model's existing exported Simulink.Signal definitions when needed.
% Preserve variables already present, so interactive tuning is not overwritten.
buckWorkspaceFolder=fileparts(get_param(bdroot,'FileName'));
addpath(buckWorkspaceFolder);
buck_npu_build_environment;
buck_npu_configure_paths(bdroot);
buckWorkspaceData=load(fullfile(buckWorkspaceFolder,'buck_NPU_MBD_workspace.mat'));
buckWorkspaceNames=fieldnames(buckWorkspaceData);
for buckWorkspaceIndex=1:numel(buckWorkspaceNames)
    buckWorkspaceName=buckWorkspaceNames{buckWorkspaceIndex};
    if ~evalin('base',sprintf('exist(''%s'',''var'')',buckWorkspaceName))
        assignin('base',buckWorkspaceName,buckWorkspaceData.(buckWorkspaceName));
    end
end
clear buckWorkspaceFolder buckWorkspaceData buckWorkspaceNames buckWorkspaceIndex buckWorkspaceName


