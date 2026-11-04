/*
 * CPU 负载电流观测器与周期识别。Cout=180 uF，Ts=1/30000 s。
 * KCL：Iload = I1+I2+I3+I4 - Cout*dVo/dt。
 * 采用对齐的四点电流均值和四点电压差分，再用三点中值抑制孤立尖峰。
 * 支持每次试验固定、试验间可变的 20~200 Hz 脉冲周期。
 * 本文件为最终 v16 交付源码；本轮仅增加说明，不修改执行语句或参数。
 */
#include "buck_load_observer.h"
#include "buck_npu_timing.h"

volatile buck_load_observer_status_t buck_load_observer;
volatile float buck_load_edge_threshold_a = 1.0f;

/* v16: 20..200 Hz load repetition; Cout=180 uF, 30 kHz control.
 * Iload = mean(Isum[k-4..k-1])-C/(4*Ts)*(Vo[k]-Vo[k-4]).
 * Median3 rejects isolated ADC spikes; no 32-sample mean.
 * Ramp delay ~=3.5 ticks (4 past intervals + median), not an analog timing
 * guarantee. ADC aperture and non-linear edge shapes still require measurement. */
#define KCL_GAIN          1.35f
#define KCL_SAMPLES       4U
#define FILTER_DELAY      3.5f
#define PERIOD_MIN        BUCK_NPU_PERIOD_MIN_TICKS
#define PERIOD_MAX        BUCK_NPU_PERIOD_MAX_TICKS
#define PERIOD_TOLERANCE  BUCK_NPU_PERIOD_AGREEMENT_TICKS
#define PERIOD_JITTER     BUCK_NPU_PERIOD_JITTER_TICKS
#define GOOD_CYCLES       2U
#define EDGE_CONFIRM      3U
#define STABLE_SAMPLES    8U
#define MIN_EDGE_GAP      20UL
#define MAX_CONFIRM_LAG   40UL
#define CANDIDATE_TIMEOUT 48UL

static float vo_history[4], i_history[4], current_sum, current_block_sum;
static float median_1, median_2, previous_filtered, configured_threshold;
static float learn_low, learn_high, pending_low, pending_high, stable_anchor;
static float low_level, high_level, threshold_low, threshold_high;
static float candidate_low, candidate_high, t25, t50, t75;
static uint16_t initialized, filter_index, filter_count, median_count;
static uint16_t level_samples, stable_count, stable_points, pending_blocks, empty_blocks;
static uint16_t learning_window;
static uint16_t phase_state, confirmation, pending_kind, crossing_mask;
static uint16_t have_edge, have_rise, have_fall, rise_good, fall_good;
static uint16_t rise_period, fall_period, last_edge_kind;
static uint32_t rise_period_q8, fall_period_q8;

/* Only the added observer is optimized. Original ADC, PI/ADRC and PWM
 * generated code retain their compiler options and source. */
#ifdef __TI_COMPILER_VERSION__
#pragma FUNCTION_OPTIONS(buck_load_observer_step, "--opt_level=2")
#pragma FUNCTION_OPTIONS(track_candidate, "--opt_level=2")
#pragma FUNCTION_OPTIONS(register_edge, "--opt_level=2")
#pragma FUNCTION_OPTIONS(learn_levels, "--opt_level=2")
#pragma FUNCTION_OPTIONS(clear_phase, "--opt_level=2")
#pragma FUNCTION_OPTIONS(initialize, "--opt_level=2")
#pragma FUNCTION_OPTIONS(set_thresholds, "--opt_level=2")
#pragma FUNC_ALWAYS_INLINE(finite_f32)
#pragma FUNC_ALWAYS_INLINE(abs_f32)
#pragma FUNC_ALWAYS_INLINE(maximum_f32)
#pragma FUNC_ALWAYS_INLINE(median3)
#pragma FUNC_ALWAYS_INLINE(period_close)
#pragma FUNC_ALWAYS_INLINE(filter_period)
#endif
/* Compare a new interval with a filtered period, not the preceding noisy
 * interval. Two adjacent interval errors share a timestamp with opposite
 * signs; comparing them directly amplified ordinary edge jitter. */
