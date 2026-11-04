/*
 * File: buck_ADRC_MBD_NPU_24b.h
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

#ifndef buck_ADRC_MBD_NPU_24b_h_
#define buck_ADRC_MBD_NPU_24b_h_
#ifndef buck_ADRC_MBD_NPU_24b_COMMON_INCLUDES_
#define buck_ADRC_MBD_NPU_24b_COMMON_INCLUDES_
#include "rtwtypes.h"
#include "c2000BoardSupport.h"
#include "MW_f28p55x_includes.h"
#include "buck_npu.h"
#include "buck_npu_mbd_bridge.h"
#include "IQmathLib.h"
#endif                              /* buck_ADRC_MBD_NPU_24b_COMMON_INCLUDES_ */

#include "MW_c28xAnalogSubsystem.h"
#include "buck_ADRC_MBD_NPU_24b_types.h"
#include <stddef.h>
#include <string.h>
#include "rt_nonfinite.h"
#include "MW_target_hardware_resources.h"

/* Macros for accessing real-time model data structure */
#ifndef rtmGetErrorStatus
#define rtmGetErrorStatus(rtm)         ((rtm)->errorStatus)
#endif

#ifndef rtmSetErrorStatus
#define rtmSetErrorStatus(rtm, val)    ((rtm)->errorStatus = (val))
#endif

extern void config_ePWMSyncSource(void);
extern void config_ePWM_GPIO (void);
extern void config_ePWM_TBSync (void);
extern void config_ePWM_XBAR(void);
extern void initBoardEnd(void);

/* user code (top of header file) */
#include "buck_npu.h"
#include "buck_npu_platform.h"

/* Block signals (default storage) */
typedef struct {
  real32_T ADC5;                       /* '<S1>/ADC5' */
  real32_T ADC6;                       /* '<S1>/ADC6' */
  real32_T ADC3;                       /* '<S1>/ADC3' */
  real32_T ADC1;                       /* '<S1>/ADC1' */
  real32_T ADC7;                       /* '<S1>/ADC7' */
  real32_T ADC4;                       /* '<S1>/ADC4' */
} B_buck_ADRC_MBD_NPU_24b_T;

/* Block states (default storage) for system '<Root>' */
typedef struct {
  mwReal32_T Integrator_DSTATE;        /* '<S45>/Integrator' */
  mwReal32_T Integrator_DSTATE_l;      /* '<S207>/Integrator' */
  mwReal32_T Integrator_DSTATE_a;      /* '<S99>/Integrator' */
  mwReal32_T Integrator_DSTATE_p;      /* '<S153>/Integrator' */
  real32_T z1;                         /* '<S2>/MATLAB Function' */
  real32_T z2;                         /* '<S2>/MATLAB Function' */
  real32_T u_prev;                     /* '<S2>/MATLAB Function' */
  int32_T DigitalOutput2_FRAC_LEN;     /* '<S1>/Digital Output2' */
  int32_T DigitalOutput1_FRAC_LEN;     /* '<S1>/Digital Output1' */
  int32_T DigitalOutput_FRAC_LEN;      /* '<S1>/Digital Output' */
  int16_T Integrator_PrevResetState;   /* '<S45>/Integrator' */
  int16_T Integrator_PrevResetState_i; /* '<S207>/Integrator' */
  int16_T Integrator_PrevResetState_k; /* '<S99>/Integrator' */
  int16_T Integrator_PrevResetState_c; /* '<S153>/Integrator' */
  boolean_T z1_not_empty;              /* '<S2>/MATLAB Function' */
} DW_buck_ADRC_MBD_NPU_24b_T;

/* Real-time Model Data Structure */
struct tag_RTM_buck_ADRC_MBD_NPU_24b_T {
  const char_T * volatile errorStatus;
};

/* Block signals (default storage) */
extern B_buck_ADRC_MBD_NPU_24b_T buck_ADRC_MBD_NPU_24b_B;

/* Block states (default storage) */
extern DW_buck_ADRC_MBD_NPU_24b_T buck_ADRC_MBD_NPU_24b_DW;

/*
 * Exported Global Signals
 *
 * Note: Exported global signals are block signals with an exported global
 * storage class designation.  Code generation will declare the memory for
 * these signals and export their symbols.
 *
 */
extern mwReal32_T IL1;                 /* '<S1>/Divide' */
extern mwReal32_T IL2;                 /* '<S1>/Divide1' */
extern mwReal32_T IL3;                 /* '<S1>/Divide2' */
extern mwReal32_T IL4;                 /* '<S1>/Divide3' */
extern real32_T Vout;                  /* '<S1>/Gain13' */
extern real32_T Vin;                   /* '<S1>/Gain' */

