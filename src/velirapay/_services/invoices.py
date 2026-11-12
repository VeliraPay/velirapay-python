"""The /v1/invoices endpoints."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

from .._page import Page
from .._params import InvoiceCreateParams, InvoiceListParams
from .._resources.invoice import Invoice
from ._base import Service, path


class InvoiceService(Service):
    """The /v1/invoices endpoints."""

    __slots__ = ()

    def create(self, params: InvoiceCreateParams, *, idempotency_key: str | None = None) -> Invoice:
        """Create an invoice, for a total or a list of items, and optionally email it to the customer. A datetime due_at is sent as its day, in its own time zone."""
        due_at = params.get("due_at")
        body = {**params, "due_at": due_at.date()} if isinstance(due_at, datetime) else params

        return Invoice(self._request("POST", "/v1/invoices", body, idempotency_key))

    def retrieve(self, id: str) -> Invoice:
        """Retrieve an invoice by its id."""
        return Invoice(self._request("GET", path("/v1/invoices/%s", id)))

    def list(self, params: InvoiceListParams | None = None) -> Page[Invoice]:
        """List invoices, newest first."""
        return self._page("/v1/invoices", params, Invoice)

    def iterator(self, params: InvoiceListParams | None = None) -> Iterator[Invoice]:
        """Iterate over every invoice, newest first, fetching pages as they are reached."""
        yield from self.list(params).auto_paging_iterator()

    def send(self, id: str, *, idempotency_key: str | None = None) -> Invoice:
        """Email an open invoice to its customer, as a reminder when it was sent before."""
        return Invoice(self._request("POST", path("/v1/invoices/%s/send", id), None, idempotency_key))

    def void(self, id: str, *, idempotency_key: str | None = None) -> Invoice:
        """Void an open invoice so it can no longer be paid."""
        return Invoice(self._request("POST", path("/v1/invoices/%s/void", id), None, idempotency_key))
