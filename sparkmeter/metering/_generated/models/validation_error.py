from __future__ import annotations

from dataclasses import dataclass

from .input_ import Input_
from .validation_error_ctx import ValidationErrorCtx
from .validation_error_loc import ValidationErrorLoc

__all__ = ["ValidationError"]

@dataclass
class ValidationError:
    """
    ValidationError dataclass
    
    Args:
        loc (ValidationErrorLoc) : 
        msg (str)                : 
        type_ (str)              : Maps from 'type'
        ctx (ValidationErrorCtx | None)
                                 : 
        input_ (Input_ | None)   : Maps from 'input'
    """
    loc: ValidationErrorLoc
    msg: str
    type_: str  # Maps from 'type'
    ctx: ValidationErrorCtx | None = None
    input_: Input_ | None = None  # Maps from 'input'
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "ctx": "ctx",
            "input": "input_",
            "loc": "loc",
            "msg": "msg",
            "type": "type_",
        }
        key_transform_with_dump = {
            "ctx": "ctx",
            "input_": "input",
            "loc": "loc",
            "msg": "msg",
            "type_": "type",
        }