"""The /v1/webhook-endpoints endpoints."""

from __future__ import annotations

from collections.abc import Iterator

from .._http import ApiResponse
from .._page import Page
from .._params import PageParams, WebhookDeliveryListParams, WebhookEndpointCreateParams, WebhookEndpointUpdateParams
from .._resources.webhook_endpoint import WebhookDelivery, WebhookEndpoint
from ._base import Service, data, meta, path


class WebhookEndpointService(Service):
    """The /v1/webhook-endpoints endpoints. Changing them needs webhook_endpoints:write."""

    __slots__ = ()

    def list(self, params: PageParams | None = None) -> Page[WebhookEndpoint]:
        """List the account's webhook endpoints in the API key's mode, newest first."""
        return self._page("/v1/webhook-endpoints", params, WebhookEndpoint)

    def iterator(self, params: PageParams | None = None) -> Iterator[WebhookEndpoint]:
        """Iterate over every webhook endpoint, newest first, fetching pages as they are reached."""
        yield from self.list(params).auto_paging_iterator()

    def retrieve(self, id: str) -> WebhookEndpoint:
        """Retrieve one webhook endpoint."""
        return WebhookEndpoint(self._request("GET", path("/v1/webhook-endpoints/%s", id)))

    def create(self, params: WebhookEndpointCreateParams, *, idempotency_key: str | None = None) -> WebhookEndpoint:
        """Add an endpoint and send it its verification challenge. The answer carries its signing secret, shown this once, and verification_error while it has not answered.

        A ConflictError whose was_replayed() is true means an earlier request with the same idempotency key, such as an
        attempt whose answer was lost, added the endpoint, and its secret is lost with that answer: rotate the secret,
        which nothing depends on yet, or delete the endpoint and add it again.
        """
        return _endpoint(self._respond("POST", "/v1/webhook-endpoints", params, idempotency_key))

    def update(
        self, id: str, params: WebhookEndpointUpdateParams, *, idempotency_key: str | None = None
    ) -> WebhookEndpoint:
        """Change an endpoint's url, events, description or active, only those given. A new url is verified again."""
        return _endpoint(self._respond("PATCH", path("/v1/webhook-endpoints/%s", id), params, idempotency_key))

    def delete(self, id: str, *, idempotency_key: str | None = None) -> None:
        """Delete an endpoint and its delivery history."""
        self._respond("DELETE", path("/v1/webhook-endpoints/%s", id), None, idempotency_key)

    def verify(self, id: str, *, idempotency_key: str | None = None) -> WebhookEndpoint:
        """Send the endpoint its verification challenge again. One that does not answer is refused with a ValidationError saying what it answered instead."""
        return WebhookEndpoint(
            self._request("POST", path("/v1/webhook-endpoints/%s/verify", id), None, idempotency_key)
        )

    def test(self, id: str, *, idempotency_key: str | None = None) -> WebhookDelivery:
        """Queue a sample charge.paid event, marked as a test, to a verified endpoint."""
        return WebhookDelivery(self._request("POST", path("/v1/webhook-endpoints/%s/test", id), None, idempotency_key))

    def rotate_secret(self, id: str, *, idempotency_key: str | None = None) -> WebhookEndpoint:
        """Replace the endpoint's signing secret. The answer carries the new one, shown this once; the old one keeps signing for a day, until previous_secret_expires_at.

        A ConflictError whose was_replayed() is true means an earlier request with the same idempotency key rotated the
        secret, and the new one is lost with its answer; the secret your receiver has keeps signing for a day. Rotate again
        only when the new secret can go into the receiver straight away: only one earlier secret is kept, so a second
        rotation stops the receiver's secret from signing at once.
        """
        return _endpoint(self._respond("POST", path("/v1/webhook-endpoints/%s/secret", id), None, idempotency_key))

    def deliveries(self, id: str, params: WebhookDeliveryListParams | None = None) -> Page[WebhookDelivery]:
        """List what the endpoint was sent, newest first, kept for 30 days."""
        return self._page(path("/v1/webhook-endpoints/%s/deliveries", id), params, WebhookDelivery)

    def retrieve_delivery(self, id: str, delivery_id: str) -> WebhookDelivery:
        """Retrieve one of the endpoint's deliveries with every attempt to send it, the latest first, and the JSON body it carried when the key may also read events."""
        return WebhookDelivery(self._request("GET", path("/v1/webhook-endpoints/%s/deliveries/%s", id, delivery_id)))

    def retry_delivery(self, id: str, delivery_id: str, *, idempotency_key: str | None = None) -> WebhookDelivery:
        """Send one of the endpoint's deliveries again, once the endpoint is verified and not paused."""
        return WebhookDelivery(
            self._request(
                "POST", path("/v1/webhook-endpoints/%s/deliveries/%s/retry", id, delivery_id), None, idempotency_key
            )
        )


def _endpoint(response: ApiResponse) -> WebhookEndpoint:
    """Read the endpoint and its meta from an answer."""
    return WebhookEndpoint(data(response), meta(response))
