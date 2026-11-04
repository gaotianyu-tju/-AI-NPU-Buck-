/*
 * 最终 v16 上升/下降沿双事务调度，在 buck_npu.c 内编译。
 * 学习可持续更新；已预约的前后预测对不可在交付前被新边沿覆盖。
 * 本文件为最终 v16 交付源码；本轮仅增加说明，不修改执行语句或参数。
 */
/* v16: 20..200 Hz; observations and immutable delivery are independent.
 * Period/phase tracking continues while a value awaits controller handoff.
 * Bounded timestamp jitter is filtered, never used to relabel H15 outputs.
 * A pending
 * prediction is immutable until handed to the controller or explicitly
 * invalidated/expired. Observer learning and continuous NPU service continue.
 * ISR enqueues scalar onset metadata and fires appointments; no NN inference.
 * All shared publications are metadata-last under bounded interrupt masks. */
#include "buck_npu_schedule.h"
#include "buck_npu_timing.h"
#include "buck_npu_phase.h"
static void restore_interrupt(uint16_t previous);
volatile uint16_t buck_npu_lead_rise_ticks=1U, buck_npu_lead_fall_ticks=1U;
volatile uint16_t buck_npu_pre_edge_ticks=6U, buck_npu_post_edge_ticks=24U;
volatile uint16_t buck_npu_phase_permit;
volatile buck_npu_phase_status_t buck_npu_phase_status[2];
volatile uint32_t buck_npu_phase_estimated, buck_npu_phase_rejected;
volatile uint32_t buck_npu_phase_bypassed;
volatile uint32_t buck_npu_phase_snapshot_miss, buck_npu_phase_confirm_overrun;
volatile uint32_t buck_npu_schedule_armed, buck_npu_schedule_missed;
volatile uint32_t buck_npu_schedule_fired, buck_npu_schedule_cancelled;
volatile uint32_t buck_npu_schedule_bad_pair;
volatile uint16_t buck_npu_delivery_pending[2];
volatile uint32_t buck_npu_delivery_suppressed, buck_npu_delivery_timeout;
volatile uint32_t buck_npu_delivery_count[2];
static volatile uint32_t delivery_deadline[2];
volatile buck_npu_ff_trace_t buck_npu_ff_trace[BUCK_NPU_FF_TRACE_COUNT];
volatile uint16_t buck_npu_ff_trace_request, buck_npu_ff_trace_ready, buck_npu_ff_trace_count;
static uint16_t trace_active;
volatile uint32_t buck_npu_phase_observed_while_pending;
volatile uint32_t buck_npu_phase_deferred_stale;
#ifdef __TI_COMPILER_VERSION__
#pragma FUNCTION_OPTIONS(schedule_invalidate_isr, "--opt_level=2")
#pragma FUNCTION_OPTIONS(schedule_track_lock_isr, "--opt_level=2")
#pragma FUNCTION_OPTIONS(schedule_confirmation_isr, "--opt_level=2")
#pragma FUNCTION_OPTIONS(schedule_fire_isr, "--opt_level=2")
#pragma FUNCTION_OPTIONS(schedule_trace_isr, "--opt_level=2")
#pragma FUNCTION_OPTIONS(schedule_main, "--opt_level=2")
#pragma FUNCTION_OPTIONS(schedule_pair_complete, "--opt_level=2")
#pragma FUNCTION_OPTIONS(schedule_cancel_main, "--opt_level=2")
#pragma FUNCTION_OPTIONS(schedule_release_main, "--opt_level=2")
#pragma FUNCTION_OPTIONS(schedule_track_main, "--opt_level=2")
#endif
typedef struct {
    uint32_t tick, onset;
    uint16_t delay;
    float uncertainty;
    uint16_t epoch, generation, valid;
} PhaseConfirmation;
typedef struct {
    uint32_t edge, start, anchor, pre_target, post_target;
    float delta;
    uint16_t period, lead, attack, pre, post, epoch, generation, valid;
} ScheduledPlan;
typedef struct {
    uint32_t last_edge, anchor, pre_target, post_target, next_edge;
    float pre_value, post_value;
    uint16_t have, good, period, epoch, generation, pre, post, mask, valid;
} PhaseWork;
static volatile PhaseConfirmation confirmations[2];
static volatile ScheduledPlan plans[2];
static PhaseWork phase_work[2];
typedef struct {
    uint32_t last_onset, first_onset, fitted_tick, period_q8, next_edge;
    uint16_t fraction_q8, have, good, period;
} PhaseTrack;
static PhaseTrack phase_track[2];
static PhaseConfirmation deferred[2];
static volatile uint16_t phase_generation=1U;
static uint16_t phase_was_locked, main_phase_generation;
static uint32_t scheduled_edge;
static uint16_t scheduled_lead, scheduled_period;
static uint16_t scheduled_attack, scheduled_pre, scheduled_post;

