from typing import Any, AsyncIterator, Dict, NoReturn, TYPE_CHECKING

from ...models.command_accepted import CommandAccepted
from ...models.stream_events_v_1_events_get_param_client_id import StreamEventsV1EventsGetParamClientId
from ...models.stream_events_v_1_events_get_param_types import StreamEventsV1EventsGetParamTypes
from ...models.submit_command_v_1_commands_post_request_body import SubmitCommandV1CommandsPostRequestBody
from sparkmeter.metering._generated.core import UnprocessableEntityError
from sparkmeter.metering._generated.core.cattrs_converter import structure_from_dict
from sparkmeter.metering._generated.core.exceptions import HTTPError
from sparkmeter.metering._generated.core.http_transport import HttpTransport
from sparkmeter.metering._generated.core.streaming_helpers import iter_sse_events_text
from sparkmeter.metering._generated.core.utils import DataclassSerializer

import collections.abc
import json

from ...models.command_accepted import CommandAccepted
from ...models.stream_events_v_1_events_get_param_client_id import StreamEventsV1EventsGetParamClientId
from ...models.stream_events_v_1_events_get_param_types import StreamEventsV1EventsGetParamTypes
from ...models.submit_command_v_1_commands_post_request_body import SubmitCommandV1CommandsPostRequestBody

if TYPE_CHECKING:
    from ...endpoints.default import DefaultClientProtocol

class MockDefaultClient:
    """
    Mock implementation of DefaultClient for testing.
    
    Provides default implementations that raise NotImplementedError.
    Override methods as needed in your tests.
    
    Example:
        class TestDefaultClient(MockDefaultClient):
            async def method_name(self, ...) -> ReturnType:
                return test_data
    """
    
    async def submit_command_v1_commands_post(
    self,
    body: SubmitCommandV1CommandsPostRequestBody,
    ) -> CommandAccepted:
        """
        Mock implementation that raises NotImplementedError.
        
        Override this method in your test subclass to provide
        the behavior needed for your test scenario.
        """
        raise NotImplementedError("MockClient_Client.submit_command_v1_commands_post() not implemented. Override this method in your test subclass.")
    
    
    async def stream_events_v1_events_get(
    self,
    types: StreamEventsV1EventsGetParamTypes | None = None,
    client_id: StreamEventsV1EventsGetParamClientId | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Mock implementation that raises NotImplementedError.
        
        Override this method in your test subclass to provide
        the behavior needed for your test scenario.
        """
        raise NotImplementedError("MockClient_Client.stream_events_v1_events_get() not implemented. Override this method in your test subclass.")
        yield  # pragma: no cover