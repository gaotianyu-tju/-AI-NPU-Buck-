#include "c2000BoardSupport.h"
#include "MW_f28p55x_includes.h"
#include "rtwtypes.h"
#include "buck_ADRC_MBD_NPU_24b.h"
#include "buck_ADRC_MBD_NPU_24b_private.h"
#include "MW_c28xAnalogSubsystem.h"

void config_ADCA_SOC0(void)
{
  EALLOW;
  AdcaRegs.ADCSOC0CTL.bit.CHSEL = 5U;  /* Set SOC0 channel select to ADCIN5*/
  AdcaRegs.ADCSOC0CTL.bit.TRIGSEL = 17U;
  AdcaRegs.ADCSOC0CTL.bit.ACQPS = (uint16_T)55.0;
                               /* Set SOC0 S/H Window to 56.0 ADC Clock Cycles*/
  AdcaRegs.ADCINTSOCSEL1.bit.SOC0 = 0U;
                                   /* SOCx No ADCINT Interrupt Trigger Select.*/
  AdcaRegs.ADCOFFTRIM.bit.OFFTRIM = (uint16_T)AdcaRegs.ADCOFFTRIM.bit.OFFTRIM;/* Set Offset Error Correction Value*/
  AdcaRegs.ADCCTL1.bit.INTPULSEPOS = 1U;
             /* Interrupt pulse generation occurs at the end of the conversion*/
  AdcaRegs.ADCSOCPRICTL.bit.SOCPRIORITY = 0U;/* All in round robin mode SOC Priority*/
  EDIS;
}

void config_ADCC_SOC1(void)
{
  EALLOW;
  AdccRegs.ADCSOC1CTL.bit.CHSEL = 10U; /* Set SOC1 channel select to ADCIN10*/
  AdccRegs.ADCSOC1CTL.bit.TRIGSEL = 7U;
  AdccRegs.ADCSOC1CTL.bit.ACQPS = (uint16_T)55.0;
                               /* Set SOC1 S/H Window to 56.0 ADC Clock Cycles*/
  AdccRegs.ADCINTSOCSEL1.bit.SOC1 = 0U;
                                   /* SOCx No ADCINT Interrupt Trigger Select.*/
  AdccRegs.ADCOFFTRIM.bit.OFFTRIM = (uint16_T)AdccRegs.ADCOFFTRIM.bit.OFFTRIM;/* Set Offset Error Correction Value*/
  AdccRegs.ADCCTL1.bit.INTPULSEPOS = 1U;
             /* Interrupt pulse generation occurs at the end of the conversion*/
  AdccRegs.ADCSOCPRICTL.bit.SOCPRIORITY = 0U;/* All in round robin mode SOC Priority*/
  GpioCtrlRegs.GPHAMSEL.bit.GPIO230 = 1U;
  AnalogSubsysRegs.AGPIOCTRLH.bit.GPIO230 = 1U;
  EDIS;
}

void config_ADCB_SOC0(void)
{
  EALLOW;
  AdcbRegs.ADCSOC0CTL.bit.CHSEL = 2U;  /* Set SOC0 channel select to ADCIN2*/
  AdcbRegs.ADCSOC0CTL.bit.TRIGSEL = 5U;
  AdcbRegs.ADCSOC0CTL.bit.ACQPS = (uint16_T)55.0;
                               /* Set SOC0 S/H Window to 56.0 ADC Clock Cycles*/
  AdcbRegs.ADCINTSOCSEL1.bit.SOC0 = 0U;
                                   /* SOCx No ADCINT Interrupt Trigger Select.*/
  AdcbRegs.ADCOFFTRIM.bit.OFFTRIM = (uint16_T)AdcbRegs.ADCOFFTRIM.bit.OFFTRIM;/* Set Offset Error Correction Value*/
  AdcbRegs.ADCCTL1.bit.INTPULSEPOS = 1U;
             /* Interrupt pulse generation occurs at the end of the conversion*/
  AdcbRegs.ADCSOCPRICTL.bit.SOCPRIORITY = 0U;/* All in round robin mode SOC Priority*/
  GpioCtrlRegs.GPHAMSEL.bit.GPIO226 = 1U;
  AnalogSubsysRegs.AGPIOCTRLH.bit.GPIO226 = 1U;
  EDIS;
}