static uint16_t filter_period(uint32_t *q8,uint16_t value) {
    int32_t error;
    if(!*q8) *q8=(uint32_t)value*256UL;
    else {
        error=(int32_t)((uint32_t)value*256UL)-(int32_t)*q8;
        *q8=(uint32_t)((int32_t)*q8+error/8L);
    }
    return (uint16_t)((*q8+128UL)/256UL);
}
static uint32_t previous_tick, last_edge_tick, last_rise_tick, last_fall_tick;
static uint32_t candidate_tick;

static uint16_t finite_f32(float x) {
    union { float f; uint32_t u; } bits;
    bits.f=x; return (uint16_t)((bits.u & 0x7f800000UL)!=0x7f800000UL);
}
static float abs_f32(float x) { return x<0.0f ? -x:x; }
static float maximum_f32(float a,float b) { return a>b ? a:b; }
static float median3(float a,float b,float c) {
    float t; if(a>b) {t=a;a=b;b=t;} if(b>c) {b=c;} return a>b ? a:b;
}
static uint16_t period_close(uint16_t a,uint16_t b) {
    return (uint16_t)((a>b ? a-b:b-a)<=PERIOD_TOLERANCE);
}
static void cancel_lock(void) {
    if(buck_load_observer.locked) ++buck_load_observer.unlocks;
    buck_load_observer.locked=0U; rise_good=fall_good=0U;
}
static void clear_phase(void) {
    cancel_lock();
    buck_load_observer.edge_kind=0U; buck_load_observer.previous_same_valid=0U;
    buck_load_observer.period_ticks=0U; buck_load_observer.high_ticks=0U;
    have_edge=have_rise=have_fall=0U; rise_period=fall_period=0U;
    rise_period_q8=fall_period_q8=0UL;
    last_edge_kind=0U; confirmation=pending_kind=crossing_mask=0U;
    buck_load_observer.confirm_count=0U;
}
static void initialize(float vo,float isum,uint32_t tick,float threshold) {
    initialized=1U; previous_tick=tick; configured_threshold=threshold;
    filter_index=filter_count=median_count=0U;
    current_sum=current_block_sum=0.0f; median_1=median_2=isum;
    previous_filtered=stable_anchor=isum;
    level_samples=stable_count=stable_points=pending_blocks=empty_blocks=0U;
    phase_state=0U;
    learning_window=BUCK_NPU_LEVEL_ACQUIRE_TICKS;
    buck_load_observer.learning_window_ticks=learning_window;
    buck_load_observer.load_a=buck_load_observer.filtered_load_a=isum;
    buck_load_observer.voltage_v=vo; buck_load_observer.valid=0U;
    buck_load_observer.level_valid=0U; buck_load_observer.learning_ticks=0U;
    buck_load_observer.schmitt_state=0U;
    buck_load_observer.low_level_a=buck_load_observer.high_level_a=isum;
    buck_load_observer.learned_span_a=0.0f;
    buck_load_observer.capacitance_uf=180.0f;
    clear_phase();
}
static void set_thresholds(float low,float high) {
    low_level=low; high_level=high;
    threshold_low=low+0.25f*(high-low);
    threshold_high=low+0.75f*(high-low);
    buck_load_observer.low_level_a=low; buck_load_observer.high_level_a=high;
    buck_load_observer.threshold_low_a=threshold_low;
    buck_load_observer.threshold_high_a=threshold_high;
    buck_load_observer.learned_span_a=high-low;
}
/* Learning runs even while a prediction is latched. Each block spans a
 * complete load cycle plus a settling margin, not a fixed 10 ms. Before
 * period lock use the longest supported period. Two consistent stable
 * ranges are still required; isolated transients cannot reset the plan. */
/* 仅用稳定平台点学习高低电平，并要求连续学习块一致后才接受。
 * 未锁定时覆盖最低频率的完整周期；锁定后窗口随实测周期变化，避免写死 100 Hz。
 * 瞬态尖峰不能直接成为新平台，也不能反复撤销已锁存的交付。 */