/* ISR-only cancellation. It never touches main's private phase_work. */
static void schedule_invalidate_isr(void) {
    ++phase_generation;
    buck_npu_phase_permit=0U;
    plans[0].valid=plans[1].valid=0U;
    confirmations[0].valid=confirmations[1].valid=0U;
    buck_npu_delivery_pending[0]=buck_npu_delivery_pending[1]=0U;
    edge_requests[0].valid=edge_requests[1].valid=0U;
    edge_requests[2].valid=edge_requests[3].valid=0U;
    held_valid=0U;
    if(trace_active) { trace_active=0U; buck_npu_ff_trace_ready=1U; }
}
static void schedule_track_lock_isr(void) {
    uint16_t locked=(uint16_t)(buck_load_observer.valid && buck_load_observer.locked);
    if(phase_was_locked && !locked) schedule_invalidate_isr();
    phase_was_locked=locked;
}
/* ISR 只发布确认事件，不在这里做历史搜索、预测配对或推理。 */
static void schedule_confirmation_isr(uint16_t kind) {
    uint16_t i=(uint16_t)(kind-1U);
    if(i>=2U) return;
    /* The inbox contains observations only. It cannot change an armed
     * prediction's anchor, NN endpoints, amplitude or scheduled delivery. */
    if(buck_npu_delivery_pending[i]) ++buck_npu_phase_observed_while_pending;
    if(confirmations[i].valid) { ++buck_npu_phase_confirm_overrun; return; }
    confirmations[i].valid=0U;
    confirmations[i].tick=buck_load_observer.confirmed_tick;
    confirmations[i].onset=buck_load_observer.event_tick;
    confirmations[i].delay=buck_load_observer.detector_delay_ticks;
    confirmations[i].uncertainty=buck_load_observer.onset_uncertainty_ticks;
    confirmations[i].epoch=epoch;
    confirmations[i].generation=phase_generation;
    confirmations[i].valid=1U;
}
/* 仅在 plans.start 到达时将已准备的扰动增量交给控制器。
 * 过时、失锁或 epoch 不匹配的事务取消；绝不把迟到结果立即补到错误相位。 */
