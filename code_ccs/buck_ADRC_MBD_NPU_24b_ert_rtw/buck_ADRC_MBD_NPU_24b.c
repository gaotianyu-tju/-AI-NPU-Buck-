/*
 * File: buck_ADRC_MBD_NPU_24b.c
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
#include "buck_ADRC_MBD_NPU_24b_private.h"
#include "rtwtypes.h"
#include "rt_nonfinite.h"
#include <math.h>
#include <string.h>

/* Exported block signals */
mwReal32_T IL1;                        /* '<S1>/Divide' */
mwReal32_T IL2;                        /* '<S1>/Divide1' */
mwReal32_T IL3;                        /* '<S1>/Divide2' */
mwReal32_T IL4;                        /* '<S1>/Divide3' */
real32_T Vout;                         /* '<S1>/Gain13' */
real32_T Vin;                          /* '<S1>/Gain' */

/* Exported block states */
real32_T enable;                       /* '<S1>/Data Store Memory' */
real32_T wc;                           /* '<S1>/Data Store Memory1' */
real32_T wo;                           /* '<S1>/Data Store Memory2' */
real32_T b0;                           /* '<S1>/Data Store Memory3' */
real32_T alpha;                        /* '<S1>/Data Store Memory4' */

/* Block signals (default storage) */
B_buck_ADRC_MBD_NPU_24b_T buck_ADRC_MBD_NPU_24b_B;

/* Block states (default storage) */
DW_buck_ADRC_MBD_NPU_24b_T buck_ADRC_MBD_NPU_24b_DW;

/* Real-time model */
static RT_MODEL_buck_ADRC_MBD_NPU_24_T buck_ADRC_MBD_NPU_24b_M_;
RT_MODEL_buck_ADRC_MBD_NPU_24_T *const buck_ADRC_MBD_NPU_24b_M =
  &buck_ADRC_MBD_NPU_24b_M_;

#ifndef __TMS320C28XX_CLA__

uint16_T MW_adcAInitFlag = 0;

#endif

#ifndef __TMS320C28XX_CLA__

uint16_T MW_adcCInitFlag = 0;

#endif

#ifndef __TMS320C28XX_CLA__

uint16_T MW_adcBInitFlag = 0;

#endif

