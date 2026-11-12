"""The /v1/payouts and /v1/payout-addresses endpoints."""

from __future__ import annotations

import builtins
from collections.abc import Iterator

from .._page import Page
from .._params import PayoutAddressUpdateParams, PayoutListParams
from .._resources.payout import Payout, PayoutAddress, PayoutSummary
from ._base import Service, objects, path


class PayoutService(Service):
    """The /v1/payouts endpoints. They only read: payouts go out on their own."""

    __slots__ = ()

    def retrieve(self, charge: str) -> Payout:
        """Retrieve the payout of a charge, by the charge's id; 404 until the charge is paid."""
        return Payout(self._request("GET", path("/v1/payouts/%s", charge)))

    def list(self, params: PayoutListParams | None = None) -> Page[Payout]:
        """List payouts, newest first."""
        return self._page("/v1/payouts", params, Payout)

    def iterator(self, params: PayoutListParams | None = None) -> Iterator[Payout]:
        """Iterate over every payout, newest first, fetching pages as they are reached."""
        yield from self.list(params).auto_paging_iterator()

    def summary(self) -> builtins.list[PayoutSummary]:
        """Add up, per coin, what has been paid out, what is on its way and what is still owed."""
        return self._page("/v1/payouts/summary", None, PayoutSummary).data


class PayoutAddressService(Service):
    """The /v1/payout-addresses endpoints. Reading needs payout_addresses:read; changing needs payout_addresses:write and an owner's switch under Payment settings."""

    __slots__ = ()

    def list(self) -> builtins.list[PayoutAddress]:
        """List where payouts go in the API key's mode: one entry per network with coins on offer, its address None while there is none."""
        return [PayoutAddress(address) for address in objects(self._respond("GET", "/v1/payout-addresses"))]

    def update(
        self, network: str, params: PayoutAddressUpdateParams, *, idempotency_key: str | None = None
    ) -> PayoutAddress:
        """Point the payouts of one network, such as "bitcoin" or "evm", at an address."""
        return PayoutAddress(self._request("PUT", path("/v1/payout-addresses/%s", network), params, idempotency_key))

    def delete(self, network: str, *, idempotency_key: str | None = None) -> PayoutAddress:
        """Remove the address of one network, so its payouts wait for a new one."""
        return PayoutAddress(self._request("DELETE", path("/v1/payout-addresses/%s", network), None, idempotency_key))
