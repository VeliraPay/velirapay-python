"""Reusable checkout pages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .._enums import PaymentLinkStatus, PricingType
from ._base import (
    ApiResource,
    boolean,
    integer,
    nullable_int,
    nullable_string,
    nullable_strings,
    records,
    string,
    strings,
    timestamp,
)


@dataclass(frozen=True, slots=True)
class CheckoutQuestion:
    """A question a payment link's checkout asks."""

    label: str
    """What is asked."""

    required: bool
    """Whether the customer has to answer it."""


class PaymentLink(ApiResource):
    """A shareable checkout page that creates a charge for each customer who pays through it."""

    __slots__ = ()

    @property
    def id(self) -> str:
        """The link's public code, also the last segment of its checkout URL."""
        return string(self._attributes, "id", string(self._attributes, "code"))

    @property
    def title(self) -> str:
        """The title shown on the checkout."""
        return string(self._attributes, "title")

    @property
    def description(self) -> str | None:
        """The description shown on the checkout."""
        return nullable_string(self._attributes, "description")

    @property
    def pricing_type(self) -> str:
        """One of the PricingType values: fixed or open."""
        return string(self._attributes, "pricing_type")

    @property
    def amount(self) -> str | None:
        """The price of a fixed-price link."""
        return nullable_string(self._attributes, "amount")

    @property
    def suggested_amounts(self) -> list[str]:
        """Amounts offered as shortcuts on an open-price link."""
        return strings(self._attributes, "suggested_amounts")

    @property
    def min_amount(self) -> str | None:
        """The least a customer may pay on an open-price link."""
        return nullable_string(self._attributes, "min_amount")

    @property
    def max_amount(self) -> str | None:
        """The most a customer may pay on an open-price link."""
        return nullable_string(self._attributes, "max_amount")

    @property
    def currency(self) -> str:
        """The fiat currency the link is priced in."""
        return string(self._attributes, "currency")

    @property
    def accepted_assets(self) -> list[str] | None:
        """The coins the link takes, or None for every coin the account can receive."""
        return nullable_strings(self._attributes, "accepted_assets")

    @property
    def status(self) -> str:
        """One of the PaymentLinkStatus values: active or archived."""
        return string(self._attributes, "status")

    @property
    def success_url(self) -> str | None:
        """Where the customer is sent after paying."""
        return nullable_string(self._attributes, "success_url")

    @property
    def cancel_url(self) -> str | None:
        """Where the customer is sent when they give up."""
        return nullable_string(self._attributes, "cancel_url")

    @property
    def collect_name(self) -> bool:
        """Whether the checkout asks for the customer's name."""
        return boolean(self._attributes, "collect_name")

    @property
    def require_email(self) -> bool:
        """Whether the checkout requires the customer's email address."""
        return boolean(self._attributes, "require_email")

    @property
    def custom_fields(self) -> list[CheckoutQuestion]:
        """The questions the checkout asks."""
        return [
            CheckoutQuestion(label=string(field, "label"), required=boolean(field, "required"))
            for field in records(self._attributes, "custom_fields")
        ]

    @property
    def success_message(self) -> str | None:
        """The message shown once the payment lands."""
        return nullable_string(self._attributes, "success_message")

    @property
    def expires_at(self) -> datetime | None:
        """When the link stops taking payments."""
        return timestamp(self._attributes, "expires_at")

    @property
    def max_payments(self) -> int | None:
        """How many payments the link takes before it closes."""
        return nullable_int(self._attributes, "max_payments")

    @property
    def accepting_payments(self) -> bool:
        """Whether the link takes payments right now."""
        return boolean(self._attributes, "accepting_payments")

    @property
    def views_count(self) -> int:
        """How many times the checkout was opened."""
        return integer(self._attributes, "views_count")

    @property
    def checkout_url(self) -> str:
        """The checkout page to share."""
        return string(self._attributes, "checkout_url")

    @property
    def created_at(self) -> datetime | None:
        """When the link was created."""
        return timestamp(self._attributes, "created_at")

    @property
    def updated_at(self) -> datetime | None:
        """When the link was last changed."""
        return timestamp(self._attributes, "updated_at")

    def is_active(self) -> bool:
        """Whether the link is active rather than archived."""
        return self.status == PaymentLinkStatus.ACTIVE

    def is_archived(self) -> bool:
        """Whether the link was archived."""
        return self.status == PaymentLinkStatus.ARCHIVED

    def has_fixed_amount(self) -> bool:
        """Whether the link has a set price rather than one the customer names."""
        return self.pricing_type == PricingType.FIXED
