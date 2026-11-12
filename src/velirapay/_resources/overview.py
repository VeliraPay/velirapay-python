"""The dashboard's figures."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

from ._base import (
    ApiResource,
    boolean,
    calendar_day,
    integer,
    mapping,
    nullable_number,
    nullable_string,
    records,
    string,
)


@dataclass(frozen=True, slots=True)
class OverviewPeriod:
    """The days the figures cover: the last 30, today included."""

    from_: datetime.date | None
    """The first day, which the API calls "from", a Python keyword; None when the period has no days."""

    to: datetime.date | None
    """The last day, today."""


@dataclass(frozen=True, slots=True)
class OverviewFunnelAsset:
    """Where the period's charges in one coin ended."""

    asset: str
    """The coin."""

    started: int
    """How many charges a customer started paying in it."""

    paid: int
    """How many of them were paid."""

    abandoned: int
    """How many expired or were canceled before any transfer arrived."""


@dataclass(frozen=True, slots=True)
class OverviewFunnel:
    """Where the period's charges ended, each in one place, a new quote or a switch of coin counting as the same attempt."""

    started: int
    """How many charges a customer started paying."""

    paid: int
    """How many of them were paid."""

    waiting: int
    """How many are still pending or underpaid."""

    abandoned: int
    """How many expired or were canceled before any transfer arrived."""

    incomplete: int
    """How many expired or were canceled after a transfer arrived."""

    assets: list[OverviewFunnelAsset]
    """The same per coin, the most started first."""


@dataclass(frozen=True, slots=True)
class OverviewChargeAmount:
    """A charge that waits on a person, with what was due and what arrived."""

    id: str
    """The charge's id."""

    asset: str
    """The coin it is in."""

    amount: str
    """What was due, in the coin."""

    received_amount: str
    """What arrived, in the coin: short of the amount for an underpaid charge, and the late payment for a late one."""


@dataclass(frozen=True, slots=True)
class OverviewWaitingPayouts:
    """The payouts in one coin that wait for a payout address."""

    asset: str
    """The coin."""

    count: int
    """How many payouts wait."""


@dataclass(frozen=True, slots=True)
class OverviewAttention:
    """What waits on a person right now."""

    underpaid_charges: list[OverviewChargeAmount]
    """The latest underpaid charges that received something, at most five, to accept or refund."""

    late_payments: list[OverviewChargeAmount]
    """The latest expired or canceled charges with a late payment, at most five, to accept or refund."""

    payouts_waiting_for_address: list[OverviewWaitingPayouts]
    """The payouts that wait for a payout address, per coin."""

    failing_webhook_endpoints: int
    """How many active webhook endpoints had a delivery fail in the last 7 days."""


@dataclass(frozen=True, slots=True)
class OverviewAsset:
    """One coin's share of the period's paid charges."""

    asset: str
    """The coin."""

    paid_charges: int
    """How many charges were paid in it."""

    share_percent: float
    """Its share of the period's paid charges, in percent."""


@dataclass(frozen=True, slots=True)
class OverviewPaymentLink:
    """One of the payment links with the most paid charges over the period."""

    id: str | None
    """The link's id."""

    title: str | None
    """The link's title."""

    paid_charges: int
    """How many charges were paid through it."""


@dataclass(frozen=True, slots=True)
class OverviewSetup:
    """What the account has in the API key's mode, to tell what is left to set up."""

    payout_address: bool
    """Whether it has a payout address."""

    payment_link: bool
    """Whether it has a payment link."""

    paid_charge: bool
    """Whether a charge has been paid."""

    webhook_endpoint: bool
    """Whether it has a webhook endpoint."""

    public_profile: bool
    """Whether its public profile has a logo, a display name or a website."""


