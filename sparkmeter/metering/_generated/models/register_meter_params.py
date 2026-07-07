from __future__ import annotations

from dataclasses import dataclass

from .register_meter_params_firmware_version import RegisterMeterParamsFirmwareVersion
from .register_meter_params_initial_balance import RegisterMeterParamsInitialBalance

__all__ = ["RegisterMeterParams"]

@dataclass
class RegisterMeterParams:
    """
    Add a meter to the provider's roster.  `meter_type` is a vendor-defined model code (e.g.
    `SM5R`, `SMHCE`). Set it to whatever the vendor's capabilities report supports.
    `firmware_version` is optional and seeds capability detection on vendors that gate
    features by version.  `initial_balance` and `initial_low_balance` set the meter's
    display credit at registration. They have the same semantics as a subsequent
    `set_balance` call: cached at the provider, delivered opportunistically.
    `request_phased_readings`, when true on a multi-phase-capable meter, causes the provider
    to emit `meter_reading_phased` events instead of `meter_reading`. Cannot be flipped
    after registration: unregister and re-register to switch.
    
    Args:
        meter_id (str)           : 
        meter_type (str)         : 
        firmware_version (RegisterMeterParamsFirmwareVersion | None)
                                 : 
        initial_balance (RegisterMeterParamsInitialBalance | None)
                                 : 
        initial_low_balance (bool | None)
                                 : 
        request_phased_readings (bool | None)
                                 : 
    """
    meter_id: str
    meter_type: str
    firmware_version: RegisterMeterParamsFirmwareVersion | None = None
    initial_balance: RegisterMeterParamsInitialBalance | None = None
    initial_low_balance: bool | None = False
    request_phased_readings: bool | None = False
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "firmware_version": "firmware_version",
            "initial_balance": "initial_balance",
            "initial_low_balance": "initial_low_balance",
            "meter_id": "meter_id",
            "meter_type": "meter_type",
            "request_phased_readings": "request_phased_readings",
        }
        key_transform_with_dump = {
            "firmware_version": "firmware_version",
            "initial_balance": "initial_balance",
            "initial_low_balance": "initial_low_balance",
            "meter_id": "meter_id",
            "meter_type": "meter_type",
            "request_phased_readings": "request_phased_readings",
        }