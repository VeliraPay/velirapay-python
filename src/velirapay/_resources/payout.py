"""What became of each paid charge, and where payouts go."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .._enums import PayoutStatus
from ._base import ApiResource, ResourceList, boolean, integer, nullable_string, record, string, strings, timestamp


@dataclass(frozen=True, slots=True)
class NetworkReserve:
    """What was set aside from the merchant's share for a payout's network costs, in the payout's coin, when its exact cost was not known as it went out."""

    reserved: str
    """What was set aside at first."""

    payout_cost: str | None
    """What forwarding the payout cost, from its receipt, or None until that is known."""

    sweep_budget: str
    """What of it was set aside for later moving VeliraPay's fee to its cold wallet."""

    sweep_cost: str | None
    """What moving the fee cost, or None until every receipt for it is known."""

    sweep_available: str
    """What is left of the sweep budget."""

    held: str
    """What is still held for the merchant, counted conservatively while costs are open."""

    residual: str | None
    """What went unused once every cost is known, which stays owed to the merchant and is recorded rather than sent back on its own; None while costs are still open."""


class Payout(ApiResource):
    """What became of one paid charge: what came in, what was kept, what was sent and the transaction that carried it."""

    __slots__ = ()

    @property
    def id(self) -> str:
        """The id of the charge the payout came from, which is also its own."""
        return string(self._attributes, "id")

    @property
    def charge(self) -> str:
        """The id of the charge the payout came from."""
        return string(self._attributes, "charge")

    @property
    def status(self) -> str:
        """One of the PayoutStatus values: pending, sending, sent, failed or manual."""
        return string(self._attributes, "status")

    @property
    def asset(self) -> str:
        """The coin it was paid in and goes out in."""
        return string(self._attributes, "asset")

    @property
    def gross_amount(self) -> str:
        """What the customer paid, in the coin."""
        return string(self._attributes, "gross_amount", "0")

    @property
    def fee_percent(self) -> str:
        """The rate of the platform's fee, in percent."""
        return string(self._attributes, "fee_percent", "0")

    @property
    def fee_amount(self) -> str:
        """What was kept, in the coin."""
        return string(self._attributes, "fee_amount", "0")

    @property
    def fee_fiat_amount(self) -> str | None:
        """What the fee was worth in fiat, at the rate the charge was locked at."""
        return nullable_string(self._attributes, "fee_fiat_amount")

    @property
    def fiat_currency(self) -> str | None:
        """The fiat currency of fee_fiat_amount and exchange_rate."""
        return nullable_string(self._attributes, "fiat_currency")

    @property
    def exchange_rate(self) -> str | None:
        """The rate the charge was locked at."""
        return nullable_string(self._attributes, "exchange_rate")

    @property
    def net_amount(self) -> str:
        """What the merchant is owed, before the chain's own fee."""
        return string(self._attributes, "net_amount", "0")

    @property
    def network_fee(self) -> str | None:
        """What the chain charged, once it has been broadcast."""
        return nullable_string(self._attributes, "network_fee")

    @property
    def merchant_network_reserve(self) -> NetworkReserve | None:
        """What was set aside from the merchant's share for network costs, for a payout whose exact cost is not known as it goes out, such as one in ETH, in TRX or over Lightning; None for older charges, payouts not yet sent and payouts whose cost is known up front, such as in the Bitcoin family or in USDT and USDC."""
        reserve = record(self._attributes, "merchant_network_reserve")

        if reserve is None:
            return None

        return NetworkReserve(
            reserved=string(reserve, "reserved", "0"),
            payout_cost=nullable_string(reserve, "payout_cost"),
            sweep_budget=string(reserve, "sweep_budget", "0"),
            sweep_cost=nullable_string(reserve, "sweep_cost"),
            sweep_available=string(reserve, "sweep_available", "0"),
            held=string(reserve, "held", "0"),
            residual=nullable_string(reserve, "residual"),
        )

    @property
    def sent_amount(self) -> str | None:
        """What reached the merchant, once it has been broadcast."""
        return nullable_string(self._attributes, "sent_amount")

    @property
    def payout_address(self) -> str | None:
        """Where it goes, or None while it waits for an address."""
        return nullable_string(self._attributes, "payout_address")

    @property
    def payout_txid(self) -> str | None:
        """The transaction that carried it."""
        return nullable_string(self._attributes, "payout_txid")

    @property
    def explorer_url(self) -> str | None:
        """The transaction's page on a block explorer."""
        return nullable_string(self._attributes, "explorer_url")

    @property
    def attempts(self) -> int:
        """How many times forwarding has been tried."""
        return integer(self._attributes, "attempts")

    @property
    def last_error(self) -> str | None:
        """Why the last try did not work, or why it is held."""
        return nullable_string(self._attributes, "last_error")

    @property
    def next_attempt_at(self) -> datetime | None:
        """When it may go out next."""
        return timestamp(self._attributes, "next_attempt_at")

    @property
    def sent_at(self) -> datetime | None:
        """When it was broadcast."""
        return timestamp(self._attributes, "sent_at")

    @property
    def confirmed_at(self) -> datetime | None:
        """When it confirmed."""
        return timestamp(self._attributes, "confirmed_at")

    @property
    def created_at(self) -> datetime | None:
        """When the books were written."""
        return timestamp(self._attributes, "created_at")

    def is_sent(self) -> bool:
        """Whether the payout has confirmed, so the money is in the merchant's wallet."""
        return self.status == PayoutStatus.SENT

    def is_manual(self) -> bool:
        """Whether the payout waits on an address or on a person."""
        return self.status == PayoutStatus.MANUAL


