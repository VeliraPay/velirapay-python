"""Charges, and the customers, transfers and refunds that belong to them."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .._enums import ChargeStatus
from ._base import (
    ApiResource,
    boolean,
    integer,
    mapping,
    nullable_int,
    nullable_string,
    record,
    records,
    reference,
    string,
    timestamp,
)


@dataclass(frozen=True, slots=True)
class ChargeTimelineEntry:
    """One entry of a charge's history."""

    event: str
    """What happened, such as "charge.paid"."""

    time: datetime | None
    """When it happened."""


@dataclass(frozen=True, slots=True)
class CustomFieldAnswer:
    """A labelled detail of a charge: an answer to a payment link's question, or one passed when creating the charge."""

    label: str
    """What was asked."""

    value: str
    """What was answered."""


class Charge(ApiResource):
    """A single payment in one coin, with the rate locked and a deposit address of its own."""

    __slots__ = ()

    @property
    def id(self) -> str:
        """The charge's public code, also the last segment of its checkout URL."""
        return string(self._attributes, "id", string(self._attributes, "code"))

    @property
    def status(self) -> str:
        """One of the ChargeStatus values: pending, underpaid, paid, expired or canceled."""
        return string(self._attributes, "status")

    @property
    def payment_link(self) -> str | None:
        """The code of the payment link the charge was made through."""
        return reference(self._attributes, "payment_link")

    @property
    def payment_link_title(self) -> str | None:
        """The title of the payment link the charge was made through, which webhooks carry; None in the API's answers, which give the code alone."""
        link = record(self._attributes, "payment_link")

        return None if link is None else nullable_string(link, "title")

    @property
    def invoice(self) -> str | None:
        """The code of the invoice the charge pays."""
        return reference(self._attributes, "invoice")

    @property
    def invoice_number(self) -> str | None:
        """The number of the invoice the charge pays, which webhooks carry; None in the API's answers, which give the code alone."""
        invoice = record(self._attributes, "invoice")

        return None if invoice is None else nullable_string(invoice, "number")

    @property
    def description(self) -> str | None:
        """The merchant's description of the charge."""
        return nullable_string(self._attributes, "description")

    @property
    def fiat_amount(self) -> str:
        """What the customer owes, in fiat."""
        return string(self._attributes, "fiat_amount", "0")

    @property
    def fiat_currency(self) -> str:
        """The fiat currency, one of the Currency values such as "USD"."""
        return string(self._attributes, "fiat_currency")

    @property
    def asset(self) -> str:
        """The coin and network paid with, one of the Asset values such as "BTC" or "USDT"."""
        return string(self._attributes, "asset")

    @property
    def asset_amount(self) -> str:
        """The exact amount of the coin to send."""
        return string(self._attributes, "asset_amount", "0")

    @property
    def network_surcharge(self) -> str | None:
        """What of asset_amount the customer pays on top of the price for the network, which VeliraPay keeps; None for a coin without one."""
        return nullable_string(self._attributes, "network_surcharge")

    @property
    def received_amount(self) -> str | None:
        """What has been credited so far, or None before anything arrived."""
        return nullable_string(self._attributes, "received_amount")

    @property
    def remaining_amount(self) -> str:
        """What is still missing."""
        return string(self._attributes, "remaining_amount", "0")

    @property
    def overpaid(self) -> bool:
        """Whether the customer sent more than the overpayment threshold allows."""
        return boolean(self._attributes, "overpaid")

    @property
    def refunded_amount(self) -> str:
        """How much has been recorded as refunded."""
        return string(self._attributes, "refunded_amount", "0")

    @property
    def refunds(self) -> list[Refund]:
        """The refunds recorded against the charge; absent from webhooks."""
        return [Refund(refund) for refund in records(self._attributes, "refunds")]

    @property
    def exchange_rate(self) -> str:
        """Fiat per one unit of the coin, locked when the charge was created."""
        return string(self._attributes, "exchange_rate", "0")

    @property
    def deposit_address(self) -> str:
        """The address the customer pays into, or the payment hash of the Lightning invoice for BTC_LIGHTNING."""
        return string(self._attributes, "deposit_address")

    @property
    def payment_request(self) -> str | None:
        """The Lightning invoice (BOLT11) the customer pays, for BTC_LIGHTNING; None for every other coin."""
        return nullable_string(self._attributes, "payment_request")

    @property
    def transactions(self) -> list[Transaction]:
        """The transfers seen into the deposit address."""
        return [Transaction(transaction) for transaction in records(self._attributes, "transactions")]

    @property
    def timeline(self) -> list[ChargeTimelineEntry]:
        """The charge's history, oldest first; absent from webhooks and from charges embedded in events."""
        return [
            ChargeTimelineEntry(event=string(entry, "event"), time=timestamp(entry, "time"))
            for entry in records(self._attributes, "timeline")
        ]

    @property
    def customer_email(self) -> str | None:
        """The customer's email address."""
        return nullable_string(self._attributes, "customer_email")

    @property
    def customer_name(self) -> str | None:
        """The customer's name."""
        return nullable_string(self._attributes, "customer_name")

    @property
    def customer(self) -> Customer:
        """Everything known about who pays, including the IP address and browser they paid from."""
        return Customer(
            {"email": self.customer_email, "name": self.customer_name, **mapping(self._attributes, "customer")}
        )

    @property
    def custom_fields(self) -> list[CustomFieldAnswer]:
        """Labelled details: the customer's answers to the payment link's questions, or what was passed when creating the charge."""
        return [
            CustomFieldAnswer(label=string(field, "label"), value=string(field, "value"))
            for field in records(self._attributes, "custom_fields")
        ]

    @property
    def metadata(self) -> dict[str, Any]:
        """The merchant's own key-value data."""
        return mapping(self._attributes, "metadata")

    @property
    def checkout_url(self) -> str | None:
        """The hosted checkout page to send the customer to; absent from webhooks."""
        return nullable_string(self._attributes, "checkout_url")

    @property
    def receipt_url(self) -> str | None:
        """The customer's receipt, once the charge is paid; absent from webhooks."""
        return nullable_string(self._attributes, "receipt_url")

    @property
    def expires_at(self) -> datetime | None:
        """When the locked rate runs out."""
        return timestamp(self._attributes, "expires_at")

    @property
    def paid_at(self) -> datetime | None:
        """When the charge was paid."""
        return timestamp(self._attributes, "paid_at")

    @property
    def created_at(self) -> datetime | None:
        """When the charge was created."""
        return timestamp(self._attributes, "created_at")

    @property
    def coupon(self) -> str | None:
        """The code of the coupon the customer used."""
        return nullable_string(self._attributes, "coupon")

    @property
    def discount_amount(self) -> str | None:
        """What the coupon took off, in fiat; fiat_amount is already the lower price."""
        return nullable_string(self._attributes, "discount_amount")

    @property
    def success_url(self) -> str | None:
        """The page the customer is offered a button back to once they have paid; absent from webhooks."""
        return nullable_string(self._attributes, "success_url")

    @property
    def cancel_url(self) -> str | None:
        """The page the customer can go back to from the checkout without paying; absent from webhooks."""
        return nullable_string(self._attributes, "cancel_url")

    @property
    def success_message(self) -> str | None:
        """What the customer is told once they have paid; absent from webhooks."""
        return nullable_string(self._attributes, "success_message")

    def is_pending(self) -> bool:
        """Whether the charge is waiting for its payment."""
        return self.status == ChargeStatus.PENDING

    def is_underpaid(self) -> bool:
        """Whether less than the amount due has arrived."""
        return self.status == ChargeStatus.UNDERPAID

    def is_paid(self) -> bool:
        """Whether the charge is paid in full and confirmed."""
        return self.status == ChargeStatus.PAID

    def is_expired(self) -> bool:
        """Whether the locked rate ran out before the charge was paid."""
        return self.status == ChargeStatus.EXPIRED

    def is_canceled(self) -> bool:
        """Whether the charge was canceled."""
        return self.status == ChargeStatus.CANCELED

    def is_open(self) -> bool:
        """Whether the charge can still be paid."""
        return self.is_pending() or self.is_underpaid()


