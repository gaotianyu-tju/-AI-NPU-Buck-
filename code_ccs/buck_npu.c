/*
 * NPU 与 MBD 的运行接口（H15 网络，30 kHz 控制周期）。
 * 控制 ISR：begin -> 原 ESO -> apply_prediction -> 最终限幅 -> commit。
 * CPU main：service -> 预处理 -> 启动 NPU -> 完成后恢复物理量并发布。
 * 推理为异步单任务；无结果用 NaN 表示，由控制准入逻辑取消补偿。
 * 本文件为最终 v16 交付源码；本轮仅增加说明，不修改执行语句或参数。
 */
#include "buck_npu.h"
#include "buck_npu_platform.h"
#include "buck_load_observer.h"
#include "tvmgen_default.h"
#include "ndp_model_io.h"
#include "buck_golden.h"
#include "driverlib.h"
#include <math.h>
#include <float.h>

/* v16: 20..200 Hz, 180 uF observer, filtered edge clock and delivery latch.
 * Original H15 weights, baseline controller and v13 ESO handoff unchanged.
 * ISR: bounded KCL/edge tracking, appointment delivery and sample staging.
 * MAIN: continuous inference plus two TRUE H15 endpoints per accepted edge.
 * NPU IRQ records completion only; runtime continuation remains in main. */
#define RING_SIZE 128U
#define RESULT_SIZE 512U
#define HORIZON_TICKS 15UL
/* Independent background-result age bound (8 ms), not a load-period
 * assumption. Edge pairs additionally obey their immutable next-edge/start
 * deadline in schedule_pair_complete, including periods shorter than 240.
 * A copied plan may wait >512 ticks; it never rereads the rolling cache. */
#define REPLAY_SOURCE_MAX_AGE 240UL
#define TIMEOUT_TICKS 30000UL
static volatile float raw_ring[RING_SIZE][9];
static float staged[7], snapshot[8][9];
static volatile uint32_t tick, latest_tick;
static volatile uint16_t epoch, active, raw_count, staged_valid, ready;
static volatile uint16_t control_reset = 1U;
typedef struct {
    float value;
    uint32_t target;
    uint16_t epoch, valid, edge_kind;
} Result;
/* CPU RAM array. Every published output retains its TRUE H15 target tick.
 * kind 0: continuous; 1/2: rising pre/post; 3/4: falling pre/post jobs. */
volatile Result buck_npu_cycle_cache[RESULT_SIZE];
typedef struct { uint32_t target; uint16_t epoch, generation, valid; } EdgeRequest;
static volatile EdgeRequest edge_requests[4];
static float held_prediction;
static float comp_voltage_v;
static uint16_t held_valid;
static uint16_t flight_edge_kind, flight_phase_generation;
#ifdef __TI_COMPILER_VERSION__
#pragma DATA_SECTION(model_input, ".bss.noinit.buck_npu")
#pragma DATA_ALIGN(model_input, 8)
#pragma DATA_SECTION(model_output, ".bss.noinit.buck_npu")
#pragma DATA_ALIGN(model_output, 8)
#endif
static float model_input[96], model_output[4];
static struct tvmgen_default_inputs inputs = { model_input };
static struct tvmgen_default_outputs outputs = { model_output };
static uint16_t flight_kind, flight_epoch, have_submitted, last_epoch, test_index;
static uint32_t flight_source, flight_launch, last_source;
static float flight_z2;

volatile uint16_t buck_npu_run_enable = 0U;
volatile uint16_t buck_npu_busy, buck_npu_fault;
volatile uint32_t buck_npu_submitted, buck_npu_accepted, buck_npu_dropped, buck_npu_errors;
volatile uint32_t buck_npu_completed, buck_npu_late, buck_npu_mailbox_overrun;
volatile uint32_t buck_npu_last_latency_ticks, buck_npu_max_latency_ticks;
volatile uint32_t buck_npu_last_compute_ticks, buck_npu_max_compute_ticks;
volatile uint32_t buck_npu_last_prepare_elapsed_ticks, buck_npu_max_prepare_elapsed_ticks;
volatile uint32_t buck_npu_last_preprocess_ticks, buck_npu_max_preprocess_ticks;
volatile uint16_t buck_npu_io_revision=16U;
/* TI Timer2 clocks around the scalar compensation call only, excluding the
 * observer, PWM writes and ISR entry/exit. 150 clocks = 1 us in this image.
 * Hardware-only diagnostics: host builds do not model target execution time. */
