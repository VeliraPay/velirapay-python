"""The client for the VeliraPay API."""

from __future__ import annotations

import math
import platform
import re
import urllib.parse
from collections.abc import Mapping
from typing import Final

from ._enums import Mode
from ._errors import InvalidArgumentError
from ._http import ApiResponse, Transport, UrllibTransport
from ._requester import Requester
from ._services.account import AccountService
from ._services.assets import AssetService
from ._services.charges import ChargeService
from ._services.coupons import CouponService
from ._services.events import EventService
from ._services.invoices import InvoiceService
from ._services.management import (
    ActivityService,
    ApiKeyService,
    BillingService,
    InvitationService,
    MemberService,
    OverviewService,
)
from ._services.payment_links import PaymentLinkService
from ._services.payouts import PayoutAddressService, PayoutService
from ._services.webhook_endpoints import WebhookEndpointService
from ._version import VERSION

_KEY_CHARACTERS = re.compile(r"[\x21-\x7e]+")
_PRINTABLE = re.compile(r"[\x20-\x7e]+")


class VeliraPayClient:
    """A client for the VeliraPay API, authenticated with one API key. It can be shared between threads."""

    VERSION: Final = VERSION
    """The version of this library."""

    DEFAULT_BASE_URL: Final = "https://api.velirapay.com"
    """The address of the VeliraPay API."""

    account: AccountService
    """The account the API key belongs to."""

    assets: AssetService
    """Assets: the coins on offer, and the lowest price each can be charged at."""

    charges: ChargeService
    """Charges: how to ask a customer for a payment, in one coin."""

    payment_links: PaymentLinkService
    """Payment links: reusable checkout pages many customers pay through."""

    invoices: InvoiceService
    """Invoices: itemised bills customers pay in the coin of their choice."""

    coupons: CouponService
    """Coupons: discount codes for the hosted checkout and new charges."""

    payouts: PayoutService
    """Payouts: what became of each paid charge."""

    events: EventService
    """Events: the history of every charge and invoice."""

    webhook_endpoints: WebhookEndpointService
    """Webhook endpoints: where webhooks are delivered, and whether they can be."""

    overview: OverviewService
    """The overview: the dashboard's figures for the last 30 days."""

    payout_addresses: PayoutAddressService
    """Payout addresses: where the account's payouts go on each network."""

    activity: ActivityService
    """The activity log: everything done in the account, and who did it."""

    api_keys: ApiKeyService
    """API keys: the account's keys, never reaching further than the one asking."""

    members: MemberService
    """Members: the people in the account and their roles."""

    invitations: InvitationService
    """Invitations: who has been asked to join and has not yet."""

    billing: BillingService
    """Billing: paying for Pro in crypto."""

    def __init__(
        self,
        api_key: str | None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        max_retries: int = 2,
        max_retry_after: float = 10,
        timeout: float = 30,
        app_info: str | None = None,
        transport: Transport | None = None,
    ) -> None:
        """Create a client with a secret key from the dashboard, starting with "vp_live_" or "vp_test_". Keep it on your server.

        max_retries is how many times a request is tried again after a network error, a rate limit, an outage, or while one
        with the same idempotency key is still being processed, 0 turning retries off; max_retry_after the longest
        Retry-After, in seconds, waited out before trying again, a longer one being raised straight away; timeout how many
        seconds an attempt may wait for the API, to connect and each time it waits for more of the answer; app_info your
        application's name and version, added to the User-Agent; and transport what sends each attempt, urllib unless given.
        """
        if not isinstance(api_key, str) or api_key.strip() == "":
            raise InvalidArgumentError(
                "A VeliraPay API key is required. Create one in the dashboard under Developers > API keys."
            )

        mode = next((candidate for candidate in Mode if api_key.startswith(f"vp_{candidate.value}_")), None)

        if mode is None:
            raise InvalidArgumentError(
                'A VeliraPay API key starts with "vp_live_" or "vp_test_". Copy yours from the dashboard under Developers > API keys.'
            )

        if not _KEY_CHARACTERS.fullmatch(api_key):
            raise InvalidArgumentError(
                "The API key holds a character no key has, such as a space or a line break. Check how it is loaded."
            )

        if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0:
            raise InvalidArgumentError("The number of retries must be a whole number, 0 or more.")

        if not _is_number(max_retry_after) or not max_retry_after >= 0:
            raise InvalidArgumentError("The longest Retry-After to wait out cannot be negative.")

        if not _is_number(timeout) or not 0 < timeout < math.inf:
            raise InvalidArgumentError("The timeout must be a number of seconds above 0.")

        if not _is_web_address(base_url):
            raise InvalidArgumentError("The base URL must be an http or https address.")

        if transport is None:
            transport = UrllibTransport()
        elif not callable(transport):
            raise InvalidArgumentError(
                "The transport must be callable, taking an HttpRequest and answering with an ApiResponse."
            )

        user_agent = f"VeliraPay-Python/{VERSION} Python/{platform.python_version()}"

        if app_info is not None and app_info.strip() != "":
            if not _PRINTABLE.fullmatch(app_info):
                raise InvalidArgumentError(
                    "The app info can only hold printable ASCII characters, as it is sent in the User-Agent header."
                )

            user_agent += f" {app_info.strip()}"

        self._mode = mode
        self._requester = Requester(
            api_key=api_key,
            transport=transport,
            base_url=base_url,
            max_retries=max_retries,
            max_retry_after=max_retry_after,
            timeout=float(timeout),
            user_agent=user_agent,
        )

        self.account = AccountService(self._requester)
        self.assets = AssetService(self._requester)
        self.charges = ChargeService(self._requester)
        self.payment_links = PaymentLinkService(self._requester)
        self.invoices = InvoiceService(self._requester)
        self.coupons = CouponService(self._requester)
        self.payouts = PayoutService(self._requester)
        self.events = EventService(self._requester)
        self.webhook_endpoints = WebhookEndpointService(self._requester)
        self.overview = OverviewService(self._requester)
        self.payout_addresses = PayoutAddressService(self._requester)
        self.activity = ActivityService(self._requester)
        self.api_keys = ApiKeyService(self._requester)
        self.members = MemberService(self._requester)
        self.invitations = InvitationService(self._requester)
        self.billing = BillingService(self._requester)

    def __repr__(self) -> str:
        return f"<VeliraPayClient {self._mode.value} mode>"

    def mode(self) -> Mode:
        """The mode the API key works in, read from its prefix."""
        return self._mode

    def is_live_mode(self) -> bool:
        """Whether the API key moves real funds."""
        return self._mode is Mode.LIVE

    def is_test_mode(self) -> bool:
        """Whether the API key works on test networks."""
        return self._mode is Mode.TEST

    def last_response(self) -> ApiResponse | None:
        """The response to the most recent request this client made in this thread, such as to read its headers."""
        return self._requester.last_response()

    def request(
        self,
        method: str,
        path: str,
        params: Mapping[str, object] | None = None,
        *,
        idempotency_key: str | None = None,
    ) -> ApiResponse:
        """Send a request to an endpoint this library has no method for yet: params are the query string of a GET, and the JSON body otherwise."""
        if method.upper() == "GET":
            return self._requester.request("GET", path, params)

        return self._requester.request(method, path, None, params or None, idempotency_key)


def _is_number(value: object) -> bool:
    """Whether a value is an int or a float, not a bool."""
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_web_address(value: object) -> bool:
    """Whether a value is an http or https address with a host."""
    if not isinstance(value, str) or not _KEY_CHARACTERS.fullmatch(value):
        return False

    try:
        parts = urllib.parse.urlsplit(value)
    except ValueError:
        return False

    return parts.scheme.lower() in ("http", "https") and parts.netloc != ""
