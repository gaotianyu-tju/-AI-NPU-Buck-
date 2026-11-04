#ifndef BUCK_LOAD_OBSERVER_H
#define BUCK_LOAD_OBSERVER_H
#include <stdint.h>

/* 30 kHz CPU KCL observer, Cout=180 uF. vo is volts; isum is the sum of the
 * four MEASURED inductor currents in A. Four-interval estimate + median3.
 * event_tick estimates ramp onset; confirmed_tick records when accepted.
 * Timing uncertainty remains from waveform shape and ADC acquisition. */
typedef struct {
    /* Preserve the existing CCS diagnostic prefix and field order. */
    float load_a;
    float voltage_v;
    uint32_t event_tick;
    uint32_t previous_same_edge_tick;
    uint32_t rising_edges;
    uint32_t falling_edges;
    uint32_t unlocks;
    uint16_t valid;
    uint16_t locked;
    uint16_t edge_kind; /* 0 none, 1 confirmed rising candidate, 2 falling */
    uint16_t previous_same_valid;
    uint16_t period_ticks;
    uint16_t high_ticks;
    /* v4 diagnostics. load_a above remains the unfiltered physical estimate. */
    float filtered_load_a;
    float low_level_a;
    float high_level_a;
    float threshold_low_a;
    float threshold_high_a;
    float learned_span_a;
    uint16_t level_valid;
    uint16_t schmitt_state; /* 0 unknown, 1 low, 2 high */
    uint16_t confirm_count;
    uint16_t learning_ticks;
    uint32_t candidate_edges;
    uint32_t rejected_edges;
    uint32_t level_relearns;
    uint32_t last_candidate_period;
    uint32_t confirmed_tick;
    uint16_t detector_delay_ticks;
    float onset_uncertainty_ticks;
    float capacitance_uf;
    uint32_t stable_learning_samples;
    uint32_t learning_blocks;
    uint32_t candidate_aborts;
    /* v16 append-only diagnostics; no 100 Hz fallback when unlocked. */
    uint16_t learning_window_ticks;
    uint32_t short_period_restarts;
} buck_load_observer_status_t;

extern volatile buck_load_observer_status_t buck_load_observer;
/* Minimum edge/noise scale. Change during reset/disabled.
 * Valid 0.25..10 A; learned pulse span must be at least four times it.
 * Schmitt thresholds use 25/75 percent of learned stable levels. */
extern volatile float buck_load_edge_threshold_a;

/* Exactly once per control tick; reset!=0 inhibits and clears phase.
 * Candidate events may be returned before lock. The caller must require
 * valid && level_valid && locked && previous_same_valid for replay.
 * No loops, dynamic allocation, blocking calls, or peripheral access.
 * Filtering and three-sample confirmation limit very narrow/weak pulses.
 * Level learning continues while scheduler delivery is pending. */
uint16_t buck_load_observer_step(float vo, float isum,
                                uint16_t reset, uint32_t tick);
#endif