volatile uint32_t buck_npu_comp_cycles_last, buck_npu_comp_cycles_max;
volatile uint32_t buck_npu_comp_edge_cycles_max, buck_npu_comp_regular_cycles_max;
volatile uint32_t buck_npu_edge_requests, buck_npu_edge_submitted;
volatile uint32_t buck_npu_edge_published, buck_npu_edge_request_overrun;
volatile uint32_t buck_npu_edge_window_miss, buck_npu_edge_cache_miss;
volatile uint32_t buck_npu_rise_updates, buck_npu_fall_updates;
volatile uint32_t buck_npu_replay_from_tick, buck_npu_replay_at_tick;
volatile uint16_t buck_npu_replay_edge_kind, buck_npu_hold_valid;
volatile float buck_npu_held_prediction;
volatile uint32_t buck_npu_last_source_tick, buck_npu_last_target_tick;
volatile uint32_t buck_npu_raw_samples, buck_npu_snapshot_retries, buck_npu_preprocess_late;
volatile uint32_t buck_npu_published, buck_npu_no_result, buck_npu_stale_results;
volatile float buck_npu_last_prediction;
volatile uint16_t buck_npu_prediction_valid;
/* Write request=1 only with enable=1 AND run_enable=0; service never flashes.
 * state: 0 idle, 1 running, 2 passed, 3 failed, 4 aborted. */
volatile uint16_t buck_npu_selftest_request, buck_npu_selftest_state;
volatile uint16_t buck_npu_selftest_passed, buck_npu_selftest_failed;
volatile float buck_npu_selftest_max_input_error, buck_npu_selftest_max_output_error;

#ifdef __TI_COMPILER_VERSION__
#pragma FUNCTION_OPTIONS(buck_npu_begin, "--opt_level=2")
#pragma FUNCTION_OPTIONS(buck_npu_commit, "--opt_level=2")
#pragma FUNCTION_OPTIONS(invalidate_history, "--opt_level=2")
#pragma FUNC_ALWAYS_INLINE(finite_value)
#pragma FUNC_ALWAYS_INLINE(absolute)
#endif
static int finite_value(float v) {
    union { float f; uint32_t u; } bits;
    bits.f=v;
    return (bits.u & 0x7f800000UL) != 0x7f800000UL;
}
static float absolute(float v) { return v < 0.0f ? -v : v; }
#include "buck_npu_schedule_impl.h"
/* ISR is sole owner of epoch/raw_count. A reset cannot release NPU buffers. */
/* 清除控制历史并递增 epoch，使旧推理结果无法跨停机/重启交付。
 * 即使控制已停机，也不能清除 busy 或复用尚被 NPU 使用的输入输出缓冲区。 */
static void invalidate_history(void) {
    if (active || raw_count) {
        ++epoch; buck_npu_compensation_reset(); schedule_invalidate_isr();
    }
    active = 0U; raw_count = 0U; staged_valid = 0U;
    edge_requests[0].valid = edge_requests[1].valid = 0U;
    edge_requests[2].valid = edge_requests[3].valid = 0U;
    held_valid = buck_npu_hold_valid = 0U;
}
void buck_npu_mark_ready(void) { ready = 1U; }

/* 每个控制中断调用一次。电流为四相各自的实际 A 值，Vo/Vin 为 V。
 * 观测器用四相电流之和估计负载；只取已发布的事件值，不在这里执行或等待推理。
 * run_enable=0 关闭后台工作；alpha=0 仅取消补偿，两者含义不同。 */
