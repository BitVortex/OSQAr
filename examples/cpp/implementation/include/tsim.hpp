#pragma once

#include <array>
#include <cstdint>

// Temperature in 0.1°C units (e.g., 100.0°C => 1000)
using tsim_temp_x10_t = int16_t;

enum class tsim_state_t : uint8_t {
    safe = 0,
    unsafe = 1,
};

// REQ_FUNC_001: ADC (12-bit) to temperature conversion
// Output range: -40.0°C..+125.0°C => -400..1250 (0.1°C)
tsim_temp_x10_t tsim_adc_to_temp_x10(uint16_t adc_counts);

// REQ_FUNC_002: 5-sample moving average filter
struct tsim_filter_t {
    std::array<tsim_temp_x10_t, 5> window{};
    uint8_t count{0};
    uint8_t index{0};
    int32_t sum{0};

    void reset();
    // Returns true when output is valid (after 5 samples)
    bool update(tsim_temp_x10_t sample, tsim_temp_x10_t& out_filtered);
};

// REQ_FUNC_003/004: threshold + hysteresis state machine
struct tsim_sm_t {
    tsim_temp_x10_t threshold_high_x10{1000};
    tsim_temp_x10_t threshold_low_x10{950};
    tsim_state_t state{tsim_state_t::safe};

    void init(tsim_temp_x10_t high_x10, tsim_temp_x10_t low_x10);
    tsim_state_t evaluate(tsim_temp_x10_t filtered_temp_x10);
};
