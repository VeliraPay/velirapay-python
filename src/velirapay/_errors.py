"""The errors this library raises, all of them a VeliraPayError."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ._http import ApiResponse


class VeliraPayError(Exception):
    """The base of every error this library raises."""

    message: str
    """What went wrong."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ApiError(VeliraPayError):
    """Raised when the API answers with an error."""

    status: int
    """The HTTP status the API answered with."""

    body: dict[str, Any]
    """The decoded JSON body of the response, or an empty dict when it had none."""

    response: ApiResponse
    """The response itself."""

    def __init__(self, message: str, response: ApiResponse) -> None:
        super().__init__(message)
        self.response = response
        self.status = response.status
        self.body = response.decode() or {}

    def __reduce__(self) -> tuple[Any, ...]:
        return type(self), (self.message, self.response)

    @staticmethod
    def from_response(response: ApiResponse) -> ApiError:
        """Create the error that matches the response's status."""
        message = (response.decode() or {}).get("message")
        text = (
            message
            if isinstance(message, str) and message != ""
            else f"The VeliraPay API answered with HTTP {response.status}."
        )

        match response.status:
            case 401:
                return AuthenticationError(text, response)
            case 403:
                return PermissionDeniedError(text, response)
            case 404:
                return NotFoundError(text, response)
            case 409:
                return ConflictError(text, response)
            case 422:
                return ValidationError(text, response)
            case 429:
                return RateLimitError(text, response)
            case status if status >= 500:
                return ServerError(text, response)
            case _:
                return InvalidRequestError(text, response)

    def header(self, name: str) -> str | None:
        """The value of a response header."""
        return self.response.header(name)

    def retry_after(self) -> int | None:
        """How many seconds the API asked to wait before trying again, or None when it did not say."""
        return self.response.retry_after()


class AuthenticationError(ApiError):
    """The API key is missing, revoked or unknown (401)."""


class PermissionDeniedError(ApiError):
    """The API key may not do what was asked (403)."""


class NotFoundError(ApiError):
    """The object does not exist for this account and mode (404)."""


class ConflictError(ApiError):
    """The object's state does not allow the action, or an idempotency key was reused for a different request or is held by one still being processed (409)."""


class ValidationError(ApiError):
    """The request failed validation (422)."""

    def errors(self) -> dict[str, list[str]]:
        """The validation messages keyed by field, such as "amount" or "items.0.quantity"."""
        given = self.body.get("errors")

        if isinstance(given, list):
            given = {str(index): messages for index, messages in enumerate(given)}

        if not isinstance(given, dict):
            return {}

        return {
            str(field): [
                message
                for message in (messages if isinstance(messages, list) else [messages])
                if isinstance(message, str)
            ]
            for field, messages in given.items()
        }

    def first_error(self, field: str) -> str | None:
        """The first validation message for a field."""
        messages = self.errors().get(field, [])

        return messages[0] if messages else None


class RateLimitError(ApiError):
    """Too many requests were made, or a limit such as emailing an invoice again was reached (429)."""


class ServerError(ApiError):
    """The API failed to handle the request (5xx)."""


class InvalidRequestError(ApiError):
    """The request was malformed (400 and other client errors), or was answered with a redirect, which is not followed."""


class UnexpectedResponseError(ApiError):
    """The API answered with something this library cannot read."""


class ApiConnectionError(VeliraPayError):
    """The API could not be reached, or its answer not read, after any retries."""


class SignatureVerificationError(VeliraPayError):
    """A webhook delivery's signature is missing, invalid or too old."""


class InvalidArgumentError(VeliraPayError, ValueError):
    """The library was given something it cannot use."""