class PayoutSummary(ApiResource):
    """What one coin adds up to across the account's payouts."""

    __slots__ = ()

    @property
    def asset(self) -> str:
        """The coin this row adds up."""
        return string(self._attributes, "asset")

    @property
    def payouts(self) -> int:
        """How many paid charges it covers."""
        return integer(self._attributes, "payouts")

    @property
    def gross_amount(self) -> str:
        """What came in."""
        return string(self._attributes, "gross_amount", "0")

    @property
    def fee_amount(self) -> str:
        """What was kept in fees."""
        return string(self._attributes, "fee_amount", "0")

    @property
    def paid_out_amount(self) -> str:
        """What has reached the merchant."""
        return string(self._attributes, "paid_out_amount", "0")

    @property
    def in_flight_amount(self) -> str:
        """What is on its way and waiting to confirm."""
        return string(self._attributes, "in_flight_amount", "0")

    @property
    def owed_amount(self) -> str:
        """What is still owed and has not left yet."""
        return string(self._attributes, "owed_amount", "0")

    @property
    def network_fee_amount(self) -> str:
        """What the chains charged to forward it."""
        return string(self._attributes, "network_fee_amount", "0")

    @property
    def waiting_for_address(self) -> int:
        """How many payouts wait for an address for this coin."""
        return integer(self._attributes, "waiting_for_address")


class PayoutAddress(ApiResource):
    """Where the account's payouts on one network go."""

    __slots__ = ()

    @property
    def network(self) -> str:
        """The network family, one of the AddressNetwork values such as "bitcoin" or "evm", which is also its id in the paths."""
        return string(self._attributes, "network")

    @property
    def name(self) -> str:
        """The network's name."""
        return string(self._attributes, "name")

    @property
    def address(self) -> str | None:
        """Where payouts go, or None while there is no address: payouts in its coins then wait for one."""
        return nullable_string(self._attributes, "address")

    @property
    def assets(self) -> list[str]:
        """The coins on offer on this network."""
        return strings(self._attributes, "assets")

    @property
    def payouts_held_until(self) -> datetime | None:
        """Until when payouts to a newly saved address wait."""
        return timestamp(self._attributes, "payouts_held_until")

    @property
    def updated_at(self) -> datetime | None:
        """When the address was last saved."""
        return timestamp(self._attributes, "updated_at")


class PayoutSummaryList(ResourceList[PayoutSummary]):
    """What each coin adds up to across the account's payouts, one PayoutSummary per coin, as a list that also has the answer's mode."""

    __slots__ = ()


class PayoutAddressList(ResourceList[PayoutAddress]):
    """Where payouts go, one PayoutAddress per network family, as a list that also has the answer's mode and the owner's switch."""

    __slots__ = ()

    @property
    def api_payout_address_changes(self) -> bool:
        """Whether an owner lets API keys and AI apps change payout addresses, which update() and delete() need."""
        return boolean(self._meta, "api_payout_address_changes")
