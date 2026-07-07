from __future__ import annotations

from dataclasses import dataclass

from .meter_neighbor_last_seen_unix_seconds import MeterNeighborLastSeenUnixSeconds
from .meter_neighbor_link_quality import MeterNeighborLinkQuality
from .meter_neighbor_rssi_dbm import MeterNeighborRssiDbm

__all__ = ["MeterNeighbor"]

@dataclass
class MeterNeighbor:
    """
    MeterNeighbor dataclass
    
    Args:
        neighbor_id (str)        : 
        last_seen_unix_seconds (MeterNeighborLastSeenUnixSeconds | None)
                                 : 
        link_quality (MeterNeighborLinkQuality | None)
                                 : 
        rssi_dbm (MeterNeighborRssiDbm | None)
                                 : 
    """
    neighbor_id: str
    last_seen_unix_seconds: MeterNeighborLastSeenUnixSeconds | None = None
    link_quality: MeterNeighborLinkQuality | None = None
    rssi_dbm: MeterNeighborRssiDbm | None = None
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "last_seen_unix_seconds": "last_seen_unix_seconds",
            "link_quality": "link_quality",
            "neighbor_id": "neighbor_id",
            "rssi_dbm": "rssi_dbm",
        }
        key_transform_with_dump = {
            "last_seen_unix_seconds": "last_seen_unix_seconds",
            "link_quality": "link_quality",
            "neighbor_id": "neighbor_id",
            "rssi_dbm": "rssi_dbm",
        }