static void learn_levels(float value) {
    float stable_band=maximum_f32(0.75f*configured_threshold,
        buck_load_observer.level_valid ? 0.03f*(high_level-low_level):0.0f);
    float tolerance,span;
    if(!level_samples) {
        learning_window=buck_load_observer.locked ?
            (uint16_t)(buck_load_observer.period_ticks+BUCK_NPU_LEVEL_MARGIN_TICKS):
            BUCK_NPU_LEVEL_ACQUIRE_TICKS;
        buck_load_observer.learning_window_ticks=learning_window;
    }
    if(abs_f32(value-previous_filtered)<=0.35f*configured_threshold &&
       abs_f32(value-stable_anchor)<=stable_band) {
        if(stable_count<STABLE_SAMPLES) ++stable_count;
    } else { stable_count=0U; stable_anchor=value; }
    if(stable_count>=STABLE_SAMPLES) {
        if(!stable_points) learn_low=learn_high=value;
        else {if(value<learn_low)learn_low=value; if(value>learn_high)learn_high=value;}
        ++stable_points; ++buck_load_observer.stable_learning_samples;
    }
    ++level_samples; buck_load_observer.learning_ticks=level_samples;
    if(level_samples<learning_window) return;
    level_samples=0U; buck_load_observer.learning_ticks=0U;
    ++buck_load_observer.learning_blocks;
    span=stable_points ? learn_high-learn_low:0.0f;
    stable_points=0U;
    if(span<4.0f*configured_threshold) {
        pending_blocks=0U;
        if(empty_blocks<2U)++empty_blocks;
        if(empty_blocks==2U && buck_load_observer.level_valid) {
            ++buck_load_observer.level_relearns;
            buck_load_observer.level_valid=0U; phase_state=0U; clear_phase();
        }
        return;
    }
    empty_blocks=0U;
    tolerance=maximum_f32(2.0f*configured_threshold,0.20f*span);
    if(buck_load_observer.level_valid &&
       abs_f32(learn_low-low_level)<=tolerance && abs_f32(learn_high-high_level)<=tolerance) {
        pending_blocks=0U;
        set_thresholds(low_level+0.125f*(learn_low-low_level),
                       high_level+0.125f*(learn_high-high_level));
        return;
    }
    if(pending_blocks && abs_f32(learn_low-pending_low)<=tolerance &&
       abs_f32(learn_high-pending_high)<=tolerance) {
        if(buck_load_observer.level_valid)++buck_load_observer.level_relearns;
        set_thresholds(0.5f*(learn_low+pending_low),0.5f*(learn_high+pending_high));
        buck_load_observer.level_valid=1U; pending_blocks=0U;
        phase_state=0U; clear_phase();
    } else { pending_low=learn_low; pending_high=learn_high; pending_blocks=1U; }
}
/* 上升与下降分别计算同类边沿间隔，再核对两种周期是否一致。
 * 保留端点测时容差，不将过短同类周期默默忽略而锁到二倍周期。 */
