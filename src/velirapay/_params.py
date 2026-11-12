"""The parameters each endpoint takes, under the names the API gives them.

They are plain dicts: a key left out is not sent, and a key set to None is sent as null, which clears a field.
Enum members can be passed wherever their values can.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Required, TypeAlias, TypedDict

Amount: TypeAlias = str | int | float | Decimal
"""An amount of money or of a coin, sent as a decimal string. Pass a str such as "49.90", or a Decimal, to keep every decimal.

A float is rounded to 14 significant digits, the precision the API reads a number with, and written without an exponent:
0.00005 is sent as "0.00005", and 0.1 + 0.2 as "0.3".
"""

Metadata: TypeAlias = Mapping[str, str | int | float | bool | None]
"""Your own key-value data: up to 20 keys of at most 40 characters, each a string of at most 500 characters, a number, a boolean or None."""

Moment: TypeAlias = str | datetime | date
"""A moment, as ISO 8601 or a datetime with a time zone; a date is sent as YYYY-MM-DD."""


class PageParams(TypedDict, total=False):
    """Which page of a list to fetch."""

    page: int
    per_page: int


class CustomerParams(TypedDict, total=False):
    """What you know about the customer paying a charge. ip_address and user_agent are the customer's, not your server's."""

    email: str | None
    name: str | None
    ip_address: str | None
    user_agent: str | None
    reference: str | None
    phone: str | None
    country: str | None
    metadata: Metadata | None


class CustomFieldParams(TypedDict):
    """A labelled detail to keep with a charge."""

    label: str
    value: str


class ChargeCreateParams(TypedDict, total=False):
    """A new charge. amount and currency are required unless a payment_link is given, which gives the currency, and the price when it is fixed."""

    asset: Required[str]
    amount: Amount
    currency: str
    payment_link: str | None
    customer: CustomerParams | None
    customer_email: str | None
    coupon: str | None
    description: str | None
    metadata: Metadata | None
    custom_fields: Sequence[CustomFieldParams] | None
    success_url: str | None
    cancel_url: str | None
    success_message: str | None
    send_email: bool


class ChargeListParams(PageParams, total=False):
    """Which charges to list. search takes part of a charge's code, customer email, customer name or description, or exactly its deposit address, a transaction hash, its payout hash or the customer's IP address."""

    status: str
    asset: str
    payment_link: str
    search: str
    created_from: Moment
    created_to: Moment


class RefundParams(TypedDict, total=False):
    """A refund you sent the customer from your own wallet, in the charge's coin."""

    amount: Required[Amount]
    txid: str | None
    reason: str | None


class SimulateParams(TypedDict, total=False):
    """How much of the charge's coin a simulated payment sends; the whole amount due when left out."""

    amount: Amount | None


class InvoiceItemParams(TypedDict):
    """A line of an itemised invoice."""

    description: str
    quantity: Amount
    unit_amount: Amount


class InvoiceCreateParams(TypedDict, total=False):
    """A new invoice, for a single amount or a list of items. due_at is a day, as YYYY-MM-DD or a date."""

    customer_name: Required[str]
    customer_email: Required[str]
    currency: Required[str]
    amount: Amount
    items: Sequence[InvoiceItemParams]
    memo: str | None
    due_at: str | date | None
    send_email: bool


class InvoiceListParams(PageParams, total=False):
    """Which invoices to list."""

    status: str
    search: str
    overdue: bool


class CheckoutQuestionParams(TypedDict):
    """A question a payment link's checkout asks."""

    label: str
    required: bool


class _PaymentLinkOptions(TypedDict, total=False):
    amount: Amount | None
    description: str | None
    suggested_amounts: Sequence[Amount] | None
    min_amount: Amount | None
    max_amount: Amount | None
    accepted_assets: Sequence[str] | None
    success_url: str | None
    cancel_url: str | None
    collect_name: bool
    require_email: bool
    success_message: str | None
    custom_fields: Sequence[CheckoutQuestionParams]
    expires_at: Moment | None
    max_payments: int | None


class PaymentLinkCreateParams(_PaymentLinkOptions):
    """A new payment link. amount is the price of a fixed one, and None for accepted_assets takes every coin the account takes."""

    title: str
    pricing_type: str
    currency: str


class PaymentLinkUpdateParams(_PaymentLinkOptions, total=False):
    """What to change about a payment link."""

    title: str
    pricing_type: str
    currency: str


class PaymentLinkListParams(PageParams, total=False):
    """Which payment links to list."""

    status: str
    search: str


class CouponCreateParams(TypedDict, total=False):
    """A new coupon taking either percent_off or amount_off. code is 3 to 32 letters, digits, dashes or underscores, stored in capitals; currency is required with amount_off or min_amount; empty payment_links takes every link, and charges made without one."""

    code: Required[str]
    percent_off: Amount | None
    amount_off: Amount | None
    currency: str | None
    min_amount: Amount | None
    max_redemptions: int | None
    once_per_customer: bool
    payment_links: Sequence[str] | None
    active: bool
    expires_at: Moment | None


