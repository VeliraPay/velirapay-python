from __future__ import annotations

import unittest
from datetime import UTC, datetime

from velirapay import AccountCheckout, AccountInvoices, BusinessType, Industry, MonthlyVolume

from .support import MockTransport, body, client, fixture, path_of, query_of


class AccountTest(unittest.TestCase):
    def setUp(self) -> None:
        self.http = MockTransport()

    def test_the_account_is_retrieved_with_the_coins_it_accepts(self) -> None:
        self.http.json(fixture("account"))

        account = client(self.http).account.retrieve()

        self.assertEqual("/v1/account", path_of(self.http.last_request()))
        self.assertEqual("acme", account.id)
        self.assertTrue(account.is_organization())
        self.assertEqual("Acme", account.name)
        self.assertEqual("Acme Inc.", account.display_name)
        self.assertIsNone(account.logo_url)
        self.assertEqual("https://acme.example", account.website_url)
        self.assertEqual("billing@acme.example", account.support_email)
        self.assertEqual("+442071234567", account.support_phone)
        self.assertEqual("#4f46e5", account.brand_color)
        self.assertEqual("EUR", account.default_currency)
        self.assertEqual("1", account.underpayment_tolerance)
        self.assertEqual("3", account.overpayment_threshold)
        self.assertEqual(datetime(2026, 1, 15, 10, 0, tzinfo=UTC), account.created_at)
        self.assertEqual("test", account.mode)
        self.assertTrue(account.is_test_mode())
        self.assertEqual(["BTC", "ETH", "USDC"], account.accepted_assets)

    def test_the_business_behind_the_account_is_read_into_typed_attributes(self) -> None:
        self.http.json(fixture("account"))

        business = client(self.http).account.retrieve().business

        self.assertIs(BusinessType.COMPANY, business.type)
        self.assertEqual("Acme Holdings Ltd", business.legal_name)
        self.assertEqual("12345678", business.registration_number)
        self.assertEqual("GB123456789", business.tax_id)
        self.assertEqual("1 Example Street", business.address.line1)
        self.assertIsNone(business.address.line2)
        self.assertEqual("London", business.address.city)
        self.assertEqual("EC1A 1BB", business.address.postal_code)
        self.assertIsNone(business.address.state)
        self.assertEqual("GB", business.address.country)
        self.assertIs(Industry.SOFTWARE, business.industry)
        self.assertEqual("Project management software, billed monthly.", business.product_description)
        self.assertIs(MonthlyVolume.UNDER_50K, business.monthly_volume)
        self.assertEqual("+442071234500", business.phone)

    def test_the_accounts_checkout_invoice_and_payment_settings_are_read(self) -> None:
        self.http.json(
            {
                "data": {
                    "id": "acme",
                    "logo_dark_url": "https://acme.example/logo-dark.png",
                    "terms_url": "https://acme.example/terms",
                    "refund_policy_url": "https://acme.example/refunds",
                    "checkout": {
                        "appearance": "dark",
                        "coin_order": ["BTC", "ETH"],
                        "default_coin": "LTC",
                        "success_url": None,
                        "cancel_url": None,
                        "success_message": "Thank you",
                        "hide_powered_by": True,
                    },
                    "invoices": {"number_prefix": "BILL", "footer": "Thank you", "show_business_details": True},
                    "checkout_locale": "fr",
                    "invoice_reminders": True,
                    "api_payout_address_changes": True,
                }
            }
        )

        account = client(self.http).account.retrieve()

        self.assertEqual("https://acme.example/logo-dark.png", account.logo_dark_url)
        self.assertEqual("https://acme.example/terms", account.terms_url)
        self.assertEqual("https://acme.example/refunds", account.refund_policy_url)
        self.assertEqual(
            AccountCheckout(
                appearance="dark",
                coin_order=["BTC", "ETH"],
                default_coin="LTC",
                success_url=None,
                cancel_url=None,
                success_message="Thank you",
                hide_powered_by=True,
            ),
            account.checkout,
        )
        self.assertEqual(
            AccountInvoices(number_prefix="BILL", footer="Thank you", show_business_details=True), account.invoices
        )
        self.assertEqual("fr", account.checkout_locale)
        self.assertTrue(account.invoice_reminders)
        self.assertTrue(account.api_payout_address_changes)

    def test_missing_account_settings_have_safe_defaults(self) -> None:
        self.http.json({"data": {"id": "acme"}})

        account = client(self.http).account.retrieve()

        self.assertIsNone(account.logo_dark_url)
        self.assertIsNone(account.terms_url)
        self.assertIsNone(account.refund_policy_url)
        self.assertIsNone(account.checkout)
        self.assertIsNone(account.invoices)
        self.assertIsNone(account.checkout_locale)
        self.assertFalse(account.invoice_reminders)
        self.assertFalse(account.api_payout_address_changes)
        self.assertEqual("free", account.plan)
        self.assertFalse(account.is_pro())
        self.assertIsNone(account.mode)
        self.assertEqual([], account.accepted_assets)

    def test_business_details_withheld_from_a_key_without_account_write_read_as_none(self) -> None:
        self.http.json(
            {
                "data": {"id": "acme", "display_name": "Acme Inc.", "business": None},
                "meta": {"accepted_assets": ["BTC"], "mode": "live"},
            }
        )

        account = client(self.http).account.retrieve()

        self.assertIsNone(account.get("business"))
        self.assertEqual({}, account.business.to_dict())
        self.assertIsNone(account.business.type)
        self.assertIsNone(account.business.legal_name)
        self.assertIsNone(account.business.tax_id)
        self.assertIsNone(account.business.address.country)
        self.assertIsNone(account.business.industry)
        self.assertIsNone(account.business.monthly_volume)
        self.assertEqual("Acme Inc.", account.display_name)
        self.assertEqual(["BTC"], account.accepted_assets)

    def test_business_details_that_are_unset_or_unknown_to_this_library_are_none(self) -> None:
        self.http.json({"data": {"id": "acme", "business": {"type": "cooperative", "industry": None}}, "meta": {}})

        account = client(self.http).account.retrieve()

        self.assertIsNone(account.support_phone)
        self.assertIsNone(account.business.type)
        self.assertEqual("cooperative", account.business.get("type"))
        self.assertIsNone(account.business.industry)
        self.assertIsNone(account.business.monthly_volume)
        self.assertIsNone(account.business.legal_name)
        self.assertIsNone(account.business.address.country)

    def test_the_account_and_its_payment_settings_are_changed(self) -> None:
        account = fixture("account")["data"]
        (
            self.http.json(
                {
                    "data": {
                        **account,
                        "display_name": "Acme",
                        "plan": {"name": "pro", "fee_percent": "0", "pro_ends_at": "2026-12-06T00:00:00.000000Z"},
                    },
                    "meta": {"mode": "live", "accepted_assets": ["BTC"]},
                }
            ).json({"data": account, "meta": {"mode": "live", "accepted_assets": []}})
        )
        velirapay = client(self.http)

        updated = velirapay.account.update({"display_name": "Acme", "checkout": {"appearance": "dark"}})

        self.assertEqual("PATCH", self.http.last_request().method)
        self.assertEqual("/v1/account", path_of(self.http.last_request()))
        self.assertEqual({"display_name": "Acme", "checkout": {"appearance": "dark"}}, body(self.http.last_request()))
        self.assertEqual("Acme", updated.display_name)
        self.assertEqual(["BTC"], updated.accepted_assets)
        self.assertTrue(updated.is_pro())
        self.assertEqual("0", updated.fee_percent)
        self.assertEqual(datetime(2026, 12, 6, tzinfo=UTC), updated.pro_ends_at)

        settings = velirapay.account.update_payment_settings({"underpayment_tolerance": "2"})

        self.assertEqual("PATCH", self.http.last_request().method)
        self.assertEqual("/v1/payment-settings", path_of(self.http.last_request()))
        self.assertEqual({"underpayment_tolerance": "2"}, body(self.http.last_request()))
        self.assertEqual("live", settings.mode)

    def test_the_payment_tolerances_are_sent_as_decimal_strings(self) -> None:
        self.http.json({"data": fixture("account")["data"]})

        client(self.http).account.update_payment_settings(
            {"underpayment_tolerance": 2.5, "overpayment_threshold": 3, "invoice_reminders": True}
        )

        self.assertEqual(
            {"underpayment_tolerance": "2.5", "overpayment_threshold": "3", "invoice_reminders": True},
            body(self.http.last_request()),
        )

    def test_a_field_set_to_none_is_sent_as_null_to_clear_it(self) -> None:
        self.http.json({"data": fixture("account")["data"]})

        client(self.http).account.update({"support_phone": None, "business": {"address": {"line2": None}}})

        self.assertEqual(b'{"support_phone":null,"business":{"address":{"line2":null}}}', self.http.last_request().body)

    def test_the_overview_is_retrieved(self) -> None:
        self.http.json(
            {
                "data": {
                    "object": "overview",
                    "currency": "USD",
                    "volume": "1250.00",
                    "volume_change_percent": 12.5,
                    "sent_volume": "1100.00",
                    "paid_charges": 12,
                    "conversion_rate_percent": 60,
                    "pending_charges": 2,
                    "active_payment_links": 3,
                    "open_invoices": 1,
                    "overdue_invoices": 0,
                    "funnel": {"started": 20},
                }
            }
        )

        overview = client(self.http).overview.retrieve()

        self.assertEqual("/v1/overview", path_of(self.http.last_request()))
        self.assertEqual("USD", overview.currency)
        self.assertEqual("1250.00", overview.volume)
        self.assertEqual(12.5, overview.volume_change_percent)
        self.assertEqual("1100.00", overview.sent_volume)
        self.assertEqual(12, overview.paid_charges)
        self.assertEqual(60.0, overview.conversion_rate_percent)
        self.assertEqual(2, overview.pending_charges)
        self.assertEqual(3, overview.active_payment_links)
        self.assertEqual(1, overview.open_invoices)
        self.assertEqual(0, overview.overdue_invoices)
        self.assertEqual({"started": 20}, overview.get("funnel"))

    def test_an_overview_with_nothing_to_compare_against_has_no_percentages(self) -> None:
        self.http.json({"data": {"currency": "USD", "volume_change_percent": None, "conversion_rate_percent": True}})

        overview = client(self.http).overview.retrieve()

        self.assertIsNone(overview.volume_change_percent)
        self.assertIsNone(overview.conversion_rate_percent)
        self.assertEqual("0", overview.volume)
        self.assertEqual(0, overview.paid_charges)

    def test_payout_addresses_are_listed_set_and_removed(self) -> None:
        bitcoin = {
            "object": "payout_address",
            "network": "bitcoin",
            "name": "Bitcoin",
            "address": "bc1qexample",
            "assets": ["BTC"],
            "payouts_held_until": None,
            "updated_at": "2026-10-02T08:14:51.000000Z",
        }
        (
            self.http.json(
                {
                    "data": [
                        bitcoin,
                        {**bitcoin, "network": "evm", "name": "Ethereum", "address": None, "assets": ["ETH", "USDT"]},
                    ],
                    "meta": {"mode": "live"},
                }
            )
            .json({"data": {**bitcoin, "payouts_held_until": "2026-11-08T08:00:00.000000Z"}})
            .json({"data": {**bitcoin, "address": None}})
        )
        velirapay = client(self.http)

        current, missing = velirapay.payout_addresses.list()

        self.assertEqual("/v1/payout-addresses", path_of(self.http.last_request()))
        self.assertEqual("bc1qexample", current.address)
        self.assertEqual(datetime(2026, 10, 2, 8, 14, 51, tzinfo=UTC), current.updated_at)
        self.assertIsNone(missing.address)
        self.assertEqual(["ETH", "USDT"], missing.assets)

        updated = velirapay.payout_addresses.update("bitcoin", {"address": "bc1qexample"})

        self.assertEqual("PUT", self.http.last_request().method)
        self.assertEqual("/v1/payout-addresses/bitcoin", path_of(self.http.last_request()))
        self.assertEqual({"address": "bc1qexample"}, body(self.http.last_request()))
        self.assertEqual(datetime(2026, 11, 8, 8, 0, tzinfo=UTC), updated.payouts_held_until)

        self.assertIsNone(velirapay.payout_addresses.delete("bitcoin").address)
        self.assertEqual("DELETE", self.http.last_request().method)

    def test_the_activity_log_is_listed_with_its_filters(self) -> None:
        self.http.json(
            {
                "data": [
                    {
                        "id": "5",
                        "object": "activity",
                        "action": "api_key.created",
                        "description": "Created an API key",
                        "actor": 'API key "Bot"',
                        "subject": "Shop",
                        "properties": {"prefix": "vp_live_aaaa"},
                        "ip_address": "203.0.113.7",
                        "mode": "live",
                        "created_at": "2026-11-06T09:00:00.000000Z",
                    }
                ],
                "meta": {"current_page": 1, "last_page": 1, "per_page": 25, "total": 1, "mode": "live"},
            }
        )

        entry = (
            client(self.http).activity.list({"action": "sensitive", "from": "2026-11-01", "to": "2026-11-06"}).data[0]
        )

        self.assertEqual("/v1/activity", path_of(self.http.last_request()))
        self.assertEqual(
            {"action": "sensitive", "from": "2026-11-01", "to": "2026-11-06"}, query_of(self.http.last_request())
        )
        self.assertEqual("api_key.created", entry.action)
        self.assertEqual("Created an API key", entry.description)
        self.assertEqual('API key "Bot"', entry.actor)
        self.assertEqual("Shop", entry.subject)
        self.assertEqual("203.0.113.7", entry.ip_address)
        self.assertEqual("live", entry.mode)
        self.assertEqual({"prefix": "vp_live_aaaa"}, entry.properties)
        self.assertEqual(datetime(2026, 11, 6, 9, 0, tzinfo=UTC), entry.created_at)

    def test_a_pro_payment_is_started(self) -> None:
        self.http.json(
            {
                "data": {
                    "object": "pro_payment",
                    "months": 1,
                    "price": "9.99",
                    "currency": "USD",
                    "asset": "BTC",
                    "asset_amount": "0.0001",
                    "checkout_url": "https://velirapay.com/c/abc",
                    "expires_at": "2026-11-06T10:00:00.000000Z",
                },
                "meta": {"started": True},
            },
            201,
        )

        payment = client(self.http, "vp_live_secret").billing.start_pro_payment({"asset": "BTC"})

        self.assertEqual("POST", self.http.last_request().method)
        self.assertEqual("/v1/billing/pro", path_of(self.http.last_request()))
        self.assertEqual({"asset": "BTC"}, body(self.http.last_request()))
        self.assertEqual("https://velirapay.com/c/abc", payment.checkout_url)
        self.assertEqual("9.99", payment.price)
        self.assertEqual(1, payment.months)
        self.assertEqual("0.0001", payment.asset_amount)
        self.assertEqual(datetime(2026, 11, 6, 10, 0, tzinfo=UTC), payment.expires_at)
        self.assertTrue(payment.started)


if __name__ == "__main__":
    unittest.main()