static uint16_t register_edge(uint16_t kind,uint32_t onset,uint32_t confirmed,uint16_t delay) {
    uint16_t had_same=kind==1U ? have_rise:have_fall;
    uint32_t same=kind==1U ? last_rise_tick:last_fall_tick;
    uint32_t period=had_same ? onset-same:0UL, width;
    uint16_t prior_period=kind==1U ? rise_period:fall_period;
    ++buck_load_observer.candidate_edges;
    if(had_same) buck_load_observer.last_candidate_period=period;
    /* Debounce adjacent edges, independently of the load repetition period. */
    if(have_edge && (uint32_t)(onset-last_edge_tick)<MIN_EDGE_GAP) {
        ++buck_load_observer.rejected_edges; return 0U;
    }
    /* A fully confirmed but too-short SAME-polarity interval must restart
     * acquisition at this real crossing. Ignoring it would let the next
     * crossing alias to twice the physical period. No replay while unlocked. */
    if(had_same && (period<PERIOD_MIN || period>PERIOD_MAX ||
       (prior_period && (period>(uint32_t)prior_period+PERIOD_JITTER ||
                        period+PERIOD_JITTER<(uint32_t)prior_period)))) {
        ++buck_load_observer.rejected_edges;
        if(period<PERIOD_MIN)++buck_load_observer.short_period_restarts;
        clear_phase(); had_same=0U; period=0UL;
    }
    buck_load_observer.previous_same_valid=had_same;
    buck_load_observer.previous_same_edge_tick=same;
    buck_load_observer.event_tick=onset;
    buck_load_observer.confirmed_tick=confirmed;
    buck_load_observer.detector_delay_ticks=delay;
    buck_load_observer.onset_uncertainty_ticks=3.0f; /* model/ADC dependent */
    buck_load_observer.edge_kind=kind;
    if(kind==1U) {
        if(had_same) {rise_period=filter_period(&rise_period_q8,(uint16_t)period);if(rise_good<GOOD_CYCLES)++rise_good;}
        last_rise_tick=onset; have_rise=1U; ++buck_load_observer.rising_edges;
    } else {
        if(had_same) {fall_period=filter_period(&fall_period_q8,(uint16_t)period);if(fall_good<GOOD_CYCLES)++fall_good;}
        if(have_rise) {
            width=onset-last_rise_tick;
            if(width>0UL && width<PERIOD_MAX)buck_load_observer.high_ticks=(uint16_t)width;
        }
        last_fall_tick=onset; have_fall=1U; ++buck_load_observer.falling_edges;
    }
    if(rise_good>=GOOD_CYCLES && fall_good>=GOOD_CYCLES && period_close(rise_period,fall_period)) {
        buck_load_observer.period_ticks=(uint16_t)(((uint32_t)rise_period+fall_period+1UL)/2UL);
        buck_load_observer.locked=1U;
    }
    last_edge_tick=onset; last_edge_kind=kind; have_edge=1U;
    return kind;
}
/* Crossings are small offsets, not absolute ticks converted to float.
 * Three confirming samples are NOT used as the physical edge timestamp. */
/* 边沿确认不是物理边沿开始时刻：记录 25/50/75% 穿越点，
 * 利用斜率和滤波延迟回推 onset；连续确认与最小边沿间隔共同抑制波动误触发。 */
static uint16_t track_candidate(float value,uint32_t tick) {
    float q,qp,span,a,b,offset,width,ramp,lag;
    uint16_t kind,delay,edge=0U;
    if(!pending_kind) {
        kind=phase_state==1U ? 1U:2U;
        span=high_level-low_level;
        qp=kind==1U ? previous_filtered-low_level:high_level-previous_filtered;
        q=kind==1U ? value-low_level:high_level-value;
        if(!(qp<0.25f*span && q>=0.25f*span)) return 0U;
        candidate_low=low_level; candidate_high=high_level;
        candidate_tick=tick; pending_kind=kind; crossing_mask=0U; confirmation=0U;
    }
    kind=pending_kind; span=candidate_high-candidate_low;
    q=kind==1U ? value-candidate_low:candidate_high-value;
    qp=kind==1U ? previous_filtered-candidate_low:candidate_high-previous_filtered;
    if(q<0.10f*span || tick-candidate_tick>CANDIDATE_TIMEOUT) {
        pending_kind=confirmation=crossing_mask=0U;
        ++buck_load_observer.candidate_aborts; return 0U;
    }
    if(q>qp) {
        a=0.25f*span; b=q-qp;
        offset=(float)(uint32_t)(tick-candidate_tick)-1.0f;
        if(!(crossing_mask&1U) && qp<a && q>=a) {t25=offset+(a-qp)/b;crossing_mask|=1U;}
        a=0.50f*span;
        if(!(crossing_mask&2U) && qp<a && q>=a) {t50=offset+(a-qp)/b;crossing_mask|=2U;}
        a=0.75f*span;
        if(!(crossing_mask&4U) && qp<a && q>=a) {t75=offset+(a-qp)/b;crossing_mask|=4U;}
    }
    if(q>=0.75f*span) ++confirmation; else confirmation=0U;
    if(confirmation>=EDGE_CONFIRM && crossing_mask==7U) {
        width=t75-t25;
        /* Do not misinterpret the four-interval aperture of a step as a
         * physical ramp. Wider transitions are extrapolated from their midpoint. */
        ramp=width<=2.5f ? 0.0f:2.0f*width;
        lag=(float)(uint32_t)(tick-candidate_tick)-t50+FILTER_DELAY+0.5f*ramp;
        if(lag<0.0f)lag=0.0f;
        if(lag>(float)MAX_CONFIRM_LAG) {
            ++buck_load_observer.rejected_edges;
        } else {
            delay=(uint16_t)(lag+0.5f);
            edge=register_edge(kind,tick-delay,tick,delay);
            if(edge)phase_state=kind==1U ? 2U:1U;
        }
        pending_kind=confirmation=crossing_mask=0U;
    }
    return edge;
}