@dataclass(frozen=True, slots=True)
class OverviewDay:
    """One day of the period."""

    date: datetime.date | None
    """The day."""

    volume: str
    """What was paid that day, in the overview's currency."""

    sent_volume: str
    """What the payouts confirmed that day came to, at their charges' locked rates."""

    paid_charges: int
    """How many charges were paid that day."""


class Overview(ApiResource):
    """The dashboard's figures for the last 30 days, in the API key's mode."""

    __slots__ = ()

    @property
    def period(self) -> OverviewPeriod:
        """The days the figures cover."""
        period = mapping(self._attributes, "period")

        return OverviewPeriod(from_=calendar_day(period, "from"), to=calendar_day(period, "to"))

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

    @property
    def funnel(self) -> OverviewFunnel:
        """Where the period's charges ended, in all and per coin."""
        funnel = mapping(self._attributes, "funnel")

        return OverviewFunnel(
            started=integer(funnel, "started"),
            paid=integer(funnel, "paid"),
            waiting=integer(funnel, "waiting"),
            abandoned=integer(funnel, "abandoned"),
            incomplete=integer(funnel, "incomplete"),
            assets=[
                OverviewFunnelAsset(
                    asset=string(row, "asset"),
                    started=integer(row, "started"),
                    paid=integer(row, "paid"),
                    abandoned=integer(row, "abandoned"),
                )
                for row in records(funnel, "assets")
            ],
        )

    @property
    def attention(self) -> OverviewAttention:
        """What waits on a person: short and late payments, payouts without an address and failing webhook endpoints."""
        attention = mapping(self._attributes, "attention")

        return OverviewAttention(
            underpaid_charges=_charges(attention, "underpaid_charges"),
            late_payments=_charges(attention, "late_payments"),
            payouts_waiting_for_address=[
                OverviewWaitingPayouts(asset=string(row, "asset"), count=integer(row, "count"))
                for row in records(attention, "payouts_waiting_for_address")
            ],
            failing_webhook_endpoints=integer(attention, "failing_webhook_endpoints"),
        )

    @property
    def assets(self) -> list[OverviewAsset]:
        """The coins charges were paid in over the period, the most paid first."""
        return [
            OverviewAsset(
                asset=string(row, "asset"),
                paid_charges=integer(row, "paid_charges"),
                share_percent=nullable_number(row, "share_percent") or 0.0,
            )
            for row in records(self._attributes, "assets")
        ]

    @property
    def top_payment_links(self) -> list[OverviewPaymentLink]:
        """The four payment links with the most paid charges over the period."""
        return [
            OverviewPaymentLink(
                id=nullable_string(row, "id"),
                title=nullable_string(row, "title"),
                paid_charges=integer(row, "paid_charges"),
            )
            for row in records(self._attributes, "top_payment_links")
        ]

    @property
    def setup(self) -> OverviewSetup:
        """What the account has set up in the API key's mode."""
        setup = mapping(self._attributes, "setup")

        return OverviewSetup(
            payout_address=boolean(setup, "payout_address"),
            payment_link=boolean(setup, "payment_link"),
            paid_charge=boolean(setup, "paid_charge"),
            webhook_endpoint=boolean(setup, "webhook_endpoint"),
            public_profile=boolean(setup, "public_profile"),
        )

    @property
    def daily(self) -> list[OverviewDay]:
        """Every day of the period, the oldest first."""
        return [
            OverviewDay(
                date=calendar_day(day, "date"),
                volume=string(day, "volume", "0"),
                sent_volume=string(day, "sent_volume", "0"),
                paid_charges=integer(day, "paid_charges"),
            )
            for day in records(self._attributes, "daily")
        ]


def _charges(attention: dict[str, Any], key: str) -> list[OverviewChargeAmount]:
    """Read a list of the charges that wait on a person."""
    return [
        OverviewChargeAmount(
            id=string(row, "id"),
            asset=string(row, "asset"),
            amount=string(row, "amount", "0"),
            received_amount=string(row, "received_amount", "0"),
        )
        for row in records(attention, key)
    ]