/*
 * Exported States
 *
 * Note: Exported states are block states with an exported global
 * storage class designation.  Code generation will declare the memory for these
 * states and exports their symbols.
 *
 */
extern real32_T enable;                /* '<S1>/Data Store Memory' */
extern real32_T wc;                    /* '<S1>/Data Store Memory1' */
extern real32_T wo;                    /* '<S1>/Data Store Memory2' */
extern real32_T b0;                    /* '<S1>/Data Store Memory3' */
extern real32_T alpha;                 /* '<S1>/Data Store Memory4' */

/* Model entry point functions */
extern void buck_ADRC_MBD_NPU_24b_initialize(void);
extern void buck_ADRC_MBD_NPU_24b_terminate(void);
extern volatile boolean_T runModel;

/* Real-time Model object */
extern RT_MODEL_buck_ADRC_MBD_NPU_24_T *const buck_ADRC_MBD_NPU_24b_M;
void InitAdcA (void);
extern uint16_T MW_adcAInitFlag;
void config_ADCA_SOC0 (void);
void InitAdcC (void);
extern uint16_T MW_adcCInitFlag;
void config_ADCC_SOC1 (void);
void InitAdcB (void);
extern uint16_T MW_adcBInitFlag;
void config_ADCB_SOC0 (void);
void config_ADCB_SOC1 (void);
void config_ADCC_SOC0 (void);
void config_ADCA_SOC1 (void);
extern volatile boolean_T stopRequested;
extern volatile boolean_T runModel;

/*-
 * These blocks were eliminated from the model due to optimizations:
 *
 * Block '<S1>/Data Type Conversion1' : Eliminate redundant data type conversion
 * Block '<S1>/Data Type Conversion16' : Eliminate redundant data type conversion
 */

