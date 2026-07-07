from __future__ import annotations

from dataclasses import dataclass

from .set_balance_params_balance import SetBalanceParamsBalance

__all__ = ["SetBalanceParams"]

@dataclass
class SetBalanceParams:
    """
    Push display credit to be shown to the customer at the meter.  The `balance` is a
    currency value with arbitrary precision. The `low_balance` flag is an out-of-band signal
    independent of the balance value (vendors that can't render arbitrary balances may still
    use this flag to drive a low-credit indicator).
    
    Args:
        balance (SetBalanceParamsBalance)
                                 : 
        meter_id (str)           : 
        low_balance (bool | None): 
    """
    balance: SetBalanceParamsBalance
    meter_id: str
    low_balance: bool | None = False
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "balance": "balance",
            "low_balance": "low_balance",
            "meter_id": "meter_id",
        }
        key_transform_with_dump = {
            "balance": "balance",
            "low_balance": "low_balance",
            "meter_id": "meter_id",
        }