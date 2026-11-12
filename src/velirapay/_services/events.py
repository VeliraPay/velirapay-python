"""The /v1/events endpoints."""

from __future__ import annotations

from collections.abc import Iterator

from .._page import Page
from .._params import EventListParams
from .._resources.event import Event
from ._base import Service, path


class EventService(Service):
    """The /v1/events endpoints."""

    __slots__ = ()

    def retrieve(self, id: str) -> Event:
        """Retrieve an event by its id."""
        return Event(self._request("GET", path("/v1/events/%s", id)))

    def list(self, params: EventListParams | None = None) -> Page[Event]:
        """List events, newest first."""
        return self._page("/v1/events", params, Event)

    def iterator(self, params: EventListParams | None = None) -> Iterator[Event]:
        """Iterate over every event, newest first, fetching pages as they are reached."""
        yield from self.list(params).auto_paging_iterator()
