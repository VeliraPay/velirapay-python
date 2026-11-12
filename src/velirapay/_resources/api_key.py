"""The account's API keys."""

from __future__ import annotations

from datetime import datetime

from ._base import ApiResource, nullable_string, nullable_strings, string, timestamp


class ApiKey(ApiResource):
    """An API key of the account. The key itself is only in the answer that creates it."""

    __slots__ = ()

    @property
    def id(self) -> str:
        """The key's id, which is not the key itself."""
        return string(self._attributes, "id")

    @property
    def name(self) -> str:
        """What the key is for."""
        return string(self._attributes, "name")

    @property
    def prefix(self) -> str:
        """The start of the key, such as "vp_live_a1b2", to tell keys apart."""
        return string(self._attributes, "prefix")

    @property
    def key(self) -> str | None:
        """The key itself, only in the answer that created it."""
        return nullable_string(self._attributes, "key")

    @property
    def mode(self) -> str:
        """Either "live" or "test"."""
        return string(self._attributes, "mode")

    @property
    def permissions(self) -> list[str] | None:
        """The ApiKeyPermission values the key has, or None for full access."""
        return nullable_strings(self._attributes, "permissions")

    @property
    def allowed_ips(self) -> list[str] | None:
        """The addresses and ranges it may be used from, or None for anywhere."""
        return nullable_strings(self._attributes, "allowed_ips")

    @property
    def created_by(self) -> str | None:
        """The name of the member who made it."""
        return nullable_string(self._attributes, "created_by")

    @property
    def last_used_at(self) -> datetime | None:
        """When it last made a request."""
        return timestamp(self._attributes, "last_used_at")

    @property
    def created_at(self) -> datetime | None:
        """When it was made."""
        return timestamp(self._attributes, "created_at")

    def has_full_access(self) -> bool:
        """Whether the key has every permission that full access gives."""
        return self.permissions is None
