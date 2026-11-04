/*
 * F28P55 NPU 时钟、GS 共享 RAM 权限和诊断计时初始化。
 * 由 MBD 初始化路径调用一次；禁止在此重复初始化整个设备/中断控制器。
 * 本文件为最终 v16 交付源码；本轮仅增加说明，不修改执行语句或参数。
 */
/* Platform initialization for the delivered NNC 2.1.2 model.
 * Called once by model initialize, AFTER init_board(), BEFORE ADC IRQ enable.
 * Do not call Device_init/Interrupt_initModule here: MBD owns those resources.
 */
#include "driverlib.h"
#include "buck_npu.h"
#include "buck_npu_platform.h"
extern void NPU_setInterruptHandler(void (*handler)(void));
extern void NPU_enableInterrupt(void);
extern void NPU_clearInterruptACK(void);
extern __interrupt void tvmgen_default_IRQHandler(void);

/* CPU Timer2 is unused after init_board() in this CCS image (Timer0 is the
 * MBD scheduler, Timer1 belongs to profiling/XCP). Reserve Timer2 for timing.
 * 150 MHz SYSCLK / 30 kHz control => nominal 5000 counter clocks per sample.
 * This measures arrival at buck_npu_begin, not the complete ISR width.
 */
volatile uint16_t buck_ctrl_timing_reset=1U;
volatile uint32_t buck_ctrl_interval_last_cycles, buck_ctrl_interval_min_cycles;
volatile uint32_t buck_ctrl_interval_max_cycles, buck_ctrl_late_intervals;
volatile uint32_t buck_ctrl_adc_overflows, buck_ctrl_timing_samples;
static uint32_t previous_control_count;
static uint16_t have_control_count;

#pragma FUNCTION_OPTIONS(buck_npu_control_timing_sample, "--opt_level=2")
/* Timer2 为 150 MHz 向下计数器，记录相邻 begin 调用的间隔。
 * 5000 个计数对应 33.33 us；此值不是 GPIO 高电平宽度，也不是 NPU 推理耗时。
 * late_intervals 的现有阈值为 7500（50 us），不能用其为零证明所有 33.33 us 截止均满足。 */
void buck_npu_control_timing_sample(void)
{
    uint32_t count=CPUTimer_getTimerCount(CPUTIMER2_BASE);
    uint32_t elapsed;
    if(buck_ctrl_timing_reset) {
        buck_ctrl_interval_last_cycles=0UL;
        buck_ctrl_interval_min_cycles=0xffffffffUL;
        buck_ctrl_interval_max_cycles=0UL;
        buck_ctrl_late_intervals=buck_ctrl_adc_overflows=0UL;
        buck_ctrl_timing_samples=0UL;
        previous_control_count=count;
        have_control_count=1U;
        /* Begin a new observation window. Discard an overflow accumulated
         * before this reset, e.g. while CCS had the CPU halted. */
        HWREGH(ADCA_BASE+ADC_O_INTOVFCLR)=0x0008U;
        buck_ctrl_timing_reset=0U;
        return;
    }
    if(have_control_count) {
        elapsed=previous_control_count-count; /* down counter, wrap-safe */
        buck_ctrl_interval_last_cycles=elapsed;
        if(elapsed<buck_ctrl_interval_min_cycles) buck_ctrl_interval_min_cycles=elapsed;
        if(elapsed>buck_ctrl_interval_max_cycles) buck_ctrl_interval_max_cycles=elapsed;
        if(elapsed>7500UL) ++buck_ctrl_late_intervals;
        ++buck_ctrl_timing_samples;
    }
    previous_control_count=count;
    have_control_count=1U;
    /* Count ADCINT4 overflow events; normal interrupt flag/PIE acknowledge
     * remain owned by the generated ADCA4 ISR. Clear only the overflow bit. */
    if(HWREGH(ADCA_BASE+ADC_O_INTOVF) & 0x0008U) {
        ++buck_ctrl_adc_overflows;
        HWREGH(ADCA_BASE+ADC_O_INTOVFCLR)=0x0008U;
    }
}

/* 保留原 MBD 的 Timer0/Timer1 用途；Timer2 仅计时、不发中断。
 * 仅解除 GS0/GS1 的 NPU 写保护，保留其他访问策略；恢复进入时的全局中断状态。 */
void buck_npu_platform_init(void)
{
    bool wasDisabled = Interrupt_disableGlobal();
    CPUTimer_stopTimer(CPUTIMER2_BASE);
    CPUTimer_disableInterrupt(CPUTIMER2_BASE);
    CPUTimer_selectClockSource(CPUTIMER2_BASE, CPUTIMER_CLOCK_SOURCE_SYS,
                              CPUTIMER_CLOCK_PRESCALER_1);
    CPUTimer_setPreScaler(CPUTIMER2_BASE, 0U);
    CPUTimer_setPeriod(CPUTIMER2_BASE, 0xffffffffUL);
    CPUTimer_reloadTimerCounter(CPUTIMER2_BASE);
    /* Equivalent to driverlib STOPAFTERNEXTDECREMENT (SOFT=FREE=0),
     * without adding cputimer.c to the generated CCS source list. */
    HWREGH(CPUTIMER2_BASE+CPUTIMER_O_TCR) &=
        (uint16_t)~(CPUTIMER_TCR_SOFT | CPUTIMER_TCR_FREE);
    CPUTimer_startTimer(CPUTIMER2_BASE);
    SysCtl_setNPUClockDivider(SYSCTL_NPUCLK_DIV_1);
    SysCtl_enablePeripheral(SYSCTL_PERIPH_CLK_NPU);
    SYSCTL_REGWRITE_DELAY;
    /* GS0/GS1 are the verified RAMGS_DATA range used by the model linker.
     * Remove only NPU write protection, preserve CPU/DMA/fetch policy. */
    EALLOW;
    HWREG(MEMCFG_BASE + MEMCFG_O_GSXACCPROT0) &=
        ~(MEMCFG_GSXACCPROT0_NPU_WRPROT_GS0 | MEMCFG_GSXACCPROT0_NPU_WRPROT_GS1);
    EDIS;
    NPU_setInterruptHandler(&tvmgen_default_IRQHandler);
    NPU_clearInterruptACK();
    NPU_enableInterrupt();
    buck_npu_mark_ready();
    if (!wasDisabled) Interrupt_enableGlobal();
}
