function run_ai700_worker(worker_id,worker_count,only_ids,simulation_mode)
root=fileparts(mfilename('fullpath'));cd(root);assert(strcmp(version('-release'),'2024b'));
d=fullfile(root,char([25968 25454 38598 95 33033 20914 36127 36733]));s=fullfile(d,'support700');
w=fullfile(s,sprintf('worker_%02d',worker_id));if ~exist(w,'dir'),mkdir(w);end
diary(fullfile(w,'worker_log.txt'));c1=onCleanup(@()diary('off'));
% Isolate the logging repository; no simulation/solver parameters changed.
sdiFolder=fullfile(w,'sdi');if ~exist(sdiFolder,'dir'),mkdir(sdiFolder);end
Simulink.sdi.setStorageLocation(sdiFolder);Simulink.sdi.setStorageMode('memory');

Simulink.fileGenControl('set','CacheFolder',fullfile(w,'cache'),'CodeGenFolder',fullfile(w,'codegen'),'createDir',true);
plan=jsondecode(fileread(fullfile(s,'plan700.json')));
src='ai700_source';m=sprintf('ai700_w%02d',worker_id);
load_system(fullfile(s,[src '.slx']));save_system(src,fullfile(w,[m '.slx']));close_system(src,0);
load_system(fullfile(w,[m '.slx']));c2=onCleanup(@()close_model(m));
if nargin>=4,set_param(m,'SimulationMode',simulation_mode);end
set_param(m,'StartTime','0','FastRestart','on');
if nargin>=3 && ~isempty(only_ids),ids=only_ids;else,ids=worker_id:worker_count:700;end
fail=0;done=0;
for id=ids
 r=plan.rows(id);name=ai700_filename(r);file=fullfile(d,name);
 if exist(file,'file')
  a=load(file,'meta','checks');assert(a.meta.batch_case_id==id&&a.meta.all_checks_pass);done=done+1;continue;
 end
 fprintf('START id=%d %s\n',id,name);t0=tic;
 try
  [data,meta,checks,diagnostics,row]=one_case(m,r,plan,root,s);
  meta.source_sha256=plan.source_sha256;meta.current_Kp=.02;meta.current_Ki=.00025;meta.worker_id=worker_id;meta.total_wall_seconds=toc(t0);
  tmp=fullfile(w,sprintf('case_%03d.partial.mat',id));save(tmp,'data','meta','checks','diagnostics','-v7');
  movefile(tmp,file);save(fullfile(w,sprintf('summary_%03d.mat',id)),'row');
  done=done+1;fprintf('DONE id=%d samples=%d valid=%d wall=%.1fs\n',id,numel(data.time),sum(data.valid),toc(t0));
  try,preview_case(data,meta,fullfile(d,'previews',strrep(name,'.mat','.png')));catch err,fprintf('PREVIEW ERROR %s\n',err.message);end
  clear data meta checks diagnostics row;Simulink.sdi.clear;
 catch err
  fail=fail+1;fid=fopen(fullfile(w,sprintf('error_%03d.txt',id)),'w');fprintf(fid,'%s\n',getReport(err,'extended','hyperlinks','off'));fclose(fid);
  fprintf('FAILED id=%d %s\n',id,err.message);
  try,set_param(m,'FastRestart','off');catch,end
 end
 status=struct('worker_id',worker_id,'last_id',id,'completed_or_skipped',done,'failures',fail,'updated',char(datetime('now')));
 fid=fopen(fullfile(w,'status.json'),'w');fprintf(fid,'%s',jsonencode(status));fclose(fid);
end
fprintf('WORKER FINISHED id=%d completed_or_skipped=%d failures=%d\n',worker_id,done,fail);
end
function [data,meta,checks,diagnostics,row]=one_case(m,r,plan,root,s)
L={'Inductor','Inductor1','Inductor2','Inductor3'};
% Read-only assertions: physical and controller parameters must match snapshot.
assert(str2double(get_param([m '/Capacitor7'],'c'))==2640);
actualL=zeros(1,4);for j=1:4,actualL(j)=str2double(get_param([m '/' L{j}],'l'));end
assert(all(actualL==290));
assert(str2double(get_param([m '/20k/Constant4'],'Value'))==7000);
assert(str2double(get_param([m '/20k/Constant5'],'Value'))==13000);
assert(str2double(get_param([m '/20k/Constant6'],'Value'))==20000);
for tag={'PID Controller2','PID Controller3','PID Controller4','PID Controller5'}
 assert(abs(str2double(get_param([m '/20k/' tag{1}],'P'))-.02)<1e-12);
 assert(abs(str2double(get_param([m '/20k/' tag{1}],'I'))-.00025)<1e-12);