/* 30 kHz 控制 ISR 内的一步更新；只做有界计算。
 * 复位、非法输入或采样 tick 不连续时清除锁定，禁止用旧相位继续补偿。 */
uint16_t buck_load_observer_step(float vo,float isum,uint16_t reset,uint32_t tick) {
    float threshold=buck_load_edge_threshold_a, raw, value;
    uint16_t edge=0U,expected,plateau;
    buck_load_observer.edge_kind=0U;
    if(!finite_f32(vo) || !finite_f32(isum) || !finite_f32(threshold) ||
       threshold<0.25f || threshold>10.0f) {
        initialized=0U; buck_load_observer.valid=0U; buck_load_observer.level_valid=0U;
        clear_phase(); return 0U;
    }
    if(reset || !initialized || tick-previous_tick!=1UL || configured_threshold!=threshold) {
        initialize(vo,isum,tick,threshold); return 0U;
    }
    previous_tick=tick;
    raw=filter_count==KCL_SAMPLES ?
        0.25f*current_sum-KCL_GAIN*(vo-vo_history[filter_index]):isum;
    if(filter_count==KCL_SAMPLES)current_sum-=i_history[filter_index];else ++filter_count;
    vo_history[filter_index]=vo; i_history[filter_index]=isum;
    current_sum+=isum; current_block_sum+=isum;
    ++filter_index;
    if(filter_index==KCL_SAMPLES) {
        filter_index=0U; current_sum=current_block_sum; current_block_sum=0.0f;
    }
    value=median3(raw,median_1,median_2); median_2=median_1; median_1=raw;
    if(median_count<3U)++median_count;
    if(!finite_f32(raw) || !finite_f32(value)) {
        initialized=0U; buck_load_observer.valid=0U; clear_phase(); return 0U;
    }
    buck_load_observer.load_a=raw; buck_load_observer.voltage_v=vo;
    buck_load_observer.filtered_load_a=value;
    if(filter_count<KCL_SAMPLES || median_count<3U) {previous_filtered=value;return 0U;}
    buck_load_observer.valid=1U;
    if(buck_load_observer.locked && have_edge) {
        expected=last_edge_kind==1U ? buck_load_observer.high_ticks:
            (uint16_t)(buck_load_observer.period_ticks-buck_load_observer.high_ticks);
        if(tick-last_edge_tick>(uint32_t)expected+MAX_CONFIRM_LAG)clear_phase();
    } else if(have_edge && tick-last_edge_tick>PERIOD_MAX+MAX_CONFIRM_LAG)clear_phase();
    /* Detect with old thresholds; a threshold update cannot create an edge.
     * Candidate thresholds are latched until confirmation or abort. */
    if(buck_load_observer.level_valid) {
        if(!phase_state) {
            plateau=value<=threshold_low ? 2U:(value>=threshold_high ? 1U:0U);
            if(!plateau)confirmation=pending_kind=0U;
            else {
                if(plateau!=pending_kind) {pending_kind=plateau;confirmation=1U;}
                else ++confirmation;
                if(confirmation>=EDGE_CONFIRM) {
                    phase_state=plateau==2U ? 1U:2U;
                    confirmation=pending_kind=0U;
                }
            }
        } else edge=track_candidate(value,tick);
    }
    learn_levels(value);
    previous_filtered=value;
    buck_load_observer.schmitt_state=phase_state;
    buck_load_observer.confirm_count=confirmation;
    return edge;
}

/* Retained diagnostic API, not called by the control ISR or v14 scheduler. */
#include "buck_npu_phase_impl.h"
