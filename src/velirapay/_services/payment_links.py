"""The /v1/payment-links endpoints."""

from __future__ import annotations

from collections.abc import Iterator

from .._page import Page
from .._params import PaymentLinkCreateParams, PaymentLinkListParams, PaymentLinkUpdateParams
from .._resources.payment_link import PaymentLink
from ._base import Service, path


class PaymentLinkService(Service):
    """The /v1/payment-links endpoints."""

    __slots__ = ()

    def create(self, params: PaymentLinkCreateParams, *, idempotency_key: str | None = None) -> PaymentLink:
        """Create a payment link: one reusable public page, never one per customer."""
        return PaymentLink(self._request("POST", "/v1/payment-links", params, idempotency_key))

    def retrieve(self, id: str) -> PaymentLink:
        """Retrieve a payment link by its id."""
        return PaymentLink(self._request("GET", path("/v1/payment-links/%s", id)))

    def update(self, id: str, params: PaymentLinkUpdateParams, *, idempotency_key: str | None = None) -> PaymentLink:
        """Change any of a payment link's fields."""
        return PaymentLink(self._request("PATCH", path("/v1/payment-links/%s", id), params, idempotency_key))

    def list(self, params: PaymentLinkListParams | None = None) -> Page[PaymentLink]:
        """List payment links, newest first."""
        return self._page("/v1/payment-links", params, PaymentLink)

    def iterator(self, params: PaymentLinkListParams | None = None) -> Iterator[PaymentLink]:
        """Iterate over every payment link, newest first, fetching pages as they are reached."""
        yield from self.list(params).auto_paging_iterator()

    def archive(self, id: str, *, idempotency_key: str | None = None) -> PaymentLink:
        """Archive a payment link so it stops taking payments."""
        return PaymentLink(self._request("POST", path("/v1/payment-links/%s/archive", id), None, idempotency_key))

    def restore(self, id: str, *, idempotency_key: str | None = None) -> PaymentLink:
        """Restore an archived payment link."""
        return PaymentLink(self._request("DELETE", path("/v1/payment-links/%s/archive", id), None, idempotency_key))
