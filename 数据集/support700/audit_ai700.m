function audit_ai700
root=fileparts(mfilename('fullpath'));d=fullfile(root,char([25968 25454 38598 95 33033 20914 36127 36733]));s=fullfile(d,'support700');plan=jsondecode(fileread(fullfile(s,'plan700.json')));rows=struct([]);
for k=1:700
 r=plan.rows(k);name=ai700_filename(r);a=load(fullfile(d,name));F=a.data.features;H=a.data.history;t=a.data.time;assert(a.meta.all_checks_pass&&a.meta.batch_case_id==k);assert(strcmp(a.meta.source_sha256,plan.source_sha256));assert(all(isfinite(F(:)))&&all(isfinite(H(:))));assert(all(abs(diff(t)-1/30000)<1e-9));assert(~any(a.data.valid(1:7))&&all(a.data.valid(8:end)));
 for j=8:numel(t),assert(isequal(H(j,:),reshape(F(j-7:j,:).',1,72)));end
 assert(a.meta.wc==7000&&a.meta.wo==13000&&a.meta.b0==20000&&a.meta.current_Kp==.02&&a.meta.current_Ki==.00025&&a.meta.output_C_uF==2640);assert(a.meta.switching_frequency_Hz==30000);assert(a.meta.frequency_Hz==r.frequency_Hz&&a.meta.high_duty_fraction==r.duty_percent/100);assert(a.meta.low_power_W_at_12V==r.low_power_W&&a.meta.high_power_W_at_12V==r.high_power_W);
 ct=a.data.command_time;ci=a.data.command_current_A;slopes=diff(ci)./diff(ct);ev=find(ct(1:end-1)>=r.pulse_start_s-1e-10 & abs(slopes)>1);assert(numel(ev)==2*a.meta.complete_cycles);assert(all(abs(abs(slopes(ev))-1e5)<1));up=ct(ev(slopes(ev)>0));down=ct(ev(slopes(ev)<0));assert(all(abs(diff(up)-1/r.frequency_Hz)<1e-10));assert(all(abs(down-up-r.duty_percent/100/r.frequency_Hz)<1e-10));assert(a.meta.complete_cycles>=3);assert(abs(a.meta.stop_time_s-r.pulse_start_s-a.meta.complete_cycles/r.frequency_Hz)<1e-9);
 rows(k).id=k;rows(k).filename=name;rows(k).frequency_Hz=r.frequency_Hz;rows(k).high_duty_percent=r.duty_percent;rows(k).low_W=r.low_power_W;rows(k).high_W=r.high_power_W;rows(k).samples=numel(t);rows(k).valid_windows=sum(a.data.valid);rows(k).simulation_seconds=a.meta.simulation_wall_time_s;rows(k).checks_pass=true;
end
writetable(struct2table(rows),fullfile(d,'summary700.csv'));fid=fopen(fullfile(d,'verification700.txt'),'w');fprintf(fid,'PASS: 700 actual R2024b simulations.\nwc7000 wo13000 b020000 Kp0.02 Ki0.00025 C2640uF; 30kHz switching/sampling.\nAll finite/history/time-step/load-edge period/duty/slew checks passed.\nSamples: %d; valid windows: %d.\nSource SHA256: %s\nNo labels constructed or hardware-equivalence claim.\n',sum([rows.samples]),sum([rows.valid_windows]),plan.source_sha256);fclose(fid);
end

