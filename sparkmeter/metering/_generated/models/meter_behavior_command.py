from __future__ import annotations

from enum import Enum, unique

__all__ = ["MeterBehaviorCommand"]

@unique
class MeterBehaviorCommand(str, Enum):
    """
    One-shot verb to send to a meter as part of `configure_meter`.  Not every vendor
    supports every verb; check capabilities first. Calibrate verbs in particular are
    uncommon outside metering ICs that expose live calibration.
    
    Args:
        none (str)               : Value for NONE
        enable (str)             : Value for ENABLE
        disable (str)            : Value for DISABLE
        reboot (str)             : Value for REBOOT
        calibrate_start (str)    : Value for CALIBRATE_START
        calibrate_finish (str)   : Value for CALIBRATE_FINISH
        enter_unprovisioned (str): Value for ENTER_UNPROVISIONED
    """
    NONE = "none"
    ENABLE = "enable"
    DISABLE = "disable"
    REBOOT = "reboot"
    CALIBRATE_START = "calibrate_start"
    CALIBRATE_FINISH = "calibrate_finish"
    ENTER_UNPROVISIONED = "enter_unprovisioned"