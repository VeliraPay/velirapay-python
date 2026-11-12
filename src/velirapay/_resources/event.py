"""The history of every charge and invoice."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ._base import ApiResource, mapping, record, string, timestamp
from .charge import Charge
from .invoice import Invoice


class Event(ApiResource):
    """Something that happened to a charge or an invoice, as the events API lists it."""

    __slots__ = ()

    @property
    def id(self) -> str:
        """The event's id, as a webhook's event_id refers to it."""
        return string(self._attributes, "id")

    @property
    def type(self) -> str:
        """One of the EventType values, such as "charge.paid"."""
        return string(self._attributes, "type")

    @property
    def details(self) -> dict[str, Any]:
        """What the event recorded, such as the amount and transaction of a detected payment."""
        return mapping(self._attributes, "details")

    @property
    def created_at(self) -> datetime | None:
        """When it happened."""
        return timestamp(self._attributes, "created_at")

    @property
    def charge(self) -> Charge | None:
        """The charge the event is about, as it is now, without its timeline."""
        charge = record(self._attributes, "charge")

        return None if charge is None else Charge(charge)

    @property
    def invoice(self) -> Invoice | None:
        """The invoice the event is about."""
        invoice = record(self._attributes, "invoice")

        return None if invoice is None else Invoice(invoice)

    def is_type(self, *types: str) -> bool:
        """Whether the event is of any of the given types, such as EventType.CHARGE_PAID."""
        return self.type in types