static void schedule_fire_isr(void) {
    uint16_t i, lead;
    if(!buck_npu_phase_permit) { held_valid=0U; return; }
    /* A debugger edit must also cancel an already consumed appointment. */
    if(held_valid) {
        lead=buck_npu_replay_edge_kind==1U ? buck_npu_lead_rise_ticks : buck_npu_lead_fall_ticks;
        if(lead!=scheduled_lead || scheduled_attack!=buck_npu_comp_attack_ticks ||
           scheduled_pre!=buck_npu_pre_edge_ticks || scheduled_post!=buck_npu_post_edge_ticks) {
            held_valid=0U; ++buck_npu_schedule_cancelled;
        }
    }
    for(i=0U;i<2U;++i) {
        if(!plans[i].valid) continue;
        lead=i==0U ? buck_npu_lead_rise_ticks : buck_npu_lead_fall_ticks;
        if(plans[i].epoch!=epoch || plans[i].generation!=phase_generation ||
           plans[i].lead!=lead || plans[i].attack!=buck_npu_comp_attack_ticks ||
           plans[i].pre!=buck_npu_pre_edge_ticks || plans[i].post!=buck_npu_post_edge_ticks) {
            plans[i].valid=0U; buck_npu_delivery_pending[i]=0U;
            held_valid=0U; ++buck_npu_schedule_cancelled; continue;
        }
        if(tick==plans[i].start) {
            plans[i].valid=0U;
            buck_npu_delivery_pending[i]=0U;
            ++buck_npu_delivery_count[i];
            held_prediction=plans[i].delta; held_valid=1U;
            scheduled_edge=plans[i].edge; scheduled_lead=plans[i].lead;
            scheduled_period=plans[i].period;
            scheduled_attack=plans[i].attack;
            scheduled_pre=plans[i].pre; scheduled_post=plans[i].post;
            buck_npu_replay_from_tick=plans[i].anchor;
            buck_npu_replay_at_tick=tick; buck_npu_replay_edge_kind=(uint16_t)(i+1U);
            ++buck_npu_schedule_fired; ++buck_npu_accepted;
            if(i==0U) ++buck_npu_rise_updates; else ++buck_npu_fall_updates;
            if(buck_npu_ff_trace_request) {
                buck_npu_ff_trace_request=0U; buck_npu_ff_trace_ready=0U;
                buck_npu_ff_trace_count=0U; trace_active=1U;
            }
        } else if((uint32_t)(tick-plans[i].start)<0x80000000UL) {
            plans[i].valid=0U; buck_npu_delivery_pending[i]=0U;
            held_valid=0U; ++buck_npu_schedule_missed;
        }
    }
}
static void schedule_trace_isr(float z2) {
    uint16_t i;
    if(!trace_active) return;
    i=buck_npu_ff_trace_count;
    if(i>=BUCK_NPU_FF_TRACE_COUNT) { trace_active=0U; buck_npu_ff_trace_ready=1U; return; }
    buck_npu_ff_trace[i].tick=tick;
    buck_npu_ff_trace[i].voltage_v=comp_voltage_v;
    buck_npu_ff_trace[i].z2_vps=z2;
    buck_npu_ff_trace[i].load_a=buck_load_observer.load_a;
    buck_npu_ff_trace[i].delta_requested_a=buck_npu_comp_delta_a;
    buck_npu_ff_trace[i].delta_applied_a=buck_npu_comp_applied_delta_i_a;
    buck_npu_ff_trace[i].kind=buck_npu_replay_edge_kind;
    buck_npu_ff_trace[i].active=buck_npu_comp_active;
    buck_npu_ff_trace_count=(uint16_t)(i+1U);
    if(i+1U==BUCK_NPU_FF_TRACE_COUNT) { trace_active=0U; buck_npu_ff_trace_ready=1U; }
}
static void schedule_cancel_main(void) {
    uint16_t previous=Interrupt_disableGlobal();
    ++phase_generation; /* in-flight endpoint results belong to the old phase */
    buck_npu_phase_permit=0U;
    plans[0].valid=plans[1].valid=0U;
    confirmations[0].valid=confirmations[1].valid=0U;
    buck_npu_delivery_pending[0]=buck_npu_delivery_pending[1]=0U;
    held_valid=0U;
    edge_requests[0].valid=edge_requests[1].valid=0U;
    edge_requests[2].valid=edge_requests[3].valid=0U;
    restore_interrupt(previous);
    phase_work[0].valid=phase_work[1].valid=0U;
    phase_track[0].have=phase_track[1].have=0U;
    phase_track[0].good=phase_track[1].good=0U;
    deferred[0].valid=deferred[1].valid=0U;
    ++buck_npu_schedule_cancelled;
}
static uint16_t schedule_period_close(uint16_t a,uint16_t b) {
    return (uint16_t)((a>b ? a-b : b-a)<=BUCK_NPU_PERIOD_AGREEMENT_TICKS);
}
/* A reset ISR may run during main arithmetic. Release only this exact
 * transaction; never clear a newer event created after reset/reacquisition. */
static void schedule_release_main(uint16_t i,uint16_t ep,uint16_t gen,uint32_t anchor) {
    uint16_t previous=Interrupt_disableGlobal();
    if(epoch==ep && phase_generation==gen && phase_work[i].epoch==ep &&
       phase_work[i].generation==gen && phase_work[i].anchor==anchor)
        buck_npu_delivery_pending[i]=0U;
    restore_interrupt(previous);
}
/* Integer phase filter in main. Absolute 32-bit time is never converted
 * to float. Q8 stores only the small period/fraction, including at wrap.
 * Raw intervals outside shared 20..200 Hz bounds (with jitter guard),
 * or >12 ticks from the running period
 * invalidate tracking. Small edge jitter cannot repeatedly cancel plans. */
