/*
 * File: ert_main.c
 *
 * Code generated for Simulink model 'buck_ADRC_MBD_NPU_24b'.
 *
 * Model version                  : 3.14
 * Simulink Coder version         : 25.2 (R2025b) 28-Jul-2025
 * C/C++ source code generated on : Tue Nov  3 01:58:41 2026
 *
 * Target selection: ert.tlc
 * Embedded hardware selection: Texas Instruments->C2000
 * Code generation objectives: Unspecified
 * Validation result: Not run
 */

#include "buck_ADRC_MBD_NPU_24b.h"
#include "rtwtypes.h"
#include "buck_npu.h"
#include "MW_target_hardware_resources.h"

volatile int IsrOverrun = 0;
static boolean_T OverrunFlag = 0;
void rt_OneStep(void)
{
}

volatile boolean_T stopRequested;
volatile boolean_T runModel;
int main(void)
{
  float modelBaseRate = 0.2;
  float systemClock = 150;

  /* Initialize variables */
  stopRequested = false;
  runModel = false;
  c2000_flash_init();
  init_board();

#if defined(MW_EXEC_PROFILER_ON) || (defined(MW_EXTMODE_RUNNING) && !defined(XCP_TIMESTAMP_BASED_ON_SIMULATION_TIME))

  hardwareTimer1Init();

#endif

  ;
  rtmSetErrorStatus(buck_ADRC_MBD_NPU_24b_M, 0);
  buck_ADRC_MBD_NPU_24b_initialize();
  globalInterruptDisable();
  configureTimer0(modelBaseRate, systemClock);
  runModel =
    rtmGetErrorStatus(buck_ADRC_MBD_NPU_24b_M) == (NULL);
  enableTimer0Interrupt();
  enable_interrupts();
  initBoardEnd();
  globalInterruptEnable();
  while (runModel) {
    buck_npu_service();
    stopRequested = !(
                      rtmGetErrorStatus(buck_ADRC_MBD_NPU_24b_M) == (NULL));
  }

  /* Terminate model */
  buck_ADRC_MBD_NPU_24b_terminate();
  globalInterruptDisable();
  return 0;
}

/*
 * File trailer for generated code.
 *
 * [EOF]
 */
