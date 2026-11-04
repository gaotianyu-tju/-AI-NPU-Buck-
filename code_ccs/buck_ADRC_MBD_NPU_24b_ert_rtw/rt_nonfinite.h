/*
 * File: rt_nonfinite.h
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

#ifndef rt_nonfinite_h_
#define rt_nonfinite_h_
#include <stddef.h>
#include "rtwtypes.h"
#define NOT_USING_NONFINITE_LITERALS   1

extern mwReal32_T rtInf;
extern mwReal32_T rtMinusInf;
extern mwReal32_T rtNaN;
extern real32_T rtInfF;
extern real32_T rtMinusInfF;
extern real32_T rtNaNF;
extern void rt_InitInfAndNaN(size_t realSize);
extern boolean_T rtIsInf(mwReal32_T value);
extern boolean_T rtIsInfF(real32_T value);
extern boolean_T rtIsNaN(mwReal32_T value);
extern boolean_T rtIsNaNF(real32_T value);
typedef struct {
  struct {
    uint32_T wordH;
    uint32_T wordL;
  } words;
} BigEndianIEEEDouble;

typedef struct {
  struct {
    uint32_T wordL;
    uint32_T wordH;
  } words;
} LittleEndianIEEEDouble;

typedef struct {
  union {
    real32_T wordLreal;
    uint32_T wordLuint;
  } wordL;
} IEEESingle;

#endif                                 /* rt_nonfinite_h_ */

/*
 * File trailer for generated code.
 *
 * [EOF]
 */
