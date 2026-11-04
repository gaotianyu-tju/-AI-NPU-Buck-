/*
 * 事件扰动前馈与 ESO 交还，输出单位为每相电流 A。
 * 不使用固定 2 ms / 20% 周期截止；最终版按 ESO 接管程度退出。
 * 预约开始时锁存幅值，避免把保持的绝对预测值每周期重新减去变化中的 z2。
 * 本文件为最终 v16 交付源码；本轮仅增加说明，不修改执行语句或参数。
 */
#include "buck_npu_compensation.h"

volatile uint16_t buck_npu_comp_attack_ticks=2U;
volatile uint16_t buck_npu_comp_fade_ticks=6U; /* legacy diagnostic; unused in v13 */
volatile float buck_npu_comp_limit_a=1.0f;
volatile float buck_npu_comp_delta_a,buck_npu_comp_innovation_vps;
volatile float buck_npu_comp_weight,buck_npu_comp_latched_delta_a;
volatile float buck_npu_comp_source_prediction_vps,buck_npu_comp_ref_z2_vps;
volatile float buck_npu_comp_latched_innovation_vps;
volatile float buck_npu_comp_takeover_raw,buck_npu_comp_takeover_filtered;
volatile float buck_npu_comp_takeover,buck_npu_comp_z2_pre_vps;
volatile float buck_npu_comp_baseline_iref_a,buck_npu_comp_final_iref_a;
volatile float buck_npu_comp_applied_delta_i_a;
volatile uint16_t buck_npu_comp_active,buck_npu_comp_state;
volatile uint16_t buck_npu_comp_edge_kind,buck_npu_comp_config_fault;
volatile uint16_t buck_npu_comp_effective_window,buck_npu_comp_total_ticks;
volatile uint16_t buck_npu_comp_latched_period_ticks,buck_npu_comp_latched_lead_ticks;
volatile uint16_t buck_npu_comp_exit_reason;
volatile uint32_t buck_npu_comp_age_ticks,buck_npu_comp_event_tick;
volatile uint32_t buck_npu_comp_estimated_edge_tick,buck_npu_comp_command_start_tick;
volatile uint32_t buck_npu_comp_updates,buck_npu_comp_config_reject;
volatile uint32_t buck_npu_comp_event_reject,buck_npu_comp_config_changes;
volatile uint32_t buck_npu_comp_finished_window,buck_npu_comp_finished_handoff;
volatile uint32_t buck_npu_comp_forced_window,buck_npu_comp_window_overlaps;
volatile uint32_t buck_npu_comp_arm_reject,buck_npu_comp_direction_reject;
volatile uint32_t buck_npu_comp_small_signal_reject;

typedef struct {
    float alpha,wc,wo,b0,limit,seed,z2_pre;
    float inverse_df,inverse_attack,filtered,takeover;
    uint32_t last_tick,last_event_tick,start_tick,edge_tick;
    uint16_t tick_valid,event_level,event_seen,active,edge_kind;
    uint16_t attack,lead,edge_age;
} CompensationState;
static CompensationState state;
static uint32_t armed_edge_tick;
static uint16_t armed_lead,armed_valid;

#ifdef __TI_COMPILER_VERSION__
#pragma FUNC_ALWAYS_INLINE(finite_float)
#pragma FUNC_ALWAYS_INLINE(smoothstep)
#pragma FUNC_ALWAYS_INLINE(clear_pulse)
#endif
static uint16_t finite_float(float x)
{
    union {float value; uint32_t bits;} v;
    v.value=x;
    return (uint16_t)((v.bits&0x7f800000UL)!=0x7f800000UL);
}
static float smoothstep(float x)
{
    if(x<=0.0f) return 0.0f;
    if(x>=1.0f) return 1.0f;
    return x*x*(3.0f-2.0f*x);
}
/* 统一退出点：实际补偿和权重清零，同时撤销未使用的预约授权。
 * 累计计数保持不变，便于 CCS 定位退出原因。 */
static float clear_pulse(uint16_t reason)
{
    state.active=0U;
    state.filtered=state.takeover=0.0f;
    armed_valid=0U;
    buck_npu_comp_active=buck_npu_comp_state=0U;
    buck_npu_comp_delta_a=buck_npu_comp_weight=0.0f;
    if(reason) buck_npu_comp_exit_reason=reason;
    return 0.0f;
}
void buck_npu_compensation_arm(uint32_t edge_tick,uint16_t lead_ticks)
{
    armed_edge_tick=edge_tick; armed_lead=lead_ticks; armed_valid=1U;
}
void buck_npu_compensation_reset(void)
{
    (void)clear_pulse(0U);
    state.tick_valid=state.event_level=state.event_seen=0U;
    buck_npu_comp_age_ticks=buck_npu_comp_event_tick=0UL;
    buck_npu_comp_estimated_edge_tick=buck_npu_comp_command_start_tick=0UL;
    buck_npu_comp_edge_kind=buck_npu_comp_effective_window=0U;
    buck_npu_comp_total_ticks=buck_npu_comp_latched_period_ticks=0U;
    buck_npu_comp_latched_lead_ticks=0U;
    buck_npu_comp_config_fault=buck_npu_comp_exit_reason=0U;
    buck_npu_comp_innovation_vps=buck_npu_comp_latched_delta_a=0.0f;
    buck_npu_comp_source_prediction_vps=buck_npu_comp_ref_z2_vps=0.0f;
    buck_npu_comp_latched_innovation_vps=0.0f;
    buck_npu_comp_takeover_raw=buck_npu_comp_takeover_filtered=0.0f;
    buck_npu_comp_takeover=buck_npu_comp_z2_pre_vps=0.0f;
    /* Cumulative diagnostics survive an ordinary stop/reset. */
}

