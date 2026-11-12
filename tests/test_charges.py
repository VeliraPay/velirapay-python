from __future__ import annotations

import copy
import math
import pickle
import unittest
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

from velirapay import Asset, Charge, ChargeStatus, ChargeTimelineEntry, CustomFieldAnswer, InvalidArgumentError

from .support import MockTransport, body, client, fixture, list_response, path_of, query_of


class ChargeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.http = MockTransport()

    def test_a_charge_is_created(self) -> None:
        self.http.json({"data": fixture("charge")}, 201)

        charge = client(self.http).charges.create(
            {"asset": Asset.BTC, "amount": "150.00", "currency": "EUR", "metadata": {"order_id": "1042"}},
            idempotency_key="order-1042",
        )

        request = self.http.last_request()
        self.assertEqual("POST", request.method)
        self.assertEqual("/v1/charges", path_of(request))
        self.assertEqual("application/json", request.headers["Content-Type"])
        self.assertEqual("order-1042", request.headers["Idempotency-Key"])
        self.assertEqual(
            {"asset": "BTC", "amount": "150.00", "currency": "EUR", "metadata": {"order_id": "1042"}}, body(request)
        )
        self.assertIsInstance(charge, Charge)
        self.assertEqual("k3v9x2m7q8wz", charge.id)

    def test_a_charge_is_created_with_everything_already_known(self) -> None:
        self.http.json(
            {
                "data": {
                    **fixture("charge"),
                    "success_url": "https://example.com/orders/1042",
                    "cancel_url": "https://example.com/cart",
                    "success_message": "Thank you.",
                }
            },
            201,
        )

        charge = client(self.http).charges.create(
            {
                "asset": "BTC",
                "amount": "150.00",
                "currency": "EUR",
                "custom_fields": [{"label": "Company", "value": "Analytical Engines"}],
                "success_url": "https://example.com/orders/1042",
                "cancel_url": "https://example.com/cart",
                "success_message": "Thank you.",
                "send_email": True,
            }
        )

        sent = body(self.http.last_request())
        self.assertEqual([{"label": "Company", "value": "Analytical Engines"}], sent["custom_fields"])
        self.assertIs(True, sent["send_email"])
        self.assertEqual("https://example.com/orders/1042", charge.success_url)
        self.assertEqual("https://example.com/cart", charge.cancel_url)
        self.assertEqual("Thank you.", charge.success_message)

    def test_a_charge_can_be_emailed_accepted_and_paid_by_simulation(self) -> None:
        velirapay = client(self.http)

        self.http.json({"data": fixture("charge")})
        velirapay.charges.send("k3v9x2m7q8wz")
        self.assertEqual("POST", self.http.last_request().method)
        self.assertEqual("/v1/charges/k3v9x2m7q8wz/send", path_of(self.http.last_request()))

        self.http.json({"data": fixture("charge")})
        velirapay.charges.accept("k3v9x2m7q8wz")
        self.assertEqual("/v1/charges/k3v9x2m7q8wz/accept", path_of(self.http.last_request()))

        self.http.json({"data": fixture("charge")})
        velirapay.charges.simulate("k3v9x2m7q8wz")
        self.assertEqual("/v1/charges/k3v9x2m7q8wz/simulate", path_of(self.http.last_request()))
        self.assertIsNone(self.http.last_request().body)

        self.http.json({"data": fixture("charge")})
        velirapay.charges.simulate("k3v9x2m7q8wz", {"amount": "0.001"})
        self.assertEqual({"amount": "0.001"}, body(self.http.last_request()))

    def test_a_charge_is_read_into_typed_attributes(self) -> None:
        self.http.json({"data": fixture("charge")})

        charge = client(self.http).charges.retrieve("k3v9x2m7q8wz")

        self.assertEqual("/v1/charges/k3v9x2m7q8wz", path_of(self.http.last_request()))
        self.assertEqual(ChargeStatus.PAID, charge.status)
        self.assertTrue(charge.is_paid())
        self.assertFalse(charge.is_open())
        self.assertEqual("p4n8r2t6y1ua", charge.payment_link)
        self.assertIsNone(charge.payment_link_title)
        self.assertIsNone(charge.invoice)
        self.assertIsNone(charge.invoice_number)
        self.assertEqual("Pro plan, 1 year", charge.description)
        self.assertEqual("150.00", charge.fiat_amount)
        self.assertEqual("EUR", charge.fiat_currency)
        self.assertIsNone(charge.coupon)
        self.assertIsNone(charge.discount_amount)
        self.assertEqual("BTC", charge.asset)
        self.assertEqual("0.0025", charge.asset_amount)
        self.assertIsNone(charge.network_surcharge)
        self.assertEqual("0.0025", charge.received_amount)
        self.assertEqual("0", charge.remaining_amount)
        self.assertFalse(charge.overpaid)
        self.assertEqual("0.0005", charge.refunded_amount)
        self.assertEqual(1, len(charge.refunds))
        self.assertEqual("Partial refund", charge.refunds[0].reason)
        self.assertEqual(datetime(2026, 9, 21, 14, 30, tzinfo=UTC), charge.refunds[0].created_at)
        self.assertEqual("60000", charge.exchange_rate)
        self.assertEqual("bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh", charge.deposit_address)
        self.assertIsNone(charge.payment_request)
        self.assertEqual(1, len(charge.transactions))
        self.assertEqual(3, charge.transactions[0].confirmations)
        self.assertEqual(2, charge.transactions[0].required_confirmations)
        self.assertTrue(charge.transactions[0].credited)
        self.assertTrue((charge.transactions[0].explorer_url or "").startswith("https://mempool.space/tx/"))
        self.assertEqual(
            ["charge.created", "charge.payment_detected", "charge.paid"], [entry.event for entry in charge.timeline]
        )
        self.assertEqual(
            ChargeTimelineEntry(event="charge.paid", time=datetime(2026, 9, 20, 10, 5, 41, tzinfo=UTC)),
            charge.timeline[2],
        )
        self.assertEqual("ada@example.com", charge.customer_email)
        self.assertEqual("Ada Lovelace", charge.customer_name)
        self.assertEqual("ada@example.com", charge.customer.email)
        self.assertEqual("Ada Lovelace", charge.customer.name)
        self.assertEqual("203.0.113.7", charge.customer.ip_address)
        self.assertTrue((charge.customer.user_agent or "").startswith("Mozilla/5.0 (Macintosh;"))
        self.assertEqual("cus_1042", charge.customer.reference)
        self.assertEqual("+44 20 7946 0958", charge.customer.phone)
        self.assertEqual("GB", charge.customer.country)
        self.assertEqual({"orders": 7, "verified": True}, charge.customer.metadata)
        self.assertEqual([CustomFieldAnswer(label="Company", value="Analytical Engines Ltd")], charge.custom_fields)
        self.assertEqual({"order_id": "1042"}, charge.metadata)
        self.assertEqual("https://velirapay.com/c/k3v9x2m7q8wz", charge.checkout_url)
        self.assertEqual("https://velirapay.com/c/k3v9x2m7q8wz/receipt", charge.receipt_url)
        self.assertEqual(datetime(2026, 9, 20, 10, 25, tzinfo=UTC), charge.expires_at)
        self.assertEqual(datetime(2026, 9, 20, 10, 5, 41, tzinfo=UTC), charge.paid_at)
        self.assertEqual(datetime(2026, 9, 20, 9, 55, tzinfo=UTC), charge.created_at)

    def test_a_charge_reads_the_network_surcharge_the_customer_pays_on_top_of_the_price(self) -> None:
        self.http.json(
            {
                "data": {
                    **fixture("charge"),
                    "asset": "USDT_TRON",
                    "fiat_currency": "USD",
                    "exchange_rate": "1",
                    "asset_amount": "152.5",
                    "network_surcharge": "2.5",
                    "deposit_address": "TJCnKsPa7y5okkXvQAidZBzqx3QyQ6sxMW",
                }
            }
        )

        charge = client(self.http).charges.retrieve("k3v9x2m7q8wz")

        self.assertEqual(Asset.USDT_TRON, charge.asset)
        self.assertEqual("152.5", charge.asset_amount)
        self.assertEqual("2.5", charge.network_surcharge)
        self.assertIsNone(charge.payment_request)

    def test_a_lightning_charge_reads_its_invoice(self) -> None:
        invoice = "lnbc2500u1pjq8w4xpp5qy9nkv7r0v4e5n2s7a3xg6m8d0l2c4f6h8j0k2m4n6p8r0t2v4x6z8sdqqcqzzsxqyz5vq"
        payment_hash = "a3f1c9e2b7d4058f6e1a2b3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d5e6f70"
        self.http.json(
            {
                "data": {
                    **fixture("charge"),
                    "asset": "BTC_LIGHTNING",
                    "deposit_address": payment_hash,
                    "payment_request": invoice,
                }
            }
        )

        charge = client(self.http).charges.retrieve("k3v9x2m7q8wz")

        self.assertEqual(Asset.BTC_LIGHTNING, charge.asset)
        self.assertEqual(payment_hash, charge.deposit_address)
        self.assertEqual(invoice, charge.payment_request)
        self.assertIsNone(charge.network_surcharge)

    def test_the_customers_details_are_sent_with_a_new_charge(self) -> None:
        self.http.json({"data": fixture("charge")}, 201)
        customer = {
            "email": "ada@example.com",
            "ip_address": "203.0.113.7",
            "user_agent": "Mozilla/5.0",
            "reference": "cus_1042",
            "country": "GB",
            "metadata": {"orders": 7},
        }

        client(self.http).charges.create(
            {
                "asset": "BTC",
                "amount": "150.00",
                "currency": "EUR",
                "customer": {
                    "email": "ada@example.com",
                    "ip_address": "203.0.113.7",
                    "user_agent": "Mozilla/5.0",
                    "reference": "cus_1042",
                    "country": "GB",
                    "metadata": {"orders": 7},
                },
            }
        )

        self.assertEqual(customer, body(self.http.last_request())["customer"])

    def test_a_coupon_is_applied_to_a_new_charge(self) -> None:
        self.http.json(
            {"data": {**fixture("charge"), "fiat_amount": "135.00", "coupon": "SPRING10", "discount_amount": "15.00"}},
            201,
        )

        charge = client(self.http).charges.create(
            {"payment_link": "p4n8r2t6y1ua", "asset": "BTC", "coupon": "spring10"}
        )

        self.assertEqual("spring10", body(self.http.last_request())["coupon"])
        self.assertEqual("135.00", charge.fiat_amount)
        self.assertEqual("SPRING10", charge.coupon)
        self.assertEqual("15.00", charge.discount_amount)

    def test_amounts_given_as_decimals_are_sent_with_every_digit(self) -> None:
        self.http.json({"data": fixture("charge")}, 201)

        client(self.http).charges.create(
            {"asset": "BTC", "amount": Decimal("49.90"), "currency": "EUR", "metadata": {"order_id": "1042"}}
        )

        self.assertEqual(
            b'{"asset":"BTC","amount":"49.90","currency":"EUR","metadata":{"order_id":"1042"}}',
            self.http.last_request().body,
        )

        self.http.json({"data": fixture("charge")}, 201)

        client(self.http).charges.record_refund("k3v9x2m7q8wz", {"amount": Decimal("5E-4")})

        self.assertEqual({"amount": "0.0005"}, body(self.http.last_request()))

    def test_text_is_sent_as_utf8_without_escapes(self) -> None:
        self.http.json({"data": fixture("charge")}, 201)

        client(self.http).charges.create(
            {"asset": "BTC", "amount": "150.00", "currency": "EUR", "description": "Zoë’s café / 1 year"}
        )

        self.assertIn("Zoë’s café / 1 year".encode(), self.http.last_request().body or b"")

    def test_a_charge_sent_without_a_customer_object_takes_it_from_the_older_fields(self) -> None:
        attributes = fixture("charge")
        del attributes["customer"]
        self.http.json({"data": attributes})

        charge = client(self.http).charges.retrieve("k3v9x2m7q8wz")

        self.assertEqual("ada@example.com", charge.customer.email)
        self.assertEqual("Ada Lovelace", charge.customer.name)
        self.assertIsNone(charge.customer.ip_address)
        self.assertEqual({}, charge.customer.metadata)

    def test_a_charge_built_without_a_customer_takes_it_from_the_older_fields(self) -> None:
        charge = Charge({"id": "k3v9x2m7q8wz", "customer_email": "ada@example.com", "customer_name": "Ada Lovelace"})

        self.assertEqual("ada@example.com", charge.customer.email)
        self.assertEqual("Ada Lovelace", charge.customer.name)
        self.assertIsNone(charge.customer.ip_address)

    def test_attributes_the_library_does_not_know_are_kept(self) -> None:
        attributes = {**fixture("charge"), "status": "refunding", "network_fee": "0.00001"}
        self.http.json({"data": attributes})

        charge = client(self.http).charges.retrieve("k3v9x2m7q8wz")

        self.assertEqual("refunding", charge.status)
        self.assertFalse(charge.is_paid())
        self.assertEqual("0.00001", charge.get("network_fee"))
        self.assertIsNone(charge.get("nothing"))
        self.assertEqual("fallback", charge.get("nothing", "fallback"))
        self.assertEqual(attributes, charge.to_dict())
        self.assertEqual(Charge(attributes), charge)
        self.assertEqual(f"Charge({attributes!r})", repr(charge))

    def test_a_charge_cannot_be_changed_through_what_it_answers_with(self) -> None:
        charge = Charge(fixture("charge"))

        charge.metadata["order_id"] = "9999"
        charge.to_dict()["status"] = "pending"
        charge.get("customer")["email"] = "mallory@example.com"

        self.assertEqual({"order_id": "1042"}, charge.metadata)
        self.assertEqual("paid", charge.status)
        self.assertEqual("ada@example.com", charge.customer.email)

        with self.assertRaises(AttributeError):
            charge.status = "pending"  # type: ignore[misc]

    def test_a_charge_survives_pickling_and_copying(self) -> None:
        charge = Charge(fixture("charge"))

        self.assertEqual(charge, pickle.loads(pickle.dumps(charge)))
        self.assertEqual(charge, copy.deepcopy(charge))
        self.assertEqual("k3v9x2m7q8wz", pickle.loads(pickle.dumps(charge)).id)

    def test_attributes_of_an_unexpected_type_read_as_their_defaults(self) -> None:
        charge = Charge(
            {"status": None, "overpaid": "yes", "transactions": "none", "metadata": [], "expires_at": "soon"}
        )

        self.assertEqual("", charge.status)
        self.assertFalse(charge.overpaid)
        self.assertEqual([], charge.transactions)
        self.assertEqual({}, charge.metadata)
        self.assertIsNone(charge.expires_at)
        self.assertEqual("0", charge.fiat_amount)

    def test_counts_given_as_strings_of_digits_are_read_within_reason(self) -> None:
        transaction = Charge({"transactions": [{"confirmations": "0012"}, {"confirmations": "9" * 5000}]}).transactions

        self.assertEqual(12, transaction[0].confirmations)
        self.assertEqual(0, transaction[1].confirmations)

    def test_a_charge_is_read_from_a_dict_only(self) -> None:
        with self.assertRaises(InvalidArgumentError):
            Charge('{"id": "k3v9x2m7q8wz"}')  # type: ignore[arg-type]

    def test_ids_are_escaped_into_paths(self) -> None:
        self.http.json({"data": fixture("charge")})

        client(self.http).charges.retrieve("../account")

        self.assertEqual("/v1/charges/..%2Faccount", path_of(self.http.last_request()))

    def test_an_empty_id_is_refused_before_a_request_is_sent(self) -> None:
        with self.assertRaises(InvalidArgumentError) as caught:
            client(self.http).charges.cancel("")

        self.assertEqual("The id in /v1/charges/{id}/cancel cannot be empty.", str(caught.exception))

        with self.assertRaises(InvalidArgumentError):
            client(self.http).charges.retrieve(" ")

        with self.assertRaisesRegex(InvalidArgumentError, "must be a str"):
            client(self.http).charges.retrieve(42)  # type: ignore[arg-type]

        self.assertEqual([], self.http.requests)

    def test_an_id_that_a_url_would_read_as_a_directory_is_refused(self) -> None:
        with self.assertRaises(InvalidArgumentError) as caught:
            client(self.http).charges.retrieve("..")

        self.assertEqual('The id in /v1/charges/{id} cannot be "..".', str(caught.exception))

        with self.assertRaises(InvalidArgumentError):
            client(self.http).webhook_endpoints.retry_delivery("12", ".")

        self.assertEqual([], self.http.requests)

    def test_charges_are_listed_with_filters(self) -> None:
        self.http.json(list_response([fixture("charge")], current_page=2, last_page=3, per_page=1, total=3))

        page = client(self.http).charges.list(
            {
                "status": ChargeStatus.PAID,
                "payment_link": "p4n8r2t6y1ua",
                "created_from": datetime(2026, 10, 1, tzinfo=UTC),
                "created_to": date(2026, 10, 31),
                "page": 2,
                "per_page": 1,
            }
        )

        self.assertEqual("/v1/charges", path_of(self.http.last_request()))
        self.assertEqual(
            {
                "status": "paid",
                "payment_link": "p4n8r2t6y1ua",
                "created_from": "2026-10-01T00:00:00+00:00",
                "created_to": "2026-10-31",
                "page": "2",
                "per_page": "1",
            },
            query_of(self.http.last_request()),
        )
        self.assertIn("created_from=2026-10-01T00%3A00%3A00%2B00%3A00", self.http.last_request().url)
        self.assertEqual(1, len(page))
        self.assertIsInstance(page.data[0], Charge)
        self.assertEqual(2, page.current_page)
        self.assertEqual(3, page.last_page)
        self.assertEqual(1, page.per_page)
        self.assertEqual(3, page.total)
        self.assertTrue(page.has_more())

    def test_a_moment_in_another_time_zone_is_sent_as_the_same_moment_in_utc(self) -> None:
        self.http.json(list_response([]))

        client(self.http).charges.list(
            {
                "created_from": datetime(2026, 10, 1, 9, 30, tzinfo=timezone(timedelta(hours=2))),
                "created_to": datetime(2026, 10, 31, 20, 0, 0, 250000, tzinfo=timezone(timedelta(hours=-5))),
            }
        )

        self.assertEqual(
            {"created_from": "2026-10-01T07:30:00+00:00", "created_to": "2026-11-01T01:00:00.250000+00:00"},
            query_of(self.http.last_request()),
        )

    def test_a_moment_without_a_time_zone_is_taken_as_utc(self) -> None:
        self.http.json(list_response([]))

        client(self.http).charges.list({"created_from": datetime(2026, 10, 1, 9, 30)})

        self.assertEqual({"created_from": "2026-10-01T09:30:00+00:00"}, query_of(self.http.last_request()))

    def test_a_charge_is_canceled(self) -> None:
        self.http.json({"data": {**fixture("charge"), "status": "canceled"}})

        charge = client(self.http).charges.cancel("k3v9x2m7q8wz", idempotency_key="cancel-1")

        request = self.http.last_request()
        self.assertEqual("POST", request.method)
        self.assertEqual("/v1/charges/k3v9x2m7q8wz/cancel", path_of(request))
        self.assertIsNone(request.body)
        self.assertNotIn("Content-Type", request.headers)
        self.assertEqual("cancel-1", request.headers["Idempotency-Key"])
        self.assertTrue(charge.is_canceled())

    def test_a_refund_is_recorded(self) -> None:
        self.http.json({"data": fixture("charge")}, 201)

        client(self.http).charges.record_refund(
            "k3v9x2m7q8wz", {"amount": "0.0005", "txid": "c1f0e2d3", "reason": "Partial refund"}
        )

        request = self.http.last_request()
        self.assertEqual("POST", request.method)
        self.assertEqual("/v1/charges/k3v9x2m7q8wz/refunds", path_of(request))
        self.assertEqual({"amount": "0.0005", "txid": "c1f0e2d3", "reason": "Partial refund"}, body(request))

    def test_an_amount_given_as_a_number_is_sent_as_a_decimal_string_without_an_exponent(self) -> None:
        for amount, sent in (
            (0.00005, "0.00005"),
            (1e-8, "0.00000001"),
            (0.1, "0.1"),
            (0.1 + 0.2, "0.3"),
            (1.1 * 3, "3.3"),
            (123456789.123456789, "123456789.12346"),
            (1e20, "100000000000000000000"),
            (150.0, "150"),
            (2, "2"),
            (Decimal("0.00005"), "0.00005"),
            ("0.0005", "0.0005"),
        ):
            with self.subTest(amount):
                self.http.json({"data": fixture("charge")}, 201)

                client(self.http).charges.record_refund("k3v9x2m7q8wz", {"amount": amount})

                self.assertEqual({"amount": sent}, body(self.http.last_request()))

    def test_a_simulated_payment_of_a_small_amount_is_sent_without_an_exponent(self) -> None:
        self.http.json({"data": fixture("charge")})

        client(self.http).charges.simulate("k3v9x2m7q8wz", {"amount": 0.00005})

        self.assertEqual(b'{"amount":"0.00005"}', self.http.last_request().body)

    def test_an_amount_that_is_not_a_number_is_refused_before_a_request_is_sent(self) -> None:
        for amount in (math.nan, math.inf, -math.inf):
            with self.subTest(amount), self.assertRaisesRegex(InvalidArgumentError, "cannot be sent"):
                client(self.http).charges.record_refund("k3v9x2m7q8wz", {"amount": amount})

        self.assertEqual([], self.http.requests)

    def test_only_the_amount_of_a_new_charge_is_written_as_a_decimal_string(self) -> None:
        self.http.json({"data": fixture("charge")}, 201)

        client(self.http).charges.create(
            {"asset": "BTC", "amount": 49.9, "currency": "EUR", "metadata": {"score": 0.00005, "orders": 7}}
        )

        self.assertEqual(
            b'{"asset":"BTC","amount":"49.9","currency":"EUR","metadata":{"score":5e-05,"orders":7}}',
            self.http.last_request().body,
        )

    def test_each_status_has_its_helper(self) -> None:
        for status, helper in (
            ("pending", Charge.is_pending),
            ("underpaid", Charge.is_underpaid),
            ("paid", Charge.is_paid),
            ("expired", Charge.is_expired),
            ("canceled", Charge.is_canceled),
        ):
            with self.subTest(status):
                self.assertTrue(helper(Charge({"status": status})))

        self.assertTrue(Charge({"status": "underpaid"}).is_open())
        self.assertFalse(Charge({"status": "expired"}).is_open())


if __name__ == "__main__":
    unittest.main()
