from __future__ import annotations

from enum import Enum, unique

__all__ = ["LogLevel"]

@unique
class LogLevel(str, Enum):
    """
    LogLevel Enum
    
    Args:
        trace (str)              : Value for TRACE
        debug (str)              : Value for DEBUG
        info (str)               : Value for INFO
        warn (str)               : Value for WARN
        error (str)              : Value for ERROR
    """
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"