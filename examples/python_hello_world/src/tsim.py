"""
TSIM - Thermal Sensor Interface Module

Implements a domain-agnostic temperature monitoring Safety Element (SEooC)
compliant with ISO 26262 functional safety requirements.

Requirement Traceability:
  - REQ_SAFETY_001: Safety goal - prevent thermal damage
  - REQ_SAFETY_002: Detect overheat within 100ms
  - REQ_SAFETY_003: Report safe state on recovery
"""

from typing import Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import time


class TemperatureState(Enum):
    """
    State enumeration for temperature monitoring.

    Maps to: ARCH_DESIGN_001 - State Machine Implementation
    """

    SAFE = 0  # Temperature within safe range
    UNSAFE = 1  # Temperature exceeds threshold


@dataclass
class TemperatureConfig:
    """
    Configuration registers for temperature thresholds.

    Traceability:
      - ARCH_DESIGN_003: Read-only configuration registers
      - REQ_FUNC_003: Threshold configuration (≥100°C)
      - REQ_FUNC_004: Hysteresis configuration (≤95°C)
    """

    threshold_high_celsius: float = 100.0  # UNSAFE threshold
    threshold_low_celsius: float = 95.0  # SAFE recovery threshold (hysteresis)

    def __post_init__(self):
        """Validate configuration constraints."""
        if self.threshold_low_celsius >= self.threshold_high_celsius:
            raise ValueError(
                f"Hysteresis constraint violated: "
                f"low ({self.threshold_low_celsius}) must be < high ({self.threshold_high_celsius})"
            )


class SensorDriver:
    """
    ADC Sensor Input Driver

    Traceability:
      - ARCH_FUNC_001: 100Hz sampling rate
      - REQ_FUNC_001: ADC to temperature conversion
      - ARCH_SIGNAL_001: 12-bit ADC input (-40 to +125°C)
      - ARCH_SIGNAL_002: 16-bit signed output (0.1°C units)
      - ARCH_ERROR_001: Hold last safe state on invalid read
    """

    # ADC configuration (12-bit)
    ADC_MIN_COUNTS = 0  # -40°C
    ADC_MAX_COUNTS = 4095  # ~+125°C
    ADC_MIN_CELSIUS = -40.0
    ADC_MAX_CELSIUS = 125.0

    # Output precision: 0.1°C units in 16-bit signed integer
    OUTPUT_SCALE = 10.0  # 0.1°C resolution
    OUTPUT_MIN = -400  # -40.0°C
    OUTPUT_MAX = 1250  # +125.0°C

    SAMPLING_PERIOD_MS = 10.0  # 100Hz = 10ms intervals

    def __init__(self):
        """Initialize sensor driver."""
        self.last_valid_reading = 25  # Default room temperature (0.1°C units)
        self.last_read_time = time.time()
        self.consecutive_errors = 0

    def read_adc(self, adc_counts: int) -> int:
        """
        Read ADC value and convert to temperature.

        Args:
            adc_counts: Raw 12-bit ADC reading (0-4095)

        Returns:
            Temperature in 0.1°C units (-400 to +1250, representing -40.0°C to +125.0°C)

        Traceability:
            TEST_CONVERSION_001: Validates conversion across full range
            REQ_FUNC_001: Conversion requirement
        """
        try:
            # Validate ADC input range
            if not (self.ADC_MIN_COUNTS <= adc_counts <= self.ADC_MAX_COUNTS):
                raise ValueError(
                    f"ADC reading {adc_counts} out of range "
                    f"({self.ADC_MIN_COUNTS}-{self.ADC_MAX_COUNTS})"
                )

            # Linear interpolation: ADC counts → Celsius
            celsius = self.ADC_MIN_CELSIUS + (adc_counts - self.ADC_MIN_COUNTS) * (
                self.ADC_MAX_CELSIUS - self.ADC_MIN_CELSIUS
            ) / (self.ADC_MAX_COUNTS - self.ADC_MIN_COUNTS)

            # Convert to 0.1°C integer representation
            temperature_int = int(round(celsius * self.OUTPUT_SCALE))

            # Clamp to valid output range
            temperature_int = max(
                self.OUTPUT_MIN, min(self.OUTPUT_MAX, temperature_int)
            )

            self.last_valid_reading = temperature_int
            self.consecutive_errors = 0
            self.last_read_time = time.time()

            return temperature_int

        except (ValueError, TypeError) as e:
            """
            Error Handling: ARCH_ERROR_001
            Hold last safe state on invalid read
            """
            self.consecutive_errors += 1
            return self.last_valid_reading


class TemperatureFilter:
    """
    Noise-rejection filter using 5-sample moving average.

    Traceability:
      - ARCH_FUNC_002: 5-sample moving average
      - REQ_FUNC_002: Noise filtering requirement
      - TEST_FILTER_001: Validates ≥90% noise amplitude reduction
    """

    SAMPLE_WINDOW = 5  # Moving average window size

    def __init__(self):
        """Initialize filter buffer."""
        self.buffer = []  # Circular buffer for samples

    def update(self, temperature: int) -> Optional[int]:
        """
        Update filter with new sample and return filtered value.

        Args:
            temperature: Raw temperature (0.1°C units)

        Returns:
            Filtered temperature, or None if buffer not yet full

        Traceability:
            TEST_FILTER_001: Noise amplitude reduction validation
        """
        self.buffer.append(temperature)

        # Keep buffer size constant
        if len(self.buffer) > self.SAMPLE_WINDOW:
            self.buffer.pop(0)

        # Only output when buffer is full
        if len(self.buffer) < self.SAMPLE_WINDOW:
            return None

        # Calculate mean of samples
        filtered = sum(self.buffer) // len(self.buffer)
        return filtered


