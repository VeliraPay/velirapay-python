"""What the tests share: a transport that answers from a queue, the fixtures, and ways to read the requests sent."""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from velirapay import ApiResponse, HttpRequest, VeliraPayClient

FIXTURES = Path(__file__).parent / "fixtures"


class MockTransport:
    """A transport that answers with queued responses and records every request."""

    def __init__(self) -> None:
        self.requests: list[HttpRequest] = []
        self._queue: deque[ApiResponse | BaseException] = deque()

    def queue(self, *responses: ApiResponse | BaseException) -> MockTransport:
        """Queue responses or errors for the next requests."""
        self._queue.extend(responses)

        return self

    def json(self, body: object, status: int = 200, headers: Mapping[str, str] | None = None) -> MockTransport:
        """Queue a JSON response."""
        return self.queue(
            ApiResponse(status, {"Content-Type": "application/json", **(headers or {})}, json.dumps(body))
        )

    def empty(self, status: int = 204) -> MockTransport:
        """Queue an answer without a body, such as a 204."""
        return self.queue(ApiResponse(status))

    def __call__(self, request: HttpRequest) -> ApiResponse:
        self.requests.append(request)

        if not self._queue:
            raise RuntimeError(f"No response was queued for {request.method} {request.url}.")

        answer = self._queue.popleft()

        if isinstance(answer, BaseException):
            raise answer

        return answer

    def last_request(self) -> HttpRequest:
        """The most recent request."""
        if not self.requests:
            raise AssertionError("No request was sent.")

        return self.requests[-1]


def client(
    transport: MockTransport,
    api_key: str = "vp_test_secret",
    *,
    max_retries: int = 0,
    max_retry_after: float = 10,
    app_info: str | None = None,
    base_url: str = VeliraPayClient.DEFAULT_BASE_URL,
) -> VeliraPayClient:
    """A client that sends its requests to the mocked transport, without retries unless asked."""
    return VeliraPayClient(
        api_key,
        transport=transport,
        max_retries=max_retries,
        max_retry_after=max_retry_after,
        app_info=app_info,
        base_url=base_url,
    )


def fixture(name: str) -> dict[str, Any]:
    """A JSON fixture, decoded."""
    decoded: dict[str, Any] = json.loads(payload(name))

    return decoded


def payload(name: str) -> str:
    """A JSON fixture, exactly as it is on disk."""
    return (FIXTURES / f"{name}.json").read_bytes().decode("utf-8")


def list_response(
    data: list[Any],
    *,
    current_page: int = 1,
    last_page: int = 1,
    per_page: int = 25,
    total: int | None = None,
) -> dict[str, Any]:
    """Objects wrapped in a list response."""
    return {
        "data": data,
        "links": {"first": None, "last": None, "prev": None, "next": None},
        "meta": {
            "current_page": current_page,
            "from": None if not data else (current_page - 1) * per_page + 1,
            "last_page": last_page,
            "path": "https://api.velirapay.com/v1/charges",
            "per_page": per_page,
            "to": None if not data else (current_page - 1) * per_page + len(data),
            "total": len(data) if total is None else total,
        },
    }


def body(request: HttpRequest) -> Any:
    """A request's JSON body, decoded."""
    if request.body is None:
        raise AssertionError("The request had no body.")

    return json.loads(request.body)


def path_of(request: HttpRequest) -> str:
    """A request's path."""
    return urlsplit(request.url).path


def query_of(request: HttpRequest) -> dict[str, str]:
    """A request's query parameters."""
    return dict(parse_qsl(urlsplit(request.url).query, keep_blank_values=True))
