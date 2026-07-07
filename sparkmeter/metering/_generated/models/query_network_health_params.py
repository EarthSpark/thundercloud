from __future__ import annotations

from dataclasses import dataclass

from .query_network_health_params_meter_id import QueryNetworkHealthParamsMeterId

__all__ = ["QueryNetworkHealthParams"]

@dataclass
class QueryNetworkHealthParams:
    """
    Optional `meter_id` filters the response to one meter; omit for the whole network.
    
    Args:
        meter_id (QueryNetworkHealthParamsMeterId | None)
                                 : 
    """
    meter_id: QueryNetworkHealthParamsMeterId | None = None
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "meter_id": "meter_id",
        }
        key_transform_with_dump = {
            "meter_id": "meter_id",
        }