"""The /v1/account and /v1/payment-settings endpoints."""

from __future__ import annotations

from .._http import ApiResponse
from .._params import AccountUpdateParams, PaymentSettingsUpdateParams
from .._resources.account import Account
from ._base import Service, data, meta


class AccountService(Service):
    """The /v1/account and /v1/payment-settings endpoints."""

    __slots__ = ()

    def retrieve(self) -> Account:
        """Retrieve the account the API key belongs to, with the coins it accepts in the key's mode."""
        return _account(self._respond("GET", "/v1/account"))

    def update(self, params: AccountUpdateParams, *, idempotency_key: str | None = None) -> Account:
        """Change the account's name, public profile, checkout and invoice settings or business details, in the shape retrieve() reads; None clears a field. Needs account:write."""
        return _account(self._respond("PATCH", "/v1/account", params, idempotency_key))

    def update_payment_settings(
        self, params: PaymentSettingsUpdateParams, *, idempotency_key: str | None = None
    ) -> Account:
        """Change the default currency, the payment tolerances, the checkout language or invoice reminders. Needs payment_settings:write."""
        return _account(self._respond("PATCH", "/v1/payment-settings", params, idempotency_key))


def _account(response: ApiResponse) -> Account:
    """Read the account and its meta from an answer."""
    return Account(data(response), meta(response))
