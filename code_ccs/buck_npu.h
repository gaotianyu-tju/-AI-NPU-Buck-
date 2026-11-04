#ifndef BUCK_NPU_H
#define BUCK_NPU_H
#include <stdint.h>
#include "buck_load_observer.h"
#include "buck_npu_compensation.h"
#include "buck_npu_schedule.h"
#ifdef __cplusplus
extern "C" {
#endif
void buck_npu_mark_ready(void);
/* Exactly once before ADRC; CPU observer + previously prepared appointment.
 * Returns paired post-minus-pre disturbance CHANGE (V/s), or NaN. This is
 * future event feedforward metadata, not a present-time ESO state. Pass
 * through apply_prediction AFTER the current ESO update for handoff.
 * No NPU inference or wait in this function. */
float buck_npu_begin(float vo,float ia,float ib,float ic,float id,float vref,float vin,uint16_t reset);
/* Scheduled finite event feedforward; prediction is post-minus-pre change.
 * Physical ESO/Simulink ports remain unchanged. No inference or waiting. */
float buck_npu_apply_prediction(float prediction,float z2,float alpha,float b0,float wc,float wo);
/* Exactly once after ADRC; save physical signals every tick even if NPU busy. */
void buck_npu_commit(float iref,float z2,float fsw,float b0,uint16_t reset);
/* Interruptible main loop ONLY; no call from ADC/control ISR. */
void buck_npu_service(void);
extern volatile uint16_t buck_npu_run_enable, buck_npu_busy, buck_npu_fault;
extern volatile uint16_t buck_npu_prediction_valid;
extern volatile uint16_t buck_npu_io_revision;
extern volatile uint32_t buck_npu_comp_cycles_last, buck_npu_comp_cycles_max;
extern volatile uint32_t buck_npu_comp_edge_cycles_max, buck_npu_comp_regular_cycles_max;
extern volatile uint32_t buck_npu_edge_requests,buck_npu_edge_submitted,buck_npu_edge_published;
extern volatile uint32_t buck_npu_edge_request_overrun,buck_npu_edge_window_miss,buck_npu_edge_cache_miss;
extern volatile uint32_t buck_npu_rise_updates,buck_npu_fall_updates;
extern volatile uint32_t buck_npu_replay_from_tick,buck_npu_replay_at_tick;
extern volatile uint16_t buck_npu_replay_edge_kind,buck_npu_hold_valid;
extern volatile float buck_npu_held_prediction;
extern volatile uint32_t buck_npu_last_preprocess_ticks,buck_npu_max_preprocess_ticks;
extern volatile uint32_t buck_npu_submitted,buck_npu_accepted,buck_npu_dropped,buck_npu_errors;
extern volatile uint32_t buck_npu_completed,buck_npu_late,buck_npu_mailbox_overrun;
extern volatile uint32_t buck_npu_last_latency_ticks,buck_npu_max_latency_ticks;
extern volatile uint32_t buck_npu_last_compute_ticks,buck_npu_max_compute_ticks;
extern volatile uint32_t buck_npu_last_prepare_elapsed_ticks,buck_npu_max_prepare_elapsed_ticks;
extern volatile uint32_t buck_npu_last_source_tick,buck_npu_last_target_tick;
extern volatile uint32_t buck_npu_raw_samples,buck_npu_snapshot_retries,buck_npu_preprocess_late;
extern volatile uint32_t buck_npu_published,buck_npu_no_result,buck_npu_stale_results;
extern volatile float buck_npu_last_prediction;
extern volatile uint16_t buck_npu_selftest_request,buck_npu_selftest_state;
extern volatile uint16_t buck_npu_selftest_passed,buck_npu_selftest_failed;
extern volatile float buck_npu_selftest_max_input_error,buck_npu_selftest_max_output_error;
#ifdef __cplusplus
}
#endif
#endif