float buck_npu_begin(float vo,float ia,float ib,float ic,float id,
                     float vref,float vin,uint16_t reset) {
    uint16_t edge;
    float value = NAN;
    buck_npu_control_timing_sample();
    ++tick;
    control_reset = reset != 0U;
    comp_voltage_v = vo;
    buck_npu_prediction_valid = 0U;
    staged_valid = 0U;
    /* Observer remains available with run_enable=0. enable/reset still stops
     * and reinitializes it. I1+I2+I3+I4 are measured physical currents. */
    edge=buck_load_observer_step(vo,ia+ib+ic+id,control_reset,tick);
    schedule_track_lock_isr();
    if (reset || buck_npu_run_enable != 1U || !ready || buck_npu_fault) {
        invalidate_history();
        buck_npu_last_prediction = buck_npu_held_prediction = NAN;
        return NAN;
    }
    active = 1U;
    if(!buck_load_observer.valid || !buck_load_observer.locked) held_valid=0U;
    /* Acquisition candidates must not flood the background edge queue. */
    if(edge && buck_load_observer.locked) schedule_confirmation_isr(edge);
    schedule_fire_isr();
    if(held_valid) {
        value=held_prediction;
        buck_npu_prediction_valid=1U;
    } else ++buck_npu_no_result;
    buck_npu_hold_valid=held_valid;
    buck_npu_held_prediction=buck_npu_last_prediction=value;
    staged[0]=vo; staged[1]=ia; staged[2]=ib; staged[3]=ic;
    staged[4]=id; staged[5]=vref; staged[6]=vin;
    staged_valid = 1U;
    return value;
}

/* prediction now carries paired post-minus-pre event change, NOT absolute f.
 * Its explicit future timing comes from the appointment metadata. */
/* 接在原 LADRC 更新 ESO 之后、最终电流给定限幅之前。
 * prediction 是成对预测的 post-pre 扰动变化量（V/s），不是占空比或绝对总扰动。
 * 只在预约 tick 为新事件授权，其余周期由补偿状态机平滑接管/退出。 */
float buck_npu_apply_prediction(float prediction,float z2,float alpha,float b0,float wc,float wo) {
    uint16_t permit=(uint16_t)(!control_reset && active && ready &&
        buck_npu_run_enable==1U && !buck_npu_fault && held_valid &&
        buck_load_observer.valid && buck_load_observer.locked && buck_npu_phase_permit);
    uint16_t new_event=(uint16_t)(permit && buck_npu_replay_at_tick==tick);
    uint16_t period_ticks=scheduled_period;
    if(new_event) buck_npu_compensation_arm(scheduled_edge,scheduled_lead);
    {
        float correction;
#ifdef __TI_COMPILER_VERSION__
        uint32_t start_cycles=CPUTimer_getTimerCount(CPUTIMER2_BASE);
        uint32_t elapsed_cycles;
#endif
        correction=buck_npu_compensation_step(prediction,z2,alpha,b0,permit,new_event,
            buck_npu_replay_edge_kind,tick,comp_voltage_v,
            buck_load_observer.filtered_load_a,period_ticks,wc,wo);
#ifdef __TI_COMPILER_VERSION__
        elapsed_cycles=start_cycles-CPUTimer_getTimerCount(CPUTIMER2_BASE);
        buck_npu_comp_cycles_last=elapsed_cycles;
        if(elapsed_cycles>buck_npu_comp_cycles_max) buck_npu_comp_cycles_max=elapsed_cycles;
        if(new_event) {
            if(elapsed_cycles>buck_npu_comp_edge_cycles_max) buck_npu_comp_edge_cycles_max=elapsed_cycles;
        } else if(elapsed_cycles>buck_npu_comp_regular_cycles_max) {
            buck_npu_comp_regular_cycles_max=elapsed_cycles;
        }
#endif
        return correction;
    }
}

/* 原始窗口一行的通道顺序：Vo,I1,I2,I3,I4,Vref,IREF,z2,Vin。
 * IREF 为本周期最终限幅后的单相给定，不乘 4；z2 必须来自同一控制周期。
 * 先写数据、最后发布 tick/count，后台复制后还会验证 epoch 与覆盖距离。 */
void buck_npu_commit(float iref,float z2,float fsw,float b0,uint16_t reset) {
    uint16_t slot,c;
    if (reset || buck_npu_run_enable != 1U || buck_npu_fault) {
        invalidate_history(); return;
    }
    if (!active || !ready || !staged_valid) return;
    staged_valid = 0U;
    if (fsw != 30000.0f || b0 != 20000.0f || !finite_value(iref) || !finite_value(z2)) {
        invalidate_history(); ++buck_npu_errors; return;
    }
    for(c=0;c<7U;++c) if (!finite_value(staged[c])) {
        invalidate_history(); ++buck_npu_errors; return;
    }
    slot = (uint16_t)(tick & (RING_SIZE-1U));
    for(c=0;c<6U;++c) raw_ring[slot][c]=staged[c];
    raw_ring[slot][6]=iref; raw_ring[slot][7]=z2; raw_ring[slot][8]=staged[6];
    /* Publish metadata last. Main validates overwrite distance after copying. */
    if (raw_count && latest_tick+1UL != tick) {
        raw_count=0U; ++epoch;
        schedule_invalidate_isr(); buck_npu_compensation_reset();
    }
    latest_tick=tick;
    if(raw_count<RING_SIZE) ++raw_count;
    ++buck_npu_raw_samples;
    schedule_trace_isr(z2);
}

