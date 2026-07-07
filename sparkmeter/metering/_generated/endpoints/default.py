from typing import Any, AsyncIterator, Callable, Dict, NoReturn, Optional, Protocol, cast, runtime_checkable

from ..models.command_accepted import CommandAccepted
from ..models.stream_events_v_1_events_get_param_client_id import StreamEventsV1EventsGetParamClientId
from ..models.stream_events_v_1_events_get_param_types import StreamEventsV1EventsGetParamTypes
from ..models.submit_command_v_1_commands_post_request_body import SubmitCommandV1CommandsPostRequestBody
from sparkmeter.metering._generated.core import UnprocessableEntityError
from sparkmeter.metering._generated.core.cattrs_converter import structure_from_dict
from sparkmeter.metering._generated.core.exceptions import HTTPError
from sparkmeter.metering._generated.core.http_transport import HttpTransport
from sparkmeter.metering._generated.core.streaming_helpers import iter_bytes, iter_sse_events_text
from sparkmeter.metering._generated.core.utils import DataclassSerializer

import collections.abc
import json

from ..models.command_accepted import CommandAccepted
from ..models.stream_events_v_1_events_get_param_client_id import StreamEventsV1EventsGetParamClientId
from ..models.stream_events_v_1_events_get_param_types import StreamEventsV1EventsGetParamTypes
from ..models.submit_command_v_1_commands_post_request_body import SubmitCommandV1CommandsPostRequestBody

@runtime_checkable
class DefaultClientProtocol(Protocol):
    """Protocol defining the interface of DefaultClient for dependency injection."""
    
    async def submit_command_v1_commands_post(
    self,
    body: SubmitCommandV1CommandsPostRequestBody,
    ) -> CommandAccepted: ...
    
    def stream_events_v1_events_get(
    self,
    types: StreamEventsV1EventsGetParamTypes | None = None,
    client_id: StreamEventsV1EventsGetParamClientId | None = None,
    ) -> AsyncIterator[dict[str, Any]]: ...
    


class DefaultClient(DefaultClientProtocol):
    """Client for default endpoints. Uses HttpTransport for all HTTP and header management."""
    
    def __init__(self, transport: HttpTransport, base_url: str) -> None:
        self._transport = transport
        self.base_url: str = base_url
    
    async def submit_command_v1_commands_post(
        self,
        body: SubmitCommandV1CommandsPostRequestBody,
    ) -> CommandAccepted:
        """
        Submit Command
        
        Args:
            body (SubmitCommandV1CommandsPostRequestBody)
                                     : Request body. (json)
        
        Returns:
            CommandAccepted: Successful Response
        
        Raises:
            HttpError:
                HTTPError: 422: Validation Error
        """
        url = f"{self.base_url}/v1/commands"
        
        json_body: SubmitCommandV1CommandsPostRequestBody = DataclassSerializer.serialize(body)
        
        response = await self._transport.request("POST", url, params=None, json=json_body, headers=None)
        
        # Check response status code and handle accordingly
        match response.status_code:
            case 202:
                return structure_from_dict(response.json(), CommandAccepted)
            case 422:
                raise UnprocessableEntityError(response=response)
            case _:
                raise HTTPError(response=response, message="Unhandled status code", status_code=response.status_code)
        # All paths above should return or raise - this should never execute
        raise RuntimeError('Unexpected code path')  # pragma: no cover
    
    
    async def stream_events_v1_events_get(
        self,
        types: StreamEventsV1EventsGetParamTypes | None = None,
        client_id: StreamEventsV1EventsGetParamClientId | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Stream Events
        
        Args:
            types (StreamEventsV1EventsGetParamTypes | None)
                                     : Comma-separated event_type filter; omit for all events.
            client_id (StreamEventsV1EventsGetParamClientId | None)
                                     : Stable client identifier for command-reply routing. If
                                       omitted, the server assigns a fresh UUID.
        
        Returns:
            AsyncIterator[dict[str, Any]]: Long-lived Server-Sent Events stream. Each event's
                                           `data:` payload is a JSON-encoded `Event` (one of the
                                           variants in `components.schemas`).
        
        Raises:
            HttpError:
                HTTPError: 422: Validation Error
        """
        url = f"{self.base_url}/v1/events"
        
        params: dict[str, Any] = {
            **({"types": DataclassSerializer.serialize(types)} if types is not None else {}),
            **({"client_id": DataclassSerializer.serialize(client_id)} if client_id is not None else {}),
        }
        
        response = await self._transport.request(
            "GET", url,
            params=params,
            json=None,
            data=None,
            headers=None
        )
        
        # Check response status code and handle accordingly
        match response.status_code:
            case 200:
                async for chunk in iter_sse_events_text(response):
                    yield json.loads(chunk)
                return  # Explicit return for async generator
            case 422:
                raise UnprocessableEntityError(response=response)
            case _:
                raise HTTPError(response=response, message="Unhandled status code", status_code=response.status_code)
        # All paths above should return or raise - this should never execute
        raise RuntimeError('Unexpected code path')  # pragma: no cover