#ifndef BUCK_NPU_PHASE_IMPL_H
#define BUCK_NPU_PHASE_IMPL_H
/* Include exactly once, at the end of buck_load_observer.c. Keeping this
 * implementation in its existing translation unit adds no CCS C-source entry.
 * All helper names are independent of the physical observer's helpers/state. */
#include "buck_npu_phase.h"

uint16_t buck_npu_phase_last_status;
float buck_npu_phase_uncertainty_ticks;

/* Static storage avoids adding these arrays to the MCU runtime stack.
 * Only background/main may use this nonreentrant estimator. */
static float npu_phase_kcl[BUCK_NPU_PHASE_HISTORY];
static float npu_phase_normalized[BUCK_NPU_PHASE_HISTORY];

static uint16_t npu_phase_finite(float x)
{
    union { float f; uint32_t u; } v;
    v.f = x;
    return (uint16_t)((v.u & 0x7f800000UL) != 0x7f800000UL);
}
static float npu_phase_abs(float x) { return x < 0.0f ? -x : x; }
static float npu_phase_median3(float a, float b, float c)
{
    float temporary;
    if (a > b) { temporary=a; a=b; b=temporary; }
    if (b > c) { temporary=b; b=c; c=temporary; }
    if (a > b) b=a;
    return b;
}

/* Validate a six-sample platform against previously learned levels.
 * Bounds are normalized by the learned span, not fixed load amplitudes. */
static uint16_t npu_phase_platform(uint16_t first, float level,
    float *spread_out, float *error_out)
{
    uint16_t j;
    float lo=npu_phase_normalized[first], hi=lo, sum=0.0f, x, mean;
    for (j=first; j<(uint16_t)(first+6U); ++j) {
        x=npu_phase_normalized[j];
        if (x<lo) lo=x;
        if (x>hi) hi=x;
        sum+=x*(1.0f/6.0f);
    }
    mean=sum;
    *spread_out=hi-lo;
    *error_out=npu_phase_abs(mean-level);
    return (uint16_t)(npu_phase_finite(mean) && *spread_out<=0.16f &&
        *error_out<=0.12f && lo>=level-0.20f && hi<=level+0.20f);
}

static float npu_phase_crossing(uint16_t right, float threshold)
{
    float before=npu_phase_normalized[right-1U];
    /* Caller establishes a strictly positive crossing denominator. */
    return (float)(right-1U)+(threshold-before)/
        (npu_phase_normalized[right]-before);
}

