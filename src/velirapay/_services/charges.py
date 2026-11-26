"""The /v1/charges endpoints."""

from __future__ import annotations

from collections.abc import Iterator

from .._page import Page
from .._params import (
    ChargeCreateParams,
    ChargeListParams,
    PageParams,
    RefundAddressParams,
    RefundCompleteParams,
    RefundParams,
    RefundRequestCreateParams,
    RefundSentParams,
    SimulateParams,
)
from .._resources.charge import Charge, RefundRequest
from ._base import Service, amounts, path


class ChargeService(Service):
    """The /v1/charges endpoints."""

    __slots__ = ()

    def create(self, params: ChargeCreateParams, *, idempotency_key: str | None = None) -> Charge:
        """Charge a customer: create a charge with what you already know about them, and send them to its checkout_url."""
        return Charge(self._request("POST", "/v1/charges", amounts(params, "amount"), idempotency_key))

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
        return Charge(
            self._request("POST", path("/v1/charges/%s/refunds", id), amounts(params, "amount"), idempotency_key)
        )

    def refund_requests(self, id: str, params: PageParams | None = None) -> Page[RefundRequest]:
        """List the refunds started for a charge, newest first."""
        return self._page(path("/v1/charges/%s/refund-requests", id), params, RefundRequest)

    def retrieve_refund_request(self, id: str, refund_request_id: str) -> RefundRequest:
        """Retrieve one of a charge's refund requests."""
        return RefundRequest(self._request("GET", path("/v1/charges/%s/refund-requests/%s", id, refund_request_id)))

    def start_refund(
        self, id: str, params: RefundRequestCreateParams, *, idempotency_key: str | None = None
    ) -> RefundRequest:
        """Start a refund: set the amount aside and, without an address, email the customer a link to give one, which is the request's address_url either way. You then send it from your own wallet, and it is recorded once the chain shows it."""
        return RefundRequest(
            self._request(
                "POST", path("/v1/charges/%s/refund-requests", id), amounts(params, "amount"), idempotency_key
            )
        )

    def set_refund_address(
        self, id: str, refund_request_id: str, params: RefundAddressParams, *, idempotency_key: str | None = None
    ) -> RefundRequest:
        """Give a refund waiting for the customer's address the one they gave you some other way. One that has its address already, or no longer takes one, raises a ConflictError."""
        return RefundRequest(
            self._request(
                "POST",
                path("/v1/charges/%s/refund-requests/%s/address", id, refund_request_id),
                params,
                idempotency_key,
            )
        )

    def mark_refund_sent(
        self, id: str, refund_request_id: str, params: RefundSentParams, *, idempotency_key: str | None = None
    ) -> RefundRequest:
        """Give a refund the hash of the transaction you sent it in: the chain is looked at straight away, and the refund is recorded once the transfer has its confirmations. A hash that already stands for a payment, a payout or another refund raises a ValidationError on txid."""
        return RefundRequest(
            self._request(
                "POST", path("/v1/charges/%s/refund-requests/%s/sent", id, refund_request_id), params, idempotency_key
            )
        )

    def complete_refund(
        self,
        id: str,
        refund_request_id: str,
        params: RefundCompleteParams | None = None,
        *,
        idempotency_key: str | None = None,
    ) -> RefundRequest:
        """Record a started refund as sent, on your word, for a transfer the chain is not seen to carry, such as one in Monero."""
        return RefundRequest(
            self._request(
                "POST",
                path("/v1/charges/%s/refund-requests/%s/complete", id, refund_request_id),
                params or None,
                idempotency_key,
            )
        )

    def resend_refund_link(
        self, id: str, refund_request_id: str, *, idempotency_key: str | None = None
    ) -> RefundRequest:
        """Email the customer the link to give a refund's address again, which then works for another 14 days. A refund no longer waiting for the address, a charge without a customer email or an email sent too recently raises a ConflictError."""
        return RefundRequest(
            self._request(
                "POST", path("/v1/charges/%s/refund-requests/%s/resend", id, refund_request_id), None, idempotency_key
            )
        )

    def cancel_refund(self, id: str, refund_request_id: str, *, idempotency_key: str | None = None) -> RefundRequest:
        """Stop a refund that has not been recorded, which frees what it set aside."""
        return RefundRequest(
            self._request(
                "POST", path("/v1/charges/%s/refund-requests/%s/cancel", id, refund_request_id), None, idempotency_key
            )
        )

    def send(self, id: str, *, idempotency_key: str | None = None) -> Charge:
        """Email the customer the payment page of a pending charge."""
        return Charge(self._request("POST", path("/v1/charges/%s/send", id), None, idempotency_key))

    def accept(self, id: str, *, idempotency_key: str | None = None) -> Charge:
        """Accept an underpaid charge, or a late payment on an expired or canceled one, as paid for what arrived and confirmed."""
        return Charge(self._request("POST", path("/v1/charges/%s/accept", id), None, idempotency_key))

    def simulate(self, id: str, params: SimulateParams | None = None, *, idempotency_key: str | None = None) -> Charge:
        """Pay a test-mode charge without coins, in full or by a chosen amount in the charge's coin."""
        body = amounts(params, "amount") if params else None

        return Charge(self._request("POST", path("/v1/charges/%s/simulate", id), body, idempotency_key))
