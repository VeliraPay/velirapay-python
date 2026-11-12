"""Where webhooks are delivered, and what each delivery did."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .._enums import WebhookDeliveryStatus
from ._base import (
    ApiResource,
    boolean,
    integer,
    mapping,
    nullable_int,
    nullable_string,
    records,
    reference,
    string,
    strings,
    timestamp,
)


class WebhookEndpoint(ApiResource):
    """Where webhooks are delivered, and whether it can receive them. Its signing secret is only returned when it is added or rotated."""

    __slots__ = ("_meta",)

    def __init__(self, attributes: Mapping[str, Any], meta: Mapping[str, Any] | None = None) -> None:
        """Read the endpoint from its attributes and the meta the API sent with them."""
        super().__init__(attributes)
        self._meta: dict[str, Any] = copy.deepcopy(dict(meta or {}))

    @property
    def id(self) -> str:
        """The endpoint's id."""
        return string(self._attributes, "id")

    @property
    def url(self) -> str:
        """Where deliveries go."""
        return string(self._attributes, "url")

    @property
    def description(self) -> str | None:
        """What the merchant noted about it."""
        return nullable_string(self._attributes, "description")

    @property
    def events(self) -> list[str]:
        """The EventType values it subscribes to."""
        return strings(self._attributes, "events")

    @property
    def active(self) -> bool:
        """Whether it is switched on."""
        return boolean(self._attributes, "active")

    @property
    def verified(self) -> bool:
        """Whether it has answered the verification challenge; it receives nothing until it has."""
        return boolean(self._attributes, "verified")

    @property
    def deliveries_count(self) -> int:
        """How many deliveries are kept for it, from the last 30 days."""
        return integer(self._attributes, "deliveries_count")

    @property
    def failed_deliveries_count(self) -> int:
        """How many of those failed."""
        return integer(self._attributes, "failed_deliveries_count")

    @property
    def verified_at(self) -> datetime | None:
        """When it last answered the verification challenge."""
        return timestamp(self._attributes, "verified_at")

    @property
    def created_at(self) -> datetime | None:
        """When it was added."""
        return timestamp(self._attributes, "created_at")

    @property
    def secret(self) -> str | None:
        """The signing secret, only in the answers that add the endpoint or rotate it."""
        return nullable_string(self._attributes, "secret")

    @property
    def verification_error(self) -> str | None:
        """Why the endpoint did not answer the verification challenge, in the answers that sent it one."""
        return nullable_string(self._meta, "verification_error")

    @property
    def previous_secret_expires_at(self) -> datetime | None:
        """Until when the secret a rotation replaced still signs deliveries too, in the answer that rotates it."""
        return timestamp(self._meta, "previous_secret_expires_at")

    def is_receiving(self) -> bool:
        """Whether the endpoint receives deliveries right now."""
        return self.active and self.verified


class WebhookDelivery(ApiResource):
    """One event sent to a webhook endpoint, and how it went. What was sent and what came back are only in retrieve_delivery()'s answer."""

    __slots__ = ()

    @property
    def id(self) -> str:
        """The delivery's id, the X-VeliraPay-Delivery header it was sent with."""
        return string(self._attributes, "id")

    @property
    def event(self) -> str:
        """The EventType value it carried."""
        return string(self._attributes, "event")

    @property
    def event_id(self) -> str | None:
        """The id of the event it carried, or None for a test delivery."""
        return nullable_string(self._attributes, "event_id")

    @property
    def test(self) -> bool:
        """Whether it was a test event, which describes no real payment."""
        return boolean(self._attributes, "test")

    @property
    def status(self) -> str:
        """One of the WebhookDeliveryStatus values: "pending", "succeeded" or "failed"."""
        return string(self._attributes, "status")

    @property
    def attempts(self) -> int:
        """How many times it was sent."""
        return integer(self._attributes, "attempts")

    @property
    def response_status(self) -> int | None:
        """The HTTP status the endpoint last answered with."""
        return nullable_int(self._attributes, "response_status")

    @property
    def error(self) -> str | None:
        """Why the last attempt failed."""
        return nullable_string(self._attributes, "error")

    @property
    def charge(self) -> str | None:
        """The id of the charge it was about."""
        return reference(self._attributes, "charge")

    @property
    def invoice(self) -> str | None:
        """The id of the invoice it was about."""
        return reference(self._attributes, "invoice")

    @property
    def created_at(self) -> datetime | None:
        """When it was queued."""
        return timestamp(self._attributes, "created_at")

    @property
    def last_attempted_at(self) -> datetime | None:
        """When it was last sent."""
        return timestamp(self._attributes, "last_attempted_at")

    @property
    def delivered_at(self) -> datetime | None:
        """When the endpoint accepted it."""
        return timestamp(self._attributes, "delivered_at")

    @property
    def payload(self) -> dict[str, Any] | None:
        """The JSON body it carried, from retrieve_delivery() alone and only for a key that may also read events."""
        return (
            mapping(self._attributes, "payload") if isinstance(self._attributes.get("payload"), dict | list) else None
        )

    @property
    def attempt_log(self) -> list[WebhookDeliveryAttempt]:
        """Every attempt to send it, the latest first, from retrieve_delivery() alone."""
        return [WebhookDeliveryAttempt(attempt) for attempt in records(self._attributes, "attempt_log")]

    def succeeded(self) -> bool:
        """Whether the endpoint accepted the delivery."""
        return self.status == WebhookDeliveryStatus.SUCCEEDED


class WebhookDeliveryAttempt(ApiResource):
    """One attempt to send a webhook delivery: the request it made and what the endpoint answered."""

    __slots__ = ()

    @property
    def attempt(self) -> int:
        """Which attempt it was, counted from 1."""
        return integer(self._attributes, "attempt")

    @property
    def url(self) -> str | None:
        """Where it was sent, or None when nothing was sent."""
        return nullable_string(self._attributes, "url")

    @property
    def request_headers(self) -> dict[str, str] | None:
        """The headers sent, the signatures cut out but the timestamp they signed kept; None when nothing was sent."""
        return _headers(self._attributes, "request_headers")

    @property
    def response_status(self) -> int | None:
        """The HTTP status the endpoint answered with, or None when nothing answered."""
        return nullable_int(self._attributes, "response_status")

    @property
    def response_headers(self) -> dict[str, str] | None:
        """The headers the endpoint answered with, a few dozen at most and never cookies."""
        return _headers(self._attributes, "response_headers")

    @property
    def response_body(self) -> str | None:
        """The first 2,000 characters of the endpoint's answer."""
        return nullable_string(self._attributes, "response_body")

    @property
    def error(self) -> str | None:
        """Why the attempt failed, such as a timeout or a refused connection."""
        return nullable_string(self._attributes, "error")

    @property
    def duration_ms(self) -> int | None:
        """How long the endpoint took, in milliseconds."""
        return nullable_int(self._attributes, "duration_ms")

    @property
    def created_at(self) -> datetime | None:
        """When the attempt was made."""
        return timestamp(self._attributes, "created_at")

    def succeeded(self) -> bool:
        """Whether the endpoint answered the attempt with a 2xx status."""
        status = self.response_status

        return status is not None and 200 <= status < 300


def _headers(data: Mapping[str, Any], key: str) -> dict[str, str] | None:
    """Read a map of header names to values, or None when none were kept."""
    if not isinstance(data.get(key), dict | list):
        return None

    return {name: value for name, value in mapping(data, key).items() if isinstance(value, str)}