class Customer(ApiResource):
    """What is known about the customer paying a charge, including the signals that help spot fraud."""

    __slots__ = ()

    @property
    def email(self) -> str | None:
        """The customer's email address."""
        return nullable_string(self._attributes, "email")

    @property
    def name(self) -> str | None:
        """The customer's name."""
        return nullable_string(self._attributes, "name")

    @property
    def ip_address(self) -> str | None:
        """The IP address the customer paid from, recorded by the checkout or passed when the charge was created."""
        return nullable_string(self._attributes, "ip_address")

    @property
    def ip_country(self) -> str | None:
        """The country the hosted checkout placed the IP address in, as an ISO 3166 two-letter code, or T1 for Tor; None for a charge created through the API."""
        return nullable_string(self._attributes, "ip_country")

    @property
    def ip_asn(self) -> int | None:
        """The number of the network (autonomous system) the IP address belongs to, such as 24940."""
        return nullable_int(self._attributes, "ip_asn")

    @property
    def ip_network(self) -> str | None:
        """Who runs that network, such as an internet provider or a hosting company."""
        return nullable_string(self._attributes, "ip_network")

    @property
    def user_agent(self) -> str | None:
        """The user agent of the browser the customer paid from."""
        return nullable_string(self._attributes, "user_agent")

    @property
    def reference(self) -> str | None:
        """Your own id for the customer."""
        return nullable_string(self._attributes, "reference")

    @property
    def phone(self) -> str | None:
        """The customer's phone number."""
        return nullable_string(self._attributes, "phone")

    @property
    def country(self) -> str | None:
        """The customer's country, as an ISO 3166 two-letter code."""
        return nullable_string(self._attributes, "country")

    @property
    def metadata(self) -> dict[str, Any]:
        """Anything else you passed about the customer."""
        return mapping(self._attributes, "metadata")


