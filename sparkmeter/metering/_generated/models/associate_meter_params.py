from __future__ import annotations

from dataclasses import dataclass

from .associate_meter_params_set_aes_key import AssociateMeterParamsSetAesKey
from .associate_meter_params_set_channel import AssociateMeterParamsSetChannel
from .associate_meter_params_set_mac import AssociateMeterParamsSetMac

__all__ = ["AssociateMeterParams"]

@dataclass
class AssociateMeterParams:
    """
    Onboard a physical meter onto the network.  Distinct from `register_meter`, which adds a
    meter to the provider's roster. `associate_meter` is the over-the-air operation that
    gives a previously-unprovisioned meter its network identity (MAC, channel, AES key).
    All three optional fields target the meter's persistent network configuration. Provide
    whichever the operator wants to set.
    
    Args:
        meter_id (str)           : 
        set_aes_key (AssociateMeterParamsSetAesKey | None)
                                 : Raw 16-byte network key.
        set_channel (AssociateMeterParamsSetChannel | None)
                                 : 
        set_mac (AssociateMeterParamsSetMac | None)
                                 : 
    """
    meter_id: str
    set_aes_key: AssociateMeterParamsSetAesKey | None = None  # Raw 16-byte network key.
    set_channel: AssociateMeterParamsSetChannel | None = None
    set_mac: AssociateMeterParamsSetMac | None = None
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "meter_id": "meter_id",
            "set_aes_key": "set_aes_key",
            "set_channel": "set_channel",
            "set_mac": "set_mac",
        }
        key_transform_with_dump = {
            "meter_id": "meter_id",
            "set_aes_key": "set_aes_key",
            "set_channel": "set_channel",
            "set_mac": "set_mac",
        }