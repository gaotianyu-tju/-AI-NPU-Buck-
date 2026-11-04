/* Generated for this model/scaler pair. raw[t][c]: oldest to newest. */
#ifndef NDP_MODEL_IO_H_
#define NDP_MODEL_IO_H_
#define NDP_HISTORY 8
#define NDP_HORIZON_STEPS 15U
#define NDP_SAMPLE_INTERVAL_S 3.33333333e-05f
#define NDP_SAMPLE_FREQUENCY_HZ 30000.0f
#define NDP_B0_PER_PHASE 20000.0f
#define NDP_CHANNELS 9
#define NDP_PACKED_FLOATS (12 * NDP_HISTORY)
#define NDP_OUTPUT_FLOATS 4
#define NDP_EFFECTIVE_OUTPUT_CHANNEL 0
#ifdef __cplusplus
extern "C" {
#endif
int ndp_prepare_window(const float raw[NDP_HISTORY][NDP_CHANNELS], float normalized[NDP_PACKED_FLOATS]);
int ndp_restore_residual(float normalized, float *residual_V_per_s);
#ifdef __cplusplus
}
#endif
#endif
