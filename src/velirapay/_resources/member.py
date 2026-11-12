"""The people in the account, and who has been asked to join."""

from __future__ import annotations

from datetime import datetime

from ._base import ApiResource, boolean, nullable_string, string, timestamp


class Member(ApiResource):
    """A person in the account, with their role."""

    __slots__ = ()

    @property
    def id(self) -> str:
        """The member's id."""
        return string(self._attributes, "id")

    @property
    def name(self) -> str:
        """Their name."""
        return string(self._attributes, "name")

    @property
    def email(self) -> str:
        """The address they sign in with."""
        return string(self._attributes, "email")

    @property
    def role(self) -> str | None:
        """One of the MemberRole values: "owner", "admin", "finance", "support" or "viewer"."""
        return nullable_string(self._attributes, "role")

    @property
    def joined_at(self) -> datetime | None:
        """When they joined."""
        return timestamp(self._attributes, "joined_at")


class Invitation(ApiResource):
    """An invitation to the account nobody has accepted yet."""

    __slots__ = ()

    @property
    def id(self) -> str:
        """The invitation's id, which is not the code in the email's link."""
        return string(self._attributes, "id")

    @property
    def email(self) -> str:
        """Where it was sent."""
        return string(self._attributes, "email")

    @property
    def role(self) -> str:
        """The role it gives once accepted, one of the MemberRole values but "owner": "admin", "finance", "support" or "viewer"."""
        return string(self._attributes, "role")

    @property
    def invited_by(self) -> str | None:
        """The name of the member who sent it."""
        return nullable_string(self._attributes, "invited_by")

    @property
    def expired(self) -> bool:
        """Whether it can no longer be accepted."""
        return boolean(self._attributes, "expired")

    @property
    def expires_at(self) -> datetime | None:
        """When it stops working."""
        return timestamp(self._attributes, "expires_at")

    @property
    def created_at(self) -> datetime | None:
        """When it was sent."""
        return timestamp(self._attributes, "created_at")
