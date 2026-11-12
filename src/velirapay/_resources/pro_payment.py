"""Paying for Pro in crypto."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from ._base import ApiResource, boolean, integer, string, timestamp


class ProPayment(ApiResource):
    """A crypto payment for a month of Pro: where to pay it and what to send."""

    __slots__ = ("_meta",)

    def __init__(self, attributes: Mapping[str, Any], meta: Mapping[str, Any] | None = None) -> None:
        """Read the payment from its attributes and the meta the API sent with them."""
        super().__init__(attributes)
        self._meta: dict[str, Any] = copy.deepcopy(dict(meta or {}))

    @property
    def months(self) -> int:
        """How many months it pays for."""
        return integer(self._attributes, "months", 1)

    @property
    def price(self) -> str:
        """What it costs, in currency."""
        return string(self._attributes, "price")

    @property
    def currency(self) -> str:
        """The currency of the price."""
        return string(self._attributes, "currency")

    @property
    def asset(self) -> str:
        """The coin it is paid in."""
        return string(self._attributes, "asset")

    @property
    def asset_amount(self) -> str:
        """What to send, in the coin."""
        return string(self._attributes, "asset_amount")

    @property
    def checkout_url(self) -> str:
        """The page to pay it on."""
        return string(self._attributes, "checkout_url")

    @property
    def expires_at(self) -> datetime | None:
        """When its rate stops holding."""
        return timestamp(self._attributes, "expires_at")

    @property
    def started(self) -> bool:
        """Whether this request started it, rather than answering with the one already waiting."""
        return boolean(self._meta, "started")
