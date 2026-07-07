"""
Mock implementations for testing.

These mocks implement the Protocol contracts without requiring
network transport or authentication. Use them as base classes
in your tests.

Example:
    from myapi.mocks import MockAPIClient, MockPetsClient

    class TestPetsClient(MockPetsClient):
        async def list_pets(self, limit: int | None = None) -> list[Pet]:
            return [Pet(id=1, name='Test Pet')]

    client = MockAPIClient(pets=TestPetsClient())
"""

from .mock_client import MockAPIClient
from .endpoints.mock_default import MockDefaultClient

__all__ = [
    "MockAPIClient",
    "MockDefaultClient",
]