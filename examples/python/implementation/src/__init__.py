"""
TSIM - Thermal Sensor Interface Module
Demonstrates an OSQAr-annotated component with traceability from requirements to code
"""

from .tsim import (
    SensorDriver,
    TemperatureFilter,
    StateMachine,
    ThermalSensorInterfaceModule,
    TemperatureConfig,
    TemperatureState,
)

__all__ = [
    "SensorDriver",
    "TemperatureFilter",
    "StateMachine",
    "ThermalSensorInterfaceModule",
    "TemperatureConfig",
    "TemperatureState",
]
