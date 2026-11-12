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

    def test_checkout_locales_are_named_after_their_languages(self) -> None:
        self.assertEqual(
            ["ENGLISH", "FRENCH", "GERMAN", "SPANISH", "TURKISH", "PORTUGUESE", "RUSSIAN", "ARABIC"],
            [member.name for member in CheckoutLocale],
        )

    def test_every_activity_action_is_known_by_its_name_in_its_order(self) -> None:
        actions = [
            ("WALLETS_CHANGED", "wallets.changed"),
            ("PAYOUT_ADDRESS_ACCESS_CHANGED", "wallets.api_access_changed"),
            ("SECOND_FACTOR_REQUIREMENT_CHANGED", "team.second_factor_requirement_changed"),
            ("PAYMENT_SETTINGS_UPDATED", "payment_settings.updated"),
            ("PROFILE_UPDATED", "profile.updated"),
            ("BUSINESS_DETAILS_UPDATED", "business_details.updated"),
            ("API_KEY_CREATED", "api_key.created"),
            ("API_KEY_UPDATED", "api_key.updated"),
            ("API_KEY_REVOKED", "api_key.revoked"),
            ("WEBHOOK_CREATED", "webhook.created"),
            ("WEBHOOK_UPDATED", "webhook.updated"),
            ("WEBHOOK_DELETED", "webhook.deleted"),
            ("WEBHOOK_SECRET_ROTATED", "webhook.secret_rotated"),
            ("MEMBER_INVITED", "member.invited"),
            ("MEMBER_JOINED", "member.joined"),
            ("MEMBER_ROLE_CHANGED", "member.role_changed"),
            ("MEMBER_REMOVED", "member.removed"),
            ("PAYMENT_LINK_CREATED", "payment_link.created"),
            ("PAYMENT_LINK_UPDATED", "payment_link.updated"),
            ("PAYMENT_LINK_ARCHIVED", "payment_link.archived"),
            ("PAYMENT_LINK_RESTORED", "payment_link.restored"),
            ("INVITATION_CANCELED", "member.invitation_canceled"),
            ("CHARGE_PAYMENT_REQUESTED", "charge.payment_requested"),
            ("WEBHOOK_DISABLED", "webhook.disabled"),
            ("CHARGE_CANCELED", "charge.canceled"),
            ("CHARGE_ACCEPTED", "charge.accepted"),
            ("REFUND_RECORDED", "refund.recorded"),
            ("INVOICE_VOIDED", "invoice.voided"),
            ("PLAN_PAYMENT_STARTED", "plan.payment_started"),
            ("SUBSCRIPTION_CANCELED", "plan.subscription_canceled"),
            ("SUBSCRIPTION_RESUMED", "plan.subscription_resumed"),
            ("SIGNED_IN", "auth.signed_in"),
            ("SIGN_IN_FAILED", "auth.sign_in_failed"),
            ("PASSWORD_CHANGED", "auth.password_changed"),
            ("TWO_FACTOR_ENABLED", "auth.two_factor_enabled"),
            ("TWO_FACTOR_DISABLED", "auth.two_factor_disabled"),
            ("SIGNED_OUT_ELSEWHERE", "auth.signed_out_elsewhere"),
            ("TWO_FACTOR_FAILED", "auth.two_factor_failed"),
            ("EMAIL_CHANGED", "auth.email_changed"),
            ("PASSKEY_ADDED", "auth.passkey_added"),
            ("PASSKEY_REMOVED", "auth.passkey_removed"),
            ("COUPON_CREATED", "coupon.created"),
            ("COUPON_UPDATED", "coupon.updated"),
            ("COUPON_DELETED", "coupon.deleted"),
            ("APP_CONNECTED", "auth.app_connected"),
            ("APP_DISCONNECTED", "auth.app_disconnected"),
            ("CHAT_CONNECTED", "chat.connected"),
            ("CHAT_UPDATED", "chat.updated"),
            ("CHAT_REMOVED", "chat.removed"),
            ("CHAT_DISABLED", "chat.disabled"),
            ("SANCTIONS_MATCHED", "sanctions.matched"),
            ("SANCTIONS_ACCEPTED", "sanctions.accepted"),
            ("SANCTIONS_RETURN_REQUESTED", "sanctions.return_requested"),
            ("SOCIAL_ACCOUNT_CONNECTED", "auth.social_connected"),
            ("SOCIAL_ACCOUNT_DISCONNECTED", "auth.social_disconnected"),
        ]

        self.assertEqual(actions, [(action.name, action.value) for action in ActivityAction])

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
            {"default_currency": Currency.EUR, "checkout_locale": CheckoutLocale.ARABIC}
        )
        self.assertEqual({"default_currency": "EUR", "checkout_locale": "ar"}, body(self.http.last_request()))


if __name__ == "__main__":
    unittest.main()
