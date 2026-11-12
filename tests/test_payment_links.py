from __future__ import annotations

import unittest
from datetime import UTC, datetime

from velirapay import Asset, CheckoutQuestion, PaymentLink, PricingType

from .support import MockTransport, body, client, fixture, list_response, path_of, query_of


class PaymentLinkTest(unittest.TestCase):
    def setUp(self) -> None:
        self.http = MockTransport()

    def test_a_payment_link_is_created_with_enums_and_dates_converted(self) -> None:
        self.http.json({"data": fixture("payment_link")}, 201)

        link = client(self.http).payment_links.create(
            {
                "title": "Tip jar",
                "pricing_type": PricingType.OPEN,
                "currency": "USD",
                "suggested_amounts": ["5.00", "10.00", "25.00"],
                "accepted_assets": [Asset.BTC, "ETH"],
                "custom_fields": [{"label": "Message", "required": False}],
                "expires_at": datetime(2026, 12, 31, 23, 59, 59, tzinfo=UTC),
            }
        )

        request = self.http.last_request()
        self.assertEqual("POST", request.method)
        self.assertEqual("/v1/payment-links", path_of(request))
        self.assertEqual(
            {
                "title": "Tip jar",
                "pricing_type": "open",
                "currency": "USD",
                "suggested_amounts": ["5.00", "10.00", "25.00"],
                "accepted_assets": ["BTC", "ETH"],
                "custom_fields": [{"label": "Message", "required": False}],
                "expires_at": "2026-12-31T23:59:59+00:00",
            },
            body(request),
        )
        self.assertEqual("p4n8r2t6y1ua", link.id)

    def test_a_payment_link_is_read_into_typed_attributes(self) -> None:
        self.http.json({"data": fixture("payment_link")})

        link = client(self.http).payment_links.retrieve("p4n8r2t6y1ua")

        self.assertEqual("/v1/payment-links/p4n8r2t6y1ua", path_of(self.http.last_request()))
        self.assertEqual("Tip jar", link.title)
        self.assertEqual("Support the project.", link.description)
        self.assertEqual(PricingType.OPEN, link.pricing_type)
        self.assertFalse(link.has_fixed_amount())
        self.assertIsNone(link.amount)
        self.assertEqual(["5.00", "10.00", "25.00"], link.suggested_amounts)
        self.assertEqual("1.00", link.min_amount)
        self.assertEqual("500.00", link.max_amount)
        self.assertIsNone(link.accepted_assets)
        self.assertTrue(link.is_active())
        self.assertEqual("https://example.com/thanks", link.success_url)
        self.assertTrue(link.collect_name)
        self.assertFalse(link.require_email)
        self.assertEqual([CheckoutQuestion(label="Message", required=False)], link.custom_fields)
        self.assertEqual("Thank you!", link.success_message)
        self.assertIsNone(link.expires_at)
        self.assertEqual(100, link.max_payments)
        self.assertTrue(link.accepting_payments)
        self.assertEqual(12, link.views_count)
        self.assertEqual("https://velirapay.com/pay/p4n8r2t6y1ua", link.checkout_url)
        self.assertEqual(datetime(2026, 9, 2, 8, 30, tzinfo=UTC), link.updated_at)

    def test_a_payment_link_is_updated_with_none_sent_as_null(self) -> None:
        self.http.json({"data": {**fixture("payment_link"), "title": "Coffee"}})

        link = client(self.http).payment_links.update("p4n8r2t6y1ua", {"title": "Coffee", "accepted_assets": None})

        request = self.http.last_request()
        self.assertEqual("PATCH", request.method)
        self.assertEqual("/v1/payment-links/p4n8r2t6y1ua", path_of(request))
        self.assertEqual({"title": "Coffee", "accepted_assets": None}, body(request))
        self.assertEqual("Coffee", link.title)

    def test_a_payment_link_is_archived_and_restored(self) -> None:
        self.http.json({"data": {**fixture("payment_link"), "status": "archived"}}).json(
            {"data": fixture("payment_link")}
        )
        velirapay = client(self.http)

        archived = velirapay.payment_links.archive("p4n8r2t6y1ua")

        self.assertEqual("POST", self.http.last_request().method)
        self.assertEqual("/v1/payment-links/p4n8r2t6y1ua/archive", path_of(self.http.last_request()))
        self.assertTrue(archived.is_archived())

        restored = velirapay.payment_links.restore("p4n8r2t6y1ua")

        self.assertEqual("DELETE", self.http.last_request().method)
        self.assertEqual("/v1/payment-links/p4n8r2t6y1ua/archive", path_of(self.http.last_request()))
        self.assertTrue(restored.is_active())

    def test_payment_links_are_listed(self) -> None:
        self.http.json(list_response([fixture("payment_link")]))

        page = client(self.http).payment_links.list({"per_page": 10})

        self.assertEqual({"per_page": "10"}, query_of(self.http.last_request()))
        self.assertIsInstance(page.data[0], PaymentLink)


if __name__ == "__main__":
    unittest.main()
