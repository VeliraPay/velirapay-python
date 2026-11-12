from __future__ import annotations

import unittest
from datetime import UTC, date, datetime, timedelta, timezone

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
                        "send_email": True,
                    }
                )

                request = self.http.last_request()
                sent = body(request)
                self.assertEqual("POST", request.method)
                self.assertEqual("/v1/invoices", path_of(request))
                self.assertEqual("2026-10-15", sent["due_at"])
                self.assertIs(True, sent["send_email"])
                self.assertEqual(10, sent["items"][0]["quantity"])
                self.assertEqual("w7c2h5j9d3kx", invoice.id)

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
        self.assertEqual("https://velirapay.com/i/w7c2h5j9d3kx", invoice.hosted_url)
        self.assertEqual("https://velirapay.com/i/w7c2h5j9d3kx/document", invoice.document_url)
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
