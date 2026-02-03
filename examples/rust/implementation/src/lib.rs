//! TSIM - Thermal Sensor Interface Module (Rust)
//!
//! Requirement Traceability:
//!   - REQ_FUNC_001: ADC to temperature conversion
//!   - REQ_FUNC_002: 5-sample moving average filter
//!   - REQ_FUNC_003: Threshold detection (>=100°C)
//!   - REQ_FUNC_004: Hysteresis recovery (<=95°C)

/// Temperature in 0.1°C units (e.g., 100.0°C => 1000)
pub type TempX10 = i16;

#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub enum State {
    Safe,
    Unsafe,
}

/// REQ_FUNC_001: ADC (12-bit) to temperature conversion.
/// Output range: -40.0°C..+125.0°C => -400..1250 (0.1°C)
pub fn adc_to_temp_x10(adc_counts: u16) -> TempX10 {
    let adc = adc_counts.min(4095);

    // celsius = -40 + adc * (165 / 4095)
    // x10: temp_x10 = -400 + adc * (1650 / 4095)
    let numerator: i32 = (adc as i32) * 1650;
    let scaled: i32 = (numerator + 2047) / 4095; // round
    let mut temp_x10: i32 = -400 + scaled;

    if temp_x10 < -400 {
        temp_x10 = -400;
    }
    if temp_x10 > 1250 {
        temp_x10 = 1250;
    }

    temp_x10 as TempX10
}

/// REQ_FUNC_002: 5-sample moving average filter.
pub struct Filter {
    window: [TempX10; 5],
    count: usize,
    index: usize,
    sum: i32,
}

impl Filter {
    pub fn new() -> Self {
        Self {
            window: [0; 5],
            count: 0,
            index: 0,
            sum: 0,
        }
    }

    /// Returns `Some(filtered)` only once the window is full.
    pub fn update(&mut self, sample: TempX10) -> Option<TempX10> {
        if self.count < 5 {
            self.window[self.index] = sample;
            self.sum += sample as i32;
            self.index = (self.index + 1) % 5;
            self.count += 1;
            return None;
        }

        let old = self.window[self.index];
        self.sum -= old as i32;
        self.window[self.index] = sample;
        self.sum += sample as i32;
        self.index = (self.index + 1) % 5;

        Some((self.sum / 5) as TempX10)
    }
}

/// REQ_FUNC_003/004: threshold + hysteresis state machine.
pub struct StateMachine {
    high_x10: TempX10,
    low_x10: TempX10,
    pub state: State,
}

impl StateMachine {
    pub fn new(high_x10: TempX10, low_x10: TempX10) -> Self {
        Self {
            high_x10,
            low_x10,
            state: State::Safe,
        }
    }

    pub fn evaluate(&mut self, filtered_temp_x10: TempX10) -> State {
        match self.state {
            State::Safe => {
                if filtered_temp_x10 >= self.high_x10 {
                    self.state = State::Unsafe;
                }
            }
            State::Unsafe => {
                if filtered_temp_x10 <= self.low_x10 {
                    self.state = State::Safe;
                }
            }
        }
        self.state
    }
}