void config_ADCB_SOC1(void)
{
  EALLOW;
  AdcbRegs.ADCSOC1CTL.bit.CHSEL = 10U; /* Set SOC1 channel select to ADCIN10*/
  AdcbRegs.ADCSOC1CTL.bit.TRIGSEL = 5U;
  AdcbRegs.ADCSOC1CTL.bit.ACQPS = (uint16_T)55.0;
                               /* Set SOC1 S/H Window to 56.0 ADC Clock Cycles*/
  AdcbRegs.ADCINTSOCSEL1.bit.SOC1 = 0U;
                                   /* SOCx No ADCINT Interrupt Trigger Select.*/
  AdcbRegs.ADCOFFTRIM.bit.OFFTRIM = (uint16_T)AdcbRegs.ADCOFFTRIM.bit.OFFTRIM;/* Set Offset Error Correction Value*/
  AdcbRegs.ADCCTL1.bit.INTPULSEPOS = 1U;
             /* Interrupt pulse generation occurs at the end of the conversion*/
  AdcbRegs.ADCSOCPRICTL.bit.SOCPRIORITY = 0U;/* All in round robin mode SOC Priority*/
  EDIS;
}

void config_ADCC_SOC0(void)
{
  EALLOW;
  AdccRegs.ADCSOC0CTL.bit.CHSEL = 11U; /* Set SOC0 channel select to ADCIN11*/
  AdccRegs.ADCSOC0CTL.bit.TRIGSEL = 5U;
  AdccRegs.ADCSOC0CTL.bit.ACQPS = (uint16_T)55.0;
                               /* Set SOC0 S/H Window to 56.0 ADC Clock Cycles*/
  AdccRegs.ADCINTSOCSEL1.bit.SOC0 = 0U;
                                   /* SOCx No ADCINT Interrupt Trigger Select.*/
  AdccRegs.ADCOFFTRIM.bit.OFFTRIM = (uint16_T)AdccRegs.ADCOFFTRIM.bit.OFFTRIM;/* Set Offset Error Correction Value*/
  AdccRegs.ADCCTL1.bit.INTPULSEPOS = 1U;
             /* Interrupt pulse generation occurs at the end of the conversion*/
  AdccRegs.ADCSOCPRICTL.bit.SOCPRIORITY = 0U;/* All in round robin mode SOC Priority*/
  GpioCtrlRegs.GPHAMSEL.bit.GPIO253 = 1U;
  AnalogSubsysRegs.AGPIOCTRLH.bit.GPIO253 = 1U;
  EDIS;
}

void config_ADCA_SOC1(void)
{
  EALLOW;
  AdcaRegs.ADCSOC1CTL.bit.CHSEL = 4U;  /* Set SOC1 channel select to ADCIN4*/
  AdcaRegs.ADCSOC1CTL.bit.TRIGSEL = 23U;
  AdcaRegs.ADCSOC1CTL.bit.ACQPS = (uint16_T)55.0;
                               /* Set SOC1 S/H Window to 56.0 ADC Clock Cycles*/
  AdcaRegs.ADCINTSEL3N4.bit.INT4E = 1U;/* Enabled/Disable ADCINT4 interrupt*/
  AdcaRegs.ADCINTSEL3N4.bit.INT4SEL = 1U;/* Setup EOC1 to trigger ADCINT4*/
  AdcaRegs.ADCINTSEL3N4.bit.INT4CONT = 1U;
                                     /* Enable/Disable ADCINT4 Continuous mode*/
  AdcaRegs.ADCINTSOCSEL1.bit.SOC1 = 0U;
                                   /* SOCx No ADCINT Interrupt Trigger Select.*/
  AdcaRegs.ADCOFFTRIM.bit.OFFTRIM = (uint16_T)AdcaRegs.ADCOFFTRIM.bit.OFFTRIM;/* Set Offset Error Correction Value*/
  AdcaRegs.ADCCTL1.bit.INTPULSEPOS = 1U;
             /* Interrupt pulse generation occurs at the end of the conversion*/
  AdcaRegs.ADCSOCPRICTL.bit.SOCPRIORITY = 0U;/* All in round robin mode SOC Priority*/
  EDIS;
}

void InitAdcA(void)
{
  EALLOW;
  CpuSysRegs.PCLKCR13.bit.ADC_A = 1U;
  AdcaRegs.ADCCTL2.bit.PRESCALE = 8U;

  //power up the ADC
  AdcaRegs.ADCCTL1.bit.ADCPWDNZ = 1U;

  //delay for 1ms to allow ADC time to power up
  DELAY_US(1000);
  EDIS;
}

void InitAdcB(void)
{
  EALLOW;
  CpuSysRegs.PCLKCR13.bit.ADC_B = 1U;
  AdcbRegs.ADCCTL2.bit.PRESCALE = 8U;

  //power up the ADC
  AdcbRegs.ADCCTL1.bit.ADCPWDNZ = 1U;

  //delay for 1ms to allow ADC time to power up
  DELAY_US(1000);
  EDIS;
}

void InitAdcC(void)
{
  EALLOW;
  CpuSysRegs.PCLKCR13.bit.ADC_C = 1U;
  AdccRegs.ADCCTL2.bit.PRESCALE = 8U;

  //power up the ADC
  AdccRegs.ADCCTL1.bit.ADCPWDNZ = 1U;

  //delay for 1ms to allow ADC time to power up
  DELAY_US(1000);
  EDIS;
}
