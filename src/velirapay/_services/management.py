"""The endpoints that run the account: the overview, the activity log, API keys, members, invitations and billing."""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import date, datetime

from .._errors import InvalidArgumentError
from .._page import Page
from .._params import (
    ActivityListParams,
    ApiKeyCreateParams,
    ApiKeyUpdateParams,
    InvitationCreateParams,
    MemberUpdateParams,
    PageParams,
    ProPaymentParams,
)
from .._resources.activity import Activity
from .._resources.api_key import ApiKey
from .._resources.member import Invitation, Member
from .._resources.overview import Overview
from .._resources.pro_payment import ProPayment
from ._base import Service, data, meta, path

_DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


class OverviewService(Service):
    """The /v1/overview endpoint. Needs overview:read."""

    __slots__ = ()

    def retrieve(self) -> Overview:
        """Retrieve the dashboard's figures for the last 30 days, in the API key's mode."""
        response = self._respond("GET", "/v1/overview")

        return Overview(data(response), meta(response))


class ActivityService(Service):
    """The /v1/activity endpoint. Needs activity:read."""

    __slots__ = ()

    def list(self, params: ActivityListParams | None = None) -> Page[Activity]:
        """List the account's activity log, newest first: the API key's mode, and what belongs to none, such as sign-ins.

        from and to take a day, as a date or written as YYYY-MM-DD, and a datetime is taken as its day in its own time zone.
        Any other string raises an InvalidArgumentError, since the API would ignore it and list the whole log.
        """
        return self._page("/v1/activity", _days(params), Activity)

    def iterator(self, params: ActivityListParams | None = None) -> Iterator[Activity]:
        """Iterate over the whole activity log, newest first, fetching pages as they are reached."""
        yield from self.list(params).auto_paging_iterator()


class ApiKeyService(Service):
    """The /v1/api-keys endpoints. Reading needs api_keys:read and changing api_keys:write, and a key never reaches further than the key that asks."""

    __slots__ = ()

    def list(self, params: PageParams | None = None) -> Page[ApiKey]:
        """List the account's active keys in the API key's mode, newest first, without the keys themselves."""
        return self._page("/v1/api-keys", params, ApiKey)

    def iterator(self, params: PageParams | None = None) -> Iterator[ApiKey]:
        """Iterate over every active key, newest first, fetching pages as they are reached."""
        yield from self.list(params).auto_paging_iterator()

    def create(self, params: ApiKeyCreateParams, *, idempotency_key: str | None = None) -> ApiKey:
        """Create a key in the API key's mode. Its key attribute holds the key itself, shown this once; leaving permissions out gives full access."""
        return ApiKey(self._request("POST", "/v1/api-keys", params, idempotency_key))

    def update(self, id: str, params: ApiKeyUpdateParams, *, idempotency_key: str | None = None) -> ApiKey:
        """Change a key's name, permissions or allowed_ips, only those given; None permissions gives full access and None allowed_ips anywhere."""
        return ApiKey(self._request("PATCH", path("/v1/api-keys/%s", id), params, idempotency_key))

    def revoke(self, id: str, *, idempotency_key: str | None = None) -> None:
        """Revoke a key, which is refused from its next request."""
        self._respond("DELETE", path("/v1/api-keys/%s", id), None, idempotency_key)


class MemberService(Service):
    """The /v1/members endpoints. Reading needs members:read; changing a role or removing someone needs members:write on a key an owner made."""

    __slots__ = ()

    def list(self, params: PageParams | None = None) -> Page[Member]:
        """List the account's members, oldest first."""
        return self._page("/v1/members", params, Member)

    def iterator(self, params: PageParams | None = None) -> Iterator[Member]:
        """Iterate over every member, oldest first, fetching pages as they are reached."""
        yield from self.list(params).auto_paging_iterator()

    def update(self, id: str, params: MemberUpdateParams, *, idempotency_key: str | None = None) -> Member:
        """Give a member another role: "admin", "finance", "support" or "viewer". An owner is never changed this way."""
        return Member(self._request("PATCH", path("/v1/members/%s", id), params, idempotency_key))

    def remove(self, id: str, *, idempotency_key: str | None = None) -> None:
        """Remove a member, which also revokes the API keys they made. An owner is never removed this way."""
        self._respond("DELETE", path("/v1/members/%s", id), None, idempotency_key)


class InvitationService(Service):
    """The /v1/invitations endpoints. Reading needs members:read and changing members:write."""

    __slots__ = ()

    def list(self, params: PageParams | None = None) -> Page[Invitation]:
        """List the invitations nobody has accepted yet, newest first, expired ones included."""
        return self._page("/v1/invitations", params, Invitation)

    def iterator(self, params: PageParams | None = None) -> Iterator[Invitation]:
        """Iterate over every waiting invitation, newest first, fetching pages as they are reached."""
        yield from self.list(params).auto_paging_iterator()

    def create(self, params: InvitationCreateParams, *, idempotency_key: str | None = None) -> Invitation:
        """Email someone an invitation to join as an "admin", "finance", "support" or "viewer", in the name of whoever made the API key."""
        return Invitation(self._request("POST", "/v1/invitations", params, idempotency_key))

    def cancel(self, id: str, *, idempotency_key: str | None = None) -> None:
        """Withdraw an invitation, so its link stops working."""
        self._respond("DELETE", path("/v1/invitations/%s", id), None, idempotency_key)


class BillingService(Service):
    """The /v1/billing endpoints. Needs billing:write and a live key."""

    __slots__ = ()

    def start_pro_payment(self, params: ProPaymentParams, *, idempotency_key: str | None = None) -> ProPayment:
        """Start paying for a month of Pro in a coin, answering with the checkout to pay it on, or with the payment already waiting in that coin."""
        response = self._respond("POST", "/v1/billing/pro", params, idempotency_key)

        return ProPayment(data(response), meta(response))


def _days(params: ActivityListParams | None) -> dict[str, object] | None:
    """The activity log's filters, with from and to as the days the API reads."""
    if params is None:
        return None

    query: dict[str, object] = dict(params)

    for key in ("from", "to"):
        value = query.get(key)

        if isinstance(value, datetime):
            query[key] = value.date()
        elif isinstance(value, str) and value.strip() != "" and not _is_day(value.strip()):
            raise InvalidArgumentError(
                f"The activity log's {key} takes a day, as a date or written as YYYY-MM-DD such as 2026-11-01, not {value!r}."
            )

    return query


def _is_day(text: str) -> bool:
    """Whether a string is a real day written as YYYY-MM-DD."""
    if not _DAY.fullmatch(text):
        return False

    try:
        date.fromisoformat(text)
    except ValueError:
        return False

    return True
