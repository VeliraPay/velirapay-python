from __future__ import annotations

import unittest
from datetime import UTC, datetime
from typing import Any

from velirapay import Asset, PayoutStatus, PayoutSummary, PayoutSummaryList

from .support import MockTransport, client, path_of

PAYOUT: dict[str, Any] = {
    "id": "k3v9x2m7q8wz",
    "object": "payout",
    "charge": "k3v9x2m7q8wz",
    "status": "sent",
    "asset": "USDT",
    "gross_amount": "11.014175",
    "fee_percent": "3",
    "fee_amount": "0.330425",
    "fee_fiat_amount": "0.33",
    "fiat_currency": "USD",
    "exchange_rate": "0.9987",
    "net_amount": "10.68375",
    "network_fee": "0.081611",
    "sent_amount": "10.602139",
    "payout_address": "0x7099",
    "payout_txid": "0x9a4f",
    "explorer_url": "https://etherscan.io/tx/0x9a4f",
    "attempts": 1,
    "last_error": None,
    "next_attempt_at": None,
    "sent_at": "2026-11-02T20:58:00.000000Z",
    "confirmed_at": "2026-11-02T21:00:04.000000Z",
    "created_at": "2026-11-02T20:57:00.000000Z",
}


class PayoutTest(unittest.TestCase):
    def setUp(self) -> None:
        self.http = MockTransport()

    def test_a_payout_is_read_by_its_charge_into_typed_attributes(self) -> None:
        self.http.json({"data": PAYOUT})

        payout = client(self.http).payouts.retrieve("k3v9x2m7q8wz")

        self.assertEqual("/v1/payouts/k3v9x2m7q8wz", path_of(self.http.last_request()))
        self.assertEqual("k3v9x2m7q8wz", payout.id)
        self.assertEqual("k3v9x2m7q8wz", payout.charge)
        self.assertTrue(payout.is_sent())
        self.assertFalse(payout.is_manual())
        self.assertEqual("USDT", payout.asset)
        self.assertEqual("11.014175", payout.gross_amount)
        self.assertEqual("3", payout.fee_percent)
        self.assertEqual("0.330425", payout.fee_amount)
        self.assertEqual("0.33", payout.fee_fiat_amount)
        self.assertEqual("USD", payout.fiat_currency)
        self.assertEqual("0.9987", payout.exchange_rate)
        self.assertEqual("10.68375", payout.net_amount)
        self.assertEqual("0.081611", payout.network_fee)
        self.assertEqual("10.602139", payout.sent_amount)
        self.assertEqual("0x7099", payout.payout_address)
        self.assertEqual("0x9a4f", payout.payout_txid)
        self.assertEqual("https://etherscan.io/tx/0x9a4f", payout.explorer_url)
        self.assertEqual(1, payout.attempts)
        self.assertIsNone(payout.last_error)
        self.assertIsNone(payout.next_attempt_at)
        self.assertEqual(datetime(2026, 11, 2, 20, 58, tzinfo=UTC), payout.sent_at)
        self.assertEqual(datetime(2026, 11, 2, 21, 0, 4, tzinfo=UTC), payout.confirmed_at)

    def test_payouts_are_listed_with_their_filters(self) -> None:
        self.http.json({"data": [PAYOUT], "meta": {"current_page": 1, "last_page": 1, "per_page": 25, "total": 1}})

        page = client(self.http).payouts.list({"status": PayoutStatus.SENT, "asset": Asset.USDT})

        self.assertEqual("/v1/payouts", path_of(self.http.last_request()))
        self.assertEqual("https://api.velirapay.com/v1/payouts?status=sent&asset=USDT", self.http.last_request().url)
        self.assertEqual("k3v9x2m7q8wz", page.data[0].id)

    def test_the_summary_adds_up_each_coin(self) -> None:
        self.http.json(
            {
                "data": [
                    {
                        "object": "payout_summary",
                        "asset": "BTC",
                        "payouts": 3,
                        "gross_amount": "0.3",
                        "fee_amount": "0.009",
                        "owed_amount": "0.097",
                        "in_flight_amount": "0",
                        "paid_out_amount": "0.194",
                        "network_fee_amount": "0.0001",
                        "waiting_for_address": 0,
                    }
                ],
                "meta": {"mode": "live"},
            }
        )

        summary = client(self.http).payouts.summary()

        self.assertEqual("/v1/payouts/summary", path_of(self.http.last_request()))
        self.assertIsInstance(summary, PayoutSummaryList)
        self.assertIsInstance(summary, list)
        self.assertEqual("live", summary.mode)
        self.assertEqual({"mode": "live"}, summary.meta)
        self.assertEqual([PayoutSummary(summary[0].to_dict())], summary)
        self.assertEqual(1, len(summary))
        self.assertEqual("BTC", summary[0].asset)
        self.assertEqual(3, summary[0].payouts)
        self.assertEqual("0.3", summary[0].gross_amount)
        self.assertEqual("0.009", summary[0].fee_amount)
        self.assertEqual("0.194", summary[0].paid_out_amount)
        self.assertEqual("0", summary[0].in_flight_amount)
        self.assertEqual("0.097", summary[0].owed_amount)
        self.assertEqual("0.0001", summary[0].network_fee_amount)
        self.assertEqual(0, summary[0].waiting_for_address)


if __name__ == "__main__":
    unittest.main()