/*-
 * The generated code includes comments that allow you to trace directly
 * back to the appropriate location in the model.  The basic format
 * is <system>/block_name, where system is the system number (uniquely
 * assigned by Simulink) and block_name is the name of the block.
 *
 * Use the MATLAB hilite_system command to trace the generated code back
 * to the model.  For example,
 *
 * hilite_system('<S3>')    - opens system 3
 * hilite_system('<S3>/Kp') - opens and selects block Kp which resides in S3
 *
 * Here is the system hierarchy for this model
 *
 * '<Root>' : 'buck_ADRC_MBD_NPU_24b'
 * '<S1>'   : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem'
 * '<S2>'   : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环'
 * '<S3>'   : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/MATLAB Function'
 * '<S4>'   : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/NPU'
 * '<S5>'   : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2'
 * '<S6>'   : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3'
 * '<S7>'   : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4'
 * '<S8>'   : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5'
 * '<S9>'   : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Anti-windup'
 * '<S10>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/D Gain'
 * '<S11>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/External Derivative'
 * '<S12>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Filter'
 * '<S13>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Filter ICs'
 * '<S14>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/I Gain'
 * '<S15>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Ideal P Gain'
 * '<S16>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Ideal P Gain Fdbk'
 * '<S17>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Integrator'
 * '<S18>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Integrator ICs'
 * '<S19>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/N Copy'
 * '<S20>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/N Gain'
 * '<S21>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/P Copy'
 * '<S22>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Parallel P Gain'
 * '<S23>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Reset Signal'
 * '<S24>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Saturation'
 * '<S25>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Saturation Fdbk'
 * '<S26>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Sum'
 * '<S27>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Sum Fdbk'
 * '<S28>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Tracking Mode'
 * '<S29>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Tracking Mode Sum'
 * '<S30>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Tsamp - Integral'
 * '<S31>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Tsamp - Ngain'
 * '<S32>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/postSat Signal'
 * '<S33>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/preInt Signal'
 * '<S34>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/preSat Signal'
 * '<S35>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Anti-windup/Disc. Clamping Parallel'
 * '<S36>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Anti-windup/Disc. Clamping Parallel/Dead Zone'
 * '<S37>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Anti-windup/Disc. Clamping Parallel/Dead Zone/Enabled'
 * '<S38>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/D Gain/Disabled'
 * '<S39>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/External Derivative/Disabled'
 * '<S40>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Filter/Disabled'
 * '<S41>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Filter ICs/Disabled'
 * '<S42>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/I Gain/Internal Parameters'
 * '<S43>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Ideal P Gain/Passthrough'
 * '<S44>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Ideal P Gain Fdbk/Disabled'
 * '<S45>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Integrator/Discrete'
 * '<S46>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Integrator ICs/Internal IC'
 * '<S47>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/N Copy/Disabled wSignal Specification'
 * '<S48>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/N Gain/Disabled'
 * '<S49>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/P Copy/Disabled'
 * '<S50>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Parallel P Gain/Internal Parameters'
 * '<S51>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Reset Signal/External Reset'
 * '<S52>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Saturation/Enabled'
 * '<S53>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Saturation Fdbk/Disabled'
 * '<S54>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Sum/Sum_PI'
 * '<S55>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Sum Fdbk/Disabled'
 * '<S56>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Tracking Mode/Disabled'
 * '<S57>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Tracking Mode Sum/Passthrough'
 * '<S58>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Tsamp - Integral/TsSignalSpecification'
 * '<S59>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/Tsamp - Ngain/Passthrough'
 * '<S60>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/postSat Signal/Forward_Path'
 * '<S61>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/preInt Signal/Internal PreInt'
 * '<S62>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller2/preSat Signal/Forward_Path'
 * '<S63>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Anti-windup'
 * '<S64>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/D Gain'
 * '<S65>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/External Derivative'
 * '<S66>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Filter'
 * '<S67>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Filter ICs'
 * '<S68>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/I Gain'
 * '<S69>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Ideal P Gain'
 * '<S70>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Ideal P Gain Fdbk'
 * '<S71>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Integrator'
 * '<S72>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Integrator ICs'
 * '<S73>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/N Copy'
 * '<S74>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/N Gain'
 * '<S75>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/P Copy'
 * '<S76>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Parallel P Gain'
 * '<S77>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Reset Signal'
 * '<S78>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Saturation'
 * '<S79>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Saturation Fdbk'
 * '<S80>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Sum'
 * '<S81>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Sum Fdbk'
 * '<S82>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Tracking Mode'
 * '<S83>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Tracking Mode Sum'
 * '<S84>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Tsamp - Integral'
 * '<S85>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Tsamp - Ngain'
 * '<S86>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/postSat Signal'
 * '<S87>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/preInt Signal'
 * '<S88>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/preSat Signal'
 * '<S89>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Anti-windup/Disc. Clamping Parallel'
 * '<S90>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Anti-windup/Disc. Clamping Parallel/Dead Zone'
 * '<S91>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Anti-windup/Disc. Clamping Parallel/Dead Zone/Enabled'
 * '<S92>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/D Gain/Disabled'
 * '<S93>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/External Derivative/Disabled'
 * '<S94>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Filter/Disabled'
 * '<S95>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Filter ICs/Disabled'
 * '<S96>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/I Gain/Internal Parameters'
 * '<S97>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Ideal P Gain/Passthrough'
 * '<S98>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Ideal P Gain Fdbk/Disabled'
 * '<S99>'  : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Integrator/Discrete'
 * '<S100>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Integrator ICs/Internal IC'
 * '<S101>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/N Copy/Disabled wSignal Specification'
 * '<S102>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/N Gain/Disabled'
 * '<S103>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/P Copy/Disabled'
 * '<S104>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Parallel P Gain/Internal Parameters'
 * '<S105>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Reset Signal/External Reset'
 * '<S106>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Saturation/Enabled'
 * '<S107>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Saturation Fdbk/Disabled'
 * '<S108>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Sum/Sum_PI'
 * '<S109>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Sum Fdbk/Disabled'
 * '<S110>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Tracking Mode/Disabled'
 * '<S111>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Tracking Mode Sum/Passthrough'
 * '<S112>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Tsamp - Integral/TsSignalSpecification'
 * '<S113>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/Tsamp - Ngain/Passthrough'
 * '<S114>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/postSat Signal/Forward_Path'
 * '<S115>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/preInt Signal/Internal PreInt'
 * '<S116>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller3/preSat Signal/Forward_Path'
 * '<S117>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Anti-windup'
 * '<S118>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/D Gain'
 * '<S119>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/External Derivative'
 * '<S120>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Filter'
 * '<S121>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Filter ICs'
 * '<S122>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/I Gain'
 * '<S123>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Ideal P Gain'
 * '<S124>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Ideal P Gain Fdbk'
 * '<S125>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Integrator'
 * '<S126>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Integrator ICs'
 * '<S127>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/N Copy'
 * '<S128>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/N Gain'
 * '<S129>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/P Copy'
 * '<S130>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Parallel P Gain'
 * '<S131>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Reset Signal'
 * '<S132>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Saturation'
 * '<S133>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Saturation Fdbk'
 * '<S134>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Sum'
 * '<S135>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Sum Fdbk'
 * '<S136>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Tracking Mode'
 * '<S137>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Tracking Mode Sum'
 * '<S138>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Tsamp - Integral'
 * '<S139>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Tsamp - Ngain'
 * '<S140>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/postSat Signal'
 * '<S141>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/preInt Signal'
 * '<S142>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/preSat Signal'
 * '<S143>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Anti-windup/Disc. Clamping Parallel'
 * '<S144>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Anti-windup/Disc. Clamping Parallel/Dead Zone'
 * '<S145>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Anti-windup/Disc. Clamping Parallel/Dead Zone/Enabled'
 * '<S146>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/D Gain/Disabled'
 * '<S147>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/External Derivative/Disabled'
 * '<S148>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Filter/Disabled'
 * '<S149>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Filter ICs/Disabled'
 * '<S150>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/I Gain/Internal Parameters'
 * '<S151>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Ideal P Gain/Passthrough'
 * '<S152>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Ideal P Gain Fdbk/Disabled'
 * '<S153>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Integrator/Discrete'
 * '<S154>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Integrator ICs/Internal IC'
 * '<S155>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/N Copy/Disabled wSignal Specification'
 * '<S156>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/N Gain/Disabled'
 * '<S157>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/P Copy/Disabled'
 * '<S158>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Parallel P Gain/Internal Parameters'
 * '<S159>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Reset Signal/External Reset'
 * '<S160>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Saturation/Enabled'
 * '<S161>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Saturation Fdbk/Disabled'
 * '<S162>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Sum/Sum_PI'
 * '<S163>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Sum Fdbk/Disabled'
 * '<S164>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Tracking Mode/Disabled'
 * '<S165>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Tracking Mode Sum/Passthrough'
 * '<S166>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Tsamp - Integral/TsSignalSpecification'
 * '<S167>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/Tsamp - Ngain/Passthrough'
 * '<S168>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/postSat Signal/Forward_Path'
 * '<S169>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/preInt Signal/Internal PreInt'
 * '<S170>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller4/preSat Signal/Forward_Path'
 * '<S171>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Anti-windup'
 * '<S172>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/D Gain'
 * '<S173>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/External Derivative'
 * '<S174>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Filter'
 * '<S175>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Filter ICs'
 * '<S176>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/I Gain'
 * '<S177>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Ideal P Gain'
 * '<S178>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Ideal P Gain Fdbk'
 * '<S179>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Integrator'
 * '<S180>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Integrator ICs'
 * '<S181>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/N Copy'
 * '<S182>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/N Gain'
 * '<S183>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/P Copy'
 * '<S184>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Parallel P Gain'
 * '<S185>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Reset Signal'
 * '<S186>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Saturation'
 * '<S187>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Saturation Fdbk'
 * '<S188>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Sum'
 * '<S189>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Sum Fdbk'
 * '<S190>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Tracking Mode'
 * '<S191>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Tracking Mode Sum'
 * '<S192>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Tsamp - Integral'
 * '<S193>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Tsamp - Ngain'
 * '<S194>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/postSat Signal'
 * '<S195>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/preInt Signal'
 * '<S196>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/preSat Signal'
 * '<S197>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Anti-windup/Disc. Clamping Parallel'
 * '<S198>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Anti-windup/Disc. Clamping Parallel/Dead Zone'
 * '<S199>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Anti-windup/Disc. Clamping Parallel/Dead Zone/Enabled'
 * '<S200>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/D Gain/Disabled'
 * '<S201>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/External Derivative/Disabled'
 * '<S202>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Filter/Disabled'
 * '<S203>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Filter ICs/Disabled'
 * '<S204>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/I Gain/Internal Parameters'
 * '<S205>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Ideal P Gain/Passthrough'
 * '<S206>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Ideal P Gain Fdbk/Disabled'
 * '<S207>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Integrator/Discrete'
 * '<S208>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Integrator ICs/Internal IC'
 * '<S209>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/N Copy/Disabled wSignal Specification'
 * '<S210>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/N Gain/Disabled'
 * '<S211>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/P Copy/Disabled'
 * '<S212>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Parallel P Gain/Internal Parameters'
 * '<S213>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Reset Signal/External Reset'
 * '<S214>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Saturation/Enabled'
 * '<S215>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Saturation Fdbk/Disabled'
 * '<S216>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Sum/Sum_PI'
 * '<S217>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Sum Fdbk/Disabled'
 * '<S218>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Tracking Mode/Disabled'
 * '<S219>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Tracking Mode Sum/Passthrough'
 * '<S220>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Tsamp - Integral/TsSignalSpecification'
 * '<S221>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/Tsamp - Ngain/Passthrough'
 * '<S222>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/postSat Signal/Forward_Path'
 * '<S223>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/preInt Signal/Internal PreInt'
 * '<S224>' : 'buck_ADRC_MBD_NPU_24b/Function-Call Subsystem/闭环/PID Controller5/preSat Signal/Forward_Path'
 */
#endif                                 /* buck_ADRC_MBD_NPU_24b_h_ */

/*
 * File trailer for generated code.
 *
 * [EOF]
 */