class StateMachine:
    """
    Temperature state machine with hysteresis.

    Traceability:
      - ARCH_DESIGN_001: State machine architecture
      - ARCH_FUNC_003: State transitions within 50ms
      - REQ_SAFETY_002: Detect overheat within 100ms
      - REQ_SAFETY_003: Report safe state recovery
      - REQ_FUNC_003: Threshold detection (≥100°C)
      - REQ_FUNC_004: Hysteresis recovery (≤95°C)
    """

    def __init__(self, config: Optional[TemperatureConfig] = None):
        """Initialize state machine."""
        self.config = config or TemperatureConfig()
        self.state = TemperatureState.SAFE
        self.state_changed_time = time.time()

    def evaluate(self, temperature: int) -> TemperatureState:
        """
        Evaluate temperature against thresholds with hysteresis.

        Args:
            temperature: Filtered temperature (0.1°C units)

        Returns:
            Current state (SAFE or UNSAFE)

        Traceability:
            TEST_THRESHOLD_001: Validates threshold detection at 100°C
            TEST_HYSTERESIS_001: Validates hysteresis deadband (5°C)
            TEST_END_TO_END_001: Validates latency ≤50ms
        """
        # Convert config thresholds to 0.1°C units for comparison
        high_threshold = int(round(self.config.threshold_high_celsius * 10.0))
        low_threshold = int(round(self.config.threshold_low_celsius * 10.0))

        # State machine with hysteresis
        if self.state == TemperatureState.SAFE:
            # Transition to UNSAFE when threshold exceeded
            if temperature >= high_threshold:
                self.state = TemperatureState.UNSAFE
                self.state_changed_time = time.time()

        elif self.state == TemperatureState.UNSAFE:
            # Transition to SAFE only below lower threshold (hysteresis)
            if temperature <= low_threshold:
                self.state = TemperatureState.SAFE
                self.state_changed_time = time.time()

        return self.state

    def get_state_output(self) -> int:
        """
        Get current state as bit value.

        Returns:
            0 for SAFE, 1 for UNSAFE

        Traceability:
            ARCH_SIGNAL_003: 1-bit state output
        """
        return self.state.value


class ThermalSensorInterfaceModule:
    """
    Complete TSIM - Thermal Sensor Interface Module.

    Integrates sensor driver, filter, and state machine into a complete
    Safety Element out of Context (SEooC) for temperature monitoring.

    Traceability:
      - ARCH_001: Module composition
      - ARCH_SEOOC_001: SEooC assumptions
      - ARCH_SEOOC_002: Integration responsibility transfer
      - REQ_SAFETY_001: Safety goal
      - REQ_SAFETY_002: Detect within 100ms
      - REQ_SAFETY_003: Report safe state
    """

    MAX_CONSECUTIVE_ERRORS = 10  # ARCH_ERROR_002 fail-safe threshold

    def __init__(self, config: Optional[TemperatureConfig] = None):
        """Initialize TSIM."""
        self.config = config or TemperatureConfig()
        self.sensor = SensorDriver()
        self.filter = TemperatureFilter()
        self.state_machine = StateMachine(self.config)
        self.last_error_count = 0

    def process_sample(self, adc_counts: int) -> Tuple[int, TemperatureState]:
        """
        Process one ADC sample through the complete pipeline.

        Args:
            adc_counts: Raw 12-bit ADC reading

        Returns:
            Tuple of (filtered_temperature_int, state_output)

        Timing Traceability (REQ_SAFETY_002, ARCH_FUNC_003):
            - ADC read: 0-10ms
            - Filter: 10-20ms
            - State evaluation: 20-50ms
            - Safety margin: 50-100ms

        Requirement Mapping:
            TEST_END_TO_END_001: Tests complete pipeline latency
            TEST_ERROR_RECOVERY_001: Tests error handling paths
        """
        # Stage 1: Sensor Driver (10ms budget)
        raw_temp = self.sensor.read_adc(adc_counts)

        # Check error count for fail-safe (ARCH_ERROR_002)
        if self.sensor.consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS:
            # Fail-safe: go UNSAFE
            self.state_machine.state = TemperatureState.UNSAFE
            return raw_temp, TemperatureState.UNSAFE

        # Stage 2: Filter (10ms budget)
        filtered_temp = self.filter.update(raw_temp)

        # If filter buffer not yet full, use raw reading
        if filtered_temp is None:
            filtered_temp = raw_temp

        # Stage 3: State Machine (30ms budget)
        state = self.state_machine.evaluate(filtered_temp)

        return filtered_temp, state

    def get_safe_unsafe_output(self) -> int:
        """
        Get current safe/unsafe state bit.

        Returns:
            0 for SAFE, 1 for UNSAFE

        Traceability:
            ARCH_SIGNAL_003: 1-bit state output
            REQ_SAFETY_002, REQ_SAFETY_003: State reporting requirement
        """
        return self.state_machine.get_state_output()
