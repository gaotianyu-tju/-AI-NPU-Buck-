/*
 * 当前 H15 模型的预处理与物理量恢复；必须使用同包 mod.a / tvmgen_default.h。
 * 归一化只在后台执行，使用独立 strict FP 编译，禁止快速浮点重结合。
 * 本文件为最终 v16 交付源码；本轮仅增加说明，不修改执行语句或参数。
 */
#include "ndp_model_io.h"
#include <limits.h>
#include <math.h>
#include <stddef.h>
#include <stdint.h>
/* FPU32 runtime adaptation of the delivered H15 scaler. No change to weights.
 * Split mean preserves the low part lost by rounding large means to float.
 * Each feature: ((raw - mean_hi) - mean_lo) * inverse_scale.
 * No double arithmetic or division in the 72-feature normalization loop.
 * Compile strict FP: do not reassociate into raw*scale + bias.
 */
typedef char ndp_float32_required[(sizeof(float) * CHAR_BIT == 32) ? 1 : -1];
typedef char ndp_double64_required[(sizeof(double) * CHAR_BIT == 64) ? 1 : -1];
static const float x_mean_hi[9] = {11.9997578f, 6.25366926f, 6.25360394f, 6.25357246f, 6.25363731f, 12.0f, 6.2745595f, -125490.18f, 48.0f};
static const float x_mean_lo[9] = {4.58924347e-07f, -1.96421098e-07f, 6.67672069e-08f, -2.02265724e-07f, 7.78109452e-08f, 0.0f, -2.28352789e-07f, -0.00372971594f, 0.0f};
static const float x_inverse_scale[9] = {2.18372035f, 0.733723521f, 0.734671175f, 0.734930575f, 0.731822968f, 1.0f, 0.73922658f, 3.73071198e-05f, 1.0f};
static int finite_float(float value) {
    union { float f; uint32_t u; } bits;
    bits.f=value;
    return (bits.u & 0x7f800000UL) != 0x7f800000UL;
}
/* 输入 raw[时间8][通道9]，顺序由 deployment.json 约定。
 * 输出 NCHW [1,12,8,1]，索引为 c*8+t，后三个补齐通道写零。
 * 均值拆成 hi/lo 避免大数均值的单精度舍入；输入或中间结果非有限时拒绝该任务。 */
int ndp_prepare_window(const float raw[NDP_HISTORY][NDP_CHANNELS], float normalized[NDP_PACKED_FLOATS]) {
    unsigned int t, c;
    float value;
    if (raw == NULL || normalized == NULL) return -1;
    for (c=0;c<NDP_CHANNELS;++c) {
        for (t=0;t<NDP_HISTORY;++t) {
            value=raw[t][c];
            if (!finite_float(value)) return -1;
            value=(value-x_mean_hi[c])-x_mean_lo[c];
            value=value*x_inverse_scale[c];
            if (!finite_float(value)) return -1;
            normalized[c*NDP_HISTORY+t]=value;
        }
    }
    for(c=NDP_CHANNELS*NDP_HISTORY;c<NDP_PACKED_FLOATS;++c) normalized[c]=0.0f;
    return 0;
}
/* Only one output restoration per inference, in background. Keep the delivered
 * double formula here for reference-equivalent physical scaling. */
/* 只恢复网络残差，不在此加当前 z2。调用方使用 flight_z2（来源时刻）形成总扰动预测。
 * 后台每次推理只做一次 double 缩放，避免把 64 位运算放到逐点预处理/控制 ISR。 */
int ndp_restore_residual(float normalized,float *residual_V_per_s) {
    if(residual_V_per_s==NULL || !finite_float(normalized)) return -1;
    *residual_V_per_s=(float)((double)normalized * 7710.870749368849 + 234.75832193347716);
    return finite_float(*residual_V_per_s) ? 0 : -1;
}
