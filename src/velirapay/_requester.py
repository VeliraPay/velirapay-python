"""Sends requests to the VeliraPay API, trying again when that is safe, and turns its answers into responses or errors."""

from __future__ import annotations

import http.client
import json
import math
import random
import re
import threading
import time
import urllib.error
import urllib.parse
import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum

from ._errors import ApiConnectionError, ApiError, InvalidArgumentError
from ._http import ApiResponse, HttpRequest, Transport

_RETRYABLE_STATUSES = frozenset({429, 502, 503, 504, 520, 521, 522, 523, 524})
"""The statuses worth another attempt for any request, Cloudflare's 520 to 524 for an origin it got no answer from included."""

_NETWORK_ERRORS = (OSError, http.client.HTTPException)
"""What a transport raises when the API could not be reached or its answer not read."""

_HEADER_VALUE = re.compile(r"[\x20-\x7e]*")


class Requester:
    """Sends requests to the API on behalf of every group of endpoints."""

    def __init__(
        self,
        *,
        api_key: str,
        transport: Transport,
        base_url: str,
        max_retries: int,
        max_retry_after: float,
        timeout: float,
        user_agent: str,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api_key = api_key
        self._transport = transport
        self._base_url = base_url
        self._max_retries = max_retries
        self._max_retry_after = max_retry_after
        self._timeout = timeout
        self._user_agent = user_agent
        self._sleep = sleep
        self._local = threading.local()

    def request(
        self,
        method: str,
        path: str,
        query: Mapping[str, object] | None = None,
        body: Mapping[str, object] | None = None,
        idempotency_key: str | None = None,
    ) -> ApiResponse:
        """Send a request and return the successful response."""
        method = method.upper()

        if idempotency_key is not None and (
            idempotency_key.strip() == "" or not _HEADER_VALUE.fullmatch(idempotency_key)
        ):
            raise InvalidArgumentError(
                "An idempotency key is sent as a header, so it must be printable ASCII and not blank, such as order-1042-attempt-1."
            )

        # A retried write must not be carried out twice, so every attempt carries the same key.
        if method != "GET" and idempotency_key is None and self._max_retries > 0:
            idempotency_key = str(uuid.uuid4())

        request = HttpRequest(
            method=method,
            url=self._url(path, query),
            headers=self._headers(body is not None, idempotency_key),
            body=None if body is None else encode_body(body),
            timeout=self._timeout,
        )
        attempt = 0

        while True:
            try:
                response = self._transport(request)
            except _NETWORK_ERRORS as error:
                if attempt >= self._max_retries:
                    raise ApiConnectionError(f"Could not reach the VeliraPay API: {self._reason(error)}") from error

                self._sleep(_backoff(attempt))
                attempt += 1

                continue

            self._local.last_response = response

            if response.is_successful():
                return response

            delay = self._retry_delay(method, response, attempt)

            if delay is None:
                raise ApiError.from_response(response)

            self._sleep(delay)
            attempt += 1

    def last_response(self) -> ApiResponse | None:
        """The response to the most recent request made in this thread."""
        response: ApiResponse | None = getattr(self._local, "last_response", None)

        return response

    def _retry_delay(self, method: str, response: ApiResponse, attempt: int) -> float | None:
        """How long to wait before trying a failed request again, or None when it should not be retried."""
        if attempt >= self._max_retries:
            return None

        retry_after = response.retry_after()

        # A conflict that says when to come back is an earlier request with the same idempotency key still being processed.
        retryable = (
            response.status in _RETRYABLE_STATUSES
            or (response.status == 500 and method == "GET")
            or (response.status == 409 and retry_after is not None)
        )

        if not retryable:
            return None

        if retry_after is None:
            return _backoff(attempt)

        return float(retry_after) if retry_after <= self._max_retry_after else None

    def _url(self, path: str, query: Mapping[str, object] | None) -> str:
        """The address of a path, with its query string."""
        url = f"{self._base_url.rstrip('/')}/{path.lstrip('/')}"
        pairs: list[tuple[str, str]] = []

        for key, value in (query or {}).items():
            _append_query(pairs, key, value)

        return f"{url}?{urllib.parse.urlencode(pairs, quote_via=urllib.parse.quote)}" if pairs else url

    def _headers(self, has_body: bool, idempotency_key: str | None) -> dict[str, str]:
        """The headers every attempt of a request carries."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
            "User-Agent": self._user_agent,
        }

        if has_body:
            headers["Content-Type"] = "application/json"

        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key

        return headers

    def _reason(self, error: BaseException) -> str:
        """Say why a request could not reach the API."""
        reason: object = error.reason if isinstance(error, urllib.error.URLError) else error

        if isinstance(reason, TimeoutError):
            return f"no answer within {self._timeout:g} seconds."

        return str(reason) or type(reason).__name__


def encode_body(body: Mapping[str, object]) -> bytes:
    """Encode a request body as JSON."""
    try:
        return json.dumps(body, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=_json_value).encode(
            "utf-8"
        )
    except InvalidArgumentError:
        raise
    except (TypeError, ValueError, RecursionError) as error:
        raise InvalidArgumentError(f"The request could not be encoded as JSON: {error}") from error


def format_datetime(value: datetime) -> str:
    """Write a moment in ISO 8601, in UTC, which the API reads it in; a datetime without a time zone is taken as UTC."""
    moment = value.replace(tzinfo=UTC) if value.utcoffset() is None else value.astimezone(UTC)

    return moment.isoformat()


def _json_value(value: object) -> object:
    """Turn what JSON has no type for into the value the API expects."""
    if isinstance(value, Enum):
        return value.value

    if isinstance(value, datetime):
        return format_datetime(value)

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, Decimal):
        return _format_decimal(value)

    if isinstance(value, Mapping):
        return dict(value)

    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return list(value)

    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _append_query(pairs: list[tuple[str, str]], key: str, value: object) -> None:
    """Add a parameter to a query string, leaving out None."""
    if value is None:
        return

    if isinstance(value, bool):
        pairs.append((key, "1" if value else "0"))
    elif isinstance(value, Enum):
        _append_query(pairs, key, value.value)
    elif isinstance(value, str):
        pairs.append((key, value))
    elif isinstance(value, datetime):
        pairs.append((key, format_datetime(value)))
    elif isinstance(value, date):
        pairs.append((key, value.isoformat()))
    elif isinstance(value, Decimal):
        pairs.append((key, _format_decimal(value)))
    elif isinstance(value, int):
        pairs.append((key, str(value)))
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidArgumentError(f"The query parameter {key} cannot be {value}.")

        pairs.append((key, repr(value)))
    elif isinstance(value, Mapping):
        for name, item in value.items():
            _append_query(pairs, f"{key}[{name}]", item)
    elif isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        for index, item in enumerate(value):
            _append_query(pairs, f"{key}[{index}]", item)
    else:
        raise InvalidArgumentError(f"The query parameter {key} cannot be sent as a {type(value).__name__}.")


def format_amount(value: object) -> object:
    """Write an amount given as a number as a decimal string without an exponent, leaving anything else as it is.

    A float is rounded to 14 significant digits first, the precision the API reads a JSON number with, so 0.1 + 0.2 is
    sent as "0.3" and 0.00005 as "0.00005" rather than as the "5e-05" the API refuses.
    """
    if isinstance(value, bool):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidArgumentError(f"The amount {value} cannot be sent.")

        return format(Decimal(format(value, ".14g")), "f")

    if isinstance(value, int):
        return str(value)

    if isinstance(value, Decimal):
        return _format_decimal(value)

    return value


def _format_decimal(value: Decimal) -> str:
    """Write a Decimal with every digit it has and no exponent."""
    if not value.is_finite():
        raise InvalidArgumentError(f"The amount {value} cannot be sent.")

    return format(value, "f")


def _backoff(attempt: int) -> float:
    """The wait before an attempt, in seconds: half a second, doubling each time, with some jitter."""
    return min(8.0, 0.5 * 2.0**attempt) * (0.75 + random.random() * 0.5)
