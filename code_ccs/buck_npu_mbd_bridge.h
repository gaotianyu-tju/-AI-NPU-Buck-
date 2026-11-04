#ifndef BUCK_NPU_MBD_BRIDGE_H
#define BUCK_NPU_MBD_BRIDGE_H
#include "buck_npu_compensation.h"
/* Diagnostics only. Macros preserve the original v15 inline stores and
 * saturated baseline comparison, with no extra function call in the ISR.
 * The compensation/observer/network implementation remains unchanged. */
#define buck_npu_mbd_record_reset() do { \
    buck_npu_comp_baseline_iref_a=0.0F; \
    buck_npu_comp_final_iref_a=0.0F; \
    buck_npu_comp_applied_delta_i_a=0.0F; \
} while (0)
#define buck_npu_mbd_record_baseline(raw) \
    ((void)(buck_npu_comp_baseline_iref_a=(raw)))
#define buck_npu_mbd_record_final(cmd) do { \
    float buck_mbd_base; \
    buck_npu_comp_final_iref_a=(cmd); \
    buck_mbd_base=buck_npu_comp_baseline_iref_a; \
    if (!(buck_mbd_base>=-40.0F)) buck_mbd_base=-40.0F; \
    if (!(buck_mbd_base<=40.0F)) buck_mbd_base=40.0F; \
    buck_npu_comp_applied_delta_i_a=(cmd)-buck_mbd_base; \
} while (0)
#endif
