from __future__ import annotations

import json
import time
import unittest
from datetime import UTC, date, datetime
from typing import Any

from velirapay import EventType, InvalidArgumentError, SignatureVerificationError, Webhook, WebhookEvent

from .support import payload

SECRET = "whsec_2b7Qf9LkXw3NcR8vT1mZ5pYs0HdJ4gUe6AoKiVbE"


def signed(name: str) -> WebhookEvent:
    """The event of a fixture, signed now."""
    raw = payload(name)

    return Webhook.construct_event(raw, Webhook.signature_header(raw, SECRET), SECRET)


class WebhookTest(unittest.TestCase):
    def test_a_signed_charge_delivery_is_verified_and_parsed(self) -> None:
        event = signed("webhook_charge")

        self.assertEqual("5f0c6f5e-8d1b-4a53-9a57-3c2b1d0e9f87", event.id)
        self.assertEqual("9b1f7a3e-2c4d-4e8f-a6b0-1d2c3e4f5a6b", event.event_id)
        self.assertEqual("charge.paid", event.type)
        self.assertTrue(event.is_type(EventType.CHARGE_PAID))
        self.assertTrue(event.is_live_mode())
        self.assertFalse(event.test)
        self.assertEqual(datetime(2026, 9, 20, 10, 5, 42, tzinfo=UTC), event.created_at)
        self.assertIsNone(event.invoice)
        self.assertIsNone(event.transaction)

        charge = event.charge
        assert charge is not None
        self.assertEqual("k3v9x2m7q8wz", charge.id)
        self.assertTrue(charge.is_paid())
        self.assertEqual("p4n8r2t6y1ua", charge.payment_link)
        self.assertEqual("Pro plan", charge.payment_link_title)
        self.assertIsNone(charge.invoice)
        self.assertIsNone(charge.invoice_number)
        self.assertEqual("0.002500000000000000", charge.asset_amount)
        self.assertEqual(2, charge.transactions[0].confirmations)
        self.assertEqual(2, charge.transactions[0].required_confirmations)
        self.assertEqual("203.0.113.7", charge.customer.ip_address)
        self.assertEqual("DE", charge.customer.ip_country)
        self.assertEqual(24940, charge.customer.ip_asn)
        self.assertEqual("Hetzner Online GmbH", charge.customer.ip_network)
        self.assertEqual("ada@example.com", charge.customer.email)
        self.assertEqual({}, charge.customer.metadata)
        self.assertEqual({"order_id": "1042"}, charge.metadata)
        self.assertEqual([], charge.refunds)
        self.assertIsNone(charge.checkout_url)

    def test_a_delivery_without_the_ip_country_and_network_reads_them_as_none(self) -> None:
        delivery = json.loads(payload("webhook_charge"))
        for key in ("ip_country", "ip_asn", "ip_network"):
            del delivery["data"]["charge"]["customer"][key]
        raw = json.dumps(delivery)

        charge = Webhook.construct_event(raw, Webhook.signature_header(raw, SECRET), SECRET).charge

        assert charge is not None
        self.assertEqual("203.0.113.7", charge.customer.ip_address)
        self.assertIsNone(charge.customer.ip_country)
        self.assertIsNone(charge.customer.ip_asn)
        self.assertIsNone(charge.customer.ip_network)

    def test_a_payment_detected_delivery_carries_the_transfer_that_was_seen(self) -> None:
        event = signed("webhook_payment_detected")

        self.assertTrue(event.is_type(EventType.CHARGE_PAYMENT_DETECTED))
        assert event.charge is not None
        self.assertTrue(event.charge.is_pending())

        transaction = event.transaction
        assert transaction is not None
        self.assertEqual("7d1c5e9a3b2f8e6d4c0a9b8e7f6d5c4b3a2918f7e6d5c4b3a29180f7e6d5c4b3", transaction.txid)
        self.assertEqual("0.002500000000000000", transaction.amount)
        self.assertEqual(0, transaction.confirmations)
        self.assertEqual(2, transaction.required_confirmations)
        self.assertFalse(transaction.credited)
        self.assertTrue((transaction.explorer_url or "").startswith("https://mempool.space/tx/"))
        self.assertEqual(datetime(2026, 9, 20, 9, 58, 12, tzinfo=UTC), transaction.seen_at)

    def test_a_payout_delivery_carries_the_charge_and_its_payout(self) -> None:
        event = signed("webhook_payout")

        self.assertTrue(event.is_type(EventType.PAYOUT_CONFIRMED))
        assert event.charge is not None
        self.assertEqual("k3v9x2m7q8wz", event.charge.id)
        self.assertIsNone(event.transaction)

        payout = event.payout
        assert payout is not None
        self.assertEqual("k3v9x2m7q8wz", payout.charge)
        self.assertTrue(payout.is_sent())
        self.assertEqual("0.002425", payout.sent_amount)
        self.assertEqual("0.0000044", payout.network_fee)
        self.assertEqual("cc9a3e0b5629235194a6174d805c55df5554c94e2b4de8dc584db2091cc5cacf", payout.payout_txid)
        self.assertEqual(datetime(2026, 9, 20, 10, 41, 2, tzinfo=UTC), payout.confirmed_at)

    def test_only_a_payout_delivery_carries_a_payout(self) -> None:
        self.assertIsNone(signed("webhook_charge").payout)

    def test_a_delivery_about_a_charge_paying_an_invoice_names_the_invoice(self) -> None:
        delivery = json.loads(payload("webhook_charge"))
        delivery["data"]["charge"]["payment_link"] = None
        delivery["data"]["charge"]["invoice"] = {"code": "w7c2h5j9d3kx", "number": "INV-0042"}
        raw = json.dumps(delivery)

        charge = Webhook.construct_event(raw, Webhook.signature_header(raw, SECRET), SECRET).charge

        assert charge is not None
        self.assertEqual("w7c2h5j9d3kx", charge.invoice)
        self.assertEqual("INV-0042", charge.invoice_number)
        self.assertIsNone(charge.payment_link)
        self.assertIsNone(charge.payment_link_title)

    def test_a_signed_invoice_delivery_is_parsed(self) -> None:
        event = signed("webhook_invoice")

        self.assertEqual("invoice.paid", event.type)
        self.assertFalse(event.is_live_mode())
        self.assertIsNone(event.charge)

        invoice = event.invoice
        assert invoice is not None
        self.assertEqual("w7c2h5j9d3kx", invoice.id)
        self.assertTrue(invoice.is_paid())
        self.assertIsNone(invoice.overdue)
        self.assertIsNone(invoice.document_url)
        self.assertIsNone(invoice.success_url)
        self.assertEqual(["m2q7w4e9r1ty", "z8x6c4v2b0nm"], [charge.id for charge in invoice.charges])
        self.assertEqual(date(2026, 10, 15), invoice.due_at)

    def test_signatures_made_by_velirapay_are_accepted(self) -> None:
        raw = '{"id":"5f0c6f5e-8d1b-4a53-9a57-3c2b1d0e9f87","event_id":"9b1f7a3e-2c4d-4e8f-a6b0-1d2c3e4f5a6b","event":"charge.paid","mode":"live","created_at":"2026-09-20T10:05:42.000000Z","data":{"charge":{"code":"k3v9x2m7q8wz","status":"paid"}}}'
        header = "t=1790000000,v1=a7a0dd3b10e4302cf840472806bb1c3a75453b7f8a6975c6475f92d58826df35"

        Webhook.verify_signature(raw, header, SECRET, now=1790000060)
        Webhook.verify_signature(raw.encode(), header, SECRET, now=1790000060)

        self.assertEqual(header, Webhook.signature_header(raw, SECRET, 1790000000))

    def test_the_bytes_of_the_body_are_signed_whether_given_as_a_str_or_bytes(self) -> None:
        raw = payload("webhook_charge").replace("Pro plan, 1 year", "Zoë’s plan, 1 year")
        header = Webhook.signature_header(raw, SECRET, 1790000000)

        self.assertEqual(header, Webhook.signature_header(raw.encode(), SECRET, 1790000000))

        for given in (raw, raw.encode(), bytearray(raw.encode()), memoryview(raw.encode())):
            with self.subTest(type(given).__name__):
                Webhook.verify_signature(given, header, SECRET, now=1790000000)  # type: ignore[arg-type]

        event = Webhook.construct_event(raw.encode(), Webhook.signature_header(raw, SECRET), SECRET)
        assert event.charge is not None
        self.assertEqual("Zoë’s plan, 1 year", event.charge.description)

    def test_a_changed_payload_is_rejected(self) -> None:
        raw = payload("webhook_charge")
        header = Webhook.signature_header(raw, SECRET)

        with self.assertRaises(SignatureVerificationError):
            Webhook.construct_event(raw.replace("150.00", "1.00"), header, SECRET)

    def test_a_signature_made_with_another_secret_is_rejected(self) -> None:
        raw = payload("webhook_charge")

        with self.assertRaisesRegex(SignatureVerificationError, "does not match"):
            Webhook.construct_event(raw, Webhook.signature_header(raw, "whsec_other"), SECRET)

    def test_an_old_signature_is_rejected_unless_the_tolerance_is_off(self) -> None:
        raw = payload("webhook_charge")
        header = Webhook.signature_header(raw, SECRET, int(time.time()) - 301)

        Webhook.verify_signature(raw, header, SECRET, tolerance=0)

        with self.assertRaisesRegex(SignatureVerificationError, "more than the 300 allowed"):
            Webhook.verify_signature(raw, header, SECRET)

    def test_a_signature_from_the_future_is_held_to_the_same_tolerance(self) -> None:
        raw = payload("webhook_charge")
        header = Webhook.signature_header(raw, SECRET, 1790000000)

        Webhook.verify_signature(raw, header, SECRET, 300, 1790000000 - 300)

        with self.assertRaises(SignatureVerificationError) as caught:
            Webhook.verify_signature(raw, header, SECRET, 300, 1790000000 - 301)

        self.assertEqual(
            "The signature is 301 seconds away from now, more than the 300 allowed.", str(caught.exception)
        )

    def test_one_matching_signature_among_several_is_enough(self) -> None:
        raw = payload("webhook_charge")
        timestamp, signature = Webhook.signature_header(raw, SECRET).split(",")

        event = Webhook.construct_event(raw, f"{timestamp},v1={'0' * 64},{signature}", SECRET)

        self.assertEqual("charge.paid", event.type)

    def test_during_a_secret_rotation_either_secret_verifies_the_delivery(self) -> None:
        raw = payload("webhook_charge")
        previous_secret = "whsec_previousXw3NcR8vT1mZ5pYs0HdJ4gUe6AoKiVbE"
        timestamp, new_signature = Webhook.signature_header(raw, SECRET, 1790000000).split(",")
        _, old_signature = Webhook.signature_header(raw, previous_secret, 1790000000).split(",")
        header = f"{timestamp},{new_signature},{old_signature}"

        Webhook.verify_signature(raw, header, SECRET, 300, 1790000010)
        Webhook.verify_signature(raw, header, previous_secret, 300, 1790000010)

        with self.assertRaises(SignatureVerificationError):
            Webhook.verify_signature(raw, header, "whsec_neither", 300, 1790000010)

    def test_a_signature_of_another_length_is_a_mismatch_rather_than_a_crash(self) -> None:
        raw = payload("webhook_charge")
        timestamp, signature = Webhook.signature_header(raw, SECRET).split(",")

        for given in ("v1=abc", f"{signature}00", signature[:-1], f"v1={signature[3:].upper()}", "v1=ä€😀"):
            with self.subTest(given), self.assertRaisesRegex(SignatureVerificationError, "does not match"):
                Webhook.construct_event(raw, f"{timestamp},{given}", SECRET)

    def test_a_negative_signature_tolerance_is_a_configuration_error(self) -> None:
        raw = payload("webhook_charge")
        header = Webhook.signature_header(raw, SECRET, 1790000000)

        with self.assertRaisesRegex(InvalidArgumentError, "tolerance cannot be negative"):
            Webhook.verify_signature(raw, header, SECRET, tolerance=-1, now=1790000301)

    def test_a_malformed_header_is_rejected(self) -> None:
        cases: list[tuple[Any, str]] = [
            (None, "header is missing"),
            ("", "header is missing"),
            ("  ", "header is missing"),
            ("garbage", "has no timestamp"),
            ("t=yesterday,v1=abc", "has no timestamp"),
            ("t=١٧٩٠٠٠٠٠٠٠,v1=abc", "has no timestamp"),
            ("t=1790000000", "has no v1 signature"),
            ("t=1790000000,v0=abc", "has no v1 signature"),
            ("t=1790000000,v1=", "has no v1 signature"),
            ("t=1790000000000,v1=abc", "has no timestamp"),
            (f"t={'9' * 5000},v1=abc", "has no timestamp"),
        ]

        for header, message in cases:
            with self.subTest(header), self.assertRaisesRegex(SignatureVerificationError, message):
                Webhook.construct_event(payload("webhook_charge"), header, SECRET)

    def test_a_header_given_as_a_list_of_values_is_read(self) -> None:
        raw = payload("webhook_charge")
        timestamp, signature = Webhook.signature_header(raw, SECRET).split(",")

        self.assertEqual("charge.paid", Webhook.construct_event(raw, [timestamp, signature], SECRET).type)

    def test_an_empty_secret_is_a_configuration_error(self) -> None:
        raw = payload("webhook_charge")

        for secret in ("", "   "):
            with self.subTest(secret), self.assertRaises(InvalidArgumentError):
                Webhook.construct_event(raw, Webhook.signature_header(raw, secret), secret)

    def test_a_body_that_was_already_parsed_is_refused(self) -> None:
        raw = payload("webhook_charge")
        parsed: Any = json.loads(raw)

        with self.assertRaisesRegex(InvalidArgumentError, "raw request body"):
            Webhook.construct_event(parsed, Webhook.signature_header(raw, SECRET), SECRET)

    def test_test_deliveries_from_the_dashboard_are_flagged(self) -> None:
        raw = '{"id":"3c9e1f7a-5b2d-4e8c-9a1f-7b3d5e9c1a2f","event":"charge.paid","test":true,"mode":"test","created_at":"2026-09-24T09:00:00.000000Z","data":{"charge":{"code":"testab12cd34","status":"paid"}}}'

        event = Webhook.construct_event(raw, Webhook.signature_header(raw, SECRET), SECRET)

        self.assertTrue(event.test)
        self.assertIsNone(event.event_id)
        assert event.charge is not None
        self.assertEqual("testab12cd34", event.charge.id)

    def test_the_verification_challenge_is_recognised_and_answered(self) -> None:
        raw = '{"id":"0199f0c2-2b7a-7c0e-9d3a-5e8f1a2b3c4d","event":"webhook.verification","mode":"live","created_at":"2026-10-19T22:00:00.000000Z","data":{"challenge":"c4Lr9xT2mQ7vZ1"}}'

        event = Webhook.construct_event(raw, Webhook.signature_header(raw, SECRET), SECRET)

        self.assertTrue(event.is_verification())
        self.assertTrue(event.is_type(Webhook.VERIFICATION_EVENT))
        self.assertEqual("c4Lr9xT2mQ7vZ1", event.challenge())
        self.assertEqual('{"challenge":"c4Lr9xT2mQ7vZ1"}', event.challenge_response())

    def test_other_deliveries_have_no_challenge_to_answer(self) -> None:
        event = signed("webhook_charge")

        self.assertFalse(event.is_verification())
        self.assertIsNone(event.challenge())
        self.assertIsNone(event.challenge_response())

    def test_a_signed_payload_that_is_not_a_json_object_is_rejected(self) -> None:
        with self.assertRaisesRegex(InvalidArgumentError, "not a JSON object"):
            Webhook.construct_event('["charge.paid"]', Webhook.signature_header('["charge.paid"]', SECRET), SECRET)

        with self.assertRaisesRegex(InvalidArgumentError, "not valid JSON"):
            WebhookEvent.from_payload(b"\x7b\xff\x7d")

        with self.assertRaisesRegex(InvalidArgumentError, "not valid JSON"):
            WebhookEvent.from_payload("{")

    def test_an_event_keeps_what_it_was_sent_with(self) -> None:
        raw = payload("webhook_charge")
        event = signed("webhook_charge")

        self.assertEqual(json.loads(raw), event.to_dict())
        self.assertEqual("live", event.get("mode"))
        self.assertEqual(event, WebhookEvent(json.loads(raw)))


if __name__ == "__main__":
    unittest.main()
