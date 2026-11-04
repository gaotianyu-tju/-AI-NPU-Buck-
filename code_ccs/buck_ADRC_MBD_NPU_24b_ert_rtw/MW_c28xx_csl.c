#include "c2000BoardSupport.h"
#include "MW_f28p55x_includes.h"
#include "rtwtypes.h"
#include "buck_ADRC_MBD_NPU_24b.h"
#include "buck_ADRC_MBD_NPU_24b_private.h"

void enableExtInterrupt (void);
void configureGPIOExtInterrupt(void);

#include <stdint.h>

void disableWatchdog(void)
{
  int *WatchdogWDCR = (int *)(uintptr_t)0x7029;
  asm(" EALLOW ");
  *WatchdogWDCR = 0x0068;
  asm(" EDIS ");
}

interrupt void ADCA4_INT_isr(void)
{
  isr_int10pie4_task_fcn();
  EALLOW;
  AdcaRegs.ADCINTFLGCLR.bit.ADCINT4 = 1;
  EDIS;
  PieCtrlRegs.PIEACK.all = PIEACK_GROUP10;
                                     /* Acknowledge to receive more interrupts*/
}

void enable_interrupts()
{
  EALLOW;
  PieVectTable.ADCA4_INT = &ADCA4_INT_isr;/* Hook interrupt to the ISR*/
  EDIS;
  PieCtrlRegs.PIEIER10.bit.INTx4 = 1;  /* Enable interrupt ADCA4_INT*/
  IER |= M_INT10;

  /* Enable global Interrupts and higher priority real-time debug events:*/
  EINT;                                /* Enable Global interrupt INTM*/
  ERTM;                               /* Enable Global realtime interrupt DBGM*/
}