/* Hardware Interrupt Block: '<Root>/C28x Hardware Interrupt' */
void isr_int10pie4_task_fcn(void)
{
  if (1 == runModel) {
    /* Call the system: <Root>/Function-Call Subsystem */
    {
      /* S-Function (c28xisr_c2000): '<Root>/C28x Hardware Interrupt' */

      /* Output and update for function-call system: '<Root>/Function-Call Subsystem' */
      {
        mwReal32_T rtb_DeadZone;
        mwReal32_T rtb_DeadZone_b;
        mwReal32_T rtb_DeadZone_f;
        mwReal32_T rtb_DeadZone_p;
        mwReal32_T rtb_Gain2;
        mwReal32_T rtb_IntegralGain;
        mwReal32_T rtb_IntegralGain_hn;
        mwReal32_T rtb_IntegralGain_m;
        mwReal32_T rtb_IntegralGain_p;
        real32_T e;
        real32_T rtb_data;
        int16_T tmp;
        int16_T tmp_p;
        boolean_T reset;

        /* S-Function (c280xgpio_do): '<S1>/Digital Output' incorporates:
         *  Constant: '<Root>/Constant'
         */
        {
          if (1.0) {
            GpioDataRegs.GPASET.bit.GPIO22 = 1U;
          } else {
            GpioDataRegs.GPACLEAR.bit.GPIO22 = 1U;
          }
        }

        /* S-Function (c280xgpio_do): '<S1>/Digital Output2' incorporates:
         *  Constant: '<Root>/Constant1'
         */
        {
          if (0.0) {
            GpioDataRegs.GPBSET.bit.GPIO63 = 1U;
          } else {
            GpioDataRegs.GPBCLEAR.bit.GPIO63 = 1U;
          }
        }

        /* S-Function (c2802xadc): '<S1>/ADC5' */
        {
          /*  Internal Reference Voltage : Fixed scale 0 to 3.3 V range.  */
          /*  External Reference Voltage : Allowable ranges of VREFHI(ADCINA0) = 3.3 and VREFLO(tied to ground) = 0  */
          buck_ADRC_MBD_NPU_24b_B.ADC5 = (AdcbResultRegs.ADCRESULT1);
        }

        /* Gain: '<S1>/Gain13' incorporates:
         *  Gain: '<S1>/Gain1'
         *  Gain: '<S1>/Gain2'
         */
        Vout = 0.000805860793F * buck_ADRC_MBD_NPU_24b_B.ADC5 * 18.2F * 1.4883F;

        /* S-Function (c2802xadc): '<S1>/ADC6' */
        {
          /*  Internal Reference Voltage : Fixed scale 0 to 3.3 V range.  */
          /*  External Reference Voltage : Allowable ranges of VREFHI(ADCINA0) = 3.3 and VREFLO(tied to ground) = 0  */
          buck_ADRC_MBD_NPU_24b_B.ADC6 = (AdccResultRegs.ADCRESULT0);
        }

        /* Product: '<S1>/Divide' incorporates:
         *  Constant: '<S1>/Constant2'
         *  Constant: '<S1>/Constant7'
         *  Gain: '<S1>/Gain6'
         *  Sum: '<S1>/Sum2'
         */
        IL1 = (0.000805860793F * buck_ADRC_MBD_NPU_24b_B.ADC6 - 1.6475F) / 0.025;

        /* S-Function (c2802xadc): '<S1>/ADC3' */
        {
          /*  Internal Reference Voltage : Fixed scale 0 to 3.3 V range.  */
          /*  External Reference Voltage : Allowable ranges of VREFHI(ADCINA0) = 3.3 and VREFLO(tied to ground) = 0  */
          buck_ADRC_MBD_NPU_24b_B.ADC3 = (AdccResultRegs.ADCRESULT1);
        }

        /* Product: '<S1>/Divide1' incorporates:
         *  Constant: '<S1>/Constant6'
         *  Constant: '<S1>/Constant8'
         *  Gain: '<S1>/Gain11'
         *  Sum: '<S1>/Sum6'
         */
        IL2 = (0.000805860793F * buck_ADRC_MBD_NPU_24b_B.ADC3 - 1.6475F) /
          -0.025;

        /* S-Function (c2802xadc): '<S1>/ADC1' */
        {
          /*  Internal Reference Voltage : Fixed scale 0 to 3.3 V range.  */
          /*  External Reference Voltage : Allowable ranges of VREFHI(ADCINA0) = 3.3 and VREFLO(tied to ground) = 0  */
          buck_ADRC_MBD_NPU_24b_B.ADC1 = (AdcaResultRegs.ADCRESULT0);
        }

        /* Product: '<S1>/Divide2' incorporates:
         *  Constant: '<S1>/Constant3'
         *  Constant: '<S1>/Constant9'
         *  Gain: '<S1>/Gain8'
         *  Sum: '<S1>/Sum4'
         */
        IL3 = (0.000805860793F * buck_ADRC_MBD_NPU_24b_B.ADC1 - 1.6475F) / 0.025;

        /* S-Function (c2802xadc): '<S1>/ADC7' */
        {
          /*  Internal Reference Voltage : Fixed scale 0 to 3.3 V range.  */
          /*  External Reference Voltage : Allowable ranges of VREFHI(ADCINA0) = 3.3 and VREFLO(tied to ground) = 0  */
          buck_ADRC_MBD_NPU_24b_B.ADC7 = (AdcaResultRegs.ADCRESULT1);
        }

        /* Product: '<S1>/Divide3' incorporates:
         *  Constant: '<S1>/Constant10'
         *  Constant: '<S1>/Constant5'
         *  Gain: '<S1>/Gain10'
         *  Sum: '<S1>/Sum5'
         */
        IL4 = (0.000805860793F * buck_ADRC_MBD_NPU_24b_B.ADC7 - 1.6475F) /
          -0.025;

        /* S-Function (c2802xadc): '<S1>/ADC4' */
        {
          /*  Internal Reference Voltage : Fixed scale 0 to 3.3 V range.  */
          /*  External Reference Voltage : Allowable ranges of VREFHI(ADCINA0) = 3.3 and VREFLO(tied to ground) = 0  */
          buck_ADRC_MBD_NPU_24b_B.ADC4 = (AdcbResultRegs.ADCRESULT0);
        }

        /* Gain: '<S1>/Gain' incorporates:
         *  Gain: '<S1>/Gain4'
         *  Gain: '<S1>/Gain5'
         */
        Vin = 0.000805860793F * buck_ADRC_MBD_NPU_24b_B.ADC4 * 18.2F * 1.47929F;

        /* MATLAB Function: '<S2>/NPU' incorporates:
         *  Constant: '<S2>/Constant3'
         *  DataStoreRead: '<S2>/Data Store Read2'
         */
        rtb_data = buck_npu_begin(Vout, (real32_T)IL1, (real32_T)IL2, (real32_T)
          IL3, (real32_T)IL4, 12.0F, Vin, (uint16_T)(enable != 0.0F));

        /* MATLAB Function: '<S2>/MATLAB Function' incorporates:
         *  Constant: '<S2>/Constant1'
         *  Constant: '<S2>/Constant2'
         *  DataStoreRead: '<S2>/Data Store Read1'
         *  DataStoreRead: '<S2>/Data Store Read2'
         *  DataStoreRead: '<S2>/Data Store Read3'
         *  DataStoreRead: '<S2>/Data Store Read4'
         *  DataStoreRead: '<S2>/Data Store Read5'
         */
        if (!buck_ADRC_MBD_NPU_24b_DW.z1_not_empty) {
          buck_ADRC_MBD_NPU_24b_DW.z1 = Vout;
          buck_ADRC_MBD_NPU_24b_DW.z1_not_empty = true;
        }

        reset = (rtIsInfF(b0) || rtIsNaNF(b0) || ((fabsf(b0) < 1.0E-6F) ||
                  (enable != 0.0F)));
        if (reset) {
          buck_ADRC_MBD_NPU_24b_DW.z1 = Vout;
          buck_ADRC_MBD_NPU_24b_DW.z2 = 0.0F;
          buck_ADRC_MBD_NPU_24b_DW.u_prev = 0.0F;
          rtb_data = 0.0F;
          buck_npu_mbd_record_reset();
        } else {
          e = Vout - buck_ADRC_MBD_NPU_24b_DW.z1;
          buck_ADRC_MBD_NPU_24b_DW.z1 += ((b0 * buck_ADRC_MBD_NPU_24b_DW.u_prev
            + buck_ADRC_MBD_NPU_24b_DW.z2) + 2.0F * wo * e) * 3.33333337E-5F;
          buck_ADRC_MBD_NPU_24b_DW.z2 += wo * wo * e * 3.33333337E-5F;
          if (rtIsInfF(alpha) || rtIsNaNF(alpha)) {
            e = 0.0F;
          } else {
            if (alpha >= 0.0F) {
              e = alpha;
            } else {
              e = 0.0F;
            }

            if (!(e <= 1.0F)) {
              e = 1.0F;
            }
          }

          rtb_data = buck_npu_apply_prediction(rtb_data,
            buck_ADRC_MBD_NPU_24b_DW.z2, e, b0, wc, wo);
          e = ((12.0F - buck_ADRC_MBD_NPU_24b_DW.z1) * wc -
               buck_ADRC_MBD_NPU_24b_DW.z2) / b0;
          buck_npu_mbd_record_baseline(e);
          rtb_data += e;
          if (!(rtb_data >= -40.0F)) {
            rtb_data = -40.0F;
          }

          if (!(rtb_data <= 40.0F)) {
            rtb_data = 40.0F;
          }

          buck_npu_mbd_record_final(rtb_data);
          buck_ADRC_MBD_NPU_24b_DW.u_prev = rtb_data;
        }

        buck_npu_commit(rtb_data, buck_ADRC_MBD_NPU_24b_DW.z2, 30000.0F, b0,
                        (uint16_T)reset);

        /* Sum: '<S2>/Sum3' incorporates:
         *  MATLAB Function: '<S2>/MATLAB Function'
         */
        rtb_IntegralGain = rtb_data - IL1;

        /* DiscreteIntegrator: '<S45>/Integrator' incorporates:
         *  DataStoreRead: '<S2>/Data Store Read2'
         */
        if (((enable > 0.0F) &&
             (buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState <= 0)) ||
            ((enable <= 0.0F) &&
             (buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState == 1))) {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_DSTATE = 0.05;
        }

        /* Sum: '<S54>/Sum' incorporates:
         *  DiscreteIntegrator: '<S45>/Integrator'
         *  Gain: '<S50>/Proportional Gain'
         */
        rtb_DeadZone = 0.1 * rtb_IntegralGain +
          buck_ADRC_MBD_NPU_24b_DW.Integrator_DSTATE;

        /* Saturate: '<S52>/Saturation' */
        if (rtb_DeadZone > 0.95) {
          rtb_Gain2 = 0.95;
        } else if (rtb_DeadZone < 0.05) {
          rtb_Gain2 = 0.05;
        } else {
          rtb_Gain2 = rtb_DeadZone;
        }

        /* Gain: '<S2>/Gain' incorporates:
         *  Saturate: '<S52>/Saturation'
         */
        rtb_IntegralGain_p = 100.0 * rtb_Gain2;

        /* S-Function (c2802xpwm): '<S1>/ePWM1' incorporates:
         *  DataStoreRead: '<S1>/Data Store Read1'
         */
        uint16_T tbprdValue1Outputs = EPwm1Regs.TBPRD;

        /*-- Update CMPA value for ePWM1 --*/
        {
          EPwm1Regs.CMPA.bit.CMPA = (uint16_T)((uint32_T)EPwm1Regs.TBPRD *
            rtb_IntegralGain_p * 0.01);
        }

        EPwm1Regs.AQCSFRC.bit.CSFA = (uint16_T)enable;
        EPwm1Regs.AQCSFRC.bit.CSFB = (uint16_T)enable;

        /* Sum: '<S2>/Sum12' incorporates:
         *  MATLAB Function: '<S2>/MATLAB Function'
         */
        rtb_IntegralGain_p = rtb_data - IL4;

        /* DiscreteIntegrator: '<S207>/Integrator' incorporates:
         *  DataStoreRead: '<S2>/Data Store Read2'
         */
        if (((enable > 0.0F) &&
             (buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_i <= 0)) ||
            ((enable <= 0.0F) &&
             (buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_i == 1))) {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_DSTATE_l = 0.05;
        }

        /* Sum: '<S216>/Sum' incorporates:
         *  DiscreteIntegrator: '<S207>/Integrator'
         *  Gain: '<S212>/Proportional Gain'
         */
        rtb_DeadZone_p = 0.1 * rtb_IntegralGain_p +
          buck_ADRC_MBD_NPU_24b_DW.Integrator_DSTATE_l;

        /* Saturate: '<S214>/Saturation' */
        if (rtb_DeadZone_p > 0.95) {
          rtb_Gain2 = 0.95;
        } else if (rtb_DeadZone_p < 0.05) {
          rtb_Gain2 = 0.05;
        } else {
          rtb_Gain2 = rtb_DeadZone_p;
        }

        /* Gain: '<S2>/Gain3' incorporates:
         *  Saturate: '<S214>/Saturation'
         */
        rtb_IntegralGain_hn = 100.0 * rtb_Gain2;

        /* S-Function (c2802xpwm): '<S1>/ePWM10' incorporates:
         *  DataStoreRead: '<S1>/Data Store Read1'
         */
        uint16_T tbprdValue10Outputs = EPwm10Regs.TBPRD;

        /*-- Update CMPA value for ePWM10 --*/
        {
          EPwm10Regs.CMPA.bit.CMPA = (uint16_T)((uint32_T)EPwm10Regs.TBPRD *
            rtb_IntegralGain_hn * 0.01);
        }

        EPwm10Regs.AQCSFRC.bit.CSFA = (uint16_T)enable;
        EPwm10Regs.AQCSFRC.bit.CSFB = (uint16_T)enable;

        /* Sum: '<S2>/Sum6' incorporates:
         *  MATLAB Function: '<S2>/MATLAB Function'
         */
        rtb_IntegralGain_hn = rtb_data - IL2;

        /* DiscreteIntegrator: '<S99>/Integrator' incorporates:
         *  DataStoreRead: '<S2>/Data Store Read2'
         */
        if (((enable > 0.0F) &&
             (buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_k <= 0)) ||
            ((enable <= 0.0F) &&
             (buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_k == 1))) {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_DSTATE_a = 0.05;
        }

        /* Sum: '<S108>/Sum' incorporates:
         *  DiscreteIntegrator: '<S99>/Integrator'
         *  Gain: '<S104>/Proportional Gain'
         */
        rtb_DeadZone_b = 0.1 * rtb_IntegralGain_hn +
          buck_ADRC_MBD_NPU_24b_DW.Integrator_DSTATE_a;

        /* Saturate: '<S106>/Saturation' */
        if (rtb_DeadZone_b > 0.95) {
          rtb_Gain2 = 0.95;
        } else if (rtb_DeadZone_b < 0.05) {
          rtb_Gain2 = 0.05;
        } else {
          rtb_Gain2 = rtb_DeadZone_b;
        }

        /* Gain: '<S2>/Gain1' incorporates:
         *  Saturate: '<S106>/Saturation'
         */
        rtb_IntegralGain_m = 100.0 * rtb_Gain2;

        /* S-Function (c2802xpwm): '<S1>/ePWM2' incorporates:
         *  DataStoreRead: '<S1>/Data Store Read1'
         */
        uint16_T tbprdValue2Outputs = EPwm2Regs.TBPRD;

        /*-- Update CMPA value for ePWM2 --*/
        {
          EPwm2Regs.CMPA.bit.CMPA = (uint16_T)((uint32_T)EPwm2Regs.TBPRD *
            rtb_IntegralGain_m * 0.01);
        }

        EPwm2Regs.AQCSFRC.bit.CSFA = (uint16_T)enable;
        EPwm2Regs.AQCSFRC.bit.CSFB = (uint16_T)enable;

        /* Sum: '<S2>/Sum9' incorporates:
         *  MATLAB Function: '<S2>/MATLAB Function'
         */
        rtb_IntegralGain_m = rtb_data - IL3;

        /* DiscreteIntegrator: '<S153>/Integrator' incorporates:
         *  DataStoreRead: '<S2>/Data Store Read2'
         */
        if (((enable > 0.0F) &&
             (buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_c <= 0)) ||
            ((enable <= 0.0F) &&
             (buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_c == 1))) {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_DSTATE_p = 0.05;
        }

        /* Sum: '<S162>/Sum' incorporates:
         *  DiscreteIntegrator: '<S153>/Integrator'
         *  Gain: '<S158>/Proportional Gain'
         */
        rtb_DeadZone_f = 0.1 * rtb_IntegralGain_m +
          buck_ADRC_MBD_NPU_24b_DW.Integrator_DSTATE_p;

        /* Saturate: '<S160>/Saturation' */
        if (rtb_DeadZone_f > 0.95) {
          rtb_Gain2 = 0.95;
        } else if (rtb_DeadZone_f < 0.05) {
          rtb_Gain2 = 0.05;
        } else {
          rtb_Gain2 = rtb_DeadZone_f;
        }

        /* Gain: '<S2>/Gain2' incorporates:
         *  Saturate: '<S160>/Saturation'
         */
        rtb_Gain2 *= 100.0;

        /* S-Function (c2802xpwm): '<S1>/ePWM7' incorporates:
         *  DataStoreRead: '<S1>/Data Store Read1'
         */
        uint16_T tbprdValue7Outputs = EPwm7Regs.TBPRD;

        /*-- Update CMPA value for ePWM7 --*/
        {
          EPwm7Regs.CMPA.bit.CMPA = (uint16_T)((uint32_T)EPwm7Regs.TBPRD *
            rtb_Gain2 * 0.01);
        }

        EPwm7Regs.AQCSFRC.bit.CSFA = (uint16_T)enable;
        EPwm7Regs.AQCSFRC.bit.CSFB = (uint16_T)enable;

        /* DeadZone: '<S37>/DeadZone' */
        if (rtb_DeadZone > 0.95) {
          rtb_DeadZone -= 0.95;
        } else if (rtb_DeadZone >= 0.05) {
          rtb_DeadZone = 0.0;
        } else {
          rtb_DeadZone -= 0.05;
        }

        /* End of DeadZone: '<S37>/DeadZone' */

        /* Gain: '<S42>/Integral Gain' */
        rtb_IntegralGain *= 0.00025;

        /* DeadZone: '<S91>/DeadZone' */
        if (rtb_DeadZone_b > 0.95) {
          rtb_DeadZone_b -= 0.95;
        } else if (rtb_DeadZone_b >= 0.05) {
          rtb_DeadZone_b = 0.0;
        } else {
          rtb_DeadZone_b -= 0.05;
        }

        /* End of DeadZone: '<S91>/DeadZone' */

        /* Gain: '<S96>/Integral Gain' */
        rtb_IntegralGain_hn *= 0.00025;

        /* DeadZone: '<S145>/DeadZone' */
        if (rtb_DeadZone_f > 0.95) {
          rtb_DeadZone_f -= 0.95;
        } else if (rtb_DeadZone_f >= 0.05) {
          rtb_DeadZone_f = 0.0;
        } else {
          rtb_DeadZone_f -= 0.05;
        }

        /* End of DeadZone: '<S145>/DeadZone' */

        /* Gain: '<S150>/Integral Gain' */
        rtb_IntegralGain_m *= 0.00025;

        /* DeadZone: '<S199>/DeadZone' */
        if (rtb_DeadZone_p > 0.95) {
          rtb_DeadZone_p -= 0.95;
        } else if (rtb_DeadZone_p >= 0.05) {
          rtb_DeadZone_p = 0.0;
        } else {
          rtb_DeadZone_p -= 0.05;
        }

        /* End of DeadZone: '<S199>/DeadZone' */

        /* Gain: '<S204>/Integral Gain' */
        rtb_IntegralGain_p *= 0.00025;

        /* Switch: '<S35>/Switch1' incorporates:
         *  Constant: '<S35>/Clamping_zero'
         *  Constant: '<S35>/Constant'
         *  Constant: '<S35>/Constant2'
         *  RelationalOperator: '<S35>/fix for DT propagation issue'
         */
        if (rtb_DeadZone > 0.0) {
          tmp = 1;
        } else {
          tmp = -1;
        }

        /* Switch: '<S35>/Switch2' incorporates:
         *  Constant: '<S35>/Clamping_zero'
         *  Constant: '<S35>/Constant3'
         *  Constant: '<S35>/Constant4'
         *  RelationalOperator: '<S35>/fix for DT propagation issue1'
         */
        if (rtb_IntegralGain > 0.0) {
          tmp_p = 1;
        } else {
          tmp_p = -1;
        }

        /* Switch: '<S35>/Switch' incorporates:
         *  Constant: '<S35>/Clamping_zero'
         *  Constant: '<S35>/Constant1'
         *  Logic: '<S35>/AND3'
         *  RelationalOperator: '<S35>/Equal1'
         *  RelationalOperator: '<S35>/Relational Operator'
         *  Switch: '<S35>/Switch1'
         *  Switch: '<S35>/Switch2'
         */
        if ((rtb_DeadZone != 0.0) && (tmp == tmp_p)) {
          rtb_IntegralGain = 0.0;
        }

        /* Update for DiscreteIntegrator: '<S45>/Integrator' incorporates:
         *  DataStoreRead: '<S2>/Data Store Read2'
         *  Switch: '<S35>/Switch'
         */
        buck_ADRC_MBD_NPU_24b_DW.Integrator_DSTATE += rtb_IntegralGain;
        if (enable > 0.0F) {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState = 1;
        } else if (enable < 0.0F) {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState = -1;
        } else if (enable == 0.0F) {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState = 0;
        } else {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState = 2;
        }

        /* End of Update for DiscreteIntegrator: '<S45>/Integrator' */

        /* Switch: '<S197>/Switch1' incorporates:
         *  Constant: '<S197>/Clamping_zero'
         *  Constant: '<S197>/Constant'
         *  Constant: '<S197>/Constant2'
         *  RelationalOperator: '<S197>/fix for DT propagation issue'
         */
        if (rtb_DeadZone_p > 0.0) {
          tmp = 1;
        } else {
          tmp = -1;
        }

        /* Switch: '<S197>/Switch2' incorporates:
         *  Constant: '<S197>/Clamping_zero'
         *  Constant: '<S197>/Constant3'
         *  Constant: '<S197>/Constant4'
         *  RelationalOperator: '<S197>/fix for DT propagation issue1'
         */
        if (rtb_IntegralGain_p > 0.0) {
          tmp_p = 1;
        } else {
          tmp_p = -1;
        }

        /* Switch: '<S197>/Switch' incorporates:
         *  Constant: '<S197>/Clamping_zero'
         *  Constant: '<S197>/Constant1'
         *  Logic: '<S197>/AND3'
         *  RelationalOperator: '<S197>/Equal1'
         *  RelationalOperator: '<S197>/Relational Operator'
         *  Switch: '<S197>/Switch1'
         *  Switch: '<S197>/Switch2'
         */
        if ((rtb_DeadZone_p != 0.0) && (tmp == tmp_p)) {
          rtb_IntegralGain_p = 0.0;
        }

        /* Update for DiscreteIntegrator: '<S207>/Integrator' incorporates:
         *  DataStoreRead: '<S2>/Data Store Read2'
         *  Switch: '<S197>/Switch'
         */
        buck_ADRC_MBD_NPU_24b_DW.Integrator_DSTATE_l += rtb_IntegralGain_p;
        if (enable > 0.0F) {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_i = 1;
        } else if (enable < 0.0F) {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_i = -1;
        } else if (enable == 0.0F) {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_i = 0;
        } else {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_i = 2;
        }

        /* End of Update for DiscreteIntegrator: '<S207>/Integrator' */

        /* Switch: '<S89>/Switch1' incorporates:
         *  Constant: '<S89>/Clamping_zero'
         *  Constant: '<S89>/Constant'
         *  Constant: '<S89>/Constant2'
         *  RelationalOperator: '<S89>/fix for DT propagation issue'
         */
        if (rtb_DeadZone_b > 0.0) {
          tmp = 1;
        } else {
          tmp = -1;
        }

        /* Switch: '<S89>/Switch2' incorporates:
         *  Constant: '<S89>/Clamping_zero'
         *  Constant: '<S89>/Constant3'
         *  Constant: '<S89>/Constant4'
         *  RelationalOperator: '<S89>/fix for DT propagation issue1'
         */
        if (rtb_IntegralGain_hn > 0.0) {
          tmp_p = 1;
        } else {
          tmp_p = -1;
        }

        /* Switch: '<S89>/Switch' incorporates:
         *  Constant: '<S89>/Clamping_zero'
         *  Constant: '<S89>/Constant1'
         *  Logic: '<S89>/AND3'
         *  RelationalOperator: '<S89>/Equal1'
         *  RelationalOperator: '<S89>/Relational Operator'
         *  Switch: '<S89>/Switch1'
         *  Switch: '<S89>/Switch2'
         */
        if ((rtb_DeadZone_b != 0.0) && (tmp == tmp_p)) {
          rtb_IntegralGain_hn = 0.0;
        }

        /* Update for DiscreteIntegrator: '<S99>/Integrator' incorporates:
         *  DataStoreRead: '<S2>/Data Store Read2'
         *  Switch: '<S89>/Switch'
         */
        buck_ADRC_MBD_NPU_24b_DW.Integrator_DSTATE_a += rtb_IntegralGain_hn;
        if (enable > 0.0F) {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_k = 1;
        } else if (enable < 0.0F) {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_k = -1;
        } else if (enable == 0.0F) {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_k = 0;
        } else {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_k = 2;
        }

        /* End of Update for DiscreteIntegrator: '<S99>/Integrator' */

        /* Switch: '<S143>/Switch1' incorporates:
         *  Constant: '<S143>/Clamping_zero'
         *  Constant: '<S143>/Constant'
         *  Constant: '<S143>/Constant2'
         *  RelationalOperator: '<S143>/fix for DT propagation issue'
         */
        if (rtb_DeadZone_f > 0.0) {
          tmp = 1;
        } else {
          tmp = -1;
        }

        /* Switch: '<S143>/Switch2' incorporates:
         *  Constant: '<S143>/Clamping_zero'
         *  Constant: '<S143>/Constant3'
         *  Constant: '<S143>/Constant4'
         *  RelationalOperator: '<S143>/fix for DT propagation issue1'
         */
        if (rtb_IntegralGain_m > 0.0) {
          tmp_p = 1;
        } else {
          tmp_p = -1;
        }

        /* Switch: '<S143>/Switch' incorporates:
         *  Constant: '<S143>/Clamping_zero'
         *  Constant: '<S143>/Constant1'
         *  Logic: '<S143>/AND3'
         *  RelationalOperator: '<S143>/Equal1'
         *  RelationalOperator: '<S143>/Relational Operator'
         *  Switch: '<S143>/Switch1'
         *  Switch: '<S143>/Switch2'
         */
        if ((rtb_DeadZone_f != 0.0) && (tmp == tmp_p)) {
          rtb_IntegralGain_m = 0.0;
        }

        /* Update for DiscreteIntegrator: '<S153>/Integrator' incorporates:
         *  DataStoreRead: '<S2>/Data Store Read2'
         *  Switch: '<S143>/Switch'
         */
        buck_ADRC_MBD_NPU_24b_DW.Integrator_DSTATE_p += rtb_IntegralGain_m;
        if (enable > 0.0F) {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_c = 1;
        } else if (enable < 0.0F) {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_c = -1;
        } else if (enable == 0.0F) {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_c = 0;
        } else {
          buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_c = 2;
        }

        /* End of Update for DiscreteIntegrator: '<S153>/Integrator' */

        /* S-Function (c280xgpio_do): '<S1>/Digital Output1' incorporates:
         *  Constant: '<Root>/Constant1'
         */
        {
          if (0.0) {
            GpioDataRegs.GPASET.bit.GPIO22 = 1U;
          } else {
            GpioDataRegs.GPACLEAR.bit.GPIO22 = 1U;
          }
        }
      }

      /* End of Outputs for S-Function (c28xisr_c2000): '<Root>/C28x Hardware Interrupt' */
    }
  }
}

