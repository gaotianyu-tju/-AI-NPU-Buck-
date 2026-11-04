#ifndef BUCK_NPU_PHASE_H
#define BUCK_NPU_PHASE_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

#define BUCK_NPU_PHASE_HISTORY 64U
#define BUCK_NPU_PHASE_CHANNELS 9U
#define BUCK_NPU_PHASE_MAX_BACK_TICKS 55U

#define BUCK_NPU_PHASE_OK 1U
#define BUCK_NPU_PHASE_BAD_ARGUMENT 2U
#define BUCK_NPU_PHASE_BAD_DATA 3U
#define BUCK_NPU_PHASE_BAD_LEVELS 4U
#define BUCK_NPU_PHASE_NO_EDGE 5U
#define BUCK_NPU_PHASE_AMBIGUOUS 6U
#define BUCK_NPU_PHASE_OUT_OF_RANGE 7U
#define BUCK_NPU_PHASE_BYPASSED 8U /* confirmed-edge anchor; no physical onset estimate */

/* MAIN/BACKGROUND ONLY; NEVER call from the 30-kHz control ISR.
 * This function uses private static scratch space and is NOT reentrant.
 * raw must be a complete, coherent, consecutive 64-row snapshot for times
 * confirm_tick-63 ... confirm_tick. Caller must establish that contract before
 * calling; a C array parameter cannot prove allocation length or timestamps.
 * Vo is channel0 (V), four MEASURED phase currents are channels1..4 (A).
 * All nine channels of every row must be finite. low/high are the previously
 * learned load-current plateaus (A), high-low>=4 A. kind1=rise,kind2=fall.
 *
 * Returns1 on accepted estimate,0 on rejection. On failure confidence=0 and
 * edge_tick=confirm_tick when the pointers exist; do not use that fallback as
 * a physical edge. Accepted edge_tick is a nearest-tick PHYSICAL ONSET ESTIMATE,
 * not the observer's delayed confirmation timestamp. It uses4-interval KCL,
 * isolated-spike median rejection, polarity, pre/post platforms, continuous
 * change and10/30/70-percent crossings. A linear10/30-percent back-extrapolation
 * includes a2-tick short-window center correction. No fixed rise/fall slew is
 * assumed. Fast-step shape, ADC offsets and Cout error leave uncertainty;
 * ideal tests target about3ticks, NOT a guaranteed hardware error bound.
 * Backdating is strictly<55ticks; insufficient history, wrong polarity,
 * nonfinite data, ambiguous candidates or implausible shapes are rejected.
 *
 * confidence is a heuristic0..1 QUALITY SCORE, NOT a statistical probability.
 * uncertainty_ticks is an indicative shape/noise allowance, not a confidence
 * interval. Validate actual phase against measured load transitions before
 * enabling phase-sensitive compensation. Original physical ESO/ML features
 * and control timing are not altered by this read-only calculation.
 */
uint16_t buck_npu_phase_estimate(const float raw[64][9], float low, float high,
    uint16_t kind, uint32_t confirm_tick, uint32_t *edge_tick, float *confidence);

extern uint16_t buck_npu_phase_last_status;
extern float buck_npu_phase_uncertainty_ticks;

#ifdef __cplusplus
}
#endif
#endif
