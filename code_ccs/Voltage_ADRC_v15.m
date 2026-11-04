function i_ref = Voltage_ADRC(ref, y, wc, wo, b0, fsw, data, alpha, enable)
%#codegen
% v15：一阶 LADRC 电压外环，输出每相电感电流给定（A）。
% 保留原来的 9 个输入、1 个输出及原 ESO/电流限幅算法。
% data 是上一负载周期配对端点的总扰动变化量 df（V/s），不是当前 z2。
% v15 C 接口完成提前前馈及 ESO 接管；不能再直接计算 (data-z2)。
% enable=1：复位；enable=0：运行。alpha=0：补偿为零。
% 本函数只读取/使用预测并提交采样，不执行或等待神经网络推理。

persistent z1 z2 u_prev
ref_s = single(ref); y_s = single(y);
wc_s = single(wc); wo_s = single(wo); b0_s = single(b0);
fsw_s = single(fsw);
zero = single(0); Imax = single(40);
alpha_s = single(alpha);
if ~isfinite(alpha_s)
    alpha_s = zero;
else
    alpha_s = min(max(alpha_s,zero),single(1));
end
if isempty(z1)
    z1 = y_s; z2 = zero; u_prev = zero;
end
reset = enable ~= 0;
if ~isfinite(fsw_s) || fsw_s <= zero || ~isfinite(b0_s) || abs(b0_s) < single(1e-6)
    reset = true;
end
if coder.target('Rtw')
    coder.cinclude('buck_npu.h');
    coder.cinclude('buck_npu_mbd_bridge.h');
end
if reset
    z1 = y_s; z2 = zero; u_prev = zero;
    cmd = zero;
    if coder.target('Rtw')
        coder.ceval('buck_npu_mbd_record_reset');
    end
else
    Ts = single(1)/fsw_s;
    % 原 ESO：使用上一周期最终限幅后的电流给定。
    e = y_s-z1;
    z1 = z1+Ts*(z2+b0_s*u_prev+single(2)*wo_s*e);
    z2 = z2+Ts*(wo_s*wo_s*e);

    % 每个运行周期都调用，使 alpha=0/失锁/停用等条件能取消旧补偿。
    % 必须在本周期 ESO 更新之后调用，保持 v15 的交还时序。
    delta_I = zero;
    if coder.target('Rtw')
        delta_I = coder.ceval('buck_npu_apply_prediction',single(data),single(z2), ...
            alpha_s,b0_s,wc_s,wo_s);
    end
    raw = (wc_s*(ref_s-z1)-z2)/b0_s;
    if coder.target('Rtw')
        coder.ceval('buck_npu_mbd_record_baseline',single(raw));
    end
    cmd = min(max(raw+delta_I,-Imax),Imax);
    if coder.target('Rtw')
        coder.ceval('buck_npu_mbd_record_final',single(cmd));
    end
    u_prev = cmd;
end
i_ref = double(cmd);
% 收集本周期真实控制量与 ESO 状态；推理仍由 main 后台服务。
if coder.target('Rtw')
    coder.ceval('buck_npu_commit',single(cmd),single(z2),fsw_s,b0_s,uint16(reset));
end
end
