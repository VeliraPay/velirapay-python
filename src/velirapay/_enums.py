"""The values the API defines. Each member is also a str, so a member and its value can be used interchangeably."""

from __future__ import annotations

from enum import StrEnum


class Asset(StrEnum):
    """A coin on one particular network, such as USDT on Ethereum or USDT_TRON on Tron. The account lists the ones it accepts right now."""

    BTC = "BTC"
    BTC_LIGHTNING = "BTC_LIGHTNING"
    LTC = "LTC"
    DOGE = "DOGE"
    BCH = "BCH"
    ETH = "ETH"
    XMR = "XMR"
    SOL = "SOL"
    BNB = "BNB"
    TRX = "TRX"
    USDT = "USDT"
    USDC = "USDC"
    USDT_TRON = "USDT_TRON"
    USDC_BASE = "USDC_BASE"
    USDC_POLYGON = "USDC_POLYGON"
    USDT_BSC = "USDT_BSC"
    USDC_BSC = "USDC_BSC"
    USDT_POLYGON = "USDT_POLYGON"
    USDT_ARBITRUM = "USDT_ARBITRUM"
    USDC_ARBITRUM = "USDC_ARBITRUM"
    ETH_BASE = "ETH_BASE"
    ETH_ARBITRUM = "ETH_ARBITRUM"
    POL = "POL"


class ChargeStatus(StrEnum):
    """The states a charge moves through."""

    PENDING = "pending"
    UNDERPAID = "underpaid"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELED = "canceled"


class InvoiceStatus(StrEnum):
    """The states an invoice moves through."""

    OPEN = "open"
    PAID = "paid"
    VOID = "void"


class PayoutStatus(StrEnum):
    """Where a payout has got to."""

    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    MANUAL = "manual"


class PaymentLinkStatus(StrEnum):
    """Whether a payment link takes payments."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class PricingType(StrEnum):
    """How a payment link is priced: at a set amount, or at one the customer names."""

    FIXED = "fixed"
    OPEN = "open"


class EventType(StrEnum):
    """The events a charge, an invoice or a payout reports, through webhooks and the events API."""

    CHARGE_CREATED = "charge.created"
    CHARGE_PAYMENT_DETECTED = "charge.payment_detected"
    CHARGE_PAID = "charge.paid"
    CHARGE_UNDERPAID = "charge.underpaid"
    CHARGE_LATE_PAYMENT = "charge.late_payment"
    CHARGE_REFUNDED = "charge.refunded"
    CHARGE_EXPIRED = "charge.expired"
    CHARGE_CANCELED = "charge.canceled"
    INVOICE_CREATED = "invoice.created"
    INVOICE_SENT = "invoice.sent"
    INVOICE_VIEWED = "invoice.viewed"
    INVOICE_PAID = "invoice.paid"
    INVOICE_VOIDED = "invoice.voided"
    PAYOUT_SENT = "payout.sent"
    PAYOUT_CONFIRMED = "payout.confirmed"


class Mode(StrEnum):
    """The mode an API key, object or webhook belongs to."""

    LIVE = "live"
    TEST = "test"


class BusinessType(StrEnum):
    """What kind of legal entity runs an account."""

    INDIVIDUAL = "individual"
    COMPANY = "company"
    NON_PROFIT = "non_profit"


class Industry(StrEnum):
    """What an account sells, broadly."""

    DIGITAL_PRODUCTS = "digital_products"
    SOFTWARE = "software"
    HOSTING = "hosting"
    GAMING = "gaming"
    RETAIL = "retail"
    PROFESSIONAL_SERVICES = "professional_services"
    EDUCATION = "education"
    MEDIA = "media"
    MARKETPLACE = "marketplace"
    TRAVEL = "travel"
    DONATIONS = "donations"
    OTHER = "other"


class MonthlyVolume(StrEnum):
    """How much an account expects to take in a month, in US dollars."""

    UNDER_1K = "under_1k"
    UNDER_10K = "1k_10k"
    UNDER_50K = "10k_50k"
    UNDER_250K = "50k_250k"
    OVER_250K = "over_250k"


class ApiKeyPermission(StrEnum):
    """What a restricted API key may do. Full access gives every permission but the sensitive ones, which have to be ticked."""

    CHARGES_READ = "charges:read"
    CHARGES_WRITE = "charges:write"
    CHARGES_ACCEPT = "charges:accept"
    CHARGES_REFUND = "charges:refund"
    INVOICES_READ = "invoices:read"
    INVOICES_WRITE = "invoices:write"
    PAYMENT_LINKS_READ = "payment_links:read"
    PAYMENT_LINKS_WRITE = "payment_links:write"
    COUPONS_READ = "coupons:read"
    COUPONS_WRITE = "coupons:write"
    PAYOUTS_READ = "payouts:read"
    EVENTS_READ = "events:read"
    WEBHOOK_ENDPOINTS_READ = "webhook_endpoints:read"
    OVERVIEW_READ = "overview:read"
    PAYOUT_ADDRESSES_READ = "payout_addresses:read"
    ACTIVITY_READ = "activity:read"
    ACCOUNT_WRITE = "account:write"
    PAYMENT_SETTINGS_WRITE = "payment_settings:write"
    PAYOUT_ADDRESSES_WRITE = "payout_addresses:write"
    WEBHOOK_ENDPOINTS_WRITE = "webhook_endpoints:write"
    API_KEYS_READ = "api_keys:read"
    API_KEYS_WRITE = "api_keys:write"
    MEMBERS_READ = "members:read"
    MEMBERS_WRITE = "members:write"
    BILLING_WRITE = "billing:write"
