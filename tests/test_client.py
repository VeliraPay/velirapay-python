from __future__ import annotations

import math
import platform
import threading
import unittest
from typing import Any

from velirapay import (
    AccountService,
    ActivityService,
    ApiKeyService,
    Asset,
    AssetService,
    BillingService,
    ChargeService,
    ChargeStatus,
    CouponService,
    EventService,
    InvalidArgumentError,
    InvitationService,
    InvoiceService,
    MemberService,
    Mode,
    OverviewService,
    PaymentLinkService,
    PayoutAddressService,
    PayoutService,
    RateLimitError,
    UrllibTransport,
    VeliraPayClient,
    WebhookEndpointService,
)

from .support import MockTransport, body, client, fixture, list_response


class ClientTest(unittest.TestCase):
    def setUp(self) -> None:
        self.http = MockTransport()

    def test_requests_are_authenticated_and_identify_the_library(self) -> None:
        self.http.json(fixture("account"))

        client(self.http, app_info="MyShop/2.1").account.retrieve()

        request = self.http.last_request()
        self.assertEqual("GET", request.method)
        self.assertEqual("https://api.velirapay.com/v1/account", request.url)
        self.assertEqual("Bearer vp_test_secret", request.headers["Authorization"])
        self.assertEqual("application/json", request.headers["Accept"])
        self.assertEqual(
            f"VeliraPay-Python/{VeliraPayClient.VERSION} Python/{platform.python_version()} MyShop/2.1",
            request.headers["User-Agent"],
        )
        self.assertNotIn("Idempotency-Key", request.headers)
        self.assertNotIn("Content-Type", request.headers)
        self.assertIsNone(request.body)
        self.assertEqual(30.0, request.timeout)

    def test_each_endpoint_group_is_an_attribute_of_the_client(self) -> None:
        velirapay = client(self.http)
        groups: dict[str, type[Any]] = {
            "account": AccountService,
            "assets": AssetService,
            "charges": ChargeService,
            "payment_links": PaymentLinkService,
            "invoices": InvoiceService,
            "coupons": CouponService,
            "payouts": PayoutService,
            "events": EventService,
            "webhook_endpoints": WebhookEndpointService,
            "overview": OverviewService,
            "payout_addresses": PayoutAddressService,
            "activity": ActivityService,
            "api_keys": ApiKeyService,
            "members": MemberService,
            "invitations": InvitationService,
            "billing": BillingService,
        }

        for name, service in groups.items():
            with self.subTest(name):
                self.assertIsInstance(getattr(velirapay, name), service)

    def test_the_mode_is_read_from_the_key_prefix(self) -> None:
        self.assertIs(Mode.LIVE, client(self.http, "vp_live_secret").mode())
        self.assertTrue(client(self.http, "vp_live_secret").is_live_mode())
        self.assertFalse(client(self.http, "vp_live_secret").is_test_mode())
        self.assertIs(Mode.TEST, client(self.http, "vp_test_secret").mode())
        self.assertTrue(client(self.http, "vp_test_secret").is_test_mode())
        self.assertEqual("<VeliraPayClient test mode>", repr(client(self.http)))

    def test_a_missing_key_is_rejected(self) -> None:
        for api_key in (" ", "", None):
            with self.subTest(api_key), self.assertRaisesRegex(InvalidArgumentError, "API key is required"):
                VeliraPayClient(api_key)

    def test_a_key_that_does_not_start_with_a_mode_is_rejected(self) -> None:
        for api_key in ("sk_live_secret", "vp_secret", "VP_LIVE_secret"):
            with self.subTest(api_key), self.assertRaises(InvalidArgumentError) as caught:
                VeliraPayClient(api_key)

            self.assertIn('starts with "vp_live_" or "vp_test_"', str(caught.exception))

    def test_a_key_with_a_space_or_a_line_break_is_rejected_without_repeating_it(self) -> None:
        for api_key in ("vp_test_secret\n", "vp_test_sec ret", "vp_test_secrét"):
            with self.subTest(api_key), self.assertRaises(InvalidArgumentError) as caught:
                VeliraPayClient(api_key)

            self.assertNotIn("secret", str(caught.exception))

    def test_impossible_options_are_rejected(self) -> None:
        options: list[dict[str, Any]] = [
            {"max_retries": -1},
            {"max_retries": 1.5},
            {"max_retries": True},
            {"max_retry_after": -1},
            {"max_retry_after": math.nan},
            {"timeout": 0},
            {"timeout": -5},
            {"timeout": math.inf},
            {"timeout": math.nan},
            {"base_url": "api.velirapay.com"},
            {"base_url": "ftp://api.velirapay.com"},
            {"base_url": "https://"},
            {"base_url": "https://api.velirapay.com/\r\nX-Injected: 1"},
            {"app_info": "MyShop\r\nX-Injected: 1"},
            {"app_info": "Boutique éphémère/1.0"},
            {"transport": "urllib"},
        ]

        for given in options:
            with self.subTest(given), self.assertRaises(InvalidArgumentError):
                VeliraPayClient("vp_test_secret", **{"transport": self.http, **given})

    def test_the_errors_of_impossible_arguments_are_also_value_errors(self) -> None:
        with self.assertRaises(ValueError):
            VeliraPayClient("not a key")

    def test_a_retry_after_longer_than_the_configured_longest_is_thrown_straight_away(self) -> None:
        self.http.json({"message": "Too Many Attempts."}, 429, {"Retry-After": "6"})

        with self.assertRaises(RateLimitError) as caught:
            client(self.http, max_retries=2, max_retry_after=5).charges.list()

        self.assertEqual(6, caught.exception.retry_after())
        self.assertEqual(1, len(self.http.requests))

    def test_the_urllib_transport_is_used_when_none_is_given(self) -> None:
        velirapay = VeliraPayClient("vp_test_secret")

        self.assertIs(Mode.TEST, velirapay.mode())
        self.assertIsInstance(velirapay._requester._transport, UrllibTransport)

    def test_requests_go_to_a_custom_base_url(self) -> None:
        self.http.json({"data": fixture("charge")})

        client(self.http, base_url="http://localhost:8000/").charges.retrieve("k3v9x2m7q8wz")

        self.assertEqual("http://localhost:8000/v1/charges/k3v9x2m7q8wz", self.http.last_request().url)

    def test_raw_requests_send_params_as_the_query_or_the_body(self) -> None:
        self.http.json(list_response([])).json({"data": fixture("charge")}, 201)
        velirapay = client(self.http)

        velirapay.request("GET", "/v1/charges", {"status": ChargeStatus.PAID, "per_page": 5, "payment_link": None})

        self.assertEqual("https://api.velirapay.com/v1/charges?status=paid&per_page=5", self.http.last_request().url)

        response = velirapay.request("POST", "/v1/charges", {"asset": "BTC", "amount": 25.0}, idempotency_key="order-7")

        self.assertEqual(201, response.status)
        self.assertEqual(b'{"asset":"BTC","amount":25.0}', self.http.last_request().body)
        self.assertEqual("application/json", self.http.last_request().headers["Content-Type"])
        self.assertEqual("order-7", self.http.last_request().headers["Idempotency-Key"])
        self.assertIs(response, velirapay.last_response())

    def test_replayed_responses_are_recognised(self) -> None:
        self.http.json({"data": fixture("charge")}, 201, {"Idempotent-Replayed": "true"})
        velirapay = client(self.http)

        velirapay.charges.create({"asset": "BTC", "amount": "150.00", "currency": "EUR"}, idempotency_key="order-1042")

        response = velirapay.last_response()
        self.assertIsNotNone(response)
        assert response is not None
        self.assertTrue(response.was_replayed())
        self.assertEqual({"asset": "BTC", "amount": "150.00", "currency": "EUR"}, body(self.http.last_request()))

    def test_a_body_that_cannot_be_encoded_is_refused_before_anything_is_sent(self) -> None:
        circular: dict[str, Any] = {}
        circular["self"] = circular

        for params in (circular, {"amount": math.nan}, {"amount": math.inf}, {"tags": {"a", "b"}}, {"key": object()}):
            with self.subTest(params), self.assertRaisesRegex(InvalidArgumentError, "could not be encoded as JSON"):
                client(self.http).request("POST", "/v1/charges", params)

        self.assertEqual([], self.http.requests)

    def test_an_idempotency_key_that_cannot_be_a_header_is_refused_before_anything_is_sent(self) -> None:
        for key in ("", "  ", "order-1\r\nX-Injected: 1", "commande-élégante"):
            with self.subTest(key), self.assertRaises(InvalidArgumentError):
                client(self.http).charges.cancel("k3v9x2m7q8wz", idempotency_key=key)

        self.assertEqual([], self.http.requests)

    def test_lists_and_objects_in_a_query_are_written_as_php_writes_them(self) -> None:
        self.http.json(list_response([]))

        client(self.http).request(
            "GET",
            "/v1/charges",
            {"asset": ["BTC", Asset.ETH], "filter": {"status": "paid", "test": True, "note": None}, "q": "a b+c/d"},
        )

        self.assertEqual(
            "https://api.velirapay.com/v1/charges"
            "?asset%5B0%5D=BTC&asset%5B1%5D=ETH&filter%5Bstatus%5D=paid&filter%5Btest%5D=1&q=a%20b%2Bc%2Fd",
            self.http.last_request().url,
        )

    def test_the_last_response_belongs_to_the_thread_that_made_it(self) -> None:
        self.http.json({"data": fixture("charge")})
        velirapay = client(self.http)
        seen: list[object] = []

        thread = threading.Thread(target=lambda: seen.append(velirapay.charges.retrieve("k3v9x2m7q8wz")))
        thread.start()
        thread.join()

        self.assertEqual(1, len(seen))
        self.assertIsNone(velirapay.last_response())


if __name__ == "__main__":
    unittest.main()
