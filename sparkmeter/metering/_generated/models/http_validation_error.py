from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .validation_error import ValidationError

__all__ = ["HttpValidationError"]

@dataclass
class HttpValidationError:
    """
    HttpValidationError dataclass
    
    Args:
        detail (List[ValidationError] | None)
                                 : 
    """
    detail: List[ValidationError] | None = field(default_factory=list)
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "detail": "detail",
        }
        key_transform_with_dump = {
            "detail": "detail",
        }