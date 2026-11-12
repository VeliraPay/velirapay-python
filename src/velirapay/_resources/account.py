"""The account an API key belongs to."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .._enums import AccountType, BusinessType, Industry, Mode, MonthlyVolume, PlanName
from ._base import (
    ApiResource,
    boolean,
    mapping,
    nullable_string,
    one_of,
    record,
    string,
    strings,
    timestamp,
)


@dataclass(frozen=True, slots=True)
class AccountCheckout:
    """How the account's checkout looks and what it falls back on."""

    appearance: str
    """One of the CheckoutAppearance values: "auto", "light" or "dark"."""

    coin_order: list[str]
    """The order coins are listed in."""

    default_coin: str | None
    """The coin the checkout starts on, or None when the merchant has not picked one."""

    success_url: str | None
    """Where customers are sent after paying, when the charge and its payment link say nowhere."""

    cancel_url: str | None
    """Where customers can go back to without paying, when the charge and its payment link say nowhere."""

    success_message: str | None
    """What customers are told once they have paid, when the charge and its payment link say nothing."""

    hide_powered_by: bool
    """Whether "Powered by VeliraPay" is left off the checkout and invoices, on Pro."""


@dataclass(frozen=True, slots=True)
class AccountInvoices:
    """How the account's invoices are numbered and printed."""

    number_prefix: str | None
    """What new invoice numbers start with."""

    footer: str | None
    """The note at the bottom of invoices and receipts."""

    show_business_details: bool
    """Whether invoices and receipts print the business details."""


class Account(ApiResource):
    """The account an API key belongs to: a personal account or an organization."""

    __slots__ = ("_meta",)

    def __init__(self, attributes: Mapping[str, Any], meta: Mapping[str, Any] | None = None) -> None:
        """Read the account from its attributes and the meta the API sent with them."""
        super().__init__(attributes)
        self._meta: dict[str, Any] = copy.deepcopy(dict(meta or {}))

    @property
    def id(self) -> str:
        """The account's slug."""
        return string(self._attributes, "id")

    @property
    def type(self) -> str:
        """One of the AccountType values: "personal" or "organization"."""
        return string(self._attributes, "type")

    @property
    def name(self) -> str:
        """The account's name."""
        return string(self._attributes, "name")

    @property
    def display_name(self) -> str:
        """The name customers see."""
        return string(self._attributes, "display_name", self.name)

    @property
    def logo_url(self) -> str | None:
        """The logo customers see."""
        return nullable_string(self._attributes, "logo_url")

    @property
    def logo_dark_url(self) -> str | None:
        """The logo customers see on a dark background."""
        return nullable_string(self._attributes, "logo_dark_url")

    @property
    def website_url(self) -> str | None:
        """The merchant's website."""
        return nullable_string(self._attributes, "website_url")

    @property
    def support_email(self) -> str | None:
        """Where customers can reach the merchant."""
        return nullable_string(self._attributes, "support_email")

    @property
    def support_phone(self) -> str | None:
        """The phone number customers see next to the support email."""
        return nullable_string(self._attributes, "support_phone")

    @property
    def brand_color(self) -> str | None:
        """The checkout's accent colour, as "#rrggbb"."""
        return nullable_string(self._attributes, "brand_color")

    @property
    def terms_url(self) -> str | None:
        """The merchant's terms and conditions."""
        return nullable_string(self._attributes, "terms_url")

    @property
    def refund_policy_url(self) -> str | None:
        """The merchant's refund policy."""
        return nullable_string(self._attributes, "refund_policy_url")

    @property
    def business(self) -> AccountBusiness:
        """Who runs the account and what it sells; every field is None until it is filled in, and for a key without the sensitive account:write permission."""
        return AccountBusiness(mapping(self._attributes, "business"))

    @property
    def default_currency(self) -> str:
        """The currency new links and reports default to, one of the Currency values."""
        return string(self._attributes, "default_currency")

    @property
    def underpayment_tolerance(self) -> str:
        """How far short of the amount due, in percent, still counts as paid."""
        return string(self._attributes, "underpayment_tolerance", "0")

    @property
    def overpayment_threshold(self) -> str:
        """How much surplus, in percent, is ignored before a charge is flagged as overpaid."""
        return string(self._attributes, "overpayment_threshold", "0")

    @property
    def plan(self) -> str:
        """One of the PlanName values: "free" or "pro"."""
        return string(mapping(self._attributes, "plan"), "name", "free")

    @property
    def fee_percent(self) -> str:
        """The share of each payment kept as the platform's fee, in percent."""
        return string(mapping(self._attributes, "plan"), "fee_percent", "0")

    @property
    def pro_ends_at(self) -> datetime | None:
        """When Pro ends, or None while it renews, has no end or the account is on the free plan."""
        return timestamp(mapping(self._attributes, "plan"), "pro_ends_at")

    @property
    def checkout(self) -> AccountCheckout | None:
        """The checkout's appearance, coin order, default coin and defaults."""
        checkout = record(self._attributes, "checkout")

        if checkout is None:
            return None

        return AccountCheckout(
            appearance=string(checkout, "appearance", "auto"),
            coin_order=strings(checkout, "coin_order"),
            default_coin=nullable_string(checkout, "default_coin"),
            success_url=nullable_string(checkout, "success_url"),
            cancel_url=nullable_string(checkout, "cancel_url"),
            success_message=nullable_string(checkout, "success_message"),
            hide_powered_by=boolean(checkout, "hide_powered_by"),
        )

    @property
    def invoices(self) -> AccountInvoices | None:
        """The invoice numbering, footer and business details settings."""
        invoices = record(self._attributes, "invoices")

        if invoices is None:
            return None

        return AccountInvoices(
            number_prefix=nullable_string(invoices, "number_prefix"),
            footer=nullable_string(invoices, "footer"),
            show_business_details=boolean(invoices, "show_business_details"),
        )

    @property
    def checkout_locale(self) -> str | None:
        """The fallback checkout language, one of the CheckoutLocale values, or None for English."""
        return nullable_string(self._attributes, "checkout_locale")

    @property
    def invoice_reminders(self) -> bool:
        """Whether automatic invoice reminders are enabled."""
        return boolean(self._attributes, "invoice_reminders")

    @property
    def api_payout_address_changes(self) -> bool:
        """Whether the owner allows API keys and AI apps to change payout addresses."""
        return boolean(self._attributes, "api_payout_address_changes")

    @property
    def created_at(self) -> datetime | None:
        """When the account was created."""
        return timestamp(self._attributes, "created_at")

    @property
    def mode(self) -> str | None:
        """The mode of the API key that fetched the account: "live" or "test"."""
        return nullable_string(self._meta, "mode")

    @property
    def accepted_assets(self) -> list[str]:
        """The coins the account can be paid in right now, in that mode."""
        return strings(self._meta, "accepted_assets")

    def is_pro(self) -> bool:
        """Whether the account is on Pro, which keeps no fee."""
        return self.plan == PlanName.PRO

    def is_organization(self) -> bool:
        """Whether this is an organization rather than a personal account."""
        return self.type == AccountType.ORGANIZATION

    def is_test_mode(self) -> bool:
        """Whether the key that fetched the account works in test mode."""
        return self.mode == Mode.TEST


