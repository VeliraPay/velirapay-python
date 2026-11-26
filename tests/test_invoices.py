from __future__ import annotations

import unittest
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

from velirapay import Invoice, InvoiceCharge, InvoiceStatus

from .support import MockTransport, body, client, fixture, list_response, path_of, query_of


class InvoiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.http = MockTransport()

    def test_an_invoice_is_created_with_its_due_date_as_a_day(self) -> None:
        new_york = timezone(timedelta(hours=-4))

        for due_at in ("2026-10-15", date(2026, 10, 15), datetime(2026, 10, 15, 21, 30, tzinfo=new_york)):
            with self.subTest(due_at):
                self.http.json({"data": fixture("invoice")}, 201)

                invoice = client(self.http).invoices.create(
                    {
                        "customer_name": "Grace Hopper",
                        "customer_email": "grace@example.com",
                        "currency": "USD",
                        "items": [
                            {"description": "Consulting", "quantity": 10, "unit_amount": "100.00"},
                            {"description": "Hosting", "quantity": "2.5", "unit_amount": "100.00"},
                        ],
                        "due_at": due_at,
                        "success_url": "https://example.com/orders/1042",
                        "cancel_url": "https://example.com/checkout",
                        "send_email": True,
                    }
                )

                request = self.http.last_request()
                sent = body(request)
                self.assertEqual("POST", request.method)
                self.assertEqual("/v1/invoices", path_of(request))
                self.assertEqual("2026-10-15", sent["due_at"])
                self.assertIs(True, sent["send_email"])
                self.assertEqual("https://example.com/orders/1042", sent["success_url"])
                self.assertEqual("https://example.com/checkout", sent["cancel_url"])
                self.assertEqual("10", sent["items"][0]["quantity"])
                self.assertEqual("w7c2h5j9d3kx", invoice.id)

    def test_an_invoice_closes_at_a_moment_sent_in_utc_or_at_the_end_of_a_day(self) -> None:
        new_york = timezone(timedelta(hours=-4))

        for expires_at, sent in (
            (datetime(2026, 10, 31, 20, 0, tzinfo=new_york), "2026-11-01T00:00:00+00:00"),
            (date(2026, 10, 31), "2026-10-31"),
            ("2026-10-31T23:59:59+02:00", "2026-10-31T23:59:59+02:00"),
        ):
            with self.subTest(expires_at):
                self.http.json({"data": fixture("invoice")}, 201)

                client(self.http).invoices.create(
                    {
                        "customer_name": "Grace Hopper",
                        "customer_email": "grace@example.com",
                        "currency": "USD",
                        "amount": "1250.00",
                        "due_at": datetime(2026, 10, 15, 21, 30, tzinfo=new_york),
                        "expires_at": expires_at,
                        "success_message": "Thank you, your licence is on its way.",
                    }
                )

                request = body(self.http.last_request())
                self.assertEqual(sent, request["expires_at"])
                self.assertEqual("2026-10-15", request["due_at"])
                self.assertEqual("Thank you, your licence is on its way.", request["success_message"])

    def test_an_invoice_can_name_its_customer_by_a_name_or_an_email_alone(self) -> None:
        by_name = {**fixture("invoice"), "customer_name": "buyer_1042", "customer_email": None}
        by_email = {**fixture("invoice"), "customer_name": None}
        self.http.json({"data": by_name}, 201).json({"data": by_email}, 201)
        velirapay = client(self.http)

        invoice = velirapay.invoices.create({"customer_name": "buyer_1042", "currency": "USD", "amount": "1250.00"})

        self.assertEqual(
            {"customer_name": "buyer_1042", "currency": "USD", "amount": "1250.00"}, body(self.http.last_request())
        )
        self.assertEqual("buyer_1042", invoice.customer_name)
        self.assertIsNone(invoice.customer_email)

        invoice = velirapay.invoices.create(
            {"customer_name": None, "customer_email": "grace@example.com", "currency": "USD", "amount": "1250.00"}
        )

        self.assertEqual(
            {"customer_name": None, "customer_email": "grace@example.com", "currency": "USD", "amount": "1250.00"},
            body(self.http.last_request()),
        )
        self.assertIsNone(invoice.customer_name)
        self.assertEqual("grace@example.com", invoice.customer_email)

    def test_the_amounts_of_a_new_invoice_are_sent_as_decimal_strings(self) -> None:
        self.http.json({"data": fixture("invoice")}, 201).json({"data": fixture("invoice")}, 201)
        velirapay = client(self.http)

        velirapay.invoices.create(
            {
                "customer_name": "Grace Hopper",
                "customer_email": "grace@example.com",
                "currency": "USD",
                "amount": 1250.5,
            }
        )

        self.assertEqual("1250.5", body(self.http.last_request())["amount"])

        velirapay.invoices.create(
            {
                "customer_name": "Grace Hopper",
                "customer_email": "grace@example.com",
                "currency": "USD",
                "items": [{"description": "Consulting", "quantity": 2.5, "unit_amount": 99.9}],
            }
        )

        self.assertEqual(
            [{"description": "Consulting", "quantity": "2.5", "unit_amount": "99.9"}],
            body(self.http.last_request())["items"],
        )

    def test_the_tax_rates_and_discount_of_a_new_invoice_are_sent_as_decimal_strings(self) -> None:
        self.http.json({"data": fixture("invoice")}, 201).json({"data": fixture("invoice")}, 201)
        velirapay = client(self.http)

        velirapay.invoices.create(
            {
                "customer_email": "grace@example.com",
                "currency": "USD",
                "items": [
                    {"description": "Consulting", "quantity": "10", "unit_amount": "100.00", "tax_rate": 20.0},
                    {"description": "Licence", "quantity": 1, "unit_amount": 250, "tax_rate": Decimal("5.50")},
                    {"description": "Hosting", "quantity": "2.5", "unit_amount": "100.00", "tax_rate": None},
                    {"description": "Support", "quantity": "1", "unit_amount": "50.00"},
                ],
                "discount_percent": 12.5,
            }
        )

        sent = body(self.http.last_request())
        self.assertEqual(
            [
                {"description": "Consulting", "quantity": "10", "unit_amount": "100.00", "tax_rate": "20"},
                {"description": "Licence", "quantity": "1", "unit_amount": "250", "tax_rate": "5.50"},
                {"description": "Hosting", "quantity": "2.5", "unit_amount": "100.00", "tax_rate": None},
                {"description": "Support", "quantity": "1", "unit_amount": "50.00"},
            ],
            sent["items"],
        )
        self.assertEqual("12.5", sent["discount_percent"])
        self.assertNotIn("discount_amount", sent)

        velirapay.invoices.create(
            {
                "customer_email": "grace@example.com",
                "currency": "USD",
                "items": [{"description": "Consulting", "quantity": "10", "unit_amount": "100.00"}],
                "discount_amount": Decimal("25.00"),
                "discount_percent": None,
            }
        )

        sent = body(self.http.last_request())
        self.assertEqual("25.00", sent["discount_amount"])
        self.assertIsNone(sent["discount_percent"])

    def test_an_invoice_with_a_discount_and_tax_reads_its_breakdown(self) -> None:
        attributes = fixture("invoice")
        attributes.update(
            amount="1305.00", subtotal="1250.00", discount="125.00", discount_percent="10.00", tax="180.00"
        )
        attributes["items"][0]["tax_rate"] = "20.00"
        self.http.json({"data": attributes})

        invoice = client(self.http).invoices.retrieve("w7c2h5j9d3kx")

        self.assertEqual("1305.00", invoice.amount)
        self.assertEqual("1250.00", invoice.subtotal)
        self.assertEqual("125.00", invoice.discount)
        self.assertEqual("10.00", invoice.discount_percent)
        self.assertEqual("180.00", invoice.tax)
        self.assertEqual("20.00", invoice.items[0].tax_rate)
        self.assertEqual("1000.00", invoice.items[0].total)
        self.assertIsNone(invoice.items[1].tax_rate)

    def test_an_invoice_without_a_breakdown_or_sent_before_it_reads_it_as_none(self) -> None:
        older = fixture("invoice")
        for key in ("subtotal", "discount", "discount_percent", "tax"):
            del older[key]
        for item in older["items"]:
            del item["tax_rate"]

        for label, attributes in (("null", fixture("invoice")), ("absent", older)):
            with self.subTest(label):
                invoice = Invoice(attributes)

                self.assertIsNone(invoice.subtotal)
                self.assertIsNone(invoice.discount)
                self.assertIsNone(invoice.discount_percent)
                self.assertIsNone(invoice.tax)
                self.assertEqual([None, None], [item.tax_rate for item in invoice.items])

    def test_an_invoice_is_read_into_typed_attributes(self) -> None:
        self.http.json({"data": fixture("invoice")})

        invoice = client(self.http).invoices.retrieve("w7c2h5j9d3kx")

        self.assertEqual("/v1/invoices/w7c2h5j9d3kx", path_of(self.http.last_request()))
        self.assertEqual("INV-0042", invoice.number)
        self.assertEqual(InvoiceStatus.OPEN, invoice.status)
        self.assertTrue(invoice.is_open())
        self.assertIs(False, invoice.overdue)
        self.assertEqual("Grace Hopper", invoice.customer_name)
        self.assertEqual("grace@example.com", invoice.customer_email)
        self.assertEqual("Thanks for your business.", invoice.memo)
        self.assertEqual("1250.00", invoice.amount)
        self.assertEqual("USD", invoice.currency)
        self.assertEqual(2, len(invoice.items))
        self.assertEqual("2.5", invoice.items[1].quantity)
        self.assertEqual("100.00", invoice.items[1].unit_amount)
        self.assertEqual("250.00", invoice.items[1].total)
        self.assertEqual(date(2026, 10, 15), invoice.due_at)
        self.assertEqual(datetime(2026, 10, 31, 23, 59, 59, tzinfo=UTC), invoice.expires_at)
        self.assertEqual("https://velirapay.com/i/w7c2h5j9d3kx", invoice.hosted_url)
        self.assertEqual("https://velirapay.com/i/w7c2h5j9d3kx/document", invoice.document_url)
        self.assertEqual("https://example.com/orders/1042", invoice.success_url)
        self.assertIsNone(invoice.cancel_url)
        self.assertEqual("Thank you, your licence is on its way.", invoice.success_message)
        self.assertEqual([InvoiceCharge(id="m2q7w4e9r1ty", status="expired", asset="ETH")], invoice.charges)
        self.assertEqual(datetime(2026, 9, 21, 8, 0, tzinfo=UTC), invoice.sent_at)
        self.assertIsNone(invoice.paid_at)

    def test_an_invoice_is_sent_and_voided(self) -> None:
        self.http.json({"data": fixture("invoice")}).json({"data": {**fixture("invoice"), "status": "void"}})
        velirapay = client(self.http)

        velirapay.invoices.send("w7c2h5j9d3kx")

        self.assertEqual("POST", self.http.last_request().method)
        self.assertEqual("/v1/invoices/w7c2h5j9d3kx/send", path_of(self.http.last_request()))

        invoice = velirapay.invoices.void("w7c2h5j9d3kx")

        self.assertEqual("POST", self.http.last_request().method)
        self.assertEqual("/v1/invoices/w7c2h5j9d3kx/void", path_of(self.http.last_request()))
        self.assertTrue(invoice.is_void())

    def test_invoices_are_listed_by_status_and_overdue_ones_on_their_own(self) -> None:
        self.http.json(list_response([fixture("invoice")])).json(list_response([]))
        velirapay = client(self.http)

        page = velirapay.invoices.list({"status": InvoiceStatus.OPEN})

        self.assertEqual({"status": "open"}, query_of(self.http.last_request()))
        self.assertIsInstance(page.data[0], Invoice)

        velirapay.invoices.list({"overdue": True, "search": "grace@example.com"})

        self.assertEqual({"overdue": "1", "search": "grace@example.com"}, query_of(self.http.last_request()))
        self.assertIn("search=grace%40example.com", self.http.last_request().url)


if __name__ == "__main__":
    unittest.main()
