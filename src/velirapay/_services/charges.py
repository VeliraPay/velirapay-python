"""The /v1/charges endpoints."""

from __future__ import annotations

from collections.abc import Iterator

from .._page import Page
from .._params import ChargeCreateParams, ChargeListParams, RefundParams, SimulateParams
from .._resources.charge import Charge
from ._base import Service, path


class ChargeService(Service):
    """The /v1/charges endpoints."""

    __slots__ = ()

    def create(self, params: ChargeCreateParams, *, idempotency_key: str | None = None) -> Charge:
        """Charge a customer: create a charge with what you already know about them, and send them to its checkout_url."""
        return Charge(self._request("POST", "/v1/charges", params, idempotency_key))

    def retrieve(self, id: str) -> Charge:
        """Retrieve a charge by its id."""
        return Charge(self._request("GET", path("/v1/charges/%s", id)))

    def list(self, params: ChargeListParams | None = None) -> Page[Charge]:
        """List charges, newest first."""
        return self._page("/v1/charges", params, Charge)

    def iterator(self, params: ChargeListParams | None = None) -> Iterator[Charge]:
        """Iterate over every charge, newest first, fetching pages as they are reached."""
        yield from self.list(params).auto_paging_iterator()

    def cancel(self, id: str, *, idempotency_key: str | None = None) -> Charge:
        """Cancel a pending charge that no transfer has been seen for, so it can no longer be paid."""
        return Charge(self._request("POST", path("/v1/charges/%s/cancel", id), None, idempotency_key))

    def record_refund(self, id: str, params: RefundParams, *, idempotency_key: str | None = None) -> Charge:
        """Record a refund you sent the customer from your own wallet. An underpaid charge or a late payment is accepted first, and the network surcharge is never refundable."""
        return Charge(self._request("POST", path("/v1/charges/%s/refunds", id), params, idempotency_key))

    def send(self, id: str, *, idempotency_key: str | None = None) -> Charge:
        """Email the customer the payment page of a pending charge."""
        return Charge(self._request("POST", path("/v1/charges/%s/send", id), None, idempotency_key))

    def accept(self, id: str, *, idempotency_key: str | None = None) -> Charge:
        """Accept an underpaid charge, or a late payment on an expired or canceled one, as paid for what arrived and confirmed."""
        return Charge(self._request("POST", path("/v1/charges/%s/accept", id), None, idempotency_key))

    def simulate(self, id: str, params: SimulateParams | None = None, *, idempotency_key: str | None = None) -> Charge:
        """Pay a test-mode charge without coins, in full or by a chosen amount in the charge's coin."""
        return Charge(self._request("POST", path("/v1/charges/%s/simulate", id), params or None, idempotency_key))
