#ifndef ai700_w202_acc_h_
#define ai700_w202_acc_h_
#ifndef ai700_w202_acc_COMMON_INCLUDES_
#define ai700_w202_acc_COMMON_INCLUDES_
#include <stdlib.h>
#define S_FUNCTION_NAME simulink_only_sfcn
#define S_FUNCTION_LEVEL 2
#ifndef RTW_GENERATED_S_FUNCTION
#define RTW_GENERATED_S_FUNCTION
#endif
#include "sl_AsyncioQueue/AsyncioQueueCAPI.h"
#include "rtwtypes.h"
#include "simstruc.h"
#include "fixedpoint.h"
#include "rt_nonfinite.h"
#include "math.h"
#endif
#include "ai700_w202_acc_types.h"
#include "mwmathutil.h"
#include <stddef.h>
#include "rtGetInf.h"
#include "rt_defines.h"
#include "simstruc_types.h"
typedef struct { real_T B_3_244_1512 ; } B_u0k2_ai700_w202_T ; typedef struct
{ int32_T u0k2_sysIdxToRun ; int8_T u0k2_SubsysRanBC ; char_T
pad_u0k2_SubsysRanBC [ 3 ] ; } DW_u0k2_ai700_w202_T ; typedef struct { real_T
u0k2_Trig_ZC ; } ZCV_u0k2_ai700_w202_T ; typedef struct { ZCSigState
u0k2_Trig_ZCE ; } ZCE_u0k2_ai700_w202_T ; typedef struct { real_T B_7_0_0 ;
real_T B_7_1_8 ; real_T B_7_2_16 [ 4 ] ; real_T B_7_6_48 ; real_T B_7_7_56 ;
real_T B_7_8_64 ; real_T B_7_9_72 ; real_T B_7_10_80 ; real_T B_7_11_88 ;
real_T B_7_12_96 ; real_T B_7_13_104 ; real_T B_7_14_112 ; real_T B_7_15_120
; real_T B_7_16_128 ; real_T B_7_17_136 ; real_T B_7_18_144 ; real_T
B_7_19_152 ; real_T B_7_20_160 ; real_T B_7_21_168 ; real_T B_7_22_176 [ 4 ]
; real_T B_7_26_208 ; real_T B_7_27_216 [ 4 ] ; real_T B_7_31_248 ; real_T
B_7_32_256 [ 4 ] ; real_T B_7_36_288 ; real_T B_7_37_296 [ 4 ] ; real_T
B_7_41_328 ; real_T B_7_42_336 [ 4 ] ; real_T B_7_46_368 ; real_T B_7_47_376
[ 4 ] ; real_T B_7_51_408 ; real_T B_7_52_416 [ 4 ] ; real_T B_7_56_448 ;
real_T B_7_57_456 [ 4 ] ; real_T B_7_61_488 [ 48 ] ; real_T B_7_109_872 [ 5 ]
; real_T B_7_114_912 ; real_T B_7_115_920 ; real_T B_7_116_928 ; real_T
B_7_117_936 ; real_T B_7_118_944 ; real_T B_7_119_952 ; real_T B_7_120_960 ;
real_T B_7_121_968 ; real_T B_2_122_976 ; real_T B_2_123_984 ; real_T
B_2_124_992 ; real_T B_2_125_1000 ; real_T B_2_126_1008 ; real_T B_2_127_1016
; real_T B_2_128_1024 ; real_T B_2_129_1032 ; real_T B_2_130_1040 ; real_T
B_2_131_1048 ; real_T B_2_132_1056 ; real_T B_2_133_1064 ; real_T
B_2_134_1072 ; real_T B_2_135_1080 ; real_T B_2_136_1088 ; real_T
B_2_137_1096 ; real_T B_2_138_1104 ; real_T B_2_139_1112 ; real_T
B_2_140_1120 ; real_T B_0_141_1128 ; real_T B_0_142_1136 ; real32_T
B_2_143_1144 [ 9 ] ; real32_T B_1_152_1180 [ 72 ] ; int8_T B_2_224_1468 ;
int8_T B_2_225_1469 ; int8_T B_2_226_1470 ; int8_T B_2_227_1471 ; int8_T
B_2_228_1472 ; int8_T B_2_229_1473 ; int8_T B_2_230_1474 ; int8_T
B_2_231_1475 ; int8_T B_2_232_1476 ; int8_T B_2_233_1477 ; int8_T
B_2_234_1478 ; int8_T B_2_235_1479 ; int8_T B_2_236_1480 ; int8_T
B_2_237_1481 ; int8_T B_2_238_1482 ; int8_T B_2_239_1483 ; boolean_T
B_1_240_1484 ; char_T pad_B_1_240_1484 [ 3 ] ; B_u0k2_ai700_w202_T u0k5 ;
B_u0k2_ai700_w202_T u0k4 ; B_u0k2_ai700_w202_T u0k3 ; B_u0k2_ai700_w202_T
u0k2 ; } B_ai700_w202_T ; typedef struct { real_T INPUT_1_1_1_Discrete [ 2 ]
; real_T DelayOneStep1_DSTATE ; real_T DelayOneStep2_DSTATE ; real_T
DelayOneStep3_DSTATE ; real_T DelayOneStep4_DSTATE ; real_T
DelayOneStep5_DSTATE ; real_T INPUT_2_1_1_Discrete [ 2 ] ; real_T
INPUT_3_1_1_Discrete [ 2 ] ; real_T INPUT_4_1_1_Discrete [ 2 ] ; real_T
INPUT_5_1_1_Discrete [ 2 ] ; real_T INPUT_6_1_1_Discrete [ 2 ] ; real_T
INPUT_7_1_1_Discrete [ 2 ] ; real_T INPUT_8_1_1_Discrete [ 2 ] ; real_T
INPUT_9_1_1_Discrete [ 2 ] ; real_T STATE_1_Discrete [ 32 ] ; real_T
Integrator_DSTATE ; real_T Integrator_DSTATE_d ; real_T Integrator_DSTATE_do
; real_T Integrator_DSTATE_m ; real_T TimeStampA ; real_T LastUAtTimeA ;
real_T TimeStampB ; real_T LastUAtTimeB ; real_T TimeStampA_m ; real_T
LastUAtTimeA_d ; real_T TimeStampB_e ; real_T LastUAtTimeB_p ; real_T
TimeStampA_d ; real_T LastUAtTimeA_a ; real_T TimeStampB_g ; real_T
LastUAtTimeB_e ; real_T TimeStampA_c ; real_T LastUAtTimeA_e ; real_T
TimeStampB_ef ; real_T LastUAtTimeB_d ; real_T nextTime ; real_T
STATE_1_ZcValueStore ; real_T OUTPUT_1_0_Discrete ; real_T
OUTPUT_1_0_ZcValueStore ; int64_T numCompleteCycles ; struct { real_T
modelTStart ; } TransportDelay_RWORK ; struct { real_T modelTStart ; }
TransportDelay1_RWORK ; struct { real_T modelTStart ; } TransportDelay2_RWORK
; void * Dataset_Current_Command_PWORK [ 3 ] ; struct { void * TUbufferPtrs [
2 ] ; } TransportDelay_PWORK ; struct { void * TUbufferPtrs [ 2 ] ; }
TransportDelay1_PWORK ; struct { void * TUbufferPtrs [ 2 ] ; }
TransportDelay2_PWORK ; void * STATE_1_Simulator ; void * STATE_1_SimData ;
void * STATE_1_DiagMgr ; void * STATE_1_ZcLogger ; void * STATE_1_TsInfo ;
void * OUTPUT_1_0_Simulator ; void * OUTPUT_1_0_SimData ; void *
OUTPUT_1_0_DiagMgr ; void * OUTPUT_1_0_ZcLogger ; void * OUTPUT_1_0_TsInfo ;
void * Scope2_PWORK [ 5 ] ; struct { void * AQHandles ; }
TAQSigLogging_InsertedFor_PSSimulinkConverter1_at_outport_0_PWORK ; struct {
void * AQHandles ; }
TAQSigLogging_InsertedFor_PSSimulinkConverter2_at_outport_0_PWORK ; struct {
void * AQHandles ; }
TAQSigLogging_InsertedFor_PSSimulinkConverter3_at_outport_0_PWORK ; struct {
void * AQHandles ; }
TAQSigLogging_InsertedFor_PSSimulinkConverter4_at_outport_0_PWORK ; struct {
void * AQHandles ; }
TAQSigLogging_InsertedFor_PSSimulinkConverter5_at_outport_0_PWORK ; struct {
void * AQHandles ; }
TAQSigLogging_InsertedFor_Dataset_Current_Command_at_outport_0_PWORK ; void *
RTP_1_RtpManager ; struct { void * AQHandles ; }
TAQSigLogging_InsertedFor_PIDController2_at_outport_0_PWORK ; struct { void *
AQHandles ; } TAQSigLogging_InsertedFor_PIDController3_at_outport_0_PWORK ;
struct { void * AQHandles ; }
TAQSigLogging_InsertedFor_PIDController4_at_outport_0_PWORK ; struct { void *
AQHandles ; } TAQSigLogging_InsertedFor_PIDController5_at_outport_0_PWORK ;
struct { void * AQHandles ; } _asyncqueue_inserted_for_NDP_features_PWORK ;
struct { void * AQHandles ; } _asyncqueue_inserted_for_NDP_history_PWORK ;
struct { void * AQHandles ; } _asyncqueue_inserted_for_NDP_valid_PWORK ;
int32_T justEnabled ; int32_T currentValue ; int32_T u0k_sysIdxToRun ;
int32_T NDP_InputWindow_sysIdxToRun ; int32_T MATLABFunction_sysIdxToRun ;
int_T Dataset_Current_Command_IWORK ; struct { int_T Tail ; int_T Head ;
int_T Last ; int_T CircularBufSize ; int_T MaxNewBufSize ; }
TransportDelay_IWORK ; struct { int_T Tail ; int_T Head ; int_T Last ; int_T
CircularBufSize ; int_T MaxNewBufSize ; } TransportDelay1_IWORK ; struct {
int_T Tail ; int_T Head ; int_T Last ; int_T CircularBufSize ; int_T
MaxNewBufSize ; } TransportDelay2_IWORK ; int_T STATE_1_Modes [ 16 ] ; int_T
OUTPUT_1_0_Modes ; int8_T u0k_SubsysRanBC ; int8_T Integrator_PrevResetState
; int8_T Integrator_PrevResetState_l ; int8_T Integrator_PrevResetState_lo ;
int8_T Integrator_PrevResetState_m ; uint8_T STATE_1_ZcSignalDir ; uint8_T
STATE_1_ZcStateStore ; uint8_T OUTPUT_1_0_ZcSignalDir ; uint8_T
OUTPUT_1_0_ZcStateStore ; boolean_T RelationalOperator_Mode ; boolean_T
RelationalOperator_Mode_c ; boolean_T RelationalOperator_Mode_i ; boolean_T
RelationalOperator_Mode_p ; boolean_T Cell1Acompare_Mode ; boolean_T
Cell1Acompare1_Mode ; boolean_T Cell1Acompare2_Mode ; boolean_T
Cell1Acompare3_Mode ; boolean_T STATE_1_FirstOutput ; boolean_T
OUTPUT_1_0_FirstOutput ; boolean_T RTP_1_SetParametersNeeded ; char_T
pad_RTP_1_SetParametersNeeded [ 4 ] ; DW_u0k2_ai700_w202_T u0k5 ;
DW_u0k2_ai700_w202_T u0k4 ; DW_u0k2_ai700_w202_T u0k3 ; DW_u0k2_ai700_w202_T
u0k2 ; } DW_ai700_w202_T ; typedef struct { real_T
RelationalOperator_RelopInput_ZC ; real_T RelationalOperator_RelopInput_ZC_j
; real_T RelationalOperator_RelopInput_ZC_a ; real_T
RelationalOperator_RelopInput_ZC_o ; real_T Cell1Acompare_RelopInput_ZC ;
real_T Cell1Acompare1_RelopInput_ZC ; real_T Cell1Acompare2_RelopInput_ZC ;
real_T Cell1Acompare3_RelopInput_ZC ; ZCV_u0k2_ai700_w202_T u0k5 ;
ZCV_u0k2_ai700_w202_T u0k4 ; ZCV_u0k2_ai700_w202_T u0k3 ;
ZCV_u0k2_ai700_w202_T u0k2 ; real_T u0k_Trig_ZC ; } ZCV_ai700_w202_T ;
typedef struct { ZCSigState RelationalOperator_RelopInput_ZCE ; ZCSigState
RelationalOperator_RelopInput_ZCE_i ; ZCSigState
RelationalOperator_RelopInput_ZCE_b ; ZCSigState
RelationalOperator_RelopInput_ZCE_k ; ZCSigState Cell1Acompare_RelopInput_ZCE
; ZCSigState Cell1Acompare1_RelopInput_ZCE ; ZCSigState
Cell1Acompare2_RelopInput_ZCE ; ZCSigState Cell1Acompare3_RelopInput_ZCE ;
ZCE_u0k2_ai700_w202_T u0k5 ; ZCE_u0k2_ai700_w202_T u0k4 ;
ZCE_u0k2_ai700_w202_T u0k3 ; ZCE_u0k2_ai700_w202_T u0k2 ; ZCSigState
u0k_Trig_ZCE ; } PrevZCX_ai700_w202_T ; typedef struct { const real_T
B_2_313_1784 ; const real_T B_2_314_1792 ; const real_T B_2_315_1800 ; const
real_T B_2_316_1808 ; } ConstB_ai700_w202_T ;
#define ai700_w202_rtC(S) ((ConstB_ai700_w202_T *) _ssGetConstBlockIO(S))
struct P_u0k2_ai700_w202_T_ { real_T P_0 ; } ; struct P_ai700_w202_T_ {
real_T P_0 ; real_T P_1 ; real_T P_2 ; real_T P_3 ; real_T P_4 ; real_T P_5 ;
real_T P_6 ; real_T P_7 ; real_T P_8 ; real_T P_9 ; real_T P_10 ; real_T P_11
; real_T P_12 ; real_T P_13 ; real_T P_14 ; real_T P_15 ; real_T P_16 ;
real_T P_17 ; real_T P_18 ; real_T P_19 ; real_T P_20 ; real_T P_21 ; real_T
P_22 ; real_T P_23 ; real_T P_24 ; real_T P_25 ; real_T P_26 ; real_T P_27 ;
real_T P_28 ; real_T P_29 ; real_T P_30 ; real_T P_31 ; real_T P_32 ; real_T
P_33 ; real_T P_34 ; real_T P_35 ; real_T P_36 ; real_T P_37 ; real_T P_38 ;
real_T P_39 ; real_T P_40 ; real_T P_41 ; real_T P_42 ; real_T P_43 ; real_T
P_44 ; real_T P_45 ; real_T P_46 ; real_T P_47 ; real_T P_48 ; real_T P_49 ;
real_T P_50 ; real_T P_51 ; real_T P_52 ; real_T P_53 ; real_T P_54 [ 3 ] ;
real_T P_55 [ 3 ] ; real_T P_56 ; real_T P_57 ; real_T P_58 ; real_T P_59 ;
real_T P_60 ; real_T P_61 ; real_T P_62 ; real_T P_63 ; real_T P_64 ; real_T
P_65 ; real_T P_66 ; real_T P_67 ; real_T P_68 ; real_T P_69 ; real_T P_70 ;
real_T P_71 ; real_T P_72 ; real_T P_73 ; real_T P_74 ; real_T P_75 ; int8_T
P_76 ; int8_T P_77 ; int8_T P_78 ; int8_T P_79 ; int8_T P_80 ; int8_T P_81 ;
int8_T P_82 ; int8_T P_83 ; int8_T P_84 ; int8_T P_85 ; int8_T P_86 ; int8_T
P_87 ; int8_T P_88 ; int8_T P_89 ; int8_T P_90 ; int8_T P_91 ;
P_u0k2_ai700_w202_T u0k5 ; P_u0k2_ai700_w202_T u0k4 ; P_u0k2_ai700_w202_T
u0k3 ; P_u0k2_ai700_w202_T u0k2 ; } ; extern P_ai700_w202_T
ai700_w202_rtDefaultP ; extern const ConstB_ai700_w202_T
ai700_w202_rtInvariant ;
#endif