static uint16_t schedule_track_main(uint16_t i,const PhaseConfirmation *c) {
    PhaseTrack *t=&phase_track[i];
    uint32_t interval=0UL, predicted, fraction;
    int32_t error, correction, q;
    if(t->have && c->onset==t->last_onset) return 0U;
    if(t->have) {
        interval=(uint32_t)(c->onset-t->last_onset);
        /* The observer resets phase on a genuine too-short cycle. A repeated
         * inbox notification must not rewrite an immutable pending plan. */
        if(interval<BUCK_NPU_PERIOD_MIN_TICKS) return 0U;
        if(interval>BUCK_NPU_PERIOD_MAX_TICKS || (t->period &&
           (interval>(uint32_t)t->period+BUCK_NPU_PERIOD_JITTER_TICKS ||
            interval+BUCK_NPU_PERIOD_JITTER_TICKS<t->period))) {
            ++buck_npu_phase_rejected; schedule_cancel_main(); return 0U;
        }
        if(t->good<2U) {
            /* Acquire from the span of up to two intervals. Do not integrate
             * the noisy first interval into a displaced phase accumulator. */
            t->period_q8=(uint32_t)(c->onset-t->first_onset)*256UL/(uint32_t)(t->good+1U);
            t->fitted_tick=c->onset; t->fraction_q8=0U;
            error=0L;
        } else {
            fraction=(uint32_t)t->fraction_q8+(t->period_q8&255UL);
            predicted=t->fitted_tick+(t->period_q8>>8)+(fraction>>8);
            error=(int32_t)(c->onset-predicted)*256L-(int32_t)(fraction&255UL);
            correction=error/2L;
            if(correction>768L)correction=768L;
            if(correction< -768L)correction= -768L;
            q=(int32_t)(fraction&255UL)+correction;
            /* Use a positive bias for portable division, no signed shifts. */
            t->fitted_tick=predicted+(uint32_t)((q+1024L)/256L)-4UL;
            t->fraction_q8=(uint16_t)((q+1024L)%256L);
            q=(int32_t)(interval*256UL)-(int32_t)t->period_q8;
            t->period_q8=(uint32_t)((int32_t)t->period_q8+q/4L);
        }
        t->period=(uint16_t)((t->period_q8+128UL)>>8);
        if(t->good<2U)++t->good;
    } else {
        t->period_q8=0UL;t->period=t->good=0U;
        t->first_onset=c->onset;
        t->fitted_tick=c->onset;t->fraction_q8=0U;error=0L;
    }
    t->last_onset=c->onset;t->have=1U;
    t->next_edge=t->fitted_tick+
        (((uint32_t)t->fraction_q8+t->period_q8+128UL)>>8);
    buck_npu_phase_status[i].confirmed_tick=c->tick;
    buck_npu_phase_status[i].estimated_tick=c->onset;
    buck_npu_phase_status[i].detector_delay_ticks=c->delay;
    buck_npu_phase_status[i].confidence=0.f;
    buck_npu_phase_status[i].phase_error_ticks=error/256L;
    buck_npu_phase_status[i].raw_period_ticks=(uint16_t)interval;
    buck_npu_phase_status[i].period_ticks=t->period;
    buck_npu_phase_status[i].good_cycles=t->good;
    ++buck_npu_phase_estimated;
    buck_npu_phase_last_status=BUCK_NPU_PHASE_OK;
    buck_npu_phase_uncertainty_ticks=c->uncertainty;
    return 1U;
}
/* MAIN owns tracker/deferred/work. ISR owns the metadata inbox and exact-tick
 * handoff. A blocked delivery never blocks observations or learning. */
/* 后台消化事件、跟踪相位并申请四类预测端点。
 * 目标为边沿前 pre 与边沿后 post；H15 输入来源分别是这两个目标再减 15 tick。
 * 事务待交付期间保留 pending，新的学习独立继续，不覆盖已经锁存的预约。 */
