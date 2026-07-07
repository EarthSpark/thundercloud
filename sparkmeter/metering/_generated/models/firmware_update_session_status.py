from __future__ import annotations

from enum import Enum, unique

__all__ = ["FirmwareUpdateSessionStatus"]

@unique
class FirmwareUpdateSessionStatus(str, Enum):
    """
    FirmwareUpdateSessionStatus Enum
    
    Args:
        starting (str)           : Value for STARTING
        in_progress (str)        : Value for IN_PROGRESS
        completed (str)          : Value for COMPLETED
        cancelled (str)          : Value for CANCELLED
        failed (str)             : Value for FAILED
    """
    STARTING = "starting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"