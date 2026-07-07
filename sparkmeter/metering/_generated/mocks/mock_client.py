from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import APIClientProtocol
    from ..endpoints.default import DefaultClientProtocol

from .endpoints.mock_default import MockDefaultClient

class MockAPIClient:
    """
    Mock implementation of APIClient for testing.
    
    Auto-creates default mock implementations for all tag-based endpoint clients.
    You can override specific tag clients by passing them to the constructor.
    
    Example:
        # Use all defaults
        client = MockAPIClient()
    
        # Override specific tag client
        class MyDefaultClientMock(MockDefaultClient):
            async def method_name(self, ...) -> ReturnType:
                return test_data
    
        client = MockAPIClient(default=MyDefaultClientMock())
    """
    
    def __init__(
        self,
        default: "DefaultClientProtocol | None" = None,
    ) -> None:
        self._default = default if default is not None else MockDefaultClient()
    
    @property
    def default(self) -> "DefaultClientProtocol":
        return self._default
    
    async def request(self, method: str, url: str, **kwargs: Any) -> Any:
        """
        Mock request method - raises NotImplementedError.
        
        This is a low-level method - consider using tag-specific methods instead.
        """
        raise NotImplementedError("MockAPIClient.request() not implemented. Use tag-specific methods instead.")
    
    async def close(self) -> None:
        """Mock close method - no-op for testing."""
        pass  # No cleanup needed for mocks
    
    async def __aenter__(self) -> "APIClientProtocol":
        """Enter async context manager."""
        return self
    
    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object | None) -> None:
        """Exit async context manager - no-op for mocks."""
        pass  # No cleanup needed for mocks