/* 仅对合法、按时到达的上升或下降事件建立前馈。
 * 检查预测方向、小信号阈值、周期范围与电流限幅，防止错误符号进入控制。 */
static uint16_t start_pulse(float df,float z2,float alpha,float b0,
    uint16_t kind,uint32_t tick,uint16_t period,float wc,float wo,
    uint16_t arm_valid,uint32_t edge_tick,uint16_t lead)
{
    uint16_t attack=buck_npu_comp_attack_ticks;
    uint16_t fault=0U;
    float limit=buck_npu_comp_limit_a,seed;
    if((kind!=1U && kind!=2U) || !finite_float(df) ||
       period<BUCK_NPU_COMP_PERIOD_MIN_TICKS || period>BUCK_NPU_COMP_PERIOD_MAX_TICKS) {
        ++buck_npu_comp_event_reject; (void)clear_pulse(7U); return 0U;
    }
    if(df>-BUCK_NPU_COMP_MIN_DF_VPS && df<BUCK_NPU_COMP_MIN_DF_VPS) {
        ++buck_npu_comp_small_signal_reject; ++buck_npu_comp_event_reject;
        (void)clear_pulse(7U); return 0U;
    }
    if((kind==1U && df>=0.0f) || (kind==2U && df<=0.0f)) {
        ++buck_npu_comp_direction_reject; ++buck_npu_comp_event_reject;
        (void)clear_pulse(7U); return 0U;
    }
    if(!finite_float(limit) || limit<=0.0f || limit>BUCK_NPU_COMP_HARD_LIMIT_A) fault|=8U;
    if(attack<1U || attack>15U) fault|=32U;
    buck_npu_comp_config_fault=fault;
    if(fault) {
        ++buck_npu_comp_config_reject; (void)clear_pulse(5U); return 0U;
    }
    /* Exact start check rejects late, stale, malformed and absent arms. */
    if(!arm_valid || lead>BUCK_NPU_COMP_MAX_LEAD_TICKS ||
       (uint32_t)(edge_tick-tick)!=(uint32_t)attack+lead) {
        ++buck_npu_comp_arm_reject; ++buck_npu_comp_event_reject;
        (void)clear_pulse(8U); return 0U;
    }
/* 扰动单位 V/s 除以 b0 后才得到电流 A。负载上升对应 df<0，补偿增加电流。
 * 随后按每相限幅裁剪；原 LADRC 最终给定还会再统一限幅。 */
    seed=(-alpha*df)/b0;
    if(!finite_float(seed)) {
        ++buck_npu_comp_event_reject; (void)clear_pulse(7U); return 0U;
    }
    if(seed < -limit) seed=-limit;
    if(seed > limit) seed=limit;
    if(state.active) ++buck_npu_comp_window_overlaps;
    state.alpha=alpha; state.wc=wc; state.wo=wo; state.b0=b0; state.limit=limit;
    state.seed=seed; state.z2_pre=z2;
    state.inverse_df=1.0f/df;
    state.inverse_attack=1.0f/(float)attack;
    state.filtered=state.takeover=0.0f;
    state.attack=attack; state.lead=lead;
    state.edge_age=(uint16_t)(attack+lead);
    state.start_tick=tick; state.edge_tick=edge_tick; state.active=1U; state.edge_kind=kind;
    /* v13: zero means no elapsed-time deadline, not a zero-length pulse. */
    buck_npu_comp_effective_window=0U; buck_npu_comp_total_ticks=0U;
    buck_npu_comp_latched_period_ticks=period; buck_npu_comp_latched_lead_ticks=lead;
    buck_npu_comp_event_tick=buck_npu_comp_command_start_tick=tick;
    buck_npu_comp_estimated_edge_tick=edge_tick; buck_npu_comp_edge_kind=kind;
    buck_npu_comp_source_prediction_vps=buck_npu_comp_innovation_vps=df;
    buck_npu_comp_z2_pre_vps=buck_npu_comp_ref_z2_vps=z2;
    buck_npu_comp_latched_delta_a=seed;
    buck_npu_comp_latched_innovation_vps=-seed*b0;
    buck_npu_comp_takeover_raw=buck_npu_comp_takeover_filtered=buck_npu_comp_takeover=0.0f;
    buck_npu_comp_exit_reason=0U;
    ++buck_npu_comp_updates;
    return 1U;
}

/* 每周期调用的有状态补偿器。alpha<=0、失锁、非法量、调参中断等均取消补偿。
 * 预约只授权本次调用；连续重复的事件电平不会反复启动同一前馈。 */
float buck_npu_compensation_step(float prediction,float z2,float alpha,float b0,
    uint16_t permit,uint16_t new_event,uint16_t edge_kind,uint32_t tick,
    float voltage_v,float filtered_load_a,uint16_t period_ticks,float wc,float wo)
{
    uint16_t event_level=(uint16_t)(new_event!=0U);
    uint16_t fresh=(uint16_t)(event_level && !state.event_level &&
        (!state.event_seen || tick!=state.last_event_tick));
    uint16_t continuous=(uint16_t)(!state.tick_valid || (uint32_t)(tick-state.last_tick)==1UL);
    uint16_t arm_valid=armed_valid,lead=armed_lead;
    uint32_t edge_tick=armed_edge_tick,age;
    float raw=0.0f,weight,wo_ts;
    armed_valid=0U; /* An arm authorizes this call only, never a later event. */
    state.event_level=event_level;
    if(fresh) {state.event_seen=1U; state.last_event_tick=tick;}
    state.last_tick=tick; state.tick_valid=1U;
    if(!continuous || !finite_float(voltage_v) || !finite_float(filtered_load_a) || !finite_float(z2))
        return clear_pulse(6U);
    if(!finite_float(alpha) || b0!=BUCK_NPU_COMP_REQUIRED_B0) {
        buck_npu_comp_config_fault=!finite_float(alpha)?1U:2U;
        return clear_pulse(5U);
    }
    wo_ts=wo*BUCK_NPU_COMP_TS;
    if(!finite_float(wc) || wc<0.0f || wc>BUCK_NPU_COMP_MAX_WC ||
       !finite_float(wo) || wo_ts<=0.0f || wo_ts>1.0f) {
        buck_npu_comp_config_fault=64U; return clear_pulse(5U);
    }
    if(!permit || alpha<=0.0f) return clear_pulse(3U);
    if(alpha>1.0f) alpha=1.0f;
    if(state.active && (alpha!=state.alpha || wc!=state.wc || wo!=state.wo || b0!=state.b0 ||
       buck_npu_comp_attack_ticks!=state.attack ||
       buck_npu_comp_limit_a!=state.limit)) {
        ++buck_npu_comp_config_changes; return clear_pulse(4U);
    }
    /* v13: the user requested no 20%-period timeout or terminal fade.
     * ESO handoff and all eligibility/invalid-input cancellation remain. */
    if(fresh) {
        if(state.active && edge_kind==state.edge_kind) ++buck_npu_comp_event_reject;
        else if(!start_pulse(prediction,z2,alpha,b0,edge_kind,tick,period_ticks,wc,wo,
                            arm_valid,edge_tick,lead)) return 0.0f;
    }
    if(!state.active) return clear_pulse(0U);
    age=(uint32_t)(tick-state.start_tick); buck_npu_comp_age_ticks=age;
/* 到预计真实边沿后才估计 ESO 已承担的扰动比例：
 * (z2-z2_pre)/df 经限幅和一阶滤波，再取单调最大值。防止 ESO 振铃使前馈反复回升。 */
    if(age>=state.edge_age) {
        raw=(z2-state.z2_pre)*state.inverse_df;
        if(!finite_float(raw)) return clear_pulse(6U);
        if(raw<0.0f) raw=0.0f;
        if(raw>1.0f) raw=1.0f;
        state.filtered+=0.25f*(raw-state.filtered);
        if(state.filtered>state.takeover) state.takeover=state.filtered;
        if(state.takeover>1.0f) state.takeover=1.0f;
    }
    buck_npu_comp_takeover_raw=raw;
    buck_npu_comp_takeover_filtered=state.filtered;
    buck_npu_comp_takeover=state.takeover;
    if(age>=state.edge_age && state.takeover>=BUCK_NPU_COMP_HANDOFF_DONE) {
        buck_npu_comp_takeover=1.0f;
        ++buck_npu_comp_finished_handoff;
        return clear_pulse(2U);
    }
/* 补偿建立采用三次 smoothstep；退出由 1-takeover 连续减小。
 * 达到交还阈值强制归零；没有再次叠加持续的直流偏置项。 */
    weight=smoothstep((float)age*state.inverse_attack)*(1.0f-state.takeover);
    buck_npu_comp_active=1U;
    buck_npu_comp_state=age>=state.edge_age?2U:1U;
    buck_npu_comp_weight=weight;
    buck_npu_comp_delta_a=state.seed*weight;
    return buck_npu_comp_delta_a;
}
