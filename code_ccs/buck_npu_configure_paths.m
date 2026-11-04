function buck_npu_configure_paths(model)
% Resolve local build inputs from this model's actual folder.
% Called by InitFcn, so moving the complete folder does not retain old paths.
folder=fileparts(get_param(model,'FileName'));
sdk='D:/ti/c2000/C2000Ware_26_02_00_00';
sources={'buck_npu.c','buck_npu_sdk_port.c','buck_npu_platform.c', ...
    'buck_load_observer.c','buck_npu_compensation.c'};
for k=1:numel(sources)
    assert(isfile(fullfile(folder,sources{k})),'Missing v15 source: %s',sources{k});
end
inc=strjoin({folder,[sdk '/device_support/f28p55x/common/include'], ...
    [sdk '/driverlib/f28p55x/driverlib']},newline);
src=strjoin(cellfun(@(n)fullfile(folder,n),sources,'UniformOutput',false),newline);
lib=strjoin({fullfile(folder,'mod.a'),fullfile(folder,'buck_npu_sections.cmd')},newline);
settings={'CustomInclude',inc;'CustomSource',src;'CustomLibrary',lib; ...
    'CustomHeaderCode',sprintf('#include "buck_npu.h"\n#include "buck_npu_platform.h"'); ...
    'CustomInitializer','buck_npu_platform_init();'; ...
    'PostCodeGenCommand','buck_npu_post_codegen(buildInfo); codertarget.postCodeGenHookCommand(h);'};
for k=1:size(settings,1)
    if ~strcmp(get_param(model,settings{k,1}),settings{k,2})
        set_param(model,settings{k,1},settings{k,2});
    end
end
end