static void restore_interrupt(uint16_t previous) {
    if (!previous) Interrupt_enableGlobal();
}

/* 后台启动一次异步推理。关中断仅用于移交任务元数据；归一化和 run 可被控制 ISR 抢占。
 * 模型返回异常时锁存 fault，禁止假设 NPU 已释放缓冲区后继续提交。 */
static void launch(uint16_t kind,uint32_t source,uint16_t source_epoch,float source_z2,uint16_t edge_kind) {
    int32_t rc;
    uint16_t previous=Interrupt_disableGlobal();
    /* Short state handoff only: normalization and tvmgen_run stay interruptible. */
    if ((kind==1U && (!active || epoch!=source_epoch || buck_npu_run_enable!=1U ||
                      (uint32_t)(tick-source)>=REPLAY_SOURCE_MAX_AGE)) ||
        (kind==2U && (!control_reset || buck_npu_run_enable!=0U))) {
        restore_interrupt(previous); return;
    }
    if(edge_kind) {
        uint16_t request_slot=(uint16_t)(edge_kind-1U);
        if(!edge_requests[request_slot].valid ||
           edge_requests[request_slot].epoch!=source_epoch ||
           edge_requests[request_slot].generation!=phase_generation ||
           edge_requests[request_slot].target!=source+HORIZON_TICKS) {
            restore_interrupt(previous); return;
        }
        flight_phase_generation=edge_requests[request_slot].generation;
        edge_requests[request_slot].valid=0U;
        ++buck_npu_edge_submitted;
    }
    flight_kind=kind; flight_epoch=source_epoch; flight_edge_kind=edge_kind;
    flight_source=source; flight_launch=tick; flight_z2=source_z2;
    buck_npu_busy=1U;
    tvmgen_default_finished=0;
    if(kind==1U) {
        have_submitted=1U; last_source=source; last_epoch=source_epoch;
        buck_npu_last_source_tick=source;
        buck_npu_last_target_tick=source+HORIZON_TICKS;
        ++buck_npu_submitted;
    }
    restore_interrupt(previous);
    rc=tvmgen_default_run(&inputs,&outputs);
    if(rc!=0) {
        /* Unknown accelerator ownership: latch fault; never reuse buffers. */
        buck_npu_fault=1U; ++buck_npu_errors;
        if(kind==2U) buck_npu_selftest_state=3U;
    }
}

/* 完成处理仅在后台执行。输出先反标准化为残差，再加输入来源时刻的 z2。
 * 预测目标始终是 source+15，而不是完成时刻+15。结果允许用于下一负载周期回放，
 * 但仍须满足任务 epoch、时间窗和事件配对要求；不能把迟到结果伪装成当前预测。 */
