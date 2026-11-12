from __future__ import annotations

import unittest
from enum import StrEnum

from velirapay import (
    AccountType,
    ActivityAction,
    AddressNetwork,
    CheckoutAppearance,
    CheckoutLocale,
    Currency,
    MemberRole,
    PlanName,
    WebhookDeliveryStatus,
)

from .support import MockTransport, body, client, fixture, list_response, path_of, query_of


class EnumTest(unittest.TestCase):
    def setUp(self) -> None:
        self.http = MockTransport()

    def test_every_value_the_api_uses_is_known_in_its_order(self) -> None:
        sets: list[tuple[type[StrEnum], list[str]]] = [
            (Currency, ["USD", "EUR", "GBP", "CAD", "AUD", "CHF", "TRY"]),
            (MemberRole, ["owner", "admin", "finance", "support", "viewer"]),
            (
                AddressNetwork,
                [
                    "bitcoin", "litecoin", "dogecoin", "bitcoincash", "evm", "bsc", "base", "arbitrum", "polygon",
                    "tron", "monero", "solana", "lightning",
                ],
            ),
            (CheckoutAppearance, ["auto", "light", "dark"]),
            (WebhookDeliveryStatus, ["pending", "succeeded", "failed"]),
            (PlanName, ["free", "pro"]),
            (AccountType, ["personal", "organization"]),
            (CheckoutLocale, ["en", "fr", "de", "es", "tr", "pt", "ru", "ar"]),
        ]  # fmt: skip

        for enum, values in sets:
            with self.subTest(enum.__name__):
                self.assertEqual(values, [member.value for member in enum])

    def test_every_activity_action_is_named_after_its_value(self) -> None:
        self.assertEqual(55, len(ActivityAction))
        self.assertEqual(
            "team.second_factor_requirement_changed", ActivityAction.TEAM_SECOND_FACTOR_REQUIREMENT_CHANGED
        )
        self.assertEqual("wallets.changed", next(iter(ActivityAction)))
        self.assertEqual("auth.social_disconnected", list(ActivityAction)[-1])

        for action in ActivityAction:
            with self.subTest(action.value):
                self.assertEqual(action.value.replace(".", "_").upper(), action.name)

    def test_members_are_sent_as_their_values(self) -> None:
        member = {"id": "3", "object": "member", "name": "Ada", "email": "ada@example.com", "role": "finance"}
        address = {"object": "payout_address", "network": "bitcoin", "name": "Bitcoin", "address": "bc1q", "assets": []}
        (
            self.http.json({"data": member})
            .json({"data": address})
            .json({"data": [], "meta": {"mode": "live", "currencies": ["USD"]}})
            .json(list_response([]))
            .json(list_response([]))
            .json({"data": fixture("account")["data"]})
        )
        velirapay = client(self.http)

        velirapay.members.update("3", {"role": MemberRole.FINANCE})
        self.assertEqual({"role": "finance"}, body(self.http.last_request()))

        velirapay.payout_addresses.update(AddressNetwork.BITCOIN_CASH, {"address": "bitcoincash:qexample"})
        self.assertEqual("/v1/payout-addresses/bitcoincash", path_of(self.http.last_request()))

        velirapay.assets.list({"currency": Currency.TRY})
        self.assertEqual({"currency": "TRY"}, query_of(self.http.last_request()))

        velirapay.webhook_endpoints.deliveries("12", {"status": WebhookDeliveryStatus.FAILED})
        self.assertEqual({"status": "failed"}, query_of(self.http.last_request()))

        velirapay.activity.list({"action": ActivityAction.API_KEY_REVOKED})
        self.assertEqual({"action": "api_key.revoked"}, query_of(self.http.last_request()))

        velirapay.account.update_payment_settings(
            {"default_currency": Currency.EUR, "checkout_locale": CheckoutLocale.AR}
        )
        self.assertEqual({"default_currency": "EUR", "checkout_locale": "ar"}, body(self.http.last_request()))


if __name__ == "__main__":
    unittest.main()
