#ifndef BUCK_NPU_SCHEDULE_H
#define BUCK_NPU_SCHEDULE_H
#include <stdint.h>
/* Change while alpha=0 and NPU disabled. Lead is command PEAK advance
 * relative to the estimated physical onset; verify alignment on hardware. */
extern volatile uint16_t buck_npu_lead_rise_ticks, buck_npu_lead_fall_ticks;
extern volatile uint16_t buck_npu_pre_edge_ticks, buck_npu_post_edge_ticks;
extern volatile uint16_t buck_npu_phase_permit;
typedef struct {
    /* Confirmation is later than estimated onset. The estimate is not a
     * hardware sync signal; confidence=0 makes no statistical guarantee. */
    uint32_t confirmed_tick, estimated_tick, next_edge_tick, command_start_tick;
    uint32_t pre_target_tick, post_target_tick;
    int32_t phase_error_ticks;
    float confidence, prediction_pre, prediction_post, change_vps;
    uint16_t detector_delay_ticks, period_ticks, good_cycles, pair_mask, raw_period_ticks;
} buck_npu_phase_status_t;
extern volatile buck_npu_phase_status_t buck_npu_phase_status[2];
extern volatile uint32_t buck_npu_phase_estimated, buck_npu_phase_rejected;
extern volatile uint32_t buck_npu_phase_bypassed;
extern volatile uint32_t buck_npu_phase_snapshot_miss, buck_npu_phase_confirm_overrun;
extern volatile uint32_t buck_npu_schedule_armed, buck_npu_schedule_missed;
extern volatile uint32_t buck_npu_schedule_fired, buck_npu_schedule_cancelled;
extern volatile uint32_t buck_npu_schedule_bad_pair;
/* [0] rising, [1] falling. A queued value is never overwritten until delivery
 * or explicit invalidation/failure/expiry. Learning and inference never wait. */
extern volatile uint16_t buck_npu_delivery_pending[2];
extern volatile uint32_t buck_npu_delivery_suppressed, buck_npu_delivery_timeout;
extern volatile uint32_t buck_npu_delivery_count[2];
extern volatile uint32_t buck_npu_phase_observed_while_pending;
extern volatile uint32_t buck_npu_phase_deferred_stale;
/* Optional one-shot coherent ISR trace, request=1 captures next applied event.
 * Reads are coherent once count stops and ready=1. Never freezes the CPU. */
typedef struct {
    uint32_t tick;
    float voltage_v, z2_vps, load_a, delta_requested_a, delta_applied_a;
    uint16_t kind, active;
} buck_npu_ff_trace_t;
#define BUCK_NPU_FF_TRACE_COUNT 96U
extern volatile buck_npu_ff_trace_t buck_npu_ff_trace[BUCK_NPU_FF_TRACE_COUNT];
extern volatile uint16_t buck_npu_ff_trace_request, buck_npu_ff_trace_ready;
extern volatile uint16_t buck_npu_ff_trace_count;
#endif
