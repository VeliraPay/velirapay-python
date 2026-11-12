"""What every group of endpoints shares."""

from __future__ import annotations

import urllib.parse
from collections.abc import Callable, Mapping, Sequence
from typing import Any, TypeVar

from .._errors import InvalidArgumentError, UnexpectedResponseError
from .._http import ApiResponse
from .._page import Page
from .._requester import Requester, format_amount
from .._resources._base import ApiResource, whole_number

T = TypeVar("T", bound=ApiResource)


class Service:
    """The requests shared by every group of endpoints."""

    __slots__ = ("_requester",)

    def __init__(self, requester: Requester) -> None:
        self._requester = requester

    def _request(
        self,
        method: str,
        path: str,
        body: Mapping[str, object] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Send a request and return the object under the response's "data" key."""
        return data(self._respond(method, path, body, idempotency_key))

    def _respond(
        self,
        method: str,
        path: str,
        body: Mapping[str, object] | None = None,
        idempotency_key: str | None = None,
    ) -> ApiResponse:
        """Send a request and return the whole response, for answers whose meta matters too."""
        return self._requester.request(method, path, None, body, idempotency_key)

    def _page(self, path: str, params: Mapping[str, object] | None, hydrate: Callable[[dict[str, Any]], T]) -> Page[T]:
        """Fetch one page of a list."""
        query = dict(params or {})
        response = self._requester.request("GET", path, query)
        items = [hydrate(item) for item in objects(response)]
        given = response.json().get("meta")
        position: dict[str, Any] = given if isinstance(given, dict) else {}
        current_page = _number(position.get("current_page"), 1)

        return Page(
            items,
            current_page=current_page,
            last_page=_number(position.get("last_page"), current_page),
            per_page=_number(position.get("per_page"), len(items)),
            total=_number(position.get("total"), len(items)),
            meta=position,
            fetch=lambda page: self._page(path, {**query, "page": page}, hydrate),
        )


def data(response: ApiResponse) -> dict[str, Any]:
    """Read the object under a response's "data" key."""
    value = response.json().get("data")

    if not isinstance(value, dict):
        raise UnexpectedResponseError("The VeliraPay API answered without the object it was asked for.", response)

    return value


def meta(response: ApiResponse) -> dict[str, Any]:
    """Read what is under a response's "meta" key."""
    value = response.json().get("meta")

    return value if isinstance(value, dict) else {}


def objects(response: ApiResponse) -> list[dict[str, Any]]:
    """Read the objects of the list under a response's "data" key."""
    value = response.json().get("data")

    if not isinstance(value, list):
        raise UnexpectedResponseError("The VeliraPay API answered without the list it was asked for.", response)

    return [item for item in value if isinstance(item, dict)]


def amounts(params: Mapping[str, object], *keys: str) -> dict[str, object]:
    """The params with the amounts under the given keys, or each amount of a list there, written as decimal strings."""
    body = dict(params)

    for key in keys:
        value = body.get(key)

        if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
            body[key] = [format_amount(item) for item in value]
        elif key in body:
            body[key] = format_amount(value)

    return body


def path(template: str, *ids: str) -> str:
    """Build a path with the given ids escaped into its %s placeholders."""
    shown = template.replace("%s", "{id}")
    escaped: list[str] = []

    for identifier in ids:
        if not isinstance(identifier, str):
            raise InvalidArgumentError(f"The id in {shown} must be a str, not {type(identifier).__name__}.")

        if identifier.strip() == "":
            raise InvalidArgumentError(f"The id in {shown} cannot be empty.")

        # A server, or a proxy before it, reads these as the current and parent path, and the request would go elsewhere.
        if identifier in (".", ".."):
            raise InvalidArgumentError(f'The id in {shown} cannot be "{identifier}".')

        escaped.append(urllib.parse.quote(identifier, safe=""))

    return template % tuple(escaped)


def _number(value: object, fallback: int) -> int:
    """Read an integer from list metadata."""
    number = whole_number(value)

    return fallback if number is None else number
