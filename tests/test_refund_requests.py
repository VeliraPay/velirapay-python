from __future__ import annotations

import unittest
from datetime import UTC, datetime
from decimal import Decimal

from velirapay import InvalidArgumentError, Refund, RefundCompleteParams, RefundRequest, RefundRequestStatus

from .support import MockTransport, body, client, fixture, list_response, path_of, query_of

TXID = "b6f6991d03df0e2e04dafffcd6bc418aac66049e2cd74b80f14ac86db1e3f0da"


class RefundRequestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.http = MockTransport()

    def test_a_refund_is_started_with_an_idempotency_key(self) -> None:
        self.http.json({"data": {**fixture("refund_request"), "status": "awaiting_address"}}, 201)

        refund_request = client(self.http).charges.start_refund(
            "2t4bcuqkpkoy", {"amount": "0.0025", "reason": "Order canceled"}, idempotency_key="refund-1042-1"
        )

        request = self.http.last_request()
        self.assertEqual("POST", request.method)
        self.assertEqual("/v1/charges/2t4bcuqkpkoy/refund-requests", path_of(request))
        self.assertEqual("application/json", request.headers["Content-Type"])
        self.assertEqual("refund-1042-1", request.headers["Idempotency-Key"])
        self.assertEqual({"amount": "0.0025", "reason": "Order canceled"}, body(request))
        self.assertIsInstance(refund_request, RefundRequest)
        self.assertEqual(RefundRequestStatus.AWAITING_ADDRESS, refund_request.status)

    def test_the_amount_of_a_refund_is_sent_as_a_decimal_string(self) -> None:
        for amount, sent in ((Decimal("5E-4"), "0.0005"), (0.00005, "0.00005"), (2, "2")):
            with self.subTest(amount):
                self.http.json({"data": fixture("refund_request")}, 201)

                client(self.http).charges.start_refund(
                    "k3v9x2m7q8wz", {"amount": amount, "address": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"}
                )

                self.assertEqual(
                    {"amount": sent, "address": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"},
                    body(self.http.last_request()),
                )

    def test_a_charges_refund_requests_are_listed(self) -> None:
        self.http.json(list_response([fixture("refund_request")], current_page=2, last_page=2, per_page=1, total=2))

        page = client(self.http).charges.refund_requests("k3v9x2m7q8wz", {"page": 2, "per_page": 1})

        request = self.http.last_request()
        self.assertEqual("GET", request.method)
        self.assertEqual("/v1/charges/k3v9x2m7q8wz/refund-requests", path_of(request))
        self.assertEqual({"page": "2", "per_page": "1"}, query_of(request))
        self.assertIsInstance(page.data[0], RefundRequest)
        self.assertEqual("r8k2m4q7xw3e", page.data[0].id)
        self.assertEqual(2, page.total)
        self.assertFalse(page.has_more())

        self.http.json(list_response([]))
        client(self.http).charges.refund_requests("k3v9x2m7q8wz")

        self.assertEqual({}, query_of(self.http.last_request()))

    def test_a_refund_request_is_read_into_typed_attributes(self) -> None:
        self.http.json({"data": fixture("refund_request")})

        refund_request = client(self.http).charges.retrieve_refund_request("k3v9x2m7q8wz", "r8k2m4q7xw3e")

        self.assertEqual("GET", self.http.last_request().method)
        self.assertEqual("/v1/charges/k3v9x2m7q8wz/refund-requests/r8k2m4q7xw3e", path_of(self.http.last_request()))
        self.assertEqual("r8k2m4q7xw3e", refund_request.id)
        self.assertEqual("k3v9x2m7q8wz", refund_request.charge)
        self.assertEqual(RefundRequestStatus.REFUNDED, refund_request.status)
        self.assertTrue(refund_request.is_refunded())
        self.assertFalse(refund_request.is_open())
        self.assertEqual("0.0005", refund_request.amount)
        self.assertEqual("Order canceled", refund_request.reason)
        self.assertEqual("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq", refund_request.address)
        self.assertEqual("customer", refund_request.address_given_by)
        self.assertIsNone(refund_request.address_url)
        self.assertEqual(datetime(2026, 12, 10, 9, 0, tzinfo=UTC), refund_request.link_expires_at)
        self.assertEqual(datetime(2026, 11, 26, 9, 0, tzinfo=UTC), refund_request.emailed_at)
        self.assertEqual("c1f0e2d3b4a5968778695a4b3c2d1e0f9e8d7c6b5a49382716f5e4d3c2b1a090", refund_request.txid)
        self.assertEqual(refund_request.txid, refund_request.detected_txid)
        self.assertEqual("0.0005", refund_request.detected_amount)
        self.assertEqual(3, refund_request.confirmations)
        self.assertEqual(datetime(2026, 11, 26, 9, 0, tzinfo=UTC), refund_request.created_at)
        self.assertEqual(datetime(2026, 11, 26, 10, 0, tzinfo=UTC), refund_request.completed_at)
        self.assertIsNone(refund_request.canceled_at)

        refund = refund_request.refund
        self.assertIsInstance(refund, Refund)
        assert refund is not None
        self.assertEqual("0.0005", refund.amount)
        self.assertEqual("CN-0007", refund.number)
        self.assertEqual("30.00", refund.fiat_amount)
        self.assertEqual("https://velirapay.com/c/k3v9x2m7q8wz/credit-notes/CN-0007", refund.credit_note_url)
        self.assertEqual(datetime(2026, 11, 26, 10, 0, tzinfo=UTC), refund.confirmed_on_chain_at)

    def test_a_refund_waiting_for_the_customers_address_reads_what_it_lacks_as_none(self) -> None:
        refund_request = RefundRequest(
            {
                **fixture("refund_request"),
                "status": "awaiting_address",
                "address": None,
                "address_given_by": None,
                "address_url": "https://velirapay.com/r/r8k2m4q7xw3e?signature=abc",
                "txid": None,
                "detected_txid": None,
                "detected_amount": None,
                "confirmations": None,
                "refund": None,
                "completed_at": None,
            }
        )

        self.assertTrue(refund_request.is_open())
        self.assertFalse(refund_request.is_refunded())
        self.assertIsNone(refund_request.address)
        self.assertIsNone(refund_request.address_given_by)
        self.assertEqual("https://velirapay.com/r/r8k2m4q7xw3e?signature=abc", refund_request.address_url)
        self.assertIsNone(refund_request.txid)
        self.assertIsNone(refund_request.detected_txid)
        self.assertIsNone(refund_request.detected_amount)
        self.assertIsNone(refund_request.confirmations)
        self.assertIsNone(refund_request.refund)
        self.assertIsNone(refund_request.completed_at)

    def test_attributes_of_an_unexpected_type_read_as_their_defaults(self) -> None:
        refund_request = RefundRequest({"status": None, "amount": None, "confirmations": "many", "refund": []})

        self.assertEqual("", refund_request.status)
        self.assertEqual("0", refund_request.amount)
        self.assertIsNone(refund_request.confirmations)
        self.assertIsNone(refund_request.refund)
        self.assertFalse(refund_request.is_open())

    def test_only_the_waiting_statuses_are_open(self) -> None:
        for status, is_open in (
            (RefundRequestStatus.AWAITING_ADDRESS, True),
            (RefundRequestStatus.AWAITING_TRANSFER, True),
            (RefundRequestStatus.CONFIRMING, True),
            (RefundRequestStatus.REFUNDED, False),
            (RefundRequestStatus.CANCELED, False),
            (RefundRequestStatus.EXPIRED, False),
        ):
            with self.subTest(status):
                refund_request = RefundRequest({"status": status.value})

                self.assertIs(is_open, refund_request.is_open())
                self.assertIs(status == RefundRequestStatus.REFUNDED, refund_request.is_refunded())

    def test_the_address_the_customer_gave_you_is_set(self) -> None:
        self.http.json({"data": {**fixture("refund_request"), "status": "awaiting_transfer"}})

        refund_request = client(self.http).charges.set_refund_address(
            "k3v9x2m7q8wz",
            "r8k2m4q7xw3e",
            {"address": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"},
            idempotency_key="address-1",
        )

        request = self.http.last_request()
        self.assertEqual("POST", request.method)
        self.assertEqual("/v1/charges/k3v9x2m7q8wz/refund-requests/r8k2m4q7xw3e/address", path_of(request))
        self.assertEqual({"address": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"}, body(request))
        self.assertEqual("address-1", request.headers["Idempotency-Key"])
        self.assertEqual(RefundRequestStatus.AWAITING_TRANSFER, refund_request.status)

    def test_a_refund_is_marked_as_sent_with_its_transaction(self) -> None:
        self.http.json({"data": {**fixture("refund_request"), "status": "confirming"}})

        refund_request = client(self.http).charges.mark_refund_sent("2t4bcuqkpkoy", "r8k2m4q7xw3e", {"txid": TXID})

        request = self.http.last_request()
        self.assertEqual("POST", request.method)
        self.assertEqual("/v1/charges/2t4bcuqkpkoy/refund-requests/r8k2m4q7xw3e/sent", path_of(request))
        self.assertEqual({"txid": TXID}, body(request))
        self.assertEqual(RefundRequestStatus.CONFIRMING, refund_request.status)

        self.http.json({"data": fixture("refund_request")})
        client(self.http).charges.mark_refund_sent(
            "2t4bcuqkpkoy", "r8k2m4q7xw3e", {"txid": TXID}, idempotency_key="sent-1"
        )

        self.assertEqual("sent-1", self.http.last_request().headers["Idempotency-Key"])

    def test_a_refund_is_completed_on_your_word_with_or_without_its_transaction(self) -> None:
        velirapay = client(self.http)
        cases: list[tuple[RefundCompleteParams | None, dict[str, str | None] | None]] = [
            (None, None),
            ({}, None),
            ({"txid": TXID}, {"txid": TXID}),
            ({"txid": None}, {"txid": None}),
        ]

        for params, sent in cases:
            with self.subTest(params):
                self.http.json({"data": fixture("refund_request")})

                refund_request = velirapay.charges.complete_refund(
                    "k3v9x2m7q8wz", "r8k2m4q7xw3e", params, idempotency_key="complete-1"
                )

                request = self.http.last_request()
                self.assertEqual("POST", request.method)
                self.assertEqual("/v1/charges/k3v9x2m7q8wz/refund-requests/r8k2m4q7xw3e/complete", path_of(request))
                self.assertEqual("complete-1", request.headers["Idempotency-Key"])
                self.assertTrue(refund_request.is_refunded())

                if sent is None:
                    self.assertIsNone(request.body)
                    self.assertNotIn("Content-Type", request.headers)
                else:
                    self.assertEqual(sent, body(request))

        self.http.json({"data": fixture("refund_request")})
        velirapay.charges.complete_refund("k3v9x2m7q8wz", "r8k2m4q7xw3e")

        self.assertIsNone(self.http.last_request().body)

    def test_the_link_is_emailed_again_and_a_refund_is_canceled(self) -> None:
        velirapay = client(self.http)

        self.http.json({"data": {**fixture("refund_request"), "status": "awaiting_address"}})
        velirapay.charges.resend_refund_link("k3v9x2m7q8wz", "r8k2m4q7xw3e", idempotency_key="resend-1")

        request = self.http.last_request()
        self.assertEqual("POST", request.method)
        self.assertEqual("/v1/charges/k3v9x2m7q8wz/refund-requests/r8k2m4q7xw3e/resend", path_of(request))
        self.assertIsNone(request.body)
        self.assertEqual("resend-1", request.headers["Idempotency-Key"])

        self.http.json({"data": {**fixture("refund_request"), "status": "canceled", "refund": None}})
        refund_request = velirapay.charges.cancel_refund("k3v9x2m7q8wz", "r8k2m4q7xw3e", idempotency_key="cancel-1")

        request = self.http.last_request()
        self.assertEqual("POST", request.method)
        self.assertEqual("/v1/charges/k3v9x2m7q8wz/refund-requests/r8k2m4q7xw3e/cancel", path_of(request))
        self.assertIsNone(request.body)
        self.assertEqual("cancel-1", request.headers["Idempotency-Key"])
        self.assertEqual(RefundRequestStatus.CANCELED, refund_request.status)
        self.assertFalse(refund_request.is_open())

    def test_both_ids_are_escaped_into_the_path(self) -> None:
        self.http.json({"data": fixture("refund_request")})

        client(self.http).charges.retrieve_refund_request("k3v9/x2m7", "../r8k2")

        self.assertEqual("/v1/charges/k3v9%2Fx2m7/refund-requests/..%2Fr8k2", path_of(self.http.last_request()))

    def test_an_empty_refund_request_id_is_refused_before_a_request_is_sent(self) -> None:
        with self.assertRaises(InvalidArgumentError) as caught:
            client(self.http).charges.cancel_refund("k3v9x2m7q8wz", "")

        self.assertEqual(
            "The id in /v1/charges/{id}/refund-requests/{id}/cancel cannot be empty.", str(caught.exception)
        )

        with self.assertRaises(InvalidArgumentError):
            client(self.http).charges.refund_requests("..")

        self.assertEqual([], self.http.requests)


if __name__ == "__main__":
    unittest.main()
