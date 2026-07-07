from __future__ import annotations

from dataclasses import dataclass

__all__ = ["CommandAccepted"]

@dataclass
class CommandAccepted:
    """
    HTTP-level acknowledgement that the request was received and validated.  This is NOT the
    command's terminal reply — that comes via SSE, keyed by `correlation_id`. The HTTP `202`
    simply confirms the command was syntactically valid and queued for processing.
    
    Args:
        correlation_id (str)     : 
        queued (bool | None)     : 
    """
    correlation_id: str
    queued: bool | None = True
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "correlation_id": "correlation_id",
            "queued": "queued",
        }
        key_transform_with_dump = {
            "correlation_id": "correlation_id",
            "queued": "queued",
        }