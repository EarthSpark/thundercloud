# Re-export core exceptions and generated aliases
from .exceptions import HTTPError, ClientError, ServerError
from .exception_aliases import *  # noqa: F403

# Re-export other commonly used core components
from .http_transport import HttpTransport, HttpxTransport
from .config import ClientConfig
from .cattrs_converter import structure_from_dict, unstructure_to_dict, converter
from .utils import DataclassSerializer
from .auth.base import BaseAuth
from .auth.plugins import ApiKeyAuth, BearerAuth, OAuth2Auth

__all__ = [
    # Base exceptions
    "HTTPError",
    "ClientError",
    "ServerError",
    # All ErrorXXX from exception_aliases are implicitly in __all__ due to star import

    # Transport layer
    "HttpTransport",
    "HttpxTransport",

    # Configuration
    "ClientConfig",

    # Serialization (cattrs)
    "structure_from_dict",
    "unstructure_to_dict",
    "converter",

    # Utilities
    "DataclassSerializer",

    # Authentication
    "BaseAuth",
    "ApiKeyAuth",
    "BearerAuth",
    "OAuth2Auth",
    # Generated exception aliases
    "UnprocessableEntityError",
]