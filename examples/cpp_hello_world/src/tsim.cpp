#include "tsim.hpp"

#include <algorithm>

/*
OSQAR-CODE-TRACE (implementation tags)

REQ: REQ_SAFETY_001 REQ_SAFETY_002 REQ_SAFETY_003 REQ_FUNC_001 REQ_FUNC_002 REQ_FUNC_003 REQ_FUNC_004
ARCH: ARCH_001 ARCH_DESIGN_001 ARCH_DESIGN_002 ARCH_DESIGN_003 ARCH_ERROR_001 ARCH_ERROR_002 ARCH_FUNC_001 ARCH_FUNC_002 ARCH_FUNC_003 ARCH_SEOOC_001 ARCH_SEOOC_002 ARCH_SIGNAL_001 ARCH_SIGNAL_002 ARCH_SIGNAL_003
*/

// Linear mapping of ADC counts (0..4095) to Celsius (-40..125)
// Returned as 0.1°C integer.

tsim_temp_x10_t tsim_adc_to_temp_x10(uint16_t adc_counts) {
    if (adc_counts > 4095u) {
        adc_counts = 4095u;
    }

    // celsius = -40 + adc * (165 / 4095)
    // x10: temp_x10 = -400 + adc * (1650 / 4095)
    const int32_t numerator = static_cast<int32_t>(adc_counts) * 1650;
    const int32_t scaled = (numerator + 2047) / 4095; // round
    int32_t temp_x10 = -400 + scaled;

    temp_x10 = std::clamp(temp_x10, -400, 1250);
    return static_cast<tsim_temp_x10_t>(temp_x10);
}

void tsim_filter_t::reset() {
    window.fill(0);
    count = 0;
    index = 0;
    sum = 0;
}

bool tsim_filter_t::update(tsim_temp_x10_t sample, tsim_temp_x10_t& out_filtered) {
    if (count < 5) {
        window[index] = sample;
        sum += sample;
        index = static_cast<uint8_t>((index + 1u) % 5u);
        count++;
        return false;
    }

    const tsim_temp_x10_t old = window[index];
    sum -= old;
    window[index] = sample;
    sum += sample;
    index = static_cast<uint8_t>((index + 1u) % 5u);

    out_filtered = static_cast<tsim_temp_x10_t>(sum / 5);
    return true;
}

void tsim_sm_t::init(tsim_temp_x10_t high_x10, tsim_temp_x10_t low_x10) {
    threshold_high_x10 = high_x10;
    threshold_low_x10 = low_x10;
    state = tsim_state_t::safe;
}

tsim_state_t tsim_sm_t::evaluate(tsim_temp_x10_t filtered_temp_x10) {
    if (state == tsim_state_t::safe) {
        if (filtered_temp_x10 >= threshold_high_x10) {
            state = tsim_state_t::unsafe;
        }
    } else {
        if (filtered_temp_x10 <= threshold_low_x10) {
            state = tsim_state_t::safe;
        }
    }

    return state;
}
