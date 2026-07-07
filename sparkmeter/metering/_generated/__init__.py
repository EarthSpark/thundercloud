# Client package __init__.py
# Re-exports from core and local client.

from sparkmeter.metering._generated.core.auth import BaseAuth, ApiKeyAuth, BearerAuth, OAuth2Auth
from sparkmeter.metering._generated.core.config import ClientConfig
from sparkmeter.metering._generated.core.exceptions import HTTPError, ClientError, ServerError
from sparkmeter.metering._generated.core.exception_aliases import *  # noqa: F401, F403
from sparkmeter.metering._generated.core.http_transport import HttpTransport, HttpxTransport
from sparkmeter.metering._generated.core.cattrs_converter import structure_from_dict, unstructure_to_dict, converter
from .client import APIClient

__all__ = [
    "APIClient",
    "BaseAuth", "ApiKeyAuth", "BearerAuth", "OAuth2Auth",
    "ClientConfig",
    "HTTPError", "ClientError", "ServerError",
    "HttpTransport", "HttpxTransport",
    "structure_from_dict", "unstructure_to_dict", "converter",
]
