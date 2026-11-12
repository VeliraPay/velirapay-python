"""Discount codes."""

from __future__ import annotations

from datetime import datetime

from ._base import ApiResource, boolean, integer, nullable_int, nullable_string, string, strings, timestamp


class Coupon(ApiResource):
    """A discount code customers enter at checkout, or that is applied for them through a payment link's URL or the API."""

    __slots__ = ()

    @property
    def id(self) -> str:
        """The coupon's id, which is its code."""
        return string(self._attributes, "id", self.code)

    @property
    def code(self) -> str:
        """The code customers type, in capitals; it is matched in any case."""
        return string(self._attributes, "code", string(self._attributes, "id"))

    @property
    def percent_off(self) -> str | None:
        """The share taken off, such as "10.00", or None for an amount off."""
        return nullable_string(self._attributes, "percent_off")

    @property
    def amount_off(self) -> str | None:
        """The amount taken off, or None for a percentage."""
        return nullable_string(self._attributes, "amount_off")

    @property
    def currency(self) -> str | None:
        """The only fiat currency the coupon works in, or None for a percentage that works in every one."""
        return nullable_string(self._attributes, "currency")

    @property
    def min_amount(self) -> str | None:
        """The least the price before the discount must be."""
        return nullable_string(self._attributes, "min_amount")

    @property
    def max_redemptions(self) -> int | None:
        """How many payments may use the coupon, or None for no limit."""
        return nullable_int(self._attributes, "max_redemptions")

    @property
    def times_redeemed(self) -> int:
        """How many paid charges used the coupon."""
        return integer(self._attributes, "times_redeemed")

    @property
    def once_per_customer(self) -> bool:
        """Whether each customer email can use the coupon only once."""
        return boolean(self._attributes, "once_per_customer")

    @property
    def payment_links(self) -> list[str]:
        """The codes of the payment links the coupon is limited to; empty for every link, and charges without one."""
        return strings(self._attributes, "payment_links")

    @property
    def active(self) -> bool:
        """Whether customers can use the coupon, rather than it being paused."""
        return boolean(self._attributes, "active")

    @property
    def expires_at(self) -> datetime | None:
        """When the coupon stops working."""
        return timestamp(self._attributes, "expires_at")

    @property
    def created_at(self) -> datetime | None:
        """When the coupon was created."""
        return timestamp(self._attributes, "created_at")

    @property
    def updated_at(self) -> datetime | None:
        """When the coupon was last changed."""
        return timestamp(self._attributes, "updated_at")

    def is_percentage(self) -> bool:
        """Whether the coupon takes a percentage off rather than a fixed amount."""
        return self.percent_off is not None
