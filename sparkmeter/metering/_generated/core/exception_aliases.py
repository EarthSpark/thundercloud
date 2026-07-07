from httpx import Response
from sparkmeter.metering._generated.core.exceptions import ClientError, ServerError

class UnprocessableEntityError(ClientError):
    """HTTP 422 Unprocessable Entity.

Raised when the server responds with a 422 status code."""
    def __init__(self, response: Response) -> None:
        """Initialise UnprocessableEntityError with the HTTP response.

        Args:
            response: The httpx Response object that triggered this exception
        """
        super().__init__(status_code=response.status_code, message=response.text, response=response)


__all__ = ["UnprocessableEntityError"]
