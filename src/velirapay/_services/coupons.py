"""The /v1/coupons endpoints."""

from __future__ import annotations

from collections.abc import Iterator

from .._page import Page
from .._params import CouponCreateParams, CouponListParams, CouponUpdateParams
from .._resources.coupon import Coupon
from ._base import Service, path


class CouponService(Service):
    """The /v1/coupons endpoints, where a coupon's id is its code."""

    __slots__ = ()

    def create(self, params: CouponCreateParams, *, idempotency_key: str | None = None) -> Coupon:
        """Create a coupon taking either percent_off or amount_off; currency is required with amount_off or min_amount."""
        return Coupon(self._request("POST", "/v1/coupons", params, idempotency_key))

    def retrieve(self, id: str) -> Coupon:
        """Retrieve a coupon by its code, in any case."""
        return Coupon(self._request("GET", path("/v1/coupons/%s", id)))

    def update(self, id: str, params: CouponUpdateParams, *, idempotency_key: str | None = None) -> Coupon:
        """Change a coupon's limits; its code, discount, currency and minimum price cannot change."""
        return Coupon(self._request("PATCH", path("/v1/coupons/%s", id), params, idempotency_key))

    def list(self, params: CouponListParams | None = None) -> Page[Coupon]:
        """List coupons, newest first."""
        return self._page("/v1/coupons", params, Coupon)

    def iterator(self, params: CouponListParams | None = None) -> Iterator[Coupon]:
        """Iterate over every coupon, newest first, fetching pages as they are reached."""
        yield from self.list(params).auto_paging_iterator()

    def delete(self, id: str, *, idempotency_key: str | None = None) -> None:
        """Delete a coupon; charges that used it keep its code and their discount."""
        self._respond("DELETE", path("/v1/coupons/%s", id), None, idempotency_key)
