from typing import Any, Dict, Protocol, runtime_checkable

from sparkmeter.metering._generated.core.auth.plugins import ApiKeyAuth
from sparkmeter.metering._generated.core.config import ClientConfig
from sparkmeter.metering._generated.core.http_transport import HttpTransport, HttpxTransport

from .endpoints.default import DefaultClient, DefaultClientProtocol

@runtime_checkable
class APIClientProtocol(Protocol):
    """Protocol defining the interface of APIClient for dependency injection."""
    
    @property
    def default(self) -> 'DefaultClientProtocol':
        ...
    
    async def request(self, method: str, url: str, **kwargs: Any) -> Any:
        ...
    
    async def close(self) -> None:
        ...
    
    async def __aenter__(self) -> 'APIClientProtocol':
        ...
    
    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object | None) -> None:
        ...


class APIClient(APIClientProtocol):
    """
metering-provider (version 0.1.0)

Vendor-agnostic metering provider HTTP+SSE API.


Async API client with pluggable transport, tag-specific clients, and client-level
headers.

Args:
    config (ClientConfig)    : Client configuration object.
    transport (HttpTransport | None)
                             : Custom HTTP transport (optional).
    default (DefaultClient)  : Client for 'default' endpoints.

    """
    def __init__(self, config: ClientConfig, transport: HttpTransport | None = None) -> None:
        self.config = config
        self.transport = transport if transport is not None else HttpxTransport(str(config.base_url), config.timeout)
        self._base_url: str = str(self.config.base_url)
        self._default: DefaultClient | None = None
    
    @property
    def default(self) -> DefaultClient:
        """Client for 'default' endpoints."""
        if self._default is None:
            self._default = DefaultClient(self.transport, self._base_url)
        return self._default
    
    async def request(self, method: str, url: str, **kwargs: Any) -> Any:
        """Send an HTTP request via the transport."""
        return await self.transport.request(method, url, **kwargs)
    
    async def close(self) -> None:
        """Close the underlying transport if supported."""
        if hasattr(self.transport, 'close'):
            await self.transport.close()
        else:
            pass  # Or log a warning if close is expected but not found
    
    async def __aenter__(self) -> 'APIClient':
        """Enter the async context manager. Returns self."""
        if hasattr(self.transport, '__aenter__'):
            await self.transport.__aenter__()
        return self
    
    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object | None) -> None:
        """Exit the async context manager, ensuring transport is closed."""
        if hasattr(self.transport, '__aexit__'):
            await self.transport.__aexit__(exc_type, exc_val, exc_tb)
        else:
            await self.close()
    