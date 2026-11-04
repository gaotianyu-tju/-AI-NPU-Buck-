#ifndef BUCK_NPU_PLATFORM_H
#define BUCK_NPU_PLATFORM_H
#include <stdint.h>
void buck_npu_platform_init(void);
/* Main loop only. Never call this from the ADC/control ISR. */
void buck_npu_deferred_service(void);
void buck_npu_control_timing_sample(void);
extern volatile uint16_t buck_ctrl_timing_reset;
extern volatile uint32_t buck_ctrl_interval_last_cycles, buck_ctrl_interval_min_cycles;
extern volatile uint32_t buck_ctrl_interval_max_cycles, buck_ctrl_late_intervals;
extern volatile uint32_t buck_ctrl_adc_overflows, buck_ctrl_timing_samples;
extern volatile uint16_t buck_npu_irq_pending;
extern volatile uint32_t buck_npu_irq_count, buck_npu_irq_serviced;
extern volatile uint32_t buck_npu_irq_overrun, buck_npu_irq_context_errors;
extern volatile uint32_t buck_npu_irq_binding_errors;
extern volatile uint32_t buck_npu_irq_unexpected;
#endif