static void schedule_main(void) {
    uint16_t previous,i,chosen=2U,gen,ep,pre,post;
    uint32_t conf=0UL;
    PhaseConfirmation c;
    PhaseWork *w;
    previous=Interrupt_disableGlobal(); gen=phase_generation; ep=epoch;
    if(!active || !buck_load_observer.locked || buck_npu_run_enable!=1U) {
        restore_interrupt(previous); return;
    }
    if(gen!=main_phase_generation) {
        restore_interrupt(previous);
        phase_track[0].have=phase_track[1].have=0U;
        phase_track[0].good=phase_track[1].good=0U;
        phase_work[0].valid=phase_work[1].valid=0U;
        deferred[0].valid=deferred[1].valid=0U;
        main_phase_generation=gen;
        previous=Interrupt_disableGlobal();
        if(gen!=phase_generation || ep!=epoch || !active) {
            restore_interrupt(previous);return;
        }
    }
    for(i=0U;i<2U;++i) if(buck_npu_delivery_pending[i] &&
        (uint32_t)(tick-delivery_deadline[i])<0x80000000UL) {
        plans[i].valid=0U;
        edge_requests[i*2U].valid=edge_requests[i*2U+1U].valid=0U;
        phase_work[i].valid=0U;buck_npu_delivery_pending[i]=0U;
        ++buck_npu_delivery_timeout;
    }
    for(i=0U;i<2U;++i) if(confirmations[i].valid &&
        confirmations[i].epoch==ep && confirmations[i].generation==gen &&
        (chosen==2U || (uint32_t)(tick-confirmations[i].tick)>(uint32_t)(tick-conf))) {
        chosen=i;conf=confirmations[i].tick;
    }
    if(chosen!=2U) {c=confirmations[chosen];confirmations[chosen].valid=0U;}
    restore_interrupt(previous);
    if(chosen!=2U) {
        if((uint32_t)(c.tick-c.onset)>40UL) {
            ++buck_npu_phase_rejected;schedule_cancel_main();return;
        }
        if(schedule_track_main(chosen,&c)) {
            if(deferred[chosen].valid)++buck_npu_delivery_suppressed;
            deferred[chosen]=c;deferred[chosen].valid=1U;
        }
    }
    previous=Interrupt_disableGlobal();
    if(gen!=phase_generation || ep!=epoch || !active || !buck_load_observer.locked) {
        restore_interrupt(previous);return;
    }
    buck_npu_phase_permit=(uint16_t)(phase_track[0].good>=2U && phase_track[1].good>=2U &&
        schedule_period_close(phase_track[0].period,phase_track[1].period));
    restore_interrupt(previous);
    for(i=0U;i<2U;++i) {
        if(!deferred[i].valid || buck_npu_delivery_pending[i]) continue;
        c=deferred[i];deferred[i].valid=0U;
        if(c.epoch!=ep || c.generation!=gen)continue;
        /* Bounded raw ring: do not launch old endpoints after a stalled job. */
        if((uint32_t)(tick-c.onset)>80UL) {++buck_npu_phase_deferred_stale;continue;}
        pre=buck_npu_pre_edge_ticks;post=buck_npu_post_edge_ticks;
        if(pre<4U || pre>12U || post<23U || post>40U) {
            ++buck_npu_schedule_bad_pair;schedule_cancel_main();return;
        }
        w=&phase_work[i];w->anchor=c.onset;
        w->pre_target=c.onset-pre;w->post_target=c.onset+post;
        w->pre=pre;w->post=post;w->mask=0U;w->valid=1U;
        w->epoch=ep;w->generation=gen;
        w->period=phase_track[i].period;w->next_edge=phase_track[i].next_edge;
        buck_npu_phase_status[i].pre_target_tick=w->pre_target;
        buck_npu_phase_status[i].post_target_tick=w->post_target;
        buck_npu_phase_status[i].pair_mask=0U;
        previous=Interrupt_disableGlobal();
        if(active && epoch==ep && phase_generation==gen && buck_load_observer.locked &&
           buck_npu_run_enable==1U && !buck_npu_delivery_pending[i]) {
            uint16_t j=(uint16_t)(i*2U);
            /* Acquire using the supported maximum; after period learning use
             * this transaction's next same-polarity edge, not fixed 11 ms.
             * A completed plan gets the stricter start+1 deadline below. */
            delivery_deadline[i]=w->period ? w->next_edge:
                c.onset+(uint32_t)BUCK_NPU_PERIOD_MAX_TICKS;
            buck_npu_delivery_pending[i]=1U;
            edge_requests[j].valid=edge_requests[j+1U].valid=0U;
            edge_requests[j].target=w->pre_target;edge_requests[j+1U].target=w->post_target;
            edge_requests[j].epoch=edge_requests[j+1U].epoch=ep;
            edge_requests[j].generation=edge_requests[j+1U].generation=gen;
            edge_requests[j].valid=edge_requests[j+1U].valid=1U;
            buck_npu_edge_requests+=2UL;
        } else w->valid=0U;
        restore_interrupt(previous);
    }
}
/* main only; arithmetic stays interruptible. Only final plan commit masks IRQ. */
/* 同一边沿前后预测齐全后取 delta=post-pre，预约下一同类边沿。
 * start=edge-lead-attack；先平滑建立，再在真实边沿附近给出前馈。
 * 所有较重运算保持可抢占，最终写入计划及 valid 标记才短暂屏蔽中断。 */
