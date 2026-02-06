#pragma once

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Temperature in 0.1°C units (e.g., 100.0°C => 1000)
typedef int16_t tsim_temp_x10_t;

typedef enum {
    TSIM_STATE_SAFE = 0,
    TSIM_STATE_UNSAFE = 1,
} tsim_state_t;

// REQ_FUNC_001: ADC (12-bit) to temperature conversion
// Output range: -40.0°C..+125.0°C => -400..1250 (0.1°C)
tsim_temp_x10_t tsim_adc_to_temp_x10(uint16_t adc_counts);

// REQ_FUNC_002: 5-sample moving average filter
typedef struct {
    tsim_temp_x10_t window[5];
    uint8_t count;
    uint8_t index;
    int32_t sum;
} tsim_filter_t;

void tsim_filter_init(tsim_filter_t* filter);
// Returns true when output is valid (after 5 samples)
bool tsim_filter_update(tsim_filter_t* filter, tsim_temp_x10_t sample, tsim_temp_x10_t* out_filtered);

// REQ_FUNC_003/004: threshold + hysteresis state machine
typedef struct {
    tsim_temp_x10_t threshold_high_x10;
    tsim_temp_x10_t threshold_low_x10;
    tsim_state_t state;
} tsim_sm_t;

void tsim_sm_init(tsim_sm_t* sm, tsim_temp_x10_t high_x10, tsim_temp_x10_t low_x10);
tsim_state_t tsim_sm_evaluate(tsim_sm_t* sm, tsim_temp_x10_t filtered_temp_x10);

#ifdef __cplusplus
}
#endif
