#include "c2000BoardSupport.h"
#include "MW_f28p55x_includes.h"
#include "rtwtypes.h"
#include "buck_ADRC_MBD_NPU_24b.h"
#include "buck_ADRC_MBD_NPU_24b_private.h"

void init_board (void)
{
  DisableDog();
  EALLOW;
  CpuSysRegs.PCLKCR0.bit.DMA = 1U;
  CpuSysRegs.PCLKCR17.bit.CLB1 = 1U;
  CpuSysRegs.PCLKCR17.bit.CLB2 = 1U;
  EDIS;

#ifdef CPU1

  InitSysPll(INT_OSC2, 60, 0, 1, 1, SYSCTL_DCC_BASE0);

  //Turn on all peripherals
  //InitPeripheralClocks();
  EALLOW;
  CpuSysRegs.PCLKCR0.bit.CPUTIMER0 = 1U;
  CpuSysRegs.PCLKCR0.bit.CPUTIMER1 = 1U;
  CpuSysRegs.PCLKCR0.bit.CPUTIMER2 = 1U;

  //All the new processors starting from F28001x
  CpuSysRegs.PCLKCR0.bit.HRCAL = 1U;
  CpuSysRegs.PCLKCR0.bit.ERAD = 1U;
  EDIS;

#endif                                 // #ifdef CPU1

  EALLOW;

  /* Configure low speed peripheral clocks */
  ClkCfgRegs.LOSPCP.bit.LSPCLKDIV = 0U;
  EDIS;

  /* Disable and clear all CPU interrupts */
  DINT;
  IER = 0x0000U;
  IFR = 0x0000U;
  InitPieCtrl();
  InitPieVectTable();
  InitCpuTimers();

#ifdef CPU1
#endif                                 // #ifdef CPU1

  /* initial ePWM GPIO assignment... */
  config_ePWM_GPIO();
  EALLOW;

  /* Enable clock to ePWM */
  CpuSysRegs.PCLKCR2.bit.EPWM1 = 1U;
  CpuSysRegs.PCLKCR2.bit.EPWM10 = 1U;
  CpuSysRegs.PCLKCR2.bit.EPWM2 = 1U;
  CpuSysRegs.PCLKCR2.bit.EPWM7 = 1U;

  /* Disable TBCLK within ePWM before module configuration */
  CpuSysRegs.PCLKCR0.bit.TBCLKSYNC = 0U;
  EDIS;
  config_ePWMSyncSource();
  if (MW_adcAInitFlag == 0U) {
    InitAdcA();
    MW_adcAInitFlag = 1U;
  }

  config_ADCA_SOC0 ();
  if (MW_adcCInitFlag == 0U) {
    InitAdcC();
    MW_adcCInitFlag = 1U;
  }

  config_ADCC_SOC1 ();
  if (MW_adcBInitFlag == 0U) {
    InitAdcB();
    MW_adcBInitFlag = 1U;
  }

  config_ADCB_SOC0 ();
  config_ADCB_SOC1 ();
  config_ADCC_SOC0 ();
  config_ADCA_SOC1 ();
  MW_SetVREF();

  /* initial GPIO qualification settings.... */
  EALLOW;
  GpioCtrlRegs.GPAQSEL1.all = 0x0U;
  GpioCtrlRegs.GPAQSEL2.all = 0x0U;
  GpioCtrlRegs.GPBQSEL1.all = 0x0U;
  GpioCtrlRegs.GPBQSEL2.all = 0x0U;
  GpioCtrlRegs.GPCQSEL1.all = 0x0U;
  GpioCtrlRegs.GPCQSEL2.all = 0x0U;
  GpioCtrlRegs.GPGQSEL2.all = 0x0U;
  GpioCtrlRegs.GPHQSEL1.all = 0x0U;
  GpioCtrlRegs.GPHQSEL2.all = 0x0U;
  GpioCtrlRegs.GPAAMSEL.all = 0U;
  GpioCtrlRegs.GPBAMSEL.all = 0U;
  GpioCtrlRegs.GPGAMSEL.all = 0U;
  GpioCtrlRegs.GPHAMSEL.all = 0U;
  /* Restore ADC analog inputs (v15 MBD build hook) */
  GpioCtrlRegs.GPHAMSEL.bit.GPIO225 = 1U; /* A4 */
  GpioCtrlRegs.GPHAMSEL.bit.GPIO249 = 1U; /* A5 */
  GpioCtrlRegs.GPHAMSEL.bit.GPIO253 = 1U; /* C11 */
  GpioCtrlRegs.GPHAMSEL.bit.GPIO230 = 1U; /* C10 */
  GpioCtrlRegs.GPHAMSEL.bit.GPIO226 = 1U; /* B2 */
  GpioCtrlRegs.GPHAMSEL.bit.GPIO237 = 1U; /* B10 */
  EDIS;
}

void initBoardEnd(void)
{
  config_ePWM_TBSync();
}