static void schedule_pair_complete(uint16_t code,uint32_t target,float value) {
    uint16_t i=(uint16_t)((code-1U)/2U), part=(uint16_t)((code-1U)&1U);
    uint16_t lead, attack, previous;
    uint32_t start, edge;
    float delta;
    PhaseWork *w=&phase_work[i];
    if(!w->valid || !buck_npu_delivery_pending[i] || w->epoch!=flight_epoch || w->generation!=phase_generation ||
        flight_phase_generation!=phase_generation ||
        target!=(part ? w->post_target : w->pre_target)) return;
    if(part) w->post_value=value; else w->pre_value=value;
    w->mask=(uint16_t)(w->mask|(part ? 2U:1U));
    buck_npu_phase_status[i].pair_mask=w->mask;
    if(w->mask!=3U) return;
    w->valid=0U;
    delta=w->post_value-w->pre_value;
    buck_npu_phase_status[i].prediction_pre=w->pre_value;
    buck_npu_phase_status[i].prediction_post=w->post_value;
    buck_npu_phase_status[i].change_vps=delta;
    if(!buck_npu_phase_permit) {
        schedule_release_main(i,w->epoch,w->generation,w->anchor);
        return; /* acquisition pair, no command */
    }
    lead=i==0U ? buck_npu_lead_rise_ticks : buck_npu_lead_fall_ticks;
    attack=buck_npu_comp_attack_ticks;
    if(!finite_value(delta) || absolute(delta)<100.0f ||
        (i==0U ? delta>=0.0f : delta<=0.0f) || lead>6U || attack<1U || attack>6U ||
        w->pre!=buck_npu_pre_edge_ticks || w->post!=buck_npu_post_edge_ticks) {
        ++buck_npu_schedule_bad_pair; plans[i].valid=0U;
        schedule_release_main(i,w->epoch,w->generation,w->anchor); return;
    }
    edge=w->next_edge;
    start=edge-(uint32_t)lead-attack;
    if((uint32_t)(start-tick)==0UL || (uint32_t)(start-tick)>=0x80000000UL) {
        ++buck_npu_schedule_missed;
        schedule_release_main(i,w->epoch,w->generation,w->anchor); return;
    }
    previous=Interrupt_disableGlobal();
    if(!active || epoch!=w->epoch || phase_generation!=w->generation ||
       !buck_npu_phase_permit || buck_npu_run_enable!=1U || !buck_npu_delivery_pending[i] ||
       (uint32_t)(start-tick)==0UL || (uint32_t)(start-tick)>=0x80000000UL) {
        /* A reset can have invalidated this transaction while arithmetic ran. */
        if(epoch==w->epoch && phase_generation==w->generation) buck_npu_delivery_pending[i]=0U;
        restore_interrupt(previous); ++buck_npu_schedule_cancelled; return;
    }
    plans[i].valid=0U;
    plans[i].edge=edge; plans[i].start=start; plans[i].anchor=w->anchor;
    plans[i].pre_target=w->pre_target; plans[i].post_target=w->post_target;
    plans[i].delta=delta; plans[i].period=w->period; plans[i].lead=lead; plans[i].attack=attack;
    plans[i].pre=w->pre; plans[i].post=w->post;
    plans[i].epoch=w->epoch; plans[i].generation=w->generation;
    delivery_deadline[i]=start+1UL; /* ISR hands it off at start before main */
    plans[i].valid=1U;
    restore_interrupt(previous);
    buck_npu_phase_status[i].next_edge_tick=edge;
    buck_npu_phase_status[i].command_start_tick=start;
    ++buck_npu_schedule_armed;
}
