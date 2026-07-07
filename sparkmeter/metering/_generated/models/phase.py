from __future__ import annotations

from enum import Enum, unique

__all__ = ["Phase"]

@unique
class Phase(str, Enum):
    """
    Three-phase electrical phase identifier.
    
    Args:
        a (str)                  : Value for A
        b (str)                  : Value for B
        c (str)                  : Value for C
    """
    A = "a"
    B = "b"
    C = "c"