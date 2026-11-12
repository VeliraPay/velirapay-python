from __future__ import annotations

import unittest
from typing import Any

from velirapay import Asset, SupportedAsset

from .support import MockTransport, client, path_of

ASSETS: dict[str, Any] = {
    "data": [
        {
            "id": "BTC",
            "object": "asset",
            "name": "Bitcoin",
            "ticker": "BTC",
            "network": "Bitcoin",
            "contract_address": None,
            "decimals": 8,
            "required_confirmations": 2,
            "confirmation_wait": "about 20 minutes",
            "accepted": True,
            "currency": "EUR",
            "exchange_rate": "68527.48",
            "minimum_amount": None,
            "minimum_price": "0.01",
            "network_surcharge": None,
        },
        {
            "id": "USDT",
            "object": "asset",
            "name": "Tether USD",
            "ticker": "USDT",
            "network": "Ethereum (ERC-20)",
            "contract_address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "decimals": 6,
            "required_confirmations": 6,
            "confirmation_wait": "about a minute",
            "accepted": False,
            "currency": "EUR",
            "exchange_rate": "0.8709",
            "minimum_amount": "10",
            "minimum_price": "8.71",
            "network_surcharge": None,
        },
        {
            "id": "NEWCOIN",
            "object": "asset",
            "name": "New",
            "ticker": "NEW",
            "network": "New",
            "contract_address": None,
            "decimals": 18,
            "required_confirmations": 1,
            "confirmation_wait": "under a minute",
            "accepted": None,
            "currency": "EUR",
            "exchange_rate": None,
            "minimum_amount": None,
            "minimum_price": "0.01",
            "network_surcharge": None,
        },
    ],
    "meta": {"mode": "live", "currencies": ["USD", "EUR"]},
}


class AssetTest(unittest.TestCase):
    def setUp(self) -> None:
        self.http = MockTransport()

    def test_the_coins_on_offer_are_read_with_their_minimums(self) -> None:
        self.http.json(ASSETS)

        page = client(self.http).assets.list({"currency": "EUR"})

        request = self.http.last_request()
        self.assertEqual("/v1/assets", path_of(request))
        self.assertEqual("https://api.velirapay.com/v1/assets?currency=EUR", request.url)
        self.assertEqual(3, len(page))
        self.assertFalse(page.has_more())

        bitcoin, tether, unknown = page.data

        self.assertEqual("BTC", bitcoin.id)
        self.assertIs(Asset.BTC, bitcoin.asset())
        self.assertIs(True, bitcoin.accepted)
        self.assertIsNone(bitcoin.minimum_amount)
        self.assertEqual("0.01", bitcoin.minimum_price)
        self.assertIsNone(bitcoin.contract_address)
        self.assertEqual(8, bitcoin.decimals)
        self.assertEqual(2, bitcoin.required_confirmations)
        self.assertEqual("about 20 minutes", bitcoin.confirmation_wait)
        self.assertIsNone(bitcoin.network_surcharge)

        self.assertEqual("Tether USD", tether.name)
        self.assertEqual("USDT", tether.ticker)
        self.assertEqual("Ethereum (ERC-20)", tether.network)
        self.assertEqual("0xdAC17F958D2ee523a2206206994597C13D831ec7", tether.contract_address)
        self.assertIs(False, tether.accepted)
        self.assertEqual("EUR", tether.currency)
        self.assertEqual("0.8709", tether.exchange_rate)
        self.assertEqual("10", tether.minimum_amount)
        self.assertEqual("8.71", tether.minimum_price)

        self.assertIsNone(unknown.asset())
        self.assertIsNone(unknown.accepted)
        self.assertIsNone(unknown.exchange_rate)

    def test_a_coin_says_the_network_surcharge_a_charge_in_it_asks_on_top_of_the_price(self) -> None:
        self.http.json(
            {
                "data": [
                    {
                        "id": "USDT_TRON",
                        "object": "asset",
                        "name": "Tether USD",
                        "ticker": "USDT",
                        "network": "Tron (TRC-20)",
                        "contract_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
                        "decimals": 6,
                        "required_confirmations": 19,
                        "confirmation_wait": "about a minute",
                        "accepted": True,
                        "currency": "USD",
                        "exchange_rate": "1",
                        "minimum_amount": None,
                        "minimum_price": "0.5",
                        "network_surcharge": "2.5",
                    }
                ],
                "meta": {"mode": "live", "currencies": ["USD", "EUR"]},
            }
        )

        tether = client(self.http).assets.list().data[0]

        self.assertEqual("https://api.velirapay.com/v1/assets", self.http.last_request().url)
        self.assertIs(Asset.USDT_TRON, tether.asset())
        self.assertEqual("2.5", tether.network_surcharge)

    def test_every_coin_the_api_defines_is_known(self) -> None:
        for code in (
            "BTC", "BTC_LIGHTNING", "LTC", "DOGE", "BCH", "ETH", "XMR", "SOL", "BNB", "TRX", "USDT", "USDC",
            "USDT_TRON", "USDC_BASE", "USDC_POLYGON", "USDT_BSC", "USDC_BSC", "USDT_POLYGON", "USDT_ARBITRUM",
            "USDC_ARBITRUM", "ETH_BASE", "ETH_ARBITRUM", "POL",
        ):  # fmt: skip
            with self.subTest(code):
                self.assertEqual(code, SupportedAsset({"id": code}).asset())

        self.assertEqual(23, len(Asset))


if __name__ == "__main__":
    unittest.main()