/* Model initialize function */
void buck_ADRC_MBD_NPU_24b_initialize(void)
{
  /* Registration code */

  /* initialize non-finites */
  rt_InitInfAndNaN(sizeof(mwReal32_T));

  /* initialize error status */
  rtmSetErrorStatus(buck_ADRC_MBD_NPU_24b_M, (NULL));

  /* block I/O */
  (void) memset(((void *) &buck_ADRC_MBD_NPU_24b_B), 0,
                sizeof(B_buck_ADRC_MBD_NPU_24b_T));

  /* exported global signals */
  IL1 = 0.0;
  IL2 = 0.0;
  IL3 = 0.0;
  IL4 = 0.0;
  Vout = 0.0F;
  Vin = 0.0F;

  /* states (dwork) */
  (void) memset((void *)&buck_ADRC_MBD_NPU_24b_DW, 0,
                sizeof(DW_buck_ADRC_MBD_NPU_24b_T));

  /* exported global states */
  enable = 0.0F;
  wc = 0.0F;
  wo = 0.0F;
  b0 = 0.0F;
  alpha = 0.0F;

  /* SystemInitialize for S-Function (c28xisr_c2000): '<Root>/C28x Hardware Interrupt' incorporates:
   *  SubSystem: '<Root>/Function-Call Subsystem'
   */

  /* System initialize for function-call system: '<Root>/Function-Call Subsystem' */

  /* Start for S-Function (c280xgpio_do): '<S1>/Digital Output2' incorporates:
   *  Constant: '<Root>/Constant1'
   */
  EALLOW;
  GpioCtrlRegs.GPBMUX2.all &= 0x3FFFFFFFU;
  GpioCtrlRegs.GPBDIR.all |= 0x80000000U;
  EDIS;

  /* Start for S-Function (c2802xpwm): '<S1>/ePWM1' */
  real32_T tbprdValue1 = (real32_T)EPwm1Regs.TBPRD;

  /*** Initialize ePWM1 modules ***/
  {
    /*  -- Time Base Control Register
       EPwm1Regs.TBCTL.bit.CTRMODE              = 2U;          -- Counter Mode

       EPwm1Regs.TBCTL.bit.PRDLD                = 0U;          -- Shadow select

       EPwm1Regs.TBCTL2.bit.PRDLDSYNC           = 0U;          -- Shadow select

       EPwm1Regs.TBCTL.bit.PHSEN                = 0U;          -- Phase Load Enable
       EPwm1Regs.TBCTL.bit.PHSDIR               = 0U;          -- Phase Direction Bit
       EPwm1Regs.TBCTL.bit.HSPCLKDIV            = 0U;          -- High Speed TBCLK Pre-scaler
       EPwm1Regs.TBCTL.bit.CLKDIV               = 0U;          -- Time Base Clock Pre-scaler
     */
    EPwm1Regs.TBCTL.all = (EPwm1Regs.TBCTL.all & ~0x3FCFU) | 0x2U;
    EPwm1Regs.TBCTL2.all = (EPwm1Regs.TBCTL2.all & ~0xC000U) | 0x0U;

    /* -- Time-Base EPWMxSYNCOUT Source Enable Register
       EPwm1Regs.EPWMSYNCOUTEN.bit.ZEROEN      = 1U; -- Sync Output Select - CTR = 0 event
     */
    EPwm1Regs.EPWMSYNCOUTEN.bit.SWEN = 0U;// disable the SWEN enabled during reset
    EPwm1Regs.EPWMSYNCOUTEN.all = (EPwm1Regs.EPWMSYNCOUTEN.all & ~0x2U) | 0x2U;

    /*-- Setup Time-Base (TB) Submodule --*/
    EPwm1Regs.TBPRD = 2500U;           // Time Base Period Register

    /* -- Time-Base Phase Register
       EPwm1Regs.TBPHS.bit.TBPHS               = 0U;          -- Phase offset register
     */
    EPwm1Regs.TBPHS.all = (EPwm1Regs.TBPHS.all & ~0xFFFF0000U) | 0x0U;

    // Time Base Counter Register
    EPwm1Regs.TBCTR = 0x0000U;         /* Clear counter*/

    /*-- Setup Counter_Compare (CC) Submodule --*/
    /*	-- Counter Compare Control Register

       EPwm1Regs.CMPCTL.bit.LOADASYNC           = 0U;          -- Active Compare A Load SYNC Option
       EPwm1Regs.CMPCTL.bit.LOADBSYNC           = 0U;          -- Active Compare B Load SYNC Option
       EPwm1Regs.CMPCTL.bit.LOADAMODE           = 0U;          -- Active Compare A Load
       EPwm1Regs.CMPCTL.bit.LOADBMODE           = 0U;          -- Active Compare B Load
       EPwm1Regs.CMPCTL.bit.SHDWAMODE           = 0U;          -- Compare A Register Block Operating Mode
       EPwm1Regs.CMPCTL.bit.SHDWBMODE           = 0U;          -- Compare B Register Block Operating Mode
     */
    EPwm1Regs.CMPCTL.all = (EPwm1Regs.CMPCTL.all & ~0x3C5FU) | 0x0U;

    /* EPwm1Regs.CMPCTL2.bit.SHDWCMODE           = 0U;          -- Compare C Register Block Operating Mode
       EPwm1Regs.CMPCTL2.bit.SHDWDMODE           = 0U;          -- Compare D Register Block Operating Mode
       EPwm1Regs.CMPCTL2.bit.LOADCSYNC           = 0U;          -- Active Compare C Load SYNC Option
       EPwm1Regs.CMPCTL2.bit.LOADDSYNC           = 0U;          -- Active Compare D Load SYNC Option
       EPwm1Regs.CMPCTL2.bit.LOADCMODE           = 0U;          -- Active Compare C Load
       EPwm1Regs.CMPCTL2.bit.LOADDMODE           = 0U;          -- Active Compare D Load
     */
    EPwm1Regs.CMPCTL2.all = (EPwm1Regs.CMPCTL2.all & ~0x3C5FU) | 0x0U;
    EPwm1Regs.CMPA.bit.CMPA = 1250U;   // Counter Compare A Register
    EPwm1Regs.CMPB.bit.CMPB = 32000U;  // Counter Compare B Register
    EPwm1Regs.CMPC = 32000U;           // Counter Compare C Register
    EPwm1Regs.CMPD = 32000U;           // Counter Compare D Register

    /*-- Setup Action-Qualifier (AQ) Submodule --*/
    EPwm1Regs.AQCTLA.all = 146U;
                               // Action Qualifier Control Register For Output A
    EPwm1Regs.AQCTLB.all = 2310U;
                               // Action Qualifier Control Register For Output B

    /*	-- Action Qualifier Software Force Register
       EPwm1Regs.AQSFRC.bit.RLDCSF              = 0U;          -- Reload from Shadow Options
     */
    EPwm1Regs.AQSFRC.all = (EPwm1Regs.AQSFRC.all & ~0xC0U) | 0x0U;

    /*	-- Action Qualifier Continuous S/W Force Register
       EPwm1Regs.AQCSFRC.bit.CSFA               = 0U;          -- Continuous Software Force on output A
       EPwm1Regs.AQCSFRC.bit.CSFB               = 0U;          -- Continuous Software Force on output B
     */
    EPwm1Regs.AQCSFRC.all = (EPwm1Regs.AQCSFRC.all & ~0xFU) | 0x0U;

    /*-- Setup Dead-Band Generator (DB) Submodule --*/
    /*	-- Dead-Band Generator Control Register
       EPwm1Regs.DBCTL.bit.OUT_MODE             = 3U;          -- Dead Band Output Mode Control
       EPwm1Regs.DBCTL.bit.IN_MODE              = 0U;          -- Dead Band Input Select Mode Control
       EPwm1Regs.DBCTL.bit.POLSEL               = 2U;          -- Polarity Select Control
       EPwm1Regs.DBCTL.bit.HALFCYCLE            = 0U;          -- Half Cycle Clocking Enable
       EPwm1Regs.DBCTL.bit.SHDWDBREDMODE        = 0U;          -- DBRED shadow mode
       EPwm1Regs.DBCTL.bit.SHDWDBFEDMODE        = 0U;          -- DBFED shadow mode
       EPwm1Regs.DBCTL.bit.LOADREDMODE          = 4U;        -- DBRED load
       EPwm1Regs.DBCTL.bit.LOADFEDMODE          = 4U;        -- DBFED load
     */
    EPwm1Regs.DBCTL.all = (EPwm1Regs.DBCTL.all & ~0x8FFFU) | 0xBU;
    EPwm1Regs.DBRED.bit.DBRED = (uint16_T)(50.0);
                         // Dead-Band Generator Rising Edge Delay Count Register
    EPwm1Regs.DBFED.bit.DBFED = (uint16_T)(50.0);
                        // Dead-Band Generator Falling Edge Delay Count Register

    /*-- Setup Event-Trigger (ET) Submodule --*/
    /*	-- Event Trigger Selection and Pre-Scale Register
       EPwm1Regs.ETSEL.bit.SOCAEN               = 1U;          -- Start of Conversion A Enable
       EPwm1Regs.ETSEL.bit.SOCASELCMP           = 0U;
       EPwm1Regs.ETSEL.bit.SOCASEL              = 2U;          -- Start of Conversion A Select
       EPwm1Regs.ETPS.bit.SOCPSSEL              = 1U;          -- EPWM1SOC Period Select
       EPwm1Regs.ETSOCPS.bit.SOCAPRD2           = 1U;
       EPwm1Regs.ETSEL.bit.SOCBEN               = 0U;          -- Start of Conversion B Enable
       EPwm1Regs.ETSEL.bit.SOCBSELCMP           = 0U;
       EPwm1Regs.ETSEL.bit.SOCBSEL              = 1U;          -- Start of Conversion A Select
       EPwm1Regs.ETPS.bit.SOCPSSEL              = 1;          -- EPWM1SOCB Period Select
       EPwm1Regs.ETSOCPS.bit.SOCBPRD2           = 1U;
       EPwm1Regs.ETSEL.bit.INTEN                = 0U;          -- EPWM1INTn Enable
       EPwm1Regs.ETSEL.bit.INTSELCMP            = 0U;
       EPwm1Regs.ETSEL.bit.INTSEL               = 1U;          -- Start of Conversion A Select
       EPwm1Regs.ETPS.bit.INTPSSEL              = 1U;          // EPWM1INTn Period Select
       EPwm1Regs.ETINTPS.bit.INTPRD2            = 1U;
     */
    EPwm1Regs.ETSEL.all = (EPwm1Regs.ETSEL.all & ~0xFF7FU) | 0x1A01U;
    EPwm1Regs.ETPS.all = (EPwm1Regs.ETPS.all & ~0x30U) | 0x30U;
    EPwm1Regs.ETSOCPS.all = (EPwm1Regs.ETSOCPS.all & ~0xF0FU) | 0x101U;
    EPwm1Regs.ETINTPS.all = (EPwm1Regs.ETINTPS.all & ~0xFU) | 0x1U;

    /*-- Setup PWM-Chopper (PC) Submodule --*/
    /*	-- PWM Chopper Control Register
       EPwm1Regs.PCCTL.bit.CHPEN                = 0U;          -- PWM chopping enable
       EPwm1Regs.PCCTL.bit.CHPFREQ              = 0U;          -- Chopping clock frequency
       EPwm1Regs.PCCTL.bit.OSHTWTH              = 0U;          -- One-shot pulse width
       EPwm1Regs.PCCTL.bit.CHPDUTY              = 0U;          -- Chopping clock Duty cycle
     */
    EPwm1Regs.PCCTL.all = (EPwm1Regs.PCCTL.all & ~0x7FFU) | 0x0U;

    /*-- Set up Trip-Zone (TZ) Submodule --*/
    EALLOW;
    EPwm1Regs.TZSEL.all = 0U;          // Trip Zone Select Register

    /*-- Set CBCPULSE for CBC latch Clear --*/
    EPwm1Regs.TZCLR.bit.CBCPULSE = 0U;

    /*	-- Trip Zone Control Register
       EPwm1Regs.TZCTL.bit.TZA                  = 3U;          -- TZ1 to TZ6 Trip Action On EPWM1A
       EPwm1Regs.TZCTL.bit.TZB                  = 3U;          -- TZ1 to TZ6 Trip Action On EPWM1B
       EPwm1Regs.TZCTL.bit.DCAEVT1              = 3U;          -- EPWM1A action on DCAEVT1
       EPwm1Regs.TZCTL.bit.DCAEVT2              = 3U;          -- EPWM1A action on DCAEVT2
       EPwm1Regs.TZCTL.bit.DCBEVT1              = 3U;          -- EPWM1B action on DCBEVT1
       EPwm1Regs.TZCTL.bit.DCBEVT2              = 3U;          -- EPWM1B action on DCBEVT2
     */
    EPwm1Regs.TZCTL.all = (EPwm1Regs.TZCTL.all & ~0xFFFU) | 0xFFFU;

    /*	-- Trip Zone Enable Interrupt Register
       EPwm1Regs.TZEINT.bit.OST                 = 0U;          -- Trip Zones One Shot Int Enable
       EPwm1Regs.TZEINT.bit.CBC                 = 0U;          -- Trip Zones Cycle By Cycle Int Enable
       EPwm1Regs.TZEINT.bit.DCAEVT1             = 0U;          -- Digital Compare A Event 1 Int Enable
       EPwm1Regs.TZEINT.bit.DCAEVT2             = 0U;          -- Digital Compare A Event 2 Int Enable
       EPwm1Regs.TZEINT.bit.DCBEVT1             = 0U;          -- Digital Compare B Event 1 Int Enable
       EPwm1Regs.TZEINT.bit.DCBEVT2             = 0U;          -- Digital Compare B Event 2 Int Enable
     */
    EPwm1Regs.TZEINT.all = (EPwm1Regs.TZEINT.all & ~0x7EU) | 0x0U;

    /*	-- Digital Compare A Control Register
       EPwm1Regs.DCACTL.bit.EVT1SYNCE           = 0U;          -- DCAEVT1 SYNC Enable
       EPwm1Regs.DCACTL.bit.EVT1SOCE            = 1U;          -- DCAEVT1 SOC Enable
       EPwm1Regs.DCACTL.bit.EVT1FRCSYNCSEL      = 0U;          -- DCAEVT1 Force Sync Signal
       EPwm1Regs.DCACTL.bit.EVT1SRCSEL          = 0U;          -- DCAEVT1 Source Signal
       EPwm1Regs.DCACTL.bit.EVT2FRCSYNCSEL      = 0U;          -- DCAEVT2 Force Sync Signal
       EPwm1Regs.DCACTL.bit.EVT2SRCSEL          = 0U;          -- DCAEVT2 Source Signal
     */
    EPwm1Regs.DCACTL.all = (EPwm1Regs.DCACTL.all & ~0x30FU) | 0x4U;

    /*	-- Digital Compare B Control Register
       EPwm1Regs.DCBCTL.bit.EVT1SYNCE           = 0U;          -- DCBEVT1 SYNC Enable
       EPwm1Regs.DCBCTL.bit.EVT1SOCE            = 0U;          -- DCBEVT1 SOC Enable
       EPwm1Regs.DCBCTL.bit.EVT1FRCSYNCSEL      = 0U;          -- DCBEVT1 Force Sync Signal
       EPwm1Regs.DCBCTL.bit.EVT1SRCSEL          = 0U;          -- DCBEVT1 Source Signal
       EPwm1Regs.DCBCTL.bit.EVT2FRCSYNCSEL      = 0U;          -- DCBEVT2 Force Sync Signal
       EPwm1Regs.DCBCTL.bit.EVT2SRCSEL          = 0U;          -- DCBEVT2 Source Signal
     */
    EPwm1Regs.DCBCTL.all = (EPwm1Regs.DCBCTL.all & ~0x30FU) | 0x0U;

    /*	-- Digital Compare Trip Select Register
       EPwm1Regs.DCTRIPSEL.bit.DCAHCOMPSEL      = 0U;          -- Digital Compare A High COMP Input Select

       EPwm1Regs.DCTRIPSEL.bit.DCALCOMPSEL      = 0U;          -- Digital Compare A Low COMP Input Select
       EPwm1Regs.DCTRIPSEL.bit.DCBHCOMPSEL      = 0U;          -- Digital Compare B High COMP Input Select
       EPwm1Regs.DCTRIPSEL.bit.DCBLCOMPSEL      = 0U;          -- Digital Compare B Low COMP Input Select
     */
    EPwm1Regs.DCTRIPSEL.all = (EPwm1Regs.DCTRIPSEL.all & ~ 0xFFFFU) | 0x0U;

    /*	-- Trip Zone Digital Comparator Select Register
       EPwm1Regs.TZDCSEL.bit.DCAEVT1            = 0U;          -- Digital Compare Output A Event 1
       EPwm1Regs.TZDCSEL.bit.DCAEVT2            = 0U;          -- Digital Compare Output A Event 2
       EPwm1Regs.TZDCSEL.bit.DCBEVT1            = 0U;          -- Digital Compare Output B Event 1
       EPwm1Regs.TZDCSEL.bit.DCBEVT2            = 0U;          -- Digital Compare Output B Event 2
     */
    EPwm1Regs.TZDCSEL.all = (EPwm1Regs.TZDCSEL.all & ~0xFFFU) | 0x0U;

    /*	-- Digital Compare Filter Control Register
       EPwm1Regs.DCFCTL.bit.BLANKE              = 0U;          -- Blanking Enable/Disable
       EPwm1Regs.DCFCTL.bit.PULSESEL            = 1U;          -- Pulse Select for Blanking & Capture Alignment
       EPwm1Regs.DCFCTL.bit.BLANKINV            = 0U;          -- Blanking Window Inversion
       EPwm1Regs.DCFCTL.bit.SRCSEL              = 0U;          -- Filter Block Signal Source Select
     */
    EPwm1Regs.DCFCTL.all = (EPwm1Regs.DCFCTL.all & ~0x3FU) | 0x10U;
    EPwm1Regs.DCFOFFSET = 0U;          // Digital Compare Filter Offset Register
    EPwm1Regs.DCFWINDOW = 0U;          // Digital Compare Filter Window Register

    /*	-- Digital Compare Capture Control Register
       EPwm1Regs.DCCAPCTL.bit.CAPE              = 0U;          -- Counter Capture Enable
     */
    EPwm1Regs.DCCAPCTL.all = (EPwm1Regs.DCCAPCTL.all & ~0x1U) | 0x0U;

    /*	-- HRPWM Configuration Register
       EPwm1Regs.HRCNFG.bit.SWAPAB              = 0U;          -- Swap EPWMA and EPWMB Outputs Bit
       EPwm1Regs.HRCNFG.bit.SELOUTB             = 0U;          -- EPWMB Output Selection Bit
     */
    EPwm1Regs.HRCNFG.all = (EPwm1Regs.HRCNFG.all & ~0xA0U) | 0x0U;

    /* Update the Link Registers with the link value for all the Compare values and TBPRD */
    /* No error is thrown if the ePWM register exists in the model or not */
    EPwm1Regs.EPWMXLINK.bit.TBPRDLINK = 0U;
    EPwm1Regs.EPWMXLINK.bit.CMPALINK = 0U;
    EPwm1Regs.EPWMXLINK.bit.CMPBLINK = 0U;
    EPwm1Regs.EPWMXLINK.bit.CMPCLINK = 0U;
    EPwm1Regs.EPWMXLINK.bit.CMPDLINK = 0U;

    /* SYNCPER - Peripheral synchronization output event
       EPwm1Regs.HRPCTL.bit.PWMSYNCSEL            = 0U;          -- EPWMSYNCPER selection
       EPwm1Regs.HRPCTL.bit.PWMSYNCSELX           = 0U;          --  EPWMSYNCPER selection
     */
    EPwm1Regs.HRPCTL.all = (EPwm1Regs.HRPCTL.all & ~0x72U) | 0x0U;
    EDIS;
  }

  /* Start for S-Function (c2802xpwm): '<S1>/ePWM10' */
  real32_T tbprdValue10 = (real32_T)EPwm10Regs.TBPRD;

  /*** Initialize ePWM10 modules ***/
  {
    /*  -- Time Base Control Register
       EPwm10Regs.TBCTL.bit.CTRMODE              = 2U;          -- Counter Mode

       EPwm10Regs.TBCTL.bit.PRDLD                = 0U;          -- Shadow select

       EPwm10Regs.TBCTL2.bit.PRDLDSYNC           = 0U;          -- Shadow select

       EPwm10Regs.TBCTL.bit.PHSEN                = 1U;          -- Phase Load Enable
       EPwm10Regs.TBCTL.bit.PHSDIR               = 1U;          -- Phase Direction Bit
       EPwm10Regs.TBCTL.bit.HSPCLKDIV            = 0U;          -- High Speed TBCLK Pre-scaler
       EPwm10Regs.TBCTL.bit.CLKDIV               = 0U;          -- Time Base Clock Pre-scaler
     */
    EPwm10Regs.TBCTL.all = (EPwm10Regs.TBCTL.all & ~0x3FCFU) | 0x2006U;
    EPwm10Regs.TBCTL2.all = (EPwm10Regs.TBCTL2.all & ~0xC000U) | 0x0U;

    /* -- Time-Base EPWMxSYNCOUT Source Enable Register
     */
    EPwm10Regs.EPWMSYNCOUTEN.bit.SWEN = 0U;// disable the SWEN enabled during reset
    EPwm10Regs.EPWMSYNCOUTEN.all = (EPwm10Regs.EPWMSYNCOUTEN.all & ~0x0U) | 0x0U;

    /*-- Setup Time-Base (TB) Submodule --*/
    EPwm10Regs.TBPRD = 2500U;          // Time Base Period Register

    /* -- Time-Base Phase Register
       EPwm10Regs.TBPHS.bit.TBPHS               = 1250U;          -- Phase offset register
     */
    EPwm10Regs.TBPHS.all = (EPwm10Regs.TBPHS.all & ~0xFFFF0000U) | 0x4E20000U;

    // Time Base Counter Register
    EPwm10Regs.TBCTR = 0x0000U;        /* Clear counter*/

    /*-- Setup Counter_Compare (CC) Submodule --*/
    /*	-- Counter Compare Control Register

       EPwm10Regs.CMPCTL.bit.LOADASYNC           = 0U;          -- Active Compare A Load SYNC Option
       EPwm10Regs.CMPCTL.bit.LOADBSYNC           = 0U;          -- Active Compare B Load SYNC Option
       EPwm10Regs.CMPCTL.bit.LOADAMODE           = 0U;          -- Active Compare A Load
       EPwm10Regs.CMPCTL.bit.LOADBMODE           = 0U;          -- Active Compare B Load
       EPwm10Regs.CMPCTL.bit.SHDWAMODE           = 0U;          -- Compare A Register Block Operating Mode
       EPwm10Regs.CMPCTL.bit.SHDWBMODE           = 0U;          -- Compare B Register Block Operating Mode
     */
    EPwm10Regs.CMPCTL.all = (EPwm10Regs.CMPCTL.all & ~0x3C5FU) | 0x0U;

    /* EPwm10Regs.CMPCTL2.bit.SHDWCMODE           = 0U;          -- Compare C Register Block Operating Mode
       EPwm10Regs.CMPCTL2.bit.SHDWDMODE           = 0U;          -- Compare D Register Block Operating Mode
       EPwm10Regs.CMPCTL2.bit.LOADCSYNC           = 0U;          -- Active Compare C Load SYNC Option
       EPwm10Regs.CMPCTL2.bit.LOADDSYNC           = 0U;          -- Active Compare D Load SYNC Option
       EPwm10Regs.CMPCTL2.bit.LOADCMODE           = 0U;          -- Active Compare C Load
       EPwm10Regs.CMPCTL2.bit.LOADDMODE           = 0U;          -- Active Compare D Load
     */
    EPwm10Regs.CMPCTL2.all = (EPwm10Regs.CMPCTL2.all & ~0x3C5FU) | 0x0U;
    EPwm10Regs.CMPA.bit.CMPA = 1250U;  // Counter Compare A Register
    EPwm10Regs.CMPB.bit.CMPB = 32000U; // Counter Compare B Register
    EPwm10Regs.CMPC = 32000U;          // Counter Compare C Register
    EPwm10Regs.CMPD = 32000U;          // Counter Compare D Register

    /*-- Setup Action-Qualifier (AQ) Submodule --*/
    EPwm10Regs.AQCTLA.all = 146U;
                               // Action Qualifier Control Register For Output A
    EPwm10Regs.AQCTLB.all = 2310U;
                               // Action Qualifier Control Register For Output B

    /*	-- Action Qualifier Software Force Register
       EPwm10Regs.AQSFRC.bit.RLDCSF              = 0U;          -- Reload from Shadow Options
     */
    EPwm10Regs.AQSFRC.all = (EPwm10Regs.AQSFRC.all & ~0xC0U) | 0x0U;

    /*	-- Action Qualifier Continuous S/W Force Register
       EPwm10Regs.AQCSFRC.bit.CSFA               = 0U;          -- Continuous Software Force on output A
       EPwm10Regs.AQCSFRC.bit.CSFB               = 0U;          -- Continuous Software Force on output B
     */
    EPwm10Regs.AQCSFRC.all = (EPwm10Regs.AQCSFRC.all & ~0xFU) | 0x0U;

    /*-- Setup Dead-Band Generator (DB) Submodule --*/
    /*	-- Dead-Band Generator Control Register
       EPwm10Regs.DBCTL.bit.OUT_MODE             = 3U;          -- Dead Band Output Mode Control
       EPwm10Regs.DBCTL.bit.IN_MODE              = 0U;          -- Dead Band Input Select Mode Control
       EPwm10Regs.DBCTL.bit.POLSEL               = 2U;          -- Polarity Select Control
       EPwm10Regs.DBCTL.bit.HALFCYCLE            = 0U;          -- Half Cycle Clocking Enable
       EPwm10Regs.DBCTL.bit.SHDWDBREDMODE        = 0U;          -- DBRED shadow mode
       EPwm10Regs.DBCTL.bit.SHDWDBFEDMODE        = 0U;          -- DBFED shadow mode
       EPwm10Regs.DBCTL.bit.LOADREDMODE          = 4U;        -- DBRED load
       EPwm10Regs.DBCTL.bit.LOADFEDMODE          = 4U;        -- DBFED load
     */
    EPwm10Regs.DBCTL.all = (EPwm10Regs.DBCTL.all & ~0x8FFFU) | 0xBU;
    EPwm10Regs.DBRED.bit.DBRED = (uint16_T)(50.0);
                         // Dead-Band Generator Rising Edge Delay Count Register
    EPwm10Regs.DBFED.bit.DBFED = (uint16_T)(50.0);
                        // Dead-Band Generator Falling Edge Delay Count Register

    /*-- Setup Event-Trigger (ET) Submodule --*/
    /*	-- Event Trigger Selection and Pre-Scale Register
       EPwm10Regs.ETSEL.bit.SOCAEN               = 1U;          -- Start of Conversion A Enable
       EPwm10Regs.ETSEL.bit.SOCASELCMP           = 0U;
       EPwm10Regs.ETSEL.bit.SOCASEL              = 2U;          -- Start of Conversion A Select
       EPwm10Regs.ETPS.bit.SOCPSSEL              = 1U;          -- EPWM10SOC Period Select
       EPwm10Regs.ETSOCPS.bit.SOCAPRD2           = 1U;
       EPwm10Regs.ETSEL.bit.SOCBEN               = 0U;          -- Start of Conversion B Enable
       EPwm10Regs.ETSEL.bit.SOCBSELCMP           = 0U;
       EPwm10Regs.ETSEL.bit.SOCBSEL              = 1U;          -- Start of Conversion A Select
       EPwm10Regs.ETPS.bit.SOCPSSEL              = 1;          -- EPWM10SOCB Period Select
       EPwm10Regs.ETSOCPS.bit.SOCBPRD2           = 1U;
       EPwm10Regs.ETSEL.bit.INTEN                = 0U;          -- EPWM10INTn Enable
       EPwm10Regs.ETSEL.bit.INTSELCMP            = 0U;
       EPwm10Regs.ETSEL.bit.INTSEL               = 1U;          -- Start of Conversion A Select
       EPwm10Regs.ETPS.bit.INTPSSEL              = 1U;          // EPWM10INTn Period Select
       EPwm10Regs.ETINTPS.bit.INTPRD2            = 1U;
     */
    EPwm10Regs.ETSEL.all = (EPwm10Regs.ETSEL.all & ~0xFF7FU) | 0x1A01U;
    EPwm10Regs.ETPS.all = (EPwm10Regs.ETPS.all & ~0x30U) | 0x30U;
    EPwm10Regs.ETSOCPS.all = (EPwm10Regs.ETSOCPS.all & ~0xF0FU) | 0x101U;
    EPwm10Regs.ETINTPS.all = (EPwm10Regs.ETINTPS.all & ~0xFU) | 0x1U;

    /*-- Setup PWM-Chopper (PC) Submodule --*/
    /*	-- PWM Chopper Control Register
       EPwm10Regs.PCCTL.bit.CHPEN                = 0U;          -- PWM chopping enable
       EPwm10Regs.PCCTL.bit.CHPFREQ              = 0U;          -- Chopping clock frequency
       EPwm10Regs.PCCTL.bit.OSHTWTH              = 0U;          -- One-shot pulse width
       EPwm10Regs.PCCTL.bit.CHPDUTY              = 0U;          -- Chopping clock Duty cycle
     */
    EPwm10Regs.PCCTL.all = (EPwm10Regs.PCCTL.all & ~0x7FFU) | 0x0U;

    /*-- Set up Trip-Zone (TZ) Submodule --*/
    EALLOW;
    EPwm10Regs.TZSEL.all = 0U;         // Trip Zone Select Register

    /*-- Set CBCPULSE for CBC latch Clear --*/
    EPwm10Regs.TZCLR.bit.CBCPULSE = 0U;

    /*	-- Trip Zone Control Register
       EPwm10Regs.TZCTL.bit.TZA                  = 3U;          -- TZ1 to TZ6 Trip Action On EPWM10A
       EPwm10Regs.TZCTL.bit.TZB                  = 3U;          -- TZ1 to TZ6 Trip Action On EPWM10B
       EPwm10Regs.TZCTL.bit.DCAEVT1              = 3U;          -- EPWM10A action on DCAEVT1
       EPwm10Regs.TZCTL.bit.DCAEVT2              = 3U;          -- EPWM10A action on DCAEVT2
       EPwm10Regs.TZCTL.bit.DCBEVT1              = 3U;          -- EPWM10B action on DCBEVT1
       EPwm10Regs.TZCTL.bit.DCBEVT2              = 3U;          -- EPWM10B action on DCBEVT2
     */
    EPwm10Regs.TZCTL.all = (EPwm10Regs.TZCTL.all & ~0xFFFU) | 0xFFFU;

    /*	-- Trip Zone Enable Interrupt Register
       EPwm10Regs.TZEINT.bit.OST                 = 0U;          -- Trip Zones One Shot Int Enable
       EPwm10Regs.TZEINT.bit.CBC                 = 0U;          -- Trip Zones Cycle By Cycle Int Enable
       EPwm10Regs.TZEINT.bit.DCAEVT1             = 0U;          -- Digital Compare A Event 1 Int Enable
       EPwm10Regs.TZEINT.bit.DCAEVT2             = 0U;          -- Digital Compare A Event 2 Int Enable
       EPwm10Regs.TZEINT.bit.DCBEVT1             = 0U;          -- Digital Compare B Event 1 Int Enable
       EPwm10Regs.TZEINT.bit.DCBEVT2             = 0U;          -- Digital Compare B Event 2 Int Enable
     */
    EPwm10Regs.TZEINT.all = (EPwm10Regs.TZEINT.all & ~0x7EU) | 0x0U;

    /*	-- Digital Compare A Control Register
       EPwm10Regs.DCACTL.bit.EVT1SYNCE           = 0U;          -- DCAEVT1 SYNC Enable
       EPwm10Regs.DCACTL.bit.EVT1SOCE            = 1U;          -- DCAEVT1 SOC Enable
       EPwm10Regs.DCACTL.bit.EVT1FRCSYNCSEL      = 0U;          -- DCAEVT1 Force Sync Signal
       EPwm10Regs.DCACTL.bit.EVT1SRCSEL          = 0U;          -- DCAEVT1 Source Signal
       EPwm10Regs.DCACTL.bit.EVT2FRCSYNCSEL      = 0U;          -- DCAEVT2 Force Sync Signal
       EPwm10Regs.DCACTL.bit.EVT2SRCSEL          = 0U;          -- DCAEVT2 Source Signal
     */
    EPwm10Regs.DCACTL.all = (EPwm10Regs.DCACTL.all & ~0x30FU) | 0x4U;

    /*	-- Digital Compare B Control Register
       EPwm10Regs.DCBCTL.bit.EVT1SYNCE           = 0U;          -- DCBEVT1 SYNC Enable
       EPwm10Regs.DCBCTL.bit.EVT1SOCE            = 0U;          -- DCBEVT1 SOC Enable
       EPwm10Regs.DCBCTL.bit.EVT1FRCSYNCSEL      = 0U;          -- DCBEVT1 Force Sync Signal
       EPwm10Regs.DCBCTL.bit.EVT1SRCSEL          = 0U;          -- DCBEVT1 Source Signal
       EPwm10Regs.DCBCTL.bit.EVT2FRCSYNCSEL      = 0U;          -- DCBEVT2 Force Sync Signal
       EPwm10Regs.DCBCTL.bit.EVT2SRCSEL          = 0U;          -- DCBEVT2 Source Signal
     */
    EPwm10Regs.DCBCTL.all = (EPwm10Regs.DCBCTL.all & ~0x30FU) | 0x0U;

    /*	-- Digital Compare Trip Select Register
       EPwm10Regs.DCTRIPSEL.bit.DCAHCOMPSEL      = 0U;          -- Digital Compare A High COMP Input Select

       EPwm10Regs.DCTRIPSEL.bit.DCALCOMPSEL      = 0U;          -- Digital Compare A Low COMP Input Select
       EPwm10Regs.DCTRIPSEL.bit.DCBHCOMPSEL      = 0U;          -- Digital Compare B High COMP Input Select
       EPwm10Regs.DCTRIPSEL.bit.DCBLCOMPSEL      = 0U;          -- Digital Compare B Low COMP Input Select
     */
    EPwm10Regs.DCTRIPSEL.all = (EPwm10Regs.DCTRIPSEL.all & ~ 0xFFFFU) | 0x0U;

    /*	-- Trip Zone Digital Comparator Select Register
       EPwm10Regs.TZDCSEL.bit.DCAEVT1            = 0U;          -- Digital Compare Output A Event 1
       EPwm10Regs.TZDCSEL.bit.DCAEVT2            = 0U;          -- Digital Compare Output A Event 2
       EPwm10Regs.TZDCSEL.bit.DCBEVT1            = 0U;          -- Digital Compare Output B Event 1
       EPwm10Regs.TZDCSEL.bit.DCBEVT2            = 0U;          -- Digital Compare Output B Event 2
     */
    EPwm10Regs.TZDCSEL.all = (EPwm10Regs.TZDCSEL.all & ~0xFFFU) | 0x0U;

    /*	-- Digital Compare Filter Control Register
       EPwm10Regs.DCFCTL.bit.BLANKE              = 0U;          -- Blanking Enable/Disable
       EPwm10Regs.DCFCTL.bit.PULSESEL            = 1U;          -- Pulse Select for Blanking & Capture Alignment
       EPwm10Regs.DCFCTL.bit.BLANKINV            = 0U;          -- Blanking Window Inversion
       EPwm10Regs.DCFCTL.bit.SRCSEL              = 0U;          -- Filter Block Signal Source Select
     */
    EPwm10Regs.DCFCTL.all = (EPwm10Regs.DCFCTL.all & ~0x3FU) | 0x10U;
    EPwm10Regs.DCFOFFSET = 0U;         // Digital Compare Filter Offset Register
    EPwm10Regs.DCFWINDOW = 0U;         // Digital Compare Filter Window Register

    /*	-- Digital Compare Capture Control Register
       EPwm10Regs.DCCAPCTL.bit.CAPE              = 0U;          -- Counter Capture Enable
     */
    EPwm10Regs.DCCAPCTL.all = (EPwm10Regs.DCCAPCTL.all & ~0x1U) | 0x0U;

    /*	-- HRPWM Configuration Register
       EPwm10Regs.HRCNFG.bit.SWAPAB              = 0U;          -- Swap EPWMA and EPWMB Outputs Bit
       EPwm10Regs.HRCNFG.bit.SELOUTB             = 0U;          -- EPWMB Output Selection Bit
     */
    EPwm10Regs.HRCNFG.all = (EPwm10Regs.HRCNFG.all & ~0xA0U) | 0x0U;

    /* Update the Link Registers with the link value for all the Compare values and TBPRD */
    /* No error is thrown if the ePWM register exists in the model or not */
    EPwm10Regs.EPWMXLINK.bit.TBPRDLINK = 0U;
    EPwm10Regs.EPWMXLINK.bit.CMPALINK = 9U;
    EPwm10Regs.EPWMXLINK.bit.CMPBLINK = 9U;
    EPwm10Regs.EPWMXLINK.bit.CMPCLINK = 9U;
    EPwm10Regs.EPWMXLINK.bit.CMPDLINK = 9U;

    /* SYNCPER - Peripheral synchronization output event
       EPwm10Regs.HRPCTL.bit.PWMSYNCSEL            = 0U;          -- EPWMSYNCPER selection
       EPwm10Regs.HRPCTL.bit.PWMSYNCSELX           = 0U;          --  EPWMSYNCPER selection
     */
    EPwm10Regs.HRPCTL.all = (EPwm10Regs.HRPCTL.all & ~0x72U) | 0x0U;
    EDIS;
  }

  /* Start for S-Function (c2802xpwm): '<S1>/ePWM2' */
  real32_T tbprdValue2 = (real32_T)EPwm2Regs.TBPRD;

  /*** Initialize ePWM2 modules ***/
  {
    /*  -- Time Base Control Register
       EPwm2Regs.TBCTL.bit.CTRMODE              = 2U;          -- Counter Mode

       EPwm2Regs.TBCTL.bit.PRDLD                = 0U;          -- Shadow select

       EPwm2Regs.TBCTL2.bit.PRDLDSYNC           = 0U;          -- Shadow select

       EPwm2Regs.TBCTL.bit.PHSEN                = 1U;          -- Phase Load Enable
       EPwm2Regs.TBCTL.bit.PHSDIR               = 0U;          -- Phase Direction Bit
       EPwm2Regs.TBCTL.bit.HSPCLKDIV            = 0U;          -- High Speed TBCLK Pre-scaler
       EPwm2Regs.TBCTL.bit.CLKDIV               = 0U;          -- Time Base Clock Pre-scaler
     */
    EPwm2Regs.TBCTL.all = (EPwm2Regs.TBCTL.all & ~0x3FCFU) | 0x6U;
    EPwm2Regs.TBCTL2.all = (EPwm2Regs.TBCTL2.all & ~0xC000U) | 0x0U;

    /* -- Time-Base EPWMxSYNCOUT Source Enable Register
     */
    EPwm2Regs.EPWMSYNCOUTEN.bit.SWEN = 0U;// disable the SWEN enabled during reset
    EPwm2Regs.EPWMSYNCOUTEN.all = (EPwm2Regs.EPWMSYNCOUTEN.all & ~0x0U) | 0x0U;

    /*-- Setup Time-Base (TB) Submodule --*/
    EPwm2Regs.TBPRD = 2500U;           // Time Base Period Register

    /* -- Time-Base Phase Register
       EPwm2Regs.TBPHS.bit.TBPHS               = 1250U;          -- Phase offset register
     */
    EPwm2Regs.TBPHS.all = (EPwm2Regs.TBPHS.all & ~0xFFFF0000U) | 0x4E20000U;

    // Time Base Counter Register
    EPwm2Regs.TBCTR = 0x0000U;         /* Clear counter*/

    /*-- Setup Counter_Compare (CC) Submodule --*/
    /*	-- Counter Compare Control Register

       EPwm2Regs.CMPCTL.bit.LOADASYNC           = 0U;          -- Active Compare A Load SYNC Option
       EPwm2Regs.CMPCTL.bit.LOADBSYNC           = 0U;          -- Active Compare B Load SYNC Option
       EPwm2Regs.CMPCTL.bit.LOADAMODE           = 0U;          -- Active Compare A Load
       EPwm2Regs.CMPCTL.bit.LOADBMODE           = 0U;          -- Active Compare B Load
       EPwm2Regs.CMPCTL.bit.SHDWAMODE           = 0U;          -- Compare A Register Block Operating Mode
       EPwm2Regs.CMPCTL.bit.SHDWBMODE           = 0U;          -- Compare B Register Block Operating Mode
     */
    EPwm2Regs.CMPCTL.all = (EPwm2Regs.CMPCTL.all & ~0x3C5FU) | 0x0U;

    /* EPwm2Regs.CMPCTL2.bit.SHDWCMODE           = 0U;          -- Compare C Register Block Operating Mode
       EPwm2Regs.CMPCTL2.bit.SHDWDMODE           = 0U;          -- Compare D Register Block Operating Mode
       EPwm2Regs.CMPCTL2.bit.LOADCSYNC           = 0U;          -- Active Compare C Load SYNC Option
       EPwm2Regs.CMPCTL2.bit.LOADDSYNC           = 0U;          -- Active Compare D Load SYNC Option
       EPwm2Regs.CMPCTL2.bit.LOADCMODE           = 0U;          -- Active Compare C Load
       EPwm2Regs.CMPCTL2.bit.LOADDMODE           = 0U;          -- Active Compare D Load
     */
    EPwm2Regs.CMPCTL2.all = (EPwm2Regs.CMPCTL2.all & ~0x3C5FU) | 0x0U;
    EPwm2Regs.CMPA.bit.CMPA = 1250U;   // Counter Compare A Register
    EPwm2Regs.CMPB.bit.CMPB = 32000U;  // Counter Compare B Register
    EPwm2Regs.CMPC = 32000U;           // Counter Compare C Register
    EPwm2Regs.CMPD = 32000U;           // Counter Compare D Register

    /*-- Setup Action-Qualifier (AQ) Submodule --*/
    EPwm2Regs.AQCTLA.all = 146U;
                               // Action Qualifier Control Register For Output A
    EPwm2Regs.AQCTLB.all = 2310U;
                               // Action Qualifier Control Register For Output B

    /*	-- Action Qualifier Software Force Register
       EPwm2Regs.AQSFRC.bit.RLDCSF              = 0U;          -- Reload from Shadow Options
     */
    EPwm2Regs.AQSFRC.all = (EPwm2Regs.AQSFRC.all & ~0xC0U) | 0x0U;

    /*	-- Action Qualifier Continuous S/W Force Register
       EPwm2Regs.AQCSFRC.bit.CSFA               = 0U;          -- Continuous Software Force on output A
       EPwm2Regs.AQCSFRC.bit.CSFB               = 0U;          -- Continuous Software Force on output B
     */
    EPwm2Regs.AQCSFRC.all = (EPwm2Regs.AQCSFRC.all & ~0xFU) | 0x0U;

    /*-- Setup Dead-Band Generator (DB) Submodule --*/
    /*	-- Dead-Band Generator Control Register
       EPwm2Regs.DBCTL.bit.OUT_MODE             = 3U;          -- Dead Band Output Mode Control
       EPwm2Regs.DBCTL.bit.IN_MODE              = 0U;          -- Dead Band Input Select Mode Control
       EPwm2Regs.DBCTL.bit.POLSEL               = 2U;          -- Polarity Select Control
       EPwm2Regs.DBCTL.bit.HALFCYCLE            = 0U;          -- Half Cycle Clocking Enable
       EPwm2Regs.DBCTL.bit.SHDWDBREDMODE        = 0U;          -- DBRED shadow mode
       EPwm2Regs.DBCTL.bit.SHDWDBFEDMODE        = 0U;          -- DBFED shadow mode
       EPwm2Regs.DBCTL.bit.LOADREDMODE          = 4U;        -- DBRED load
       EPwm2Regs.DBCTL.bit.LOADFEDMODE          = 4U;        -- DBFED load
     */
    EPwm2Regs.DBCTL.all = (EPwm2Regs.DBCTL.all & ~0x8FFFU) | 0xBU;
    EPwm2Regs.DBRED.bit.DBRED = (uint16_T)(50.0);
                         // Dead-Band Generator Rising Edge Delay Count Register
    EPwm2Regs.DBFED.bit.DBFED = (uint16_T)(50.0);
                        // Dead-Band Generator Falling Edge Delay Count Register

    /*-- Setup Event-Trigger (ET) Submodule --*/
    /*	-- Event Trigger Selection and Pre-Scale Register
       EPwm2Regs.ETSEL.bit.SOCAEN               = 1U;          -- Start of Conversion A Enable
       EPwm2Regs.ETSEL.bit.SOCASELCMP           = 0U;
       EPwm2Regs.ETSEL.bit.SOCASEL              = 2U;          -- Start of Conversion A Select
       EPwm2Regs.ETPS.bit.SOCPSSEL              = 1U;          -- EPWM2SOC Period Select
       EPwm2Regs.ETSOCPS.bit.SOCAPRD2           = 1U;
       EPwm2Regs.ETSEL.bit.SOCBEN               = 0U;          -- Start of Conversion B Enable
       EPwm2Regs.ETSEL.bit.SOCBSELCMP           = 0U;
       EPwm2Regs.ETSEL.bit.SOCBSEL              = 1U;          -- Start of Conversion A Select
       EPwm2Regs.ETPS.bit.SOCPSSEL              = 1;          -- EPWM2SOCB Period Select
       EPwm2Regs.ETSOCPS.bit.SOCBPRD2           = 1U;
       EPwm2Regs.ETSEL.bit.INTEN                = 0U;          -- EPWM2INTn Enable
       EPwm2Regs.ETSEL.bit.INTSELCMP            = 0U;
       EPwm2Regs.ETSEL.bit.INTSEL               = 1U;          -- Start of Conversion A Select
       EPwm2Regs.ETPS.bit.INTPSSEL              = 1U;          // EPWM2INTn Period Select
       EPwm2Regs.ETINTPS.bit.INTPRD2            = 1U;
     */
    EPwm2Regs.ETSEL.all = (EPwm2Regs.ETSEL.all & ~0xFF7FU) | 0x1A01U;
    EPwm2Regs.ETPS.all = (EPwm2Regs.ETPS.all & ~0x30U) | 0x30U;
    EPwm2Regs.ETSOCPS.all = (EPwm2Regs.ETSOCPS.all & ~0xF0FU) | 0x101U;
    EPwm2Regs.ETINTPS.all = (EPwm2Regs.ETINTPS.all & ~0xFU) | 0x1U;

    /*-- Setup PWM-Chopper (PC) Submodule --*/
    /*	-- PWM Chopper Control Register
       EPwm2Regs.PCCTL.bit.CHPEN                = 0U;          -- PWM chopping enable
       EPwm2Regs.PCCTL.bit.CHPFREQ              = 0U;          -- Chopping clock frequency
       EPwm2Regs.PCCTL.bit.OSHTWTH              = 0U;          -- One-shot pulse width
       EPwm2Regs.PCCTL.bit.CHPDUTY              = 0U;          -- Chopping clock Duty cycle
     */
    EPwm2Regs.PCCTL.all = (EPwm2Regs.PCCTL.all & ~0x7FFU) | 0x0U;

    /*-- Set up Trip-Zone (TZ) Submodule --*/
    EALLOW;
    EPwm2Regs.TZSEL.all = 0U;          // Trip Zone Select Register

    /*-- Set CBCPULSE for CBC latch Clear --*/
    EPwm2Regs.TZCLR.bit.CBCPULSE = 0U;

    /*	-- Trip Zone Control Register
       EPwm2Regs.TZCTL.bit.TZA                  = 3U;          -- TZ1 to TZ6 Trip Action On EPWM2A
       EPwm2Regs.TZCTL.bit.TZB                  = 3U;          -- TZ1 to TZ6 Trip Action On EPWM2B
       EPwm2Regs.TZCTL.bit.DCAEVT1              = 3U;          -- EPWM2A action on DCAEVT1
       EPwm2Regs.TZCTL.bit.DCAEVT2              = 3U;          -- EPWM2A action on DCAEVT2
       EPwm2Regs.TZCTL.bit.DCBEVT1              = 3U;          -- EPWM2B action on DCBEVT1
       EPwm2Regs.TZCTL.bit.DCBEVT2              = 3U;          -- EPWM2B action on DCBEVT2
     */
    EPwm2Regs.TZCTL.all = (EPwm2Regs.TZCTL.all & ~0xFFFU) | 0xFFFU;

    /*	-- Trip Zone Enable Interrupt Register
       EPwm2Regs.TZEINT.bit.OST                 = 0U;          -- Trip Zones One Shot Int Enable
       EPwm2Regs.TZEINT.bit.CBC                 = 0U;          -- Trip Zones Cycle By Cycle Int Enable
       EPwm2Regs.TZEINT.bit.DCAEVT1             = 0U;          -- Digital Compare A Event 1 Int Enable
       EPwm2Regs.TZEINT.bit.DCAEVT2             = 0U;          -- Digital Compare A Event 2 Int Enable
       EPwm2Regs.TZEINT.bit.DCBEVT1             = 0U;          -- Digital Compare B Event 1 Int Enable
       EPwm2Regs.TZEINT.bit.DCBEVT2             = 0U;          -- Digital Compare B Event 2 Int Enable
     */
    EPwm2Regs.TZEINT.all = (EPwm2Regs.TZEINT.all & ~0x7EU) | 0x0U;

    /*	-- Digital Compare A Control Register
       EPwm2Regs.DCACTL.bit.EVT1SYNCE           = 0U;          -- DCAEVT1 SYNC Enable
       EPwm2Regs.DCACTL.bit.EVT1SOCE            = 1U;          -- DCAEVT1 SOC Enable
       EPwm2Regs.DCACTL.bit.EVT1FRCSYNCSEL      = 0U;          -- DCAEVT1 Force Sync Signal
       EPwm2Regs.DCACTL.bit.EVT1SRCSEL          = 0U;          -- DCAEVT1 Source Signal
       EPwm2Regs.DCACTL.bit.EVT2FRCSYNCSEL      = 0U;          -- DCAEVT2 Force Sync Signal
       EPwm2Regs.DCACTL.bit.EVT2SRCSEL          = 0U;          -- DCAEVT2 Source Signal
     */
    EPwm2Regs.DCACTL.all = (EPwm2Regs.DCACTL.all & ~0x30FU) | 0x4U;

    /*	-- Digital Compare B Control Register
       EPwm2Regs.DCBCTL.bit.EVT1SYNCE           = 0U;          -- DCBEVT1 SYNC Enable
       EPwm2Regs.DCBCTL.bit.EVT1SOCE            = 0U;          -- DCBEVT1 SOC Enable
       EPwm2Regs.DCBCTL.bit.EVT1FRCSYNCSEL      = 0U;          -- DCBEVT1 Force Sync Signal
       EPwm2Regs.DCBCTL.bit.EVT1SRCSEL          = 0U;          -- DCBEVT1 Source Signal
       EPwm2Regs.DCBCTL.bit.EVT2FRCSYNCSEL      = 0U;          -- DCBEVT2 Force Sync Signal
       EPwm2Regs.DCBCTL.bit.EVT2SRCSEL          = 0U;          -- DCBEVT2 Source Signal
     */
    EPwm2Regs.DCBCTL.all = (EPwm2Regs.DCBCTL.all & ~0x30FU) | 0x0U;

    /*	-- Digital Compare Trip Select Register
       EPwm2Regs.DCTRIPSEL.bit.DCAHCOMPSEL      = 0U;          -- Digital Compare A High COMP Input Select

       EPwm2Regs.DCTRIPSEL.bit.DCALCOMPSEL      = 0U;          -- Digital Compare A Low COMP Input Select
       EPwm2Regs.DCTRIPSEL.bit.DCBHCOMPSEL      = 0U;          -- Digital Compare B High COMP Input Select
       EPwm2Regs.DCTRIPSEL.bit.DCBLCOMPSEL      = 0U;          -- Digital Compare B Low COMP Input Select
     */
    EPwm2Regs.DCTRIPSEL.all = (EPwm2Regs.DCTRIPSEL.all & ~ 0xFFFFU) | 0x0U;

    /*	-- Trip Zone Digital Comparator Select Register
       EPwm2Regs.TZDCSEL.bit.DCAEVT1            = 0U;          -- Digital Compare Output A Event 1
       EPwm2Regs.TZDCSEL.bit.DCAEVT2            = 0U;          -- Digital Compare Output A Event 2
       EPwm2Regs.TZDCSEL.bit.DCBEVT1            = 0U;          -- Digital Compare Output B Event 1
       EPwm2Regs.TZDCSEL.bit.DCBEVT2            = 0U;          -- Digital Compare Output B Event 2
     */
    EPwm2Regs.TZDCSEL.all = (EPwm2Regs.TZDCSEL.all & ~0xFFFU) | 0x0U;

    /*	-- Digital Compare Filter Control Register
       EPwm2Regs.DCFCTL.bit.BLANKE              = 0U;          -- Blanking Enable/Disable
       EPwm2Regs.DCFCTL.bit.PULSESEL            = 1U;          -- Pulse Select for Blanking & Capture Alignment
       EPwm2Regs.DCFCTL.bit.BLANKINV            = 0U;          -- Blanking Window Inversion
       EPwm2Regs.DCFCTL.bit.SRCSEL              = 0U;          -- Filter Block Signal Source Select
     */
    EPwm2Regs.DCFCTL.all = (EPwm2Regs.DCFCTL.all & ~0x3FU) | 0x10U;
    EPwm2Regs.DCFOFFSET = 0U;          // Digital Compare Filter Offset Register
    EPwm2Regs.DCFWINDOW = 0U;          // Digital Compare Filter Window Register

    /*	-- Digital Compare Capture Control Register
       EPwm2Regs.DCCAPCTL.bit.CAPE              = 0U;          -- Counter Capture Enable
     */
    EPwm2Regs.DCCAPCTL.all = (EPwm2Regs.DCCAPCTL.all & ~0x1U) | 0x0U;

    /*	-- HRPWM Configuration Register
       EPwm2Regs.HRCNFG.bit.SWAPAB              = 0U;          -- Swap EPWMA and EPWMB Outputs Bit
       EPwm2Regs.HRCNFG.bit.SELOUTB             = 0U;          -- EPWMB Output Selection Bit
     */
    EPwm2Regs.HRCNFG.all = (EPwm2Regs.HRCNFG.all & ~0xA0U) | 0x0U;

    /* Update the Link Registers with the link value for all the Compare values and TBPRD */
    /* No error is thrown if the ePWM register exists in the model or not */
    EPwm2Regs.EPWMXLINK.bit.TBPRDLINK = 1U;
    EPwm2Regs.EPWMXLINK.bit.CMPALINK = 1U;
    EPwm2Regs.EPWMXLINK.bit.CMPBLINK = 1U;
    EPwm2Regs.EPWMXLINK.bit.CMPCLINK = 1U;
    EPwm2Regs.EPWMXLINK.bit.CMPDLINK = 1U;

    /* SYNCPER - Peripheral synchronization output event
       EPwm2Regs.HRPCTL.bit.PWMSYNCSEL            = 0U;          -- EPWMSYNCPER selection
       EPwm2Regs.HRPCTL.bit.PWMSYNCSELX           = 0U;          --  EPWMSYNCPER selection
     */
    EPwm2Regs.HRPCTL.all = (EPwm2Regs.HRPCTL.all & ~0x72U) | 0x0U;
    EDIS;
  }

  /* Start for S-Function (c2802xpwm): '<S1>/ePWM7' */
  real32_T tbprdValue7 = (real32_T)EPwm7Regs.TBPRD;

  /*** Initialize ePWM7 modules ***/
  {
    /*  -- Time Base Control Register
       EPwm7Regs.TBCTL.bit.CTRMODE              = 2U;          -- Counter Mode

       EPwm7Regs.TBCTL.bit.PRDLD                = 0U;          -- Shadow select

       EPwm7Regs.TBCTL2.bit.PRDLDSYNC           = 0U;          -- Shadow select

       EPwm7Regs.TBCTL.bit.PHSEN                = 1U;          -- Phase Load Enable
       EPwm7Regs.TBCTL.bit.PHSDIR               = 1U;          -- Phase Direction Bit
       EPwm7Regs.TBCTL.bit.HSPCLKDIV            = 0U;          -- High Speed TBCLK Pre-scaler
       EPwm7Regs.TBCTL.bit.CLKDIV               = 0U;          -- Time Base Clock Pre-scaler
     */
    EPwm7Regs.TBCTL.all = (EPwm7Regs.TBCTL.all & ~0x3FCFU) | 0x2006U;
    EPwm7Regs.TBCTL2.all = (EPwm7Regs.TBCTL2.all & ~0xC000U) | 0x0U;

    /* -- Time-Base EPWMxSYNCOUT Source Enable Register
     */
    EPwm7Regs.EPWMSYNCOUTEN.bit.SWEN = 0U;// disable the SWEN enabled during reset
    EPwm7Regs.EPWMSYNCOUTEN.all = (EPwm7Regs.EPWMSYNCOUTEN.all & ~0x0U) | 0x0U;

    /*-- Setup Time-Base (TB) Submodule --*/
    EPwm7Regs.TBPRD = 2500U;           // Time Base Period Register

    /* -- Time-Base Phase Register
       EPwm7Regs.TBPHS.bit.TBPHS               = 2500U;          -- Phase offset register
     */
    EPwm7Regs.TBPHS.all = (EPwm7Regs.TBPHS.all & ~0xFFFF0000U) | 0x9C40000U;

    // Time Base Counter Register
    EPwm7Regs.TBCTR = 0x0000U;         /* Clear counter*/

    /*-- Setup Counter_Compare (CC) Submodule --*/
    /*	-- Counter Compare Control Register

       EPwm7Regs.CMPCTL.bit.LOADASYNC           = 0U;          -- Active Compare A Load SYNC Option
       EPwm7Regs.CMPCTL.bit.LOADBSYNC           = 0U;          -- Active Compare B Load SYNC Option
       EPwm7Regs.CMPCTL.bit.LOADAMODE           = 0U;          -- Active Compare A Load
       EPwm7Regs.CMPCTL.bit.LOADBMODE           = 0U;          -- Active Compare B Load
       EPwm7Regs.CMPCTL.bit.SHDWAMODE           = 0U;          -- Compare A Register Block Operating Mode
       EPwm7Regs.CMPCTL.bit.SHDWBMODE           = 0U;          -- Compare B Register Block Operating Mode
     */
    EPwm7Regs.CMPCTL.all = (EPwm7Regs.CMPCTL.all & ~0x3C5FU) | 0x0U;

    /* EPwm7Regs.CMPCTL2.bit.SHDWCMODE           = 0U;          -- Compare C Register Block Operating Mode
       EPwm7Regs.CMPCTL2.bit.SHDWDMODE           = 0U;          -- Compare D Register Block Operating Mode
       EPwm7Regs.CMPCTL2.bit.LOADCSYNC           = 0U;          -- Active Compare C Load SYNC Option
       EPwm7Regs.CMPCTL2.bit.LOADDSYNC           = 0U;          -- Active Compare D Load SYNC Option
       EPwm7Regs.CMPCTL2.bit.LOADCMODE           = 0U;          -- Active Compare C Load
       EPwm7Regs.CMPCTL2.bit.LOADDMODE           = 0U;          -- Active Compare D Load
     */
    EPwm7Regs.CMPCTL2.all = (EPwm7Regs.CMPCTL2.all & ~0x3C5FU) | 0x0U;
    EPwm7Regs.CMPA.bit.CMPA = 1250U;   // Counter Compare A Register
    EPwm7Regs.CMPB.bit.CMPB = 32000U;  // Counter Compare B Register
    EPwm7Regs.CMPC = 32000U;           // Counter Compare C Register
    EPwm7Regs.CMPD = 32000U;           // Counter Compare D Register

    /*-- Setup Action-Qualifier (AQ) Submodule --*/
    EPwm7Regs.AQCTLA.all = 146U;
                               // Action Qualifier Control Register For Output A
    EPwm7Regs.AQCTLB.all = 2310U;
                               // Action Qualifier Control Register For Output B

    /*	-- Action Qualifier Software Force Register
       EPwm7Regs.AQSFRC.bit.RLDCSF              = 0U;          -- Reload from Shadow Options
     */
    EPwm7Regs.AQSFRC.all = (EPwm7Regs.AQSFRC.all & ~0xC0U) | 0x0U;

    /*	-- Action Qualifier Continuous S/W Force Register
       EPwm7Regs.AQCSFRC.bit.CSFA               = 0U;          -- Continuous Software Force on output A
       EPwm7Regs.AQCSFRC.bit.CSFB               = 0U;          -- Continuous Software Force on output B
     */
    EPwm7Regs.AQCSFRC.all = (EPwm7Regs.AQCSFRC.all & ~0xFU) | 0x0U;

    /*-- Setup Dead-Band Generator (DB) Submodule --*/
    /*	-- Dead-Band Generator Control Register
       EPwm7Regs.DBCTL.bit.OUT_MODE             = 3U;          -- Dead Band Output Mode Control
       EPwm7Regs.DBCTL.bit.IN_MODE              = 0U;          -- Dead Band Input Select Mode Control
       EPwm7Regs.DBCTL.bit.POLSEL               = 2U;          -- Polarity Select Control
       EPwm7Regs.DBCTL.bit.HALFCYCLE            = 0U;          -- Half Cycle Clocking Enable
       EPwm7Regs.DBCTL.bit.SHDWDBREDMODE        = 0U;          -- DBRED shadow mode
       EPwm7Regs.DBCTL.bit.SHDWDBFEDMODE        = 0U;          -- DBFED shadow mode
       EPwm7Regs.DBCTL.bit.LOADREDMODE          = 4U;        -- DBRED load
       EPwm7Regs.DBCTL.bit.LOADFEDMODE          = 4U;        -- DBFED load
     */
    EPwm7Regs.DBCTL.all = (EPwm7Regs.DBCTL.all & ~0x8FFFU) | 0xBU;
    EPwm7Regs.DBRED.bit.DBRED = (uint16_T)(50.0);
                         // Dead-Band Generator Rising Edge Delay Count Register
    EPwm7Regs.DBFED.bit.DBFED = (uint16_T)(50.0);
                        // Dead-Band Generator Falling Edge Delay Count Register

    /*-- Setup Event-Trigger (ET) Submodule --*/
    /*	-- Event Trigger Selection and Pre-Scale Register
       EPwm7Regs.ETSEL.bit.SOCAEN               = 1U;          -- Start of Conversion A Enable
       EPwm7Regs.ETSEL.bit.SOCASELCMP           = 0U;
       EPwm7Regs.ETSEL.bit.SOCASEL              = 2U;          -- Start of Conversion A Select
       EPwm7Regs.ETPS.bit.SOCPSSEL              = 1U;          -- EPWM7SOC Period Select
       EPwm7Regs.ETSOCPS.bit.SOCAPRD2           = 1U;
       EPwm7Regs.ETSEL.bit.SOCBEN               = 0U;          -- Start of Conversion B Enable
       EPwm7Regs.ETSEL.bit.SOCBSELCMP           = 0U;
       EPwm7Regs.ETSEL.bit.SOCBSEL              = 1U;          -- Start of Conversion A Select
       EPwm7Regs.ETPS.bit.SOCPSSEL              = 1;          -- EPWM7SOCB Period Select
       EPwm7Regs.ETSOCPS.bit.SOCBPRD2           = 1U;
       EPwm7Regs.ETSEL.bit.INTEN                = 0U;          -- EPWM7INTn Enable
       EPwm7Regs.ETSEL.bit.INTSELCMP            = 0U;
       EPwm7Regs.ETSEL.bit.INTSEL               = 1U;          -- Start of Conversion A Select
       EPwm7Regs.ETPS.bit.INTPSSEL              = 1U;          // EPWM7INTn Period Select
       EPwm7Regs.ETINTPS.bit.INTPRD2            = 1U;
     */
    EPwm7Regs.ETSEL.all = (EPwm7Regs.ETSEL.all & ~0xFF7FU) | 0x1A01U;
    EPwm7Regs.ETPS.all = (EPwm7Regs.ETPS.all & ~0x30U) | 0x30U;
    EPwm7Regs.ETSOCPS.all = (EPwm7Regs.ETSOCPS.all & ~0xF0FU) | 0x101U;
    EPwm7Regs.ETINTPS.all = (EPwm7Regs.ETINTPS.all & ~0xFU) | 0x1U;

    /*-- Setup PWM-Chopper (PC) Submodule --*/
    /*	-- PWM Chopper Control Register
       EPwm7Regs.PCCTL.bit.CHPEN                = 0U;          -- PWM chopping enable
       EPwm7Regs.PCCTL.bit.CHPFREQ              = 0U;          -- Chopping clock frequency
       EPwm7Regs.PCCTL.bit.OSHTWTH              = 0U;          -- One-shot pulse width
       EPwm7Regs.PCCTL.bit.CHPDUTY              = 0U;          -- Chopping clock Duty cycle
     */
    EPwm7Regs.PCCTL.all = (EPwm7Regs.PCCTL.all & ~0x7FFU) | 0x0U;

    /*-- Set up Trip-Zone (TZ) Submodule --*/
    EALLOW;
    EPwm7Regs.TZSEL.all = 0U;          // Trip Zone Select Register

    /*-- Set CBCPULSE for CBC latch Clear --*/
    EPwm7Regs.TZCLR.bit.CBCPULSE = 0U;

    /*	-- Trip Zone Control Register
       EPwm7Regs.TZCTL.bit.TZA                  = 3U;          -- TZ1 to TZ6 Trip Action On EPWM7A
       EPwm7Regs.TZCTL.bit.TZB                  = 3U;          -- TZ1 to TZ6 Trip Action On EPWM7B
       EPwm7Regs.TZCTL.bit.DCAEVT1              = 3U;          -- EPWM7A action on DCAEVT1
       EPwm7Regs.TZCTL.bit.DCAEVT2              = 3U;          -- EPWM7A action on DCAEVT2
       EPwm7Regs.TZCTL.bit.DCBEVT1              = 3U;          -- EPWM7B action on DCBEVT1
       EPwm7Regs.TZCTL.bit.DCBEVT2              = 3U;          -- EPWM7B action on DCBEVT2
     */
    EPwm7Regs.TZCTL.all = (EPwm7Regs.TZCTL.all & ~0xFFFU) | 0xFFFU;

    /*	-- Trip Zone Enable Interrupt Register
       EPwm7Regs.TZEINT.bit.OST                 = 0U;          -- Trip Zones One Shot Int Enable
       EPwm7Regs.TZEINT.bit.CBC                 = 0U;          -- Trip Zones Cycle By Cycle Int Enable
       EPwm7Regs.TZEINT.bit.DCAEVT1             = 0U;          -- Digital Compare A Event 1 Int Enable
       EPwm7Regs.TZEINT.bit.DCAEVT2             = 0U;          -- Digital Compare A Event 2 Int Enable
       EPwm7Regs.TZEINT.bit.DCBEVT1             = 0U;          -- Digital Compare B Event 1 Int Enable
       EPwm7Regs.TZEINT.bit.DCBEVT2             = 0U;          -- Digital Compare B Event 2 Int Enable
     */
    EPwm7Regs.TZEINT.all = (EPwm7Regs.TZEINT.all & ~0x7EU) | 0x0U;

    /*	-- Digital Compare A Control Register
       EPwm7Regs.DCACTL.bit.EVT1SYNCE           = 0U;          -- DCAEVT1 SYNC Enable
       EPwm7Regs.DCACTL.bit.EVT1SOCE            = 1U;          -- DCAEVT1 SOC Enable
       EPwm7Regs.DCACTL.bit.EVT1FRCSYNCSEL      = 0U;          -- DCAEVT1 Force Sync Signal
       EPwm7Regs.DCACTL.bit.EVT1SRCSEL          = 0U;          -- DCAEVT1 Source Signal
       EPwm7Regs.DCACTL.bit.EVT2FRCSYNCSEL      = 0U;          -- DCAEVT2 Force Sync Signal
       EPwm7Regs.DCACTL.bit.EVT2SRCSEL          = 0U;          -- DCAEVT2 Source Signal
     */
    EPwm7Regs.DCACTL.all = (EPwm7Regs.DCACTL.all & ~0x30FU) | 0x4U;

    /*	-- Digital Compare B Control Register
       EPwm7Regs.DCBCTL.bit.EVT1SYNCE           = 0U;          -- DCBEVT1 SYNC Enable
       EPwm7Regs.DCBCTL.bit.EVT1SOCE            = 0U;          -- DCBEVT1 SOC Enable
       EPwm7Regs.DCBCTL.bit.EVT1FRCSYNCSEL      = 0U;          -- DCBEVT1 Force Sync Signal
       EPwm7Regs.DCBCTL.bit.EVT1SRCSEL          = 0U;          -- DCBEVT1 Source Signal
       EPwm7Regs.DCBCTL.bit.EVT2FRCSYNCSEL      = 0U;          -- DCBEVT2 Force Sync Signal
       EPwm7Regs.DCBCTL.bit.EVT2SRCSEL          = 0U;          -- DCBEVT2 Source Signal
     */
    EPwm7Regs.DCBCTL.all = (EPwm7Regs.DCBCTL.all & ~0x30FU) | 0x0U;

    /*	-- Digital Compare Trip Select Register
       EPwm7Regs.DCTRIPSEL.bit.DCAHCOMPSEL      = 0U;          -- Digital Compare A High COMP Input Select

       EPwm7Regs.DCTRIPSEL.bit.DCALCOMPSEL      = 0U;          -- Digital Compare A Low COMP Input Select
       EPwm7Regs.DCTRIPSEL.bit.DCBHCOMPSEL      = 0U;          -- Digital Compare B High COMP Input Select
       EPwm7Regs.DCTRIPSEL.bit.DCBLCOMPSEL      = 0U;          -- Digital Compare B Low COMP Input Select
     */
    EPwm7Regs.DCTRIPSEL.all = (EPwm7Regs.DCTRIPSEL.all & ~ 0xFFFFU) | 0x0U;

    /*	-- Trip Zone Digital Comparator Select Register
       EPwm7Regs.TZDCSEL.bit.DCAEVT1            = 0U;          -- Digital Compare Output A Event 1
       EPwm7Regs.TZDCSEL.bit.DCAEVT2            = 0U;          -- Digital Compare Output A Event 2
       EPwm7Regs.TZDCSEL.bit.DCBEVT1            = 0U;          -- Digital Compare Output B Event 1
       EPwm7Regs.TZDCSEL.bit.DCBEVT2            = 0U;          -- Digital Compare Output B Event 2
     */
    EPwm7Regs.TZDCSEL.all = (EPwm7Regs.TZDCSEL.all & ~0xFFFU) | 0x0U;

    /*	-- Digital Compare Filter Control Register
       EPwm7Regs.DCFCTL.bit.BLANKE              = 0U;          -- Blanking Enable/Disable
       EPwm7Regs.DCFCTL.bit.PULSESEL            = 1U;          -- Pulse Select for Blanking & Capture Alignment
       EPwm7Regs.DCFCTL.bit.BLANKINV            = 0U;          -- Blanking Window Inversion
       EPwm7Regs.DCFCTL.bit.SRCSEL              = 0U;          -- Filter Block Signal Source Select
     */
    EPwm7Regs.DCFCTL.all = (EPwm7Regs.DCFCTL.all & ~0x3FU) | 0x10U;
    EPwm7Regs.DCFOFFSET = 0U;          // Digital Compare Filter Offset Register
    EPwm7Regs.DCFWINDOW = 0U;          // Digital Compare Filter Window Register

    /*	-- Digital Compare Capture Control Register
       EPwm7Regs.DCCAPCTL.bit.CAPE              = 0U;          -- Counter Capture Enable
     */
    EPwm7Regs.DCCAPCTL.all = (EPwm7Regs.DCCAPCTL.all & ~0x1U) | 0x0U;

    /*	-- HRPWM Configuration Register
       EPwm7Regs.HRCNFG.bit.SWAPAB              = 0U;          -- Swap EPWMA and EPWMB Outputs Bit
       EPwm7Regs.HRCNFG.bit.SELOUTB             = 0U;          -- EPWMB Output Selection Bit
     */
    EPwm7Regs.HRCNFG.all = (EPwm7Regs.HRCNFG.all & ~0xA0U) | 0x0U;

    /* Update the Link Registers with the link value for all the Compare values and TBPRD */
    /* No error is thrown if the ePWM register exists in the model or not */
    EPwm7Regs.EPWMXLINK.bit.TBPRDLINK = 0U;
    EPwm7Regs.EPWMXLINK.bit.CMPALINK = 6U;
    EPwm7Regs.EPWMXLINK.bit.CMPBLINK = 6U;
    EPwm7Regs.EPWMXLINK.bit.CMPCLINK = 6U;
    EPwm7Regs.EPWMXLINK.bit.CMPDLINK = 6U;

    /* SYNCPER - Peripheral synchronization output event
       EPwm7Regs.HRPCTL.bit.PWMSYNCSEL            = 0U;          -- EPWMSYNCPER selection
       EPwm7Regs.HRPCTL.bit.PWMSYNCSELX           = 0U;          --  EPWMSYNCPER selection
     */
    EPwm7Regs.HRPCTL.all = (EPwm7Regs.HRPCTL.all & ~0x72U) | 0x0U;
    EDIS;
  }

  /* Start for DataStoreMemory: '<S1>/Data Store Memory' */
  enable = 1.0F;

  /* Start for DataStoreMemory: '<S1>/Data Store Memory1' */
  wc = 5000.0F;

  /* Start for DataStoreMemory: '<S1>/Data Store Memory2' */
  wo = 14000.0F;

  /* Start for DataStoreMemory: '<S1>/Data Store Memory3' */
  b0 = 20000.0F;

  /* InitializeConditions for DiscreteIntegrator: '<S45>/Integrator' */
  buck_ADRC_MBD_NPU_24b_DW.Integrator_DSTATE = 0.05;
  buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState = 2;

  /* InitializeConditions for DiscreteIntegrator: '<S207>/Integrator' */
  buck_ADRC_MBD_NPU_24b_DW.Integrator_DSTATE_l = 0.05;
  buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_i = 2;

  /* InitializeConditions for DiscreteIntegrator: '<S99>/Integrator' */
  buck_ADRC_MBD_NPU_24b_DW.Integrator_DSTATE_a = 0.05;
  buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_k = 2;

  /* InitializeConditions for DiscreteIntegrator: '<S153>/Integrator' */
  buck_ADRC_MBD_NPU_24b_DW.Integrator_DSTATE_p = 0.05;
  buck_ADRC_MBD_NPU_24b_DW.Integrator_PrevResetState_c = 2;

  /* Start for S-Function (c280xgpio_do): '<S1>/Digital Output' incorporates:
   *  Constant: '<Root>/Constant'
   */
  EALLOW;
  GpioCtrlRegs.GPAMUX2.all &= 0xFFFFCFFFU;
  GpioCtrlRegs.GPADIR.all |= 0x400000U;
  EDIS;

  /* SystemInitialize for MATLAB Function: '<S2>/MATLAB Function' */
  buck_ADRC_MBD_NPU_24b_DW.z1_not_empty = false;
  buck_ADRC_MBD_NPU_24b_DW.z2 = 0.0F;
  buck_ADRC_MBD_NPU_24b_DW.u_prev = 0.0F;

  /* Start for S-Function (c280xgpio_do): '<S1>/Digital Output1' incorporates:
   *  Constant: '<Root>/Constant1'
   */
  EALLOW;
  GpioCtrlRegs.GPAMUX2.all &= 0xFFFFCFFFU;
  GpioCtrlRegs.GPADIR.all |= 0x400000U;
  EDIS;

  /* End of SystemInitialize for S-Function (c28xisr_c2000): '<Root>/C28x Hardware Interrupt' */

  /* user code (Initialize function Body) */
  buck_npu_platform_init();
}

/* Model terminate function */
void buck_ADRC_MBD_NPU_24b_terminate(void)
{
  /* (no terminate code required) */
}

/*
 * File trailer for generated code.
 *
 * [EOF]
 */
