"""The dashboard's figures."""

from __future__ import annotations

from ._base import ApiResource, integer, nullable_number, string


class Overview(ApiResource):
    """The dashboard's figures for the last 30 days. Everything else it carries, such as the funnel and what needs attention, is read with get()."""

    __slots__ = ()

    @property
    def currency(self) -> str:
        """The currency the amounts are in."""
        return string(self._attributes, "currency")

    @property
    def volume(self) -> str:
        """What was paid in the period."""
        return string(self._attributes, "volume", "0")

    @property
    def volume_change_percent(self) -> float | None:
        """How the volume changed against the 30 days before, in percent, or None when nothing was paid then."""
        return nullable_number(self._attributes, "volume_change_percent")

    @property
    def sent_volume(self) -> str:
        """What the payouts confirmed in the period came to, at their charges' locked rates."""
        return string(self._attributes, "sent_volume", "0")

    @property
    def paid_charges(self) -> int:
        """How many charges were paid."""
        return integer(self._attributes, "paid_charges")

    @property
    def conversion_rate_percent(self) -> float | None:
        """Of the period's charges that were paid, expired or canceled, the share paid, in percent; None when there were none."""
        return nullable_number(self._attributes, "conversion_rate_percent")

    @property
    def pending_charges(self) -> int:
        """How many charges are waiting to be paid."""
        return integer(self._attributes, "pending_charges")

    @property
    def active_payment_links(self) -> int:
        """How many payment links take payments."""
        return integer(self._attributes, "active_payment_links")

    @property
    def open_invoices(self) -> int:
        """How many invoices are open."""
        return integer(self._attributes, "open_invoices")

    @property
    def overdue_invoices(self) -> int:
        """How many open invoices are past due."""
        return integer(self._attributes, "overdue_invoices")
