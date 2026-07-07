from __future__ import annotations

from enum import Enum, unique

__all__ = ["MeterState"]

@unique
class MeterState(str, Enum):
    """
    Operational state of an electrical meter.  Vendors may not implement every state;
    subscribers should treat unrecognised values as `unknown`.
    
    Args:
        unknown (str)            : Value for UNKNOWN
        startup (str)            : Value for STARTUP
        off (str)                : Value for OFF
        on (str)                 : Value for ON
        throttle (str)           : Value for THROTTLE
        throttle_check (str)     : Value for THROTTLE_CHECK
        throttle_error (str)     : Value for THROTTLE_ERROR
        protect (str)            : Value for PROTECT
        meter_check (str)        : Value for METER_CHECK
        meter_disabled (str)     : Value for METER_DISABLED
        calibrate (str)          : Value for CALIBRATE
        tamper (str)             : Value for TAMPER
        error (str)              : Value for ERROR
        unprovisioned (str)      : Value for UNPROVISIONED
    """
    UNKNOWN = "unknown"
    STARTUP = "startup"
    OFF = "off"
    ON = "on"
    THROTTLE = "throttle"
    THROTTLE_CHECK = "throttle_check"
    THROTTLE_ERROR = "throttle_error"
    PROTECT = "protect"
    METER_CHECK = "meter_check"
    METER_DISABLED = "meter_disabled"
    CALIBRATE = "calibrate"
    TAMPER = "tamper"
    ERROR = "error"
    UNPROVISIONED = "unprovisioned"