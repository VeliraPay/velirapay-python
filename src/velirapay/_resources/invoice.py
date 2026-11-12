"""Invoices and their lines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .._enums import InvoiceStatus
from ._base import ApiResource, calendar_day, nullable_bool, nullable_string, records, string, timestamp


@dataclass(frozen=True, slots=True)
class InvoiceCharge:
    """A charge made to pay an invoice, one per coin the customer tried."""

    id: str
    """The charge's id."""

    status: str
    """One of the ChargeStatus values."""

    asset: str
    """The coin the customer tried to pay in."""


class Invoice(ApiResource):
    """A bill sent to one customer, paid through a hosted page in the coin they choose."""

    __slots__ = ()

    @property
    def id(self) -> str:
        """The invoice's public code, also the last segment of its hosted URL."""
        return string(self._attributes, "id", string(self._attributes, "code"))

    @property
    def number(self) -> str:
        """The invoice number shown to the customer."""
        return string(self._attributes, "number")

    @property
    def status(self) -> str:
        """One of the InvoiceStatus values: open, paid or void."""
        return string(self._attributes, "status")

    @property
    def overdue(self) -> bool | None:
        """Whether the invoice is open past its due date; absent from webhooks."""
        return nullable_bool(self._attributes, "overdue")

    @property
    def customer_name(self) -> str:
        """The customer's name."""
        return string(self._attributes, "customer_name")

    @property
    def customer_email(self) -> str:
        """The customer's email address."""
        return string(self._attributes, "customer_email")

    @property
    def memo(self) -> str | None:
        """A note shown on the invoice."""
        return nullable_string(self._attributes, "memo")

    @property
    def amount(self) -> str:
        """The total due."""
        return string(self._attributes, "amount", "0")

    @property
    def currency(self) -> str:
        """The fiat currency, one of the Currency values such as "USD"."""
        return string(self._attributes, "currency")

    @property
    def items(self) -> list[InvoiceItem]:
        """The lines of an itemised invoice."""
        return [InvoiceItem(item) for item in records(self._attributes, "items")]

    @property
    def due_at(self) -> date | None:
        """The day the invoice is due."""
        return calendar_day(self._attributes, "due_at")

    @property
    def hosted_url(self) -> str:
        """The page where the customer pays."""
        return string(self._attributes, "hosted_url")

    @property
    def document_url(self) -> str | None:
        """The printable invoice; absent from webhooks."""
        return nullable_string(self._attributes, "document_url")

    @property
    def charges(self) -> list[InvoiceCharge]:
        """The charges made to pay the invoice, one per coin the customer tried."""
        return [
            InvoiceCharge(
                id=string(charge, "id", string(charge, "code")),
                status=string(charge, "status"),
                asset=string(charge, "asset"),
            )
            for charge in records(self._attributes, "charges")
        ]

    @property
    def sent_at(self) -> datetime | None:
        """When the invoice was emailed."""
        return timestamp(self._attributes, "sent_at")

    @property
    def viewed_at(self) -> datetime | None:
        """When the customer first opened it."""
        return timestamp(self._attributes, "viewed_at")

    @property
    def paid_at(self) -> datetime | None:
        """When it was paid."""
        return timestamp(self._attributes, "paid_at")

    @property
    def voided_at(self) -> datetime | None:
        """When it was voided."""
        return timestamp(self._attributes, "voided_at")

    @property
    def created_at(self) -> datetime | None:
        """When it was created."""
        return timestamp(self._attributes, "created_at")

    @property
    def success_url(self) -> str | None:
        """The page the customer is offered a button back to once they have paid; absent from webhooks."""
        return nullable_string(self._attributes, "success_url")

    @property
    def cancel_url(self) -> str | None:
        """The page the customer can go back to from the invoice without paying; absent from webhooks."""
        return nullable_string(self._attributes, "cancel_url")

    def is_open(self) -> bool:
        """Whether the invoice can still be paid."""
        return self.status == InvoiceStatus.OPEN

    def is_paid(self) -> bool:
        """Whether the invoice was paid."""
        return self.status == InvoiceStatus.PAID

    def is_void(self) -> bool:
        """Whether the invoice was voided."""
        return self.status == InvoiceStatus.VOID


class InvoiceItem(ApiResource):
    """A line on an itemised invoice."""

    __slots__ = ()

    @property
    def description(self) -> str:
        """What the line is for."""
        return string(self._attributes, "description")

    @property
    def quantity(self) -> str:
        """How many units the line bills."""
        return string(self._attributes, "quantity", "1")

    @property
    def unit_amount(self) -> str:
        """The price of one unit, in the invoice's currency."""
        return string(self._attributes, "unit_amount", "0")

    @property
    def total(self) -> str:
        """The quantity times the unit amount."""
        return string(self._attributes, "total", "0")
