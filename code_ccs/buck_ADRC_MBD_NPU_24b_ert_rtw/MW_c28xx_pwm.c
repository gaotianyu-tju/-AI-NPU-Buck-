#include "c2000BoardSupport.h"
#include "MW_f28p55x_includes.h"
#include "rtwtypes.h"
#include "buck_ADRC_MBD_NPU_24b.h"
#include "buck_ADRC_MBD_NPU_24b_private.h"

void config_ePWM_GPIO (void)
{
  EALLOW;

  /*-- Configure pin assignments for ePWM1 --*/
  GpioCtrlRegs.GPAGMUX1.bit.GPIO0 = 0U;
  GpioCtrlRegs.GPAMUX1.bit.GPIO0 = 1U; /* Configure GPIO0 as EPWM1A*/
  GpioCtrlRegs.GPAGMUX1.bit.GPIO1 = 0U;
  GpioCtrlRegs.GPAMUX1.bit.GPIO1 = 1U; /* Configure GPIO1 as EPWM1B*/

  /*-- Configure pin assignments for ePWM10 --*/
  GpioCtrlRegs.GPBGMUX2.bit.GPIO62 = 0U;
  GpioCtrlRegs.GPBMUX2.bit.GPIO62 = 1U;/* Configure GPIO62 as EPWM10A*/
  GpioCtrlRegs.GPBGMUX2.bit.GPIO63 = 0U;
  GpioCtrlRegs.GPBMUX2.bit.GPIO63 = 1U;/* Configure GPIO63 as EPWM10B*/

  /*-- Configure pin assignments for ePWM2 --*/
  GpioCtrlRegs.GPAGMUX1.bit.GPIO2 = 0U;
  GpioCtrlRegs.GPAMUX1.bit.GPIO2 = 1U; /* Configure GPIO2 as EPWM2A*/
  GpioCtrlRegs.GPAGMUX1.bit.GPIO3 = 0U;
  GpioCtrlRegs.GPAMUX1.bit.GPIO3 = 1U; /* Configure GPIO3 as EPWM2B*/

  /*-- Configure pin assignments for ePWM7 --*/
  GpioCtrlRegs.GPAGMUX1.bit.GPIO12 = 0U;
  GpioCtrlRegs.GPAMUX1.bit.GPIO12 = 1U;/* Configure GPIO12 as EPWM7A*/
  GpioCtrlRegs.GPAGMUX1.bit.GPIO13 = 0U;
  GpioCtrlRegs.GPAMUX1.bit.GPIO13 = 1U;/* Configure GPIO13 as EPWM7B*/
  EDIS;
}

void config_ePWM_TBSync (void)
{
  /* Enable TBCLK within the EPWM*/
  EALLOW;

  //Reassigning TBPRD register of linked ePWM1
  {
    volatile uint32_T tempRead = EPwm1Regs.TBPRD;
    EPwm1Regs.TBPRD = tempRead;
  }

  /* Enable TBCLK after the ePWM configurations */
  CpuSysRegs.PCLKCR0.bit.TBCLKSYNC = 1U;
  EDIS;
}

void config_ePWMSyncSource (void)
{
  /* Configuring ePWM Sync in source selection */
  EPwm1Regs.EPWMSYNCINSEL.bit.SEL = 0U;
  EPwm10Regs.EPWMSYNCINSEL.bit.SEL = 1U;
  EPwm2Regs.EPWMSYNCINSEL.bit.SEL = 1U;
  EPwm7Regs.EPWMSYNCINSEL.bit.SEL = 1U;
}
