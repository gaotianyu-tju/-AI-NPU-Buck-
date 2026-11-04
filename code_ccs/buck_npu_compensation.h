#ifndef BUCK_NPU_COMPENSATION_H
#define BUCK_NPU_COMPENSATION_H
#include <stdint.h>
#include "buck_npu_timing.h"
#ifdef __cplusplus
extern "C" {
#endif

#define BUCK_NPU_COMP_PERIOD_MIN_TICKS BUCK_NPU_PERIOD_MIN_TICKS
#define BUCK_NPU_COMP_PERIOD_MAX_TICKS BUCK_NPU_PERIOD_MAX_TICKS
#define BUCK_NPU_COMP_HARD_LIMIT_A 1.0f
#define BUCK_NPU_COMP_REQUIRED_B0 20000.0f
#define BUCK_NPU_COMP_TS 3.33333337E-5F
#define BUCK_NPU_COMP_MAX_WC 30000.0f
#define BUCK_NPU_COMP_MAX_LEAD_TICKS 6U
#define BUCK_NPU_COMP_MIN_DF_VPS 100.0f
#define BUCK_NPU_COMP_HANDOFF_DONE 0.9990234375f /* 1023/1024 */

extern volatile uint16_t buck_npu_comp_attack_ticks; /* default2:66.7 us */
extern volatile uint16_t buck_npu_comp_fade_ticks;   /* legacy unused; no terminal fade in v13 */
extern volatile float buck_npu_comp_limit_a;         /* default/max1 A per phase */

/* The wrapper calls arm immediately BEFORE the one new_event step.
 * edge_tick is the estimated physical edge of the NEXT load cycle; lead is
 * the interval from full feedforward amplitude to that estimated edge.
 * Start must equal edge_tick-lead-attack, including uint32 rollover.
 * An arm is consumed by the next step, whether or not that step accepts it.
 * This function never starts a pulse or performs a hardware operation. */
void buck_npu_compensation_arm(uint32_t edge_tick, uint16_t lead_ticks);

/* IMPORTANT v11 semantic change: prediction is the paired post-pre TOTAL
 * disturbance CHANGE df, in V/s, from two correctly timestamped previous-cycle
 * H15 results. It is an EVENT AMPLITUDE reference, not f(current_tick), not a
 * trajectory, and NEVER directly compared to current z2 as a future state.
 * The caller must validate both results' epochs, polarity and true targets.
 * Expected label sign: rising load ->df<0; falling load ->df>0. Magnitude below
 *100 V/s or opposite sign rejects the event and increments a specific counter.
 * This assumption needs validation against the actual trained label on board.
 *
 * Exactly once per control tick AFTER the unchanged physical ESO update.
 * At command start freeze z2_pre and seed=clamp(-alpha*df/b0,+/-limit).
 * Smoothstep attack reaches1 at edge-lead. Before edge, takeover is EXACTLY0.
 * From edge onward raw=clip((z2-z2_pre)/df,0,1); filtered+=.25*(raw-filtered);
 * takeover=max(previous_takeover,filtered). Noise cannot restore relinquished
 * compensation. Return seed*attack*(1-takeover).
 * At takeover>=1023/1024 finish to exact0: residual is <0.977mA at the hard cap.
 * This is amplitude-limited feedforward with measured ESO takeover; if df does
 * not represent the actual disturbance change, takeover need not complete.
 * It does not prove peak reduction or eliminate every transient bias.
 *
 * v13 removes the fixed 20%-period deadline AND its terminal fade. There is
 * no elapsed-time cancellation. effective_window/total_ticks=0 mean DISABLED.
 * fade_ticks remains exported only for old watch lists and has NO effect.
 * Alpha0, permit0, invalid input, discontinuous tick, changed alpha/wc/wo/b0
 * or changed attack/current limit cancel immediately, as before.
 * Invalid prediction matters at a new event only. A valid opposite event
 * replaces the old contribution, never adds pulses; overlap is counted.
 * Same-kind events while active and repeated-high levels do not restart.
 * Without full ESO takeover, contribution may persist beyond 2 ms, including
 * a platform bias. This experiment does NOT implement a per-tick NN trajectory.
 * All reciprocals are computed only at start. No loop, wait, inference or IRQ
 * masking occurs here. Fixed Ts and b0 follow the unchanged training contract.
 */
float buck_npu_compensation_step(float prediction, float z2, float alpha, float b0,
    uint16_t permit, uint16_t new_event, uint16_t edge_kind, uint32_t tick,
    float voltage_v, float filtered_load_a, uint16_t period_ticks, float wc, float wo);
void buck_npu_compensation_reset(void);

extern volatile float buck_npu_comp_delta_a;
extern volatile float buck_npu_comp_innovation_vps; /* legacy:raw paired df */
extern volatile float buck_npu_comp_weight; /* attack*(1-takeover) */
extern volatile float buck_npu_comp_latched_delta_a; /* bounded seed */
extern volatile float buck_npu_comp_source_prediction_vps; /* legacy:paired df */
extern volatile float buck_npu_comp_ref_z2_vps; /* frozen start z2 */
extern volatile float buck_npu_comp_latched_innovation_vps; /* -seed*b0 */
extern volatile float buck_npu_comp_takeover_raw;
extern volatile float buck_npu_comp_takeover_filtered;
extern volatile float buck_npu_comp_takeover;
extern volatile float buck_npu_comp_z2_pre_vps;
extern volatile float buck_npu_comp_baseline_iref_a;
extern volatile float buck_npu_comp_final_iref_a;
extern volatile float buck_npu_comp_applied_delta_i_a;
extern volatile uint16_t buck_npu_comp_active;
extern volatile uint16_t buck_npu_comp_state; /*0idle,1anticipation,2takeover; 3 reserved*/
extern volatile uint16_t buck_npu_comp_edge_kind;
extern volatile uint16_t buck_npu_comp_config_fault;
extern volatile uint16_t buck_npu_comp_effective_window; /*0 = fixed deadline disabled in v13*/
extern volatile uint16_t buck_npu_comp_total_ticks; /*0 = fixed deadline disabled in v13*/
extern volatile uint16_t buck_npu_comp_latched_period_ticks;
extern volatile uint16_t buck_npu_comp_latched_lead_ticks;
/*0none;1reserved former deadline;2ESO handoff;3inhibit;4changed gains/settings;
 *5invalid config;6invalid sample/tick;7invalid event;8invalid/missing arm. */
extern volatile uint16_t buck_npu_comp_exit_reason;
extern volatile uint32_t buck_npu_comp_age_ticks; /* from command_start */
extern volatile uint32_t buck_npu_comp_event_tick; /* legacy:command_start */
extern volatile uint32_t buck_npu_comp_estimated_edge_tick;
extern volatile uint32_t buck_npu_comp_command_start_tick;
extern volatile uint32_t buck_npu_comp_updates;
extern volatile uint32_t buck_npu_comp_config_reject;
extern volatile uint32_t buck_npu_comp_event_reject;
extern volatile uint32_t buck_npu_comp_config_changes;
extern volatile uint32_t buck_npu_comp_finished_window; /*legacy; no increments in v13*/
extern volatile uint32_t buck_npu_comp_finished_handoff;
extern volatile uint32_t buck_npu_comp_forced_window; /*legacy; no increments in v13*/
extern volatile uint32_t buck_npu_comp_window_overlaps;
extern volatile uint32_t buck_npu_comp_arm_reject;
extern volatile uint32_t buck_npu_comp_direction_reject;
extern volatile uint32_t buck_npu_comp_small_signal_reject;
/* v10 q_v/r_vps/injected_vps/innovation_remaining_vps were removed.
 * Takeover diagnostics retain the last event's value after it finishes;
 * new event/reset clears them. active/state/delta describe current execution. */
#ifdef __cplusplus
}
#endif
#endif
