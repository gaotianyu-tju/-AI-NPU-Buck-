function prepare_ai700
root=fileparts(mfilename('fullpath'));cd(root);d=fullfile(root,char([25968 25454 38598 95 33033 20914 36127 36733]));s=fullfile(d,'support700');src='buck_ADRC_fangzhen_AI_LADRC';m='ai700_source';target=fullfile(s,[m '.slx']);assert(~exist(target,'file'));load_system(fullfile(root,[src '.slx']));save_system(src,target);close_system(src,0);load_system(target);cleanup=onCleanup(@()close_system(m,0));
% Instrumentation only: no controller, plant or solver settings changed.
set_param(m,'SignalLogging','on');g=find_system(m,'SearchDepth',1,'BlockType','Goto');tags={'Vo','ILA','ILB','ILC','ILD'};
for k=1:numel(g)
 tag=get_param(g{k},'GotoTag');if ~any(strcmp(tag,tags)),continue;end
 ph=get_param(g{k},'PortHandles');ln=get_param(ph.Inport,'Line');set_param(get_param(ln,'SrcPortHandle'),'DataLogging','on','DataLoggingLimitDataPoints','off','DataLoggingNameMode','Custom','DataLoggingName',['batch_' tag]);
end
ph=get_param([m '/Dataset_Current_Command'],'PortHandles');set_param(ph.Outport,'DataLogging','on','DataLoggingLimitDataPoints','off','DataLoggingNameMode','Custom','DataLoggingName','batch_load_command');save_system(m);
end