static void complete(uint32_t now) {
    float residual, prediction, error;
    uint16_t previous,slot,c,ok=1U,pair_ready=0U;
    uint32_t age;
    if(flight_kind==2U) {
        if(!control_reset || buck_npu_run_enable!=0U) buck_npu_selftest_state=4U;
        else {
            for(c=0;c<4U;++c) {
                error=absolute(model_output[c]-ndp_golden_output_all_channels[test_index][c]);
                if(!finite_value(model_output[c]) || error > 1e-5f*(1.0f+absolute(ndp_golden_output_all_channels[test_index][c]))) ok=0U;
                if(error>buck_npu_selftest_max_output_error) buck_npu_selftest_max_output_error=error;
            }
            if(ok) ++buck_npu_selftest_passed; else ++buck_npu_selftest_failed;
            ++test_index;
            if(test_index==NDP_GOLDEN_COUNT)
                buck_npu_selftest_state=buck_npu_selftest_failed ? 3U : 2U;
        }
        buck_npu_busy=0U; return;
    }
    ++buck_npu_completed;
    buck_npu_last_compute_ticks=(uint32_t)(now-flight_launch);
    if(buck_npu_last_compute_ticks>buck_npu_max_compute_ticks)
        buck_npu_max_compute_ticks=buck_npu_last_compute_ticks;
    age=(uint32_t)(now-flight_source);
    buck_npu_last_latency_ticks=age;
    if(age>buck_npu_max_latency_ticks) buck_npu_max_latency_ticks=age;
    if(ndp_restore_residual(model_output[0],&residual)!=0) {
        ++buck_npu_errors; buck_npu_busy=0U; return;
    }
    prediction=flight_z2+residual;
    if(!finite_value(prediction)) { ++buck_npu_errors; buck_npu_busy=0U; return; }
    previous=Interrupt_disableGlobal();
    /* Replay permits completion AFTER target. It does not permit completion
     * after the next cycle's edge, or reuse across resets/epoch changes. */
    if(epoch!=flight_epoch || !active || buck_npu_run_enable!=1U ||
       (flight_edge_kind && flight_phase_generation!=phase_generation)) {
        ++buck_npu_stale_results; ++buck_npu_dropped;
    } else if((uint32_t)(tick-flight_source)>=REPLAY_SOURCE_MAX_AGE) {
        ++buck_npu_late; ++buck_npu_dropped;
    } else {
        slot=(uint16_t)((flight_source+HORIZON_TICKS)&(RESULT_SIZE-1U));
        /* A regular job at the same timestamp must not replace the exact
         * edge-tagged result. Different timestamps are normal ring reuse. */
        if(!flight_edge_kind && buck_npu_cycle_cache[slot].valid &&
           buck_npu_cycle_cache[slot].epoch==flight_epoch &&
           buck_npu_cycle_cache[slot].target==flight_source+HORIZON_TICKS &&
           buck_npu_cycle_cache[slot].edge_kind!=0U) {
            ++buck_npu_dropped;
        } else {
            buck_npu_cycle_cache[slot].valid=0U;
            buck_npu_cycle_cache[slot].value=prediction;
            buck_npu_cycle_cache[slot].target=flight_source+HORIZON_TICKS;
            buck_npu_cycle_cache[slot].epoch=flight_epoch;
            buck_npu_cycle_cache[slot].edge_kind=flight_edge_kind;
            buck_npu_cycle_cache[slot].valid=1U;
            ++buck_npu_published;
            if(flight_edge_kind) {
                ++buck_npu_edge_published;
                pair_ready=1U;
            }
        }
    }
    restore_interrupt(previous);
    if(pair_ready) schedule_pair_complete(flight_edge_kind,flight_source+HORIZON_TICKS,prediction);
    buck_npu_busy=0U;
}

/* 唯一的连续推理服务入口，由生成的 ert_main.c 主循环反复调用。
 * 先处理短 ISR 留下的层切换请求；忙时检查状态后立即返回，不自旋等待。
 * 优先服务上升/下降沿的前后端点，空闲时继续普通推理。控制 ISR 不调用此函数。 */