class CouponUpdateParams(TypedDict, total=False):
    """What to change about a coupon's limits; payment_links replaces the whole list."""

    max_redemptions: int | None
    once_per_customer: bool
    payment_links: Sequence[str] | None
    active: bool
    expires_at: Moment | None


class CouponListParams(PageParams, total=False):
    """Which coupons to list."""

    search: str


class PayoutListParams(PageParams, total=False):
    """Which payouts to list. search takes a charge id or a transaction hash."""

    status: str
    asset: str
    search: str


class EventListParams(PageParams, total=False):
    """Which events to list. charge and invoice take an id."""

    type: str
    charge: str
    invoice: str


class _WebhookEndpointOptions(TypedDict, total=False):
    description: str | None
    active: bool


class WebhookEndpointCreateParams(_WebhookEndpointOptions):
    """A new webhook endpoint, at a public https:// URL."""

    url: str
    events: Sequence[str]


class WebhookEndpointUpdateParams(_WebhookEndpointOptions, total=False):
    """What to change about a webhook endpoint. A new url is verified again."""

    url: str
    events: Sequence[str]


class WebhookDeliveryListParams(PageParams, total=False):
    """Which deliveries to list. status is "pending", "succeeded" or "failed"."""

    status: str
    event: str


class _ApiKeyOptions(TypedDict, total=False):
    permissions: Sequence[str] | None
    allowed_ips: Sequence[str] | None


class ApiKeyCreateParams(_ApiKeyOptions):
    """A new API key. Leaving permissions out, or None, gives full access, and allowed_ips (IPv4 or IPv6 addresses or ranges) anywhere."""

    name: str


class ApiKeyUpdateParams(_ApiKeyOptions, total=False):
    """What to change about an API key: None permissions gives full access, and None allowed_ips anywhere."""

    name: str


class MemberUpdateParams(TypedDict):
    """A member's new role: "admin", "finance", "support" or "viewer"."""

    role: str


class InvitationCreateParams(TypedDict):
    """Who to invite, and as an "admin", "finance", "support" or "viewer"."""

    email: str
    role: str


ActivityListParams = TypedDict(
    "ActivityListParams",
    {
        "page": int,
        "per_page": int,
        "action": str,
        "person": str,
        "q": str,
        "from": str,
        "to": str,
        "network": str,
    },
    total=False,
)
"""Which entries of the activity log to list. action takes an action or "sensitive", q a subject or the start of an IP address, from and to a YYYY-MM-DD day, and network the key's own mode, to leave out what belongs to none."""


class AssetListParams(TypedDict, total=False):
    """The currency of the prices; the account's default when left out."""

    currency: str


class PayoutAddressUpdateParams(TypedDict):
    """Where a network's payouts go."""

    address: str


class ProPaymentParams(TypedDict):
    """The coin to pay for Pro in."""

    asset: str


class AccountCheckoutParams(TypedDict, total=False):
    """How the checkout looks and what it falls back on."""

    appearance: str
    coin_order: Sequence[str]
    default_coin: str | None
    success_url: str | None
    cancel_url: str | None
    success_message: str | None
    hide_powered_by: bool


class AccountInvoicesParams(TypedDict, total=False):
    """How invoices are numbered and printed."""

    number_prefix: str | None
    footer: str | None
    show_business_details: bool


class AddressParams(TypedDict, total=False):
    """A postal address."""

    line1: str | None
    line2: str | None
    city: str | None
    postal_code: str | None
    state: str | None
    country: str | None


class AccountBusinessParams(TypedDict, total=False):
    """Who runs the account and what it sells."""

    type: str | None
    legal_name: str | None
    registration_number: str | None
    tax_id: str | None
    address: AddressParams
    industry: str | None
    product_description: str | None
    monthly_volume: str | None
    phone: str | None


class AccountUpdateParams(TypedDict, total=False):
    """What to change about the account, in the shape it is read in; None clears a field."""

    name: str
    display_name: str | None
    website_url: str | None
    support_email: str | None
    support_phone: str | None
    terms_url: str | None
    refund_policy_url: str | None
    brand_color: str | None
    checkout: AccountCheckoutParams
    invoices: AccountInvoicesParams
    business: AccountBusinessParams


class PaymentSettingsUpdateParams(TypedDict, total=False):
    """What to change about how payments are taken. checkout_locale is "en", "fr", "de", "es", "tr", "pt", "ru" or "ar", or None."""

    default_currency: str
    underpayment_tolerance: Amount
    overpayment_threshold: Amount
    checkout_locale: str | None
    invoice_reminders: bool
