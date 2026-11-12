"""The account's activity log."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ._base import ApiResource, mapping, nullable_string, string, timestamp


class Activity(ApiResource):
    """One thing done in the account, from its activity log."""

    __slots__ = ()

    @property
    def id(self) -> str:
        """The entry's id."""
        return string(self._attributes, "id")

    @property
    def action(self) -> str:
        """What was done, such as "api_key.created"."""
        return string(self._attributes, "action")

    @property
    def description(self) -> str:
        """What was done, in words."""
        return string(self._attributes, "description")

    @property
    def actor(self) -> str | None:
        """Who did it: a member's name or an API key's."""
        return nullable_string(self._attributes, "actor")

    @property
    def subject(self) -> str | None:
        """What it was done to."""
        return nullable_string(self._attributes, "subject")

    @property
    def properties(self) -> dict[str, Any]:
        """The details kept with it."""
        return mapping(self._attributes, "properties")

    @property
    def ip_address(self) -> str | None:
        """The address it came from."""
        return nullable_string(self._attributes, "ip_address")

    @property
    def mode(self) -> str | None:
        """Either "live" or "test", or None for what belongs to neither, such as a sign-in."""
        return nullable_string(self._attributes, "mode")

    @property
    def created_at(self) -> datetime | None:
        """When it was done."""
        return timestamp(self._attributes, "created_at")