void buck_npu_service(void) {
    uint16_t previous,source_epoch,can_snapshot,t,c,slot,edge_kind;
    uint32_t now,source,prepare_start;
    float error;
    if(!ready) return;
    /* Drain an in-flight model even if run_enable/reset changes. The short
     * hardware ISR never loads layers or touches the model I/O buffers. */
    buck_npu_deferred_service();
    if(buck_npu_fault) return;
    /* Main-only retrospective phase work runs while the accelerator is busy;
     * do not delay raw-history capture until an entire inference finishes. */
    schedule_main();
    previous=Interrupt_disableGlobal(); now=tick; restore_interrupt(previous);
    if(buck_npu_busy) {
        if(tvmgen_default_finished==1) complete(now);
        else {
            if((uint32_t)(now-flight_launch)>TIMEOUT_TICKS) {
                buck_npu_fault=2U; ++buck_npu_errors;
                if(flight_kind==2U) buck_npu_selftest_state=3U;
            }
            return;
        }
    }
/* 金标自检只允许在控制复位且后台运行开关关闭时进入；比较全部输出通道。
 * 自检通过说明接口数值一致，不等于已经验证带载控制效果。 */
    if(buck_npu_selftest_request) {
        buck_npu_selftest_request=0U;
        if(control_reset && buck_npu_run_enable==0U) {
            test_index=0U; buck_npu_selftest_passed=0U; buck_npu_selftest_failed=0U;
            buck_npu_selftest_max_input_error=0.0f; buck_npu_selftest_max_output_error=0.0f;
            buck_npu_selftest_state=1U;
        } else { buck_npu_selftest_state=4U; }
    }
    if(buck_npu_selftest_state==1U) {
        if(!control_reset || buck_npu_run_enable!=0U) { buck_npu_selftest_state=4U; return; }
        if(ndp_prepare_window(ndp_golden_raw[test_index],model_input)!=0) {
            buck_npu_selftest_state=3U; ++buck_npu_selftest_failed; return;
        }
        for(c=0;c<96U;++c) {
            error=absolute(model_input[c]-ndp_golden_normalized[test_index][c]);
            if(error>buck_npu_selftest_max_input_error) buck_npu_selftest_max_input_error=error;
            if(error>2e-6f*(1.0f+absolute(ndp_golden_normalized[test_index][c]))) {
                buck_npu_selftest_state=3U; ++buck_npu_selftest_failed; return;
            }
        }
        launch(2U,now,epoch,0.0f,0U); return;
    }
    previous=Interrupt_disableGlobal();
    source=latest_tick; source_epoch=epoch; edge_kind=0U; prepare_start=tick;
    can_snapshot=active && raw_count>=8U && buck_npu_run_enable==1U;
    if(can_snapshot) {
        /* Four endpoint slots: rise-pre/post, fall-pre/post. The oldest
         * available source is copied first. Future source waits in main. */
        for(c=0U;c<4U;++c) {
            uint32_t candidate_source=edge_requests[c].target-HORIZON_TICKS;
            if(edge_requests[c].valid && edge_requests[c].epoch==epoch &&
               edge_requests[c].generation==phase_generation &&
               (uint32_t)(latest_tick-candidate_source)<0x80000000UL &&
               (!edge_kind || (uint32_t)(latest_tick-candidate_source) >
                 (uint32_t)(latest_tick-(edge_requests[edge_kind-1U].target-HORIZON_TICKS))))
                edge_kind=(uint16_t)(c+1U);
        }
        if(edge_kind) {
            slot=(uint16_t)(edge_kind-1U);
            source=edge_requests[slot].target-HORIZON_TICKS;
            /* raw_count includes only samples from this epoch. Validate
             * source-7 as well as source, including uint32 tick rollover. */
            if((uint32_t)(latest_tick-source)+7UL >= (uint32_t)raw_count) {
                edge_requests[slot].valid=0U;
                ++buck_npu_edge_window_miss;
                can_snapshot=0U;
            }
        }
    }
    restore_interrupt(previous);
    if(!can_snapshot || (!edge_kind && have_submitted && last_source==source && last_epoch==source_epoch)) return;
    for(t=0;t<8U;++t) {
        slot=(uint16_t)((source-7UL+t)&(RING_SIZE-1U));
        for(c=0;c<9U;++c) snapshot[t][c]=raw_ring[slot][c];
    }
    previous=Interrupt_disableGlobal();
    can_snapshot=active && epoch==source_epoch && (uint32_t)(latest_tick-source)<(RING_SIZE-7U);
    restore_interrupt(previous);
    if(!can_snapshot) { ++buck_npu_snapshot_retries; return; }
    /* Verified FPU32 normalization, entirely in main. */
    if(ndp_prepare_window((const float (*)[9])snapshot,model_input)!=0) { ++buck_npu_errors; return; }
    previous=Interrupt_disableGlobal(); now=tick; restore_interrupt(previous);
    buck_npu_last_prepare_elapsed_ticks=(uint32_t)(now-prepare_start);
    if(buck_npu_last_prepare_elapsed_ticks>buck_npu_max_prepare_elapsed_ticks)
        buck_npu_max_prepare_elapsed_ticks=buck_npu_last_prepare_elapsed_ticks;
    buck_npu_last_preprocess_ticks=(uint32_t)(now-source);
    if(buck_npu_last_preprocess_ticks>buck_npu_max_preprocess_ticks)
        buck_npu_max_preprocess_ticks=buck_npu_last_preprocess_ticks;
    if((uint32_t)(now-source)>=REPLAY_SOURCE_MAX_AGE) { ++buck_npu_preprocess_late; return; }
    launch(1U,source,source_epoch,snapshot[7][7],edge_kind);
}
