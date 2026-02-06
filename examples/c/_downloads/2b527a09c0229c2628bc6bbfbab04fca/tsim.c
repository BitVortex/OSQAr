#include "tsim.h"

#include <stddef.h>

/*
OSQAR-CODE-TRACE (implementation tags)

REQ: REQ_SAFETY_001 REQ_SAFETY_002 REQ_SAFETY_003 REQ_FUNC_001 REQ_FUNC_002 REQ_FUNC_003 REQ_FUNC_004
ARCH: ARCH_001 ARCH_DESIGN_001 ARCH_DESIGN_002 ARCH_DESIGN_003 ARCH_ERROR_001 ARCH_ERROR_002 ARCH_FUNC_001 ARCH_FUNC_002 ARCH_FUNC_003 ARCH_SEOOC_001 ARCH_SEOOC_002 ARCH_SIGNAL_001 ARCH_SIGNAL_002 ARCH_SIGNAL_003
*/

// Linear mapping of ADC counts (0..4095) to Celsius (-40..125)
// Returned as 0.1°C integer.

tsim_temp_x10_t tsim_adc_to_temp_x10(uint16_t adc_counts) {
    if (adc_counts > 4095u) {
        // Hold last safe state behavior is integration-specific; for this example clamp.
        adc_counts = 4095u;
    }

    // Use integer math with rounding to nearest.
    // celsius = -40 + adc * (165 / 4095)
    // x10: temp_x10 = -400 + adc * (1650 / 4095)
    const int32_t numerator = (int32_t)adc_counts * 1650;
    const int32_t scaled = (numerator + 2047) / 4095; // round
    int32_t temp_x10 = -400 + scaled;

    if (temp_x10 < -400) temp_x10 = -400;
    if (temp_x10 > 1250) temp_x10 = 1250;

    return (tsim_temp_x10_t)temp_x10;
}

void tsim_filter_init(tsim_filter_t* filter) {
    if (!filter) return;
    for (size_t i = 0; i < 5; i++) {
        filter->window[i] = 0;
    }
    filter->count = 0;
    filter->index = 0;
    filter->sum = 0;
}

bool tsim_filter_update(tsim_filter_t* filter, tsim_temp_x10_t sample, tsim_temp_x10_t* out_filtered) {
    if (!filter) return false;

    if (filter->count < 5) {
        filter->window[filter->index] = sample;
        filter->sum += sample;
        filter->index = (uint8_t)((filter->index + 1u) % 5u);
        filter->count++;
        return false;
    }

    // Replace oldest sample
    const tsim_temp_x10_t old = filter->window[filter->index];
    filter->sum -= old;
    filter->window[filter->index] = sample;
    filter->sum += sample;
    filter->index = (uint8_t)((filter->index + 1u) % 5u);

    if (out_filtered) {
        *out_filtered = (tsim_temp_x10_t)(filter->sum / 5);
    }

    return true;
}

void tsim_sm_init(tsim_sm_t* sm, tsim_temp_x10_t high_x10, tsim_temp_x10_t low_x10) {
    if (!sm) return;
    sm->threshold_high_x10 = high_x10;
    sm->threshold_low_x10 = low_x10;
    sm->state = TSIM_STATE_SAFE;
}

tsim_state_t tsim_sm_evaluate(tsim_sm_t* sm, tsim_temp_x10_t filtered_temp_x10) {
    if (!sm) return TSIM_STATE_SAFE;

    if (sm->state == TSIM_STATE_SAFE) {
        if (filtered_temp_x10 >= sm->threshold_high_x10) {
            sm->state = TSIM_STATE_UNSAFE;
        }
    } else {
        if (filtered_temp_x10 <= sm->threshold_low_x10) {
            sm->state = TSIM_STATE_SAFE;
        }
    }

    return sm->state;
}
