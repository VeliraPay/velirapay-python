"""The coins on offer."""

from __future__ import annotations

from .._enums import Asset
from ._base import ApiResource, integer, nullable_bool, nullable_string, one_of, string


class SupportedAsset(ApiResource):
    """A coin that can be paid in the API key's mode, with the lowest price a charge in it can have."""

    __slots__ = ()

    @property
    def id(self) -> str:
        """What the API calls the coin, such as "BTC" or "USDT_BSC": pass it as asset when you create a charge."""
        return string(self._attributes, "id")

    @property
    def name(self) -> str:
        """The coin's name, such as "Tether USD"."""
        return string(self._attributes, "name")

    @property
    def ticker(self) -> str:
        """The coin's symbol, such as "USDT"."""
        return string(self._attributes, "ticker")

    @property
    def network(self) -> str:
        """The network the customer has to send it on."""
        return string(self._attributes, "network")

    @property
    def contract_address(self) -> str | None:
        """The token's contract on that network, or None for a network's own coin."""
        return nullable_string(self._attributes, "contract_address")

    @property
    def decimals(self) -> int:
        """The decimal places the coin has on its network."""
        return integer(self._attributes, "decimals")

    @property
    def required_confirmations(self) -> int:
        """How many confirmations a payment needs before it counts."""
        return integer(self._attributes, "required_confirmations")

    @property
    def confirmation_wait(self) -> str:
        """About how long those confirmations take, in words."""
        return string(self._attributes, "confirmation_wait")

    @property
    def accepted(self) -> bool | None:
        """Whether the account takes it right now, which needs a payout address for that network."""
        return nullable_bool(self._attributes, "accepted")

    @property
    def currency(self) -> str:
        """The currency exchange_rate and minimum_price are in."""
        return string(self._attributes, "currency")

    @property
    def exchange_rate(self) -> str | None:
        """What one unit of the coin is worth in that currency right now, or None while no rate is available."""
        return nullable_string(self._attributes, "exchange_rate")

    @property
    def minimum_amount(self) -> str | None:
        """The least a charge in it can come to, in the coin itself, or None when it has no minimum of its own."""
        return nullable_string(self._attributes, "minimum_amount")

    @property
    def minimum_price(self) -> str | None:
        """The lowest price a charge in it can have right now, in that currency, or None while a coin with a minimum has no rate."""
        return nullable_string(self._attributes, "minimum_price")

    @property
    def network_surcharge(self) -> str | None:
        """What a charge in the coin asks the customer for on top of the price, in the coin, for the network; None for a coin without one."""
        return nullable_string(self._attributes, "network_surcharge")

    def asset(self) -> Asset | None:
        """The Asset member of the coin, or None for one the API added after this version of the library."""
        return one_of(Asset, self.id)