class Transaction(ApiResource):
    """A blockchain transfer into a charge's deposit address."""

    __slots__ = ()

    @property
    def txid(self) -> str:
        """The transaction id on its chain."""
        return string(self._attributes, "txid")

    @property
    def amount(self) -> str:
        """The amount received, in the charge's coin."""
        return string(self._attributes, "amount", "0")

    @property
    def confirmations(self) -> int:
        """How many confirmations the transaction has."""
        return integer(self._attributes, "confirmations")

    @property
    def required_confirmations(self) -> int:
        """How many confirmations the coin needs before the transfer counts."""
        return integer(self._attributes, "required_confirmations")

    @property
    def credited(self) -> bool:
        """Whether the transfer has been counted towards the charge."""
        return boolean(self._attributes, "credited")

    @property
    def explorer_url(self) -> str | None:
        """A link to the transaction on a block explorer."""
        return nullable_string(self._attributes, "explorer_url")

    @property
    def seen_at(self) -> datetime | None:
        """When the transfer was first seen."""
        return timestamp(self._attributes, "seen_at")


class Refund(ApiResource):
    """A refund recorded against a charge. The transfer itself is sent by the merchant."""

    __slots__ = ()

    @property
    def amount(self) -> str:
        """The amount sent back, in the charge's coin."""
        return string(self._attributes, "amount", "0")

    @property
    def txid(self) -> str | None:
        """The transaction that carried the refund, when it was recorded."""
        return nullable_string(self._attributes, "txid")

    @property
    def reason(self) -> str | None:
        """Why the refund was made."""
        return nullable_string(self._attributes, "reason")

    @property
    def explorer_url(self) -> str | None:
        """A link to the refund transaction on a block explorer."""
        return nullable_string(self._attributes, "explorer_url")

    @property
    def created_at(self) -> datetime | None:
        """When the refund was recorded."""
        return timestamp(self._attributes, "created_at")
