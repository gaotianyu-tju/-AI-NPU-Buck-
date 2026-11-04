#ifndef BUCK_NPU_TIMING_H
#define BUCK_NPU_TIMING_H
/* v16: load repetition frequency, NOT the PWM/ADC or H15 sample frequency.
 * At 30 kHz, 20..200 Hz corresponds to 1500..150 control ticks.
 * A 12-tick raw interval guard accommodates endpoint timestamp jitter at
 * 20/200 Hz. It is not a claim of training/validation outside 20..200 Hz.
 * Keep observer, scheduler and compensation acceptance limits together. */
#define BUCK_NPU_LOAD_PERIOD_MIN_TICKS 150U
#define BUCK_NPU_LOAD_PERIOD_MAX_TICKS 1500U
#define BUCK_NPU_PERIOD_JITTER_TICKS 12U
#define BUCK_NPU_PERIOD_MIN_TICKS (BUCK_NPU_LOAD_PERIOD_MIN_TICKS-BUCK_NPU_PERIOD_JITTER_TICKS)
#define BUCK_NPU_PERIOD_MAX_TICKS (BUCK_NPU_LOAD_PERIOD_MAX_TICKS+BUCK_NPU_PERIOD_JITTER_TICKS)
#define BUCK_NPU_PERIOD_AGREEMENT_TICKS 6U
/* Cover a complete longest cycle plus filtering/settling samples during
 * acquisition. Once locked, a block follows the learned period instead.
 * Freeze block length at block start; never truncate a block mid-update. */
#define BUCK_NPU_LEVEL_MARGIN_TICKS 56U
#define BUCK_NPU_LEVEL_ACQUIRE_TICKS (BUCK_NPU_PERIOD_MAX_TICKS+BUCK_NPU_LEVEL_MARGIN_TICKS)
#endif