uint16_t buck_npu_phase_estimate(const float raw[64][9], float low, float high,
    uint16_t kind, uint32_t confirm_tick, uint32_t *edge_tick, float *confidence)
{
    uint16_t k,j,c,i10,i70,post,found10,found70,found_post,positive_steps;
    uint16_t valid_count=0U, tail_bad, outside=0U, selected_back=0U;
    float span,inverse_span,mean_current,load,x,delta;
    float t10,t30,t70,width,slope_first,slope_second,ratio;
    float pre_spread,post_spread,pre_error,post_error;
    float onset,back,noise,uncertainty,quality,selected_quality=0.0f;
    float selected_uncertainty=0.0f;
    if (edge_tick) *edge_tick=confirm_tick;
    if (confidence) *confidence=0.0f;
    buck_npu_phase_uncertainty_ticks=0.0f;
    buck_npu_phase_last_status=BUCK_NPU_PHASE_BAD_ARGUMENT;
    if (!raw || !edge_tick || !confidence || (kind!=1U && kind!=2U)) return 0U;
    span=high-low;
    if (!npu_phase_finite(low) || !npu_phase_finite(high) ||
        !npu_phase_finite(span) || span<4.0f) {
        buck_npu_phase_last_status=BUCK_NPU_PHASE_BAD_LEVELS; return 0U;
    }
    inverse_span=1.0f/span;
    for (k=0U; k<BUCK_NPU_PHASE_HISTORY; ++k) {
        for (c=0U; c<BUCK_NPU_PHASE_CHANNELS; ++c) {
            if (!npu_phase_finite(raw[k][c])) {
                buck_npu_phase_last_status=BUCK_NPU_PHASE_BAD_DATA; return 0U;
            }
        }
    }
    /* KCL averaged over [k-4,k]: mean(sumI[k-4..k-1])
     * - Cout*(Vo[k]-Vo[k-4])/(4*Ts), Cout=.00018F, Ts=1/30000s.
     * Multiplying each current by.25 before summing reduces overflow risk.
     * No new physical observer state or neural input history is written. */
    for (k=4U; k<BUCK_NPU_PHASE_HISTORY; ++k) {
        mean_current=0.0f;
        for (j=(uint16_t)(k-4U); j<k; ++j) {
            for (c=1U; c<=4U; ++c) mean_current+=0.25f*raw[j][c];
        }
        load=mean_current-(0.00018f/(4.0f*3.33333337E-5F))*(raw[k][0]-raw[k-4U][0]);
        if (!npu_phase_finite(load)) {
            buck_npu_phase_last_status=BUCK_NPU_PHASE_BAD_DATA; return 0U;
        }
        npu_phase_kcl[k]=load;
    }
    /* Offline, centered median3 removes isolated measurement spikes without
     * adding a causal-smoother delay. Valid centered samples are5..62. */
    for (k=5U; k<=62U; ++k) {
        load=npu_phase_median3(npu_phase_kcl[k-1U],npu_phase_kcl[k],npu_phase_kcl[k+1U]);
        x=kind==1U ? (load-low)*inverse_span : (high-load)*inverse_span;
        if (!npu_phase_finite(x)) {
            buck_npu_phase_last_status=BUCK_NPU_PHASE_BAD_DATA; return 0U;
        }
        npu_phase_normalized[k]=x;
    }
    /* Examine every upward30% crossing in normalized coordinates. A candidate
     * needs six valid pre-edge samples, three progressing increments,70%
     * crossing and six post-platform samples before the snapshot ends. */
    for (k=12U; k<=55U; ++k) {
        if (!(npu_phase_normalized[k-1U]<=0.30f && npu_phase_normalized[k]>0.30f)) continue;
        found10=0U; i10=0U;
        for (j=k; j>10U; --j) {
            if (npu_phase_normalized[j-1U]<=0.10f && npu_phase_normalized[j]>0.10f) {
                i10=j; found10=1U; break;
            }
        }
        if (!found10) continue;
        if (!npu_phase_platform((uint16_t)(i10-6U),0.0f,&pre_spread,&pre_error)) continue;
        found70=0U; i70=0U;
        for (j=k; j<=57U; ++j) {
            if (npu_phase_normalized[j-1U]<=0.70f && npu_phase_normalized[j]>0.70f) {
                i70=j; found70=1U; break;
            }
        }
        if (!found70) continue;
        t10=npu_phase_crossing(i10,0.10f);
        t30=npu_phase_crossing(k,0.30f);
        t70=npu_phase_crossing(i70,0.70f);
        width=t70-t10;
        if (t30-t10<0.35f || t70-t30<0.70f || width<1.5f || width>28.0f) continue;
        slope_first=0.20f/(t30-t10);
        slope_second=0.40f/(t70-t30);
        ratio=slope_first/slope_second;
        if (!npu_phase_finite(ratio) || ratio<0.40f || ratio>2.50f) continue;
        positive_steps=0U;
        for (j=i10; j<=i70; ++j) {
            delta=npu_phase_normalized[j]-npu_phase_normalized[j-1U];
            if (delta < -0.08f) break;
            if (delta > 0.01f) ++positive_steps;
        }
        if (j<=i70 || positive_steps<3U) continue;
        found_post=0U; post=0U;
        for (j=i70; j<=57U; ++j) {
            if (npu_phase_platform(j,1.0f,&post_spread,&post_error)) {
                post=j; found_post=1U; break;
            }
        }
        if (!found_post) continue;
        /* A spike followed by a return to the old platform is NOT a load edge.
         * One bounded outlier is tolerated after the six-point confirmation. */
        tail_bad=0U;
        for (j=post; j<=62U; ++j) {
            if (npu_phase_normalized[j]<0.70f || npu_phase_normalized[j]>1.30f) ++tail_bad;
        }
        if (tail_bad>1U) continue;
        onset=t10-0.10f/slope_first-2.0f;
        back=63.0f-onset;
        if (!npu_phase_finite(back) || back<0.0f || back>=(float)BUCK_NPU_PHASE_MAX_BACK_TICKS) {
            outside=1U; continue;
        }
        noise=pre_spread>post_spread ? pre_spread : post_spread;
        uncertainty=2.5f+0.5f*noise/slope_first;
        if (!npu_phase_finite(uncertainty) || uncertainty>5.0f) continue;
        quality=0.95f-0.25f*(noise/0.16f)-0.15f*((pre_error+post_error)/0.24f)
            -0.10f*npu_phase_abs(1.0f-ratio);
        if (quality<0.0f) quality=0.0f;
        if (quality>1.0f) quality=1.0f;
        j=(uint16_t)(back+0.5f);
        if (j>=BUCK_NPU_PHASE_MAX_BACK_TICKS) { outside=1U; continue; }
        ++valid_count;
        selected_back=j; selected_quality=quality; selected_uncertainty=uncertainty;
    }
    if (valid_count!=1U) {
        buck_npu_phase_last_status=valid_count>1U ? BUCK_NPU_PHASE_AMBIGUOUS :
            (outside ? BUCK_NPU_PHASE_OUT_OF_RANGE : BUCK_NPU_PHASE_NO_EDGE);
        return 0U;
    }
    /* Subtract local integer age from the32-bit timestamp: no float conversion
     * of absolute uptime, and uint32 wrap is handled by unsigned arithmetic. */
    *edge_tick=confirm_tick-(uint32_t)selected_back;
    *confidence=selected_quality;
    buck_npu_phase_uncertainty_ticks=selected_uncertainty;
    buck_npu_phase_last_status=BUCK_NPU_PHASE_OK;
    return 1U;
}
#endif
