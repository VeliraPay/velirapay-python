"""What a transport is given and answers with, and the transport requests go through unless another is given."""

from __future__ import annotations

import email.utils
import json
import math
import re
import ssl
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TypeAlias, cast

from ._errors import UnexpectedResponseError

_SECONDS = re.compile(r"0*([0-9]{1,18})|[0-9]+")
_FOREVER = 10**18
_HTTP_DATE = re.compile(r"[A-Z][a-z]{2}, [0-9]{2} [A-Z][a-z]{2} [0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2} GMT")


@dataclass(frozen=True, slots=True)
class HttpRequest:
    """One attempt of a request, as a transport is asked to send it."""

    method: str
    """The HTTP method, in capitals."""

    url: str
    """The full address, with its query string."""

    headers: Mapping[str, str]
    """The headers to send."""

    body: bytes | None
    """The JSON body, or None for a request without one."""

    timeout: float
    """How many seconds the attempt may wait for the API: to connect, and each time it waits for more of the answer."""


class ApiResponse:
    """A response from the VeliraPay API."""

    __slots__ = ("_decoded", "_parsed", "body", "headers", "status")

    status: int
    """The HTTP status."""

    headers: dict[str, str]
    """The headers, keyed by their name in lower case; repeated ones are joined with a comma."""

    body: str
    """The raw body."""

    def __init__(
        self, status: int, headers: Mapping[str, str] | Iterable[tuple[str, str]] = (), body: str | bytes = ""
    ) -> None:
        combined: dict[str, str] = {}
        pairs = headers.items() if isinstance(headers, Mapping) else headers

        for name, value in cast("Iterable[tuple[str, str]]", pairs):
            key = name.lower()
            combined[key] = f"{combined[key]}, {value}" if key in combined else value

        self.status = status
        self.headers = combined
        self.body = body.decode("utf-8", "replace") if isinstance(body, bytes) else body
        self._decoded: dict[str, Any] | None = None
        self._parsed = False

    def __repr__(self) -> str:
        return f"<ApiResponse {self.status}>"

    def is_successful(self) -> bool:
        """Whether the request succeeded."""
        return 200 <= self.status < 300

    def header(self, name: str) -> str | None:
        """The value of a header."""
        return self.headers.get(name.lower())

    def was_replayed(self) -> bool:
        """Whether the API replayed the response to an earlier request with the same idempotency key."""
        return (self.header("Idempotent-Replayed") or "").lower() == "true"

    def retry_after(self) -> int | None:
        """How many seconds the API asked to wait before trying again."""
        value = self.header("Retry-After")

        if value is None:
            return None

        value = value.strip()
        seconds = _SECONDS.fullmatch(value)

        if seconds is not None:
            # Past 18 digits the wait is longer than anyone keeps, and int() refuses more than 4,300 of them.
            return int(seconds[1]) if seconds[1] is not None else _FOREVER

        if not _HTTP_DATE.fullmatch(value):
            return None

        try:
            at = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None

        return max(0, math.ceil((at - datetime.now(UTC)).total_seconds()))

    def json(self) -> dict[str, Any]:
        """The body as a JSON object, raising an UnexpectedResponseError when it is not one."""
        decoded = self.decode()

        if decoded is None:
            raise UnexpectedResponseError("The VeliraPay API answered with a body that is not a JSON object.", self)

        return decoded

    def decode(self) -> dict[str, Any] | None:
        """The body as a JSON object, or None when it is not one."""
        if not self._parsed:
            self._decoded = _json_object(self.body)
            self._parsed = True

        return self._decoded


Transport: TypeAlias = Callable[[HttpRequest], ApiResponse]
"""Sends one attempt of a request and answers with what the API answered, whatever its status.

It raises an OSError, such as a TimeoutError or a ConnectionError, or an http.client.HTTPException, when the API could not
be reached or its answer could not be read, which is tried again; any other exception reaches the caller unchanged.
"""


class UrllibTransport:
    """Sends requests with urllib from the standard library: through the proxy the environment names, if any, and without following redirects."""

    def __init__(self, *, ssl_context: ssl.SSLContext | None = None) -> None:
        """Create the transport, optionally with the TLS settings to reach the API with, such as another set of trusted certificates."""
        handlers: list[urllib.request.BaseHandler] = [_RefuseRedirects()]

        if ssl_context is not None:
            handlers.append(urllib.request.HTTPSHandler(context=ssl_context))

        self._opener = urllib.request.build_opener(*handlers)

    def __call__(self, request: HttpRequest) -> ApiResponse:
        """Send one attempt of a request."""
        prepared = urllib.request.Request(
            request.url, data=request.body, headers=dict(request.headers), method=request.method
        )

        try:
            response = self._opener.open(prepared, timeout=request.timeout)
        except urllib.error.HTTPError as error:
            # An error status is still an answer, as is a redirect, which is not followed.
            with error:
                return ApiResponse(error.code, list(error.headers.items()), error.read())

        with response:
            return ApiResponse(response.status, list(response.headers.items()), response.read())


class _RefuseRedirects(urllib.request.HTTPRedirectHandler):
    """Leaves a redirect as it is, so that it reaches the caller as an answer instead of being followed."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        return None


def _json_object(body: str) -> dict[str, Any] | None:
    """Decode a body that should hold a JSON object, or None when it does not."""
    if body.strip() == "":
        return None

    try:
        decoded = json.loads(body)
    except (ValueError, RecursionError):
        return None

    return decoded if isinstance(decoded, dict) else None
