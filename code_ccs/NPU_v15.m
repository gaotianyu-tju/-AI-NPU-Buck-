function data = NPU(Vo,I1,I2,I3,I4,Vref,Vin,enable)
%#codegen
% v15 CPU 采样/负载电流观测/已排定事件读取接口；不等待 NPU。
% 输出是配对端点的扰动变化量 df（V/s），交给 ADRC 内的
% buck_npu_apply_prediction 使用；不能直接与当前 z2 相减。
% enable=1 复位，0 运行。普通桌面仿真使用 NaN -> 原 ADRC。
data = single(NaN);
if coder.target('Rtw')
    coder.cinclude('buck_npu.h');
    data = coder.ceval('buck_npu_begin',single(Vo),single(I1),single(I2), ...
        single(I3),single(I4),single(Vref),single(Vin),uint16(enable~=0));
end
end