class AccountBusiness(ApiResource):
    """Who runs an account and what it sells, as entered under Business details in its settings."""

    __slots__ = ()

    @property
    def type(self) -> BusinessType | None:
        """The kind of legal entity, or None when unset or a value this library does not know yet, which get("type") still returns."""
        return one_of(BusinessType, self._attributes.get("type"))

    @property
    def legal_name(self) -> str | None:
        """The registered name of the business."""
        return nullable_string(self._attributes, "legal_name")

    @property
    def registration_number(self) -> str | None:
        """The company registration number."""
        return nullable_string(self._attributes, "registration_number")

    @property
    def tax_id(self) -> str | None:
        """The tax or VAT number."""
        return nullable_string(self._attributes, "tax_id")

    @property
    def address(self) -> Address:
        """The business's address."""
        return Address(mapping(self._attributes, "address"))

    @property
    def industry(self) -> Industry | None:
        """What the account sells, or None when unset or a value this library does not know yet, which get("industry") still returns."""
        return one_of(Industry, self._attributes.get("industry"))

    @property
    def product_description(self) -> str | None:
        """What the account sells, in its own words."""
        return nullable_string(self._attributes, "product_description")

    @property
    def monthly_volume(self) -> MonthlyVolume | None:
        """The expected monthly takings, or None when unset or a value this library does not know yet, which get("monthly_volume") still returns."""
        return one_of(MonthlyVolume, self._attributes.get("monthly_volume"))

    @property
    def phone(self) -> str | None:
        """The business's phone number, in international format."""
        return nullable_string(self._attributes, "phone")


class Address(ApiResource):
    """A postal address."""

    __slots__ = ()

    @property
    def line1(self) -> str | None:
        """The street address."""
        return nullable_string(self._attributes, "line1")

    @property
    def line2(self) -> str | None:
        """The apartment, suite or building."""
        return nullable_string(self._attributes, "line2")

    @property
    def city(self) -> str | None:
        """The city or town."""
        return nullable_string(self._attributes, "city")

    @property
    def postal_code(self) -> str | None:
        """The postal code."""
        return nullable_string(self._attributes, "postal_code")

    @property
    def state(self) -> str | None:
        """The state, county or region."""
        return nullable_string(self._attributes, "state")

    @property
    def country(self) -> str | None:
        """The country, as an ISO 3166 two-letter code."""
        return nullable_string(self._attributes, "country")