end
carrier=eval(get_param([m '/Carrier 2kHz1'],'rep_seq_t'));assert(abs(1/carrier(end)-30000)<1e-6);
lo=r.low_power_W/12;hi=r.high_power_W/12;start=r.pulse_start_s;slew=1e5;tr=(hi-lo)/slew;
if r.frequency_Hz==0
 stop=.1;ct=[0;.01;stop];ci=[0;lo;lo];ncycles=0;duty=NaN;
else
 T=1/r.frequency_Hz;duty=r.duty_percent/100;ncycles=3;stop=start+ncycles*T;
 assert(tr<min(duty,1-duty)*T);ct=[0;.01;start-.001];ci=[0;lo;lo];
 for j=0:ncycles-1,up=start+j*T;down=up+duty*T;ct=[ct;up;up+tr;down;down+tr];ci=[ci;lo;hi;hi;lo];end %#ok<AGROW>
 ct=[ct;stop];ci=[ci;lo];
end
assert(all(diff(ct)>0));command=timeseries(ci,ct);command.DataInfo.Interpolation=tsdata.interpolation('linear');
in=Simulink.SimulationInput(m);in=in.setVariable('dataset_current_command',command,'Workspace',m);
in=in.setModelParameter('StopTime',num2str(stop,17));
ts=tic;out=sim(in);simSeconds=toc(ts);
ft=out.NDP_features;F=rows_ts(ft,9);H=rows_ts(out.NDP_history,72);t=double(ft.Time(:));valid=logical(out.NDP_valid.Data(:));
assert(size(F,2)==9&&size(H,2)==72&&size(F,1)==size(H,1)&&numel(t)==size(F,1));
assert(all(isfinite(F(:)))&&all(isfinite(H(:)))&&all(abs(diff(t)-1/30000)<1e-9));
assert(numel(valid)==numel(t)&&~any(valid(1:7))&&all(valid(8:end)));
for j=8:numel(t),assert(isequal(H(j,:),reshape(F(j-7:j,:).',1,72)));end
assert(all(abs(double(F(:,6))-12)<1e-6)&&all(abs(double(F(:,9))-48)<1e-6));
assert(mean(sum(double(F(t>=start,2:5)),2))>0);
expected=interp1(ct,ci,min(max(t,ct(1)),ct(end)),'linear');
lc=out.logsout.get('batch_load_command').Values;[lt,ix]=unique(double(lc.Time(:)),'last');lv=double(lc.Data(ix));
assert(lt(1)<=t(1)+1e-9&&lt(end)>=t(end)-1e-9);actual=interp1(lt,lv,min(max(t,lt(1)),lt(end)),'linear');
assert(max(abs(actual-expected))<.02);
rawt=(0:2e-6:stop).';y=zeros(numel(rawt),5);tags={'Vo','ILA','ILB','ILC','ILD'};
for j=1:5
 sig=out.logsout.get(['batch_' tags{j}]).Values;[st,ix]=unique(double(sig.Time(:)),'last');sv=double(sig.Data(ix));
 assert(rawt(1)>=st(1)-1e-9&&rawt(end)<=st(end)+1e-9);y(:,j)=interp1(st,sv,min(max(rawt,st(1)),st(end)),'linear');
end
assert(all(isfinite(y(:))));q=rawt>=.03 & rawt<=.039;baselineRms=sqrt(mean((y(q,1)-12).^2));
assert(baselineRms<.5,'Output failed pre-pulse settling check (%.4g V RMS)',baselineRms);
data=struct('time',t,'features',F,'history',H,'valid',valid,'load_current_command_A',expected,...
 'pulse_region',t>=start & r.frequency_Hz>0,'training_window_after_start',valid & t>=start+7/30000,...
 'feature_names',{{'Vo','ILA','ILB','ILC','ILD','VREF','IREF','z2','Vin'}},...
 'feature_units',{{'V','A','A','A','A','V','A per phase','V/s','V'}},...
 'command_time',ct,'command_current_A',ci,'waveform_time',rawt,'waveforms',y,'waveform_names',{tags});
checks=struct('dimensions_pass',true,'finite_pass',true,'sample_interval_pass',true,'valid_startup_pass',true,...
 'all_history_windows_pass',true,'reference_values_pass',true,'load_command_pass',true,...
 'positive_absorbed_load_pass',true,'pre_pulse_settling_pass',true,'parameter_values_pass',true);
meta=struct('batch_id',plan.batch_id,'batch_case_id',r.id,'case_group',r.group,'case_id',r.group_index,...
 'paired_nominal_id',r.paired_nominal_id,'split_group',sprintf('P%03d',r.id),...
 'frequency_Hz',r.frequency_Hz,'high_duty_fraction',duty,'low_power_W_at_12V',r.low_power_W,...
 'high_power_W_at_12V',r.high_power_W,'low_current_A',lo,'high_current_A',hi,'load_mode','CC',...
 'reference_voltage_V',12,'input_voltage_V',48,'slew_A_per_us',.1,'transition_duration_s',tr,...
 'pulse_start_s',start,'complete_cycles',ncycles,'stop_time_s',stop,'wc',7000,'wo',13000,'b0',20000,...
 'switching_frequency_Hz',30000,'sample_frequency_Hz',30000,'history_steps',8,...
 'history_order','oldest first, 9 features per time step','IREF_definition','common per-phase current reference',...
 'output_C_factor',r.C_factor,'output_C_uF',2640,'input_C_unchanged_uF',180,...
 'L_factors',r.L_factors(:).','phase_L_uH',actualL,'output_C_block','Capacitor7','phase_L_blocks',{L},...
 'controller_parameters_unchanged',true,'model_snapshot',fullfile(s,'ai700_source.slx'),...
 'model_source',fullfile(root,'buck_ADRC_fangzhen_AI_LADRC.slx'),'MATLAB_release',version('-release'),...
 'created_at',char(datetime('now')),'simulation_wall_time_s',simSeconds,'fast_restart',get_param(m,'FastRestart'),...
 'simulation_mode',get_param(m,'SimulationMode'),...
 'source_type','actual Simulink/Simscape simulation','labels_constructed',false,'hardware_validated',false,...
 'all_checks_pass',true,'baseline_rms_V',baselineRms,...
 'numerical_note','Exact user source snapshot; only load command, stop time, execution mode and logging configured. Physical/controller/solver parameters unchanged.');
diagnostics=struct('warning_diagnostics',[]);try,diagnostics.warning_diagnostics=out.SimulationMetadata.ExecutionInfo.WarningDiagnostics;catch,end
mask=rawt>=start;row=struct('id',r.id,'filename',ai700_filename(r),'group',r.group,'frequency_Hz',r.frequency_Hz,...
 'duty_percent',r.duty_percent,'low_W',r.low_power_W,'high_W',r.high_power_W,'C_factor',r.C_factor,...
 'L_factors',r.L_factors(:).','samples',numel(t),'valid_windows',sum(valid),'stop_s',stop,...
 'Vmin',min(y(mask,1)),'Vmax',max(y(mask,1)),'baseline_rms_V',baselineRms,'simulation_seconds',simSeconds,'checks_pass',true);
end
function A=rows_ts(ts,w)
if ts.IsTimeFirst,A=reshape(ts.Data,numel(ts.Time),w);else,A=reshape(ts.Data,w,numel(ts.Time)).';end
end
function preview_case(data,meta,file)
fig=figure('Visible','off','Position',[100 100 1000 750]);c=onCleanup(@()close(fig));tiledlayout(3,1,'TileSpacing','compact');
nexttile;plot(data.command_time,data.command_current_A);ylabel('CC load / A');grid on;
title(sprintf('%s %03d: %gHz, D=%g%%, %g-%gW; C=%g%%, L=[%g %g %g %g]%%',meta.case_group,meta.case_id,...
 meta.frequency_Hz,meta.high_duty_fraction*100,meta.low_power_W_at_12V,meta.high_power_W_at_12V,...
 meta.output_C_factor*100,meta.L_factors*100));
nexttile;plot(data.waveform_time,data.waveforms(:,1));yline(12,'--');ylabel('Output / V');grid on;
nexttile;plot(data.waveform_time,data.waveforms(:,2:5));legend('ILA','ILB','ILC','ILD');ylabel('Phase current / A');xlabel('Time / s');grid on;
exportgraphics(fig,file,'Resolution',110);
end
function close_model(m)
try,set_param(m,'FastRestart','off');close_system(m,0);catch,end
end




