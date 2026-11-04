#ifndef ai700_w302_acc_private_h_
#define ai700_w302_acc_private_h_
#include "rtwtypes.h"
#include "multiword_types.h"
#include "zero_crossing_types.h"
#include <stddef.h>
#include <float.h>
#include "mwmathutil.h"
#include "ai700_w302_acc.h"
#include "ai700_w302_acc_types.h"
#if !defined(ss_VALIDATE_MEMORY)
#define ss_VALIDATE_MEMORY(S, ptr)     if(!(ptr)) {\
    ssSetErrorStatus(S, RT_MEMORY_ALLOCATION_ERROR);\
    }
#endif
#if !defined(rt_FREE)
#if !defined(_WIN32)
#define rt_FREE(ptr)     if((ptr) != (NULL)) {\
    free((ptr));\
    (ptr) = (NULL);\
    }
#else
#define rt_FREE(ptr)     if((ptr) != (NULL)) {\
    free((void *)(ptr));\
    (ptr) = (NULL);\
    }
#endif
#endif
#ifndef rtInterpolate
#define rtInterpolate(v1,v2,f1,f2)     (((v1)==(v2))?((double)(v1)):    (((f1)*((double)(v1)))+((f2)*((double)(v2)))))
#endif
#ifndef rtRound
#define rtRound(v) ( ((v) >= 0) ?     muDoubleScalarFloor((v) + 0.5) :     muDoubleScalarCeil((v) - 0.5) )
#endif
#ifndef __RTW_UTFREE__
extern void * utMalloc ( size_t ) ; extern void utFree ( void * ) ;
#endif
boolean_T ai700_w302_acc_rt_TDelayUpdateTailOrGrowBuf ( int_T * bufSzPtr ,
int_T * tailPtr , int_T * headPtr , int_T * lastPtr , real_T tMinusDelay ,
real_T * * uBufPtr , boolean_T isfixedbuf , boolean_T istransportdelay ,
int_T * maxNewBufSzPtr ) ; real_T ai700_w302_acc_rt_TDelayInterpolate ( real_T
tMinusDelay , real_T tStart , real_T * uBuf , int_T bufSz , int_T * lastIdx ,
int_T oldestIdx , int_T newIdx , real_T initOutput , boolean_T discrete ,
boolean_T minorStepAndTAtLastMajorOutput ) ; extern real_T look1_binlxpw ( real_T u0 , const real_T bp0 [ ] , const real_T table [ ] , uint32_T maxIndex ) ; void ai700_w302_u0k2_Init ( SimStruct * S , B_u0k2_ai700_w302_T * localB , P_u0k2_ai700_w302_T * localP , ZCE_u0k2_ai700_w302_T * localZCE ) ; void ai700_w302_u0k2 ( SimStruct * S , boolean_T rtu_function , real_T rtu_In1 , B_u0k2_ai700_w302_T * localB , DW_u0k2_ai700_w302_T * localDW , ZCE_u0k2_ai700_w302_T * localZCE ) ; void ai700_w302_u0k2_Term ( SimStruct * const S ) ;
#endif
