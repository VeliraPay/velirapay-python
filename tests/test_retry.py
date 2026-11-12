from __future__ import annotations

import http.client
import re
import unittest
import urllib.error
from collections.abc import Callable

from velirapay import (
    ApiConnectionError,
    ApiError,
    ApiKeyService,
    ConflictError,
    RateLimitError,
    ServerError,
    ValidationError,
    VeliraPayClient,
    WebhookEndpointService,
)
from velirapay._requester import Requester

from .support import MockTransport, fixture, list_response, path_of


class RetryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.http = MockTransport()
        self.sleeps: list[float] = []

    def transport(self, *, max_retries: int = 2, max_retry_after: float = 10) -> Requester:
        """A requester that records its waits instead of sleeping."""
        return Requester(
            api_key="vp_test_secret",
            transport=self.http,
            base_url=VeliraPayClient.DEFAULT_BASE_URL,
            max_retries=max_retries,
            max_retry_after=max_retry_after,
            timeout=30.0,
            user_agent="VeliraPay-Python/test",
            sleep=self.sleeps.append,
        )

    def test_outages_and_rate_limits_are_retried_with_the_same_idempotency_key(self) -> None:
        (
            self.http.json({"message": "Service Unavailable"}, 503)
            .json({"message": "Too Many Attempts."}, 429, {"Retry-After": "2"})
            .json({"data": fixture("charge")}, 201)
        )

        response = self.transport().request("POST", "/v1/charges", None, {"asset": "BTC"})

        self.assertEqual(201, response.status)
        self.assertEqual(3, len(self.http.requests))

        keys = {request.headers.get("Idempotency-Key") for request in self.http.requests}
        self.assertEqual(1, len(keys))
        self.assertRegex(
            next(iter(keys)) or "", re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
        )
        self.assertEqual({b'{"asset":"BTC"}'}, {request.body for request in self.http.requests})

        self.assertEqual(2, len(self.sleeps))
        self.assertGreaterEqual(self.sleeps[0], 0.375)
        self.assertLessEqual(self.sleeps[0], 0.625)
        self.assertEqual(2.0, self.sleeps[1])

    def test_the_wait_doubles_with_each_attempt(self) -> None:
        self.http.queue(*[ConnectionResetError("reset")] * 5).json(list_response([]))

        self.transport(max_retries=5).request("GET", "/v1/charges")

        for attempt, wait in enumerate(self.sleeps):
            with self.subTest(attempt):
                expected = min(8.0, 0.5 * 2**attempt)
                self.assertGreaterEqual(wait, expected * 0.75)
                self.assertLessEqual(wait, expected * 1.25)

    def test_a_given_idempotency_key_is_kept(self) -> None:
        self.http.json({"message": "Bad Gateway"}, 502).json({"data": fixture("charge")}, 201)

        self.transport().request("POST", "/v1/charges", None, {"asset": "BTC"}, "order-1042")

        self.assertEqual("order-1042", self.http.requests[0].headers["Idempotency-Key"])
        self.assertEqual("order-1042", self.http.requests[1].headers["Idempotency-Key"])

    def test_a_server_error_is_retried_for_reads_only(self) -> None:
        (
            self.http.json({"message": "Server Error"}, 500)
            .json({"data": fixture("charge")})
            .json({"message": "Server Error"}, 500)
        )

        self.transport().request("GET", "/v1/charges/k3v9x2m7q8wz")

        self.assertEqual(2, len(self.http.requests))

        with self.assertRaises(ServerError):
            self.transport().request("POST", "/v1/charges/k3v9x2m7q8wz/cancel")

        self.assertEqual(3, len(self.http.requests))

    def test_a_long_retry_after_is_reported_rather_than_waited(self) -> None:
        self.http.json({"message": "Too Many Attempts."}, 429, {"Retry-After": "60"})

        with self.assertRaises(RateLimitError) as caught:
            self.transport().request("GET", "/v1/charges")

        self.assertEqual(60, caught.exception.retry_after())
        self.assertEqual(1, len(self.http.requests))
        self.assertEqual([], self.sleeps)

    def test_any_retry_after_longer_than_the_longest_is_thrown_straight_away(self) -> None:
        for status, error in ((409, ConflictError), (503, ServerError)):
            with self.subTest(status):
                self.setUp()
                self.http.json({"message": "Try again later."}, status, {"Retry-After": "11"})

                with self.assertRaises(ApiError) as caught:
                    self.transport().request("POST", "/v1/charges", None, {"asset": "BTC"})

                self.assertIsInstance(caught.exception, error)
                self.assertEqual(11, caught.exception.retry_after())
                self.assertEqual(1, len(self.http.requests))
                self.assertEqual([], self.sleeps)

    def test_the_longest_retry_after_that_is_waited_out_can_be_raised(self) -> None:
        self.http.json({"message": "Too Many Attempts."}, 429, {"Retry-After": "60"}).json(list_response([]))

        self.transport(max_retry_after=60).request("GET", "/v1/charges")

        self.assertEqual(2, len(self.http.requests))
        self.assertEqual([60.0], self.sleeps)

    def test_a_write_still_being_processed_under_the_same_key_is_waited_for(self) -> None:
        (
            self.http.json(
                {"message": "A request with this Idempotency-Key is still being processed."}, 409, {"Retry-After": "1"}
            ).json({"data": fixture("charge")}, 201, {"Idempotent-Replayed": "true"})
        )

        response = self.transport().request("POST", "/v1/charges", None, {"asset": "BTC"}, "order-1042")

        self.assertEqual(201, response.status)
        self.assertTrue(response.was_replayed())
        self.assertEqual(2, len(self.http.requests))
        self.assertEqual("order-1042", self.http.requests[1].headers["Idempotency-Key"])
        self.assertEqual([1.0], self.sleeps)

    def test_a_conflict_without_a_retry_after_is_not_retried(self) -> None:
        self.http.json({"message": "This Idempotency-Key was already used for a different request."}, 409)

        with self.assertRaises(ConflictError) as caught:
            self.transport().request("POST", "/v1/charges", None, {"asset": "BTC"}, "order-1042")

        self.assertIsNone(caught.exception.retry_after())
        self.assertEqual(1, len(self.http.requests))
        self.assertEqual([], self.sleeps)

    def test_a_write_whose_lost_answer_carried_a_secret_raises_a_replayed_conflict(self) -> None:
        stored = {
            "message": "A request with this Idempotency-Key already succeeded. Its answer carried a secret, which is"
            " shown once and not kept, so it cannot be replayed."
        }
        writes: list[tuple[str, Callable[[Requester], object]]] = [
            ("/v1/api-keys", lambda requester: ApiKeyService(requester).create({"name": "Shop server"})),
            (
                "/v1/webhook-endpoints",
                lambda requester: WebhookEndpointService(requester).create(
                    {"url": "https://example.com/hooks", "events": ["charge.paid"]}
                ),
            ),
            (
                "/v1/webhook-endpoints/12/secret",
                lambda requester: WebhookEndpointService(requester).rotate_secret("12"),
            ),
        ]

        for path, write in writes:
            with self.subTest(path):
                self.setUp()
                self.http.queue(TimeoutError("timed out")).json(stored, 409, {"Idempotent-Replayed": "true"})

                with self.assertRaises(ConflictError) as caught:
                    write(self.transport())

                self.assertTrue(caught.exception.was_replayed())
                self.assertEqual(stored["message"], str(caught.exception))
                self.assertEqual([path, path], [path_of(request) for request in self.http.requests])
                self.assertEqual(
                    self.http.requests[0].headers["Idempotency-Key"], self.http.requests[1].headers["Idempotency-Key"]
                )

    def test_a_conflict_over_an_objects_state_was_not_replayed(self) -> None:
        self.http.json({"message": "Only a pending charge can be canceled."}, 409)

        with self.assertRaises(ConflictError) as caught:
            self.transport().request("POST", "/v1/charges/k3v9x2m7q8wz/cancel")

        self.assertFalse(caught.exception.was_replayed())

    def test_network_errors_are_retried_until_the_limit(self) -> None:
        failure = urllib.error.URLError(ConnectionRefusedError(111, "Connection refused"))
        self.http.queue(failure, failure, failure)

        with self.assertRaises(ApiConnectionError) as caught:
            self.transport(max_retries=2).request("GET", "/v1/charges")

        self.assertEqual("Could not reach the VeliraPay API: [Errno 111] Connection refused", str(caught.exception))
        self.assertIs(failure, caught.exception.__cause__)
        self.assertEqual(3, len(self.http.requests))
        self.assertEqual(2, len(self.sleeps))

    def test_a_network_error_is_retried_and_the_retry_answered(self) -> None:
        self.http.queue(ConnectionResetError("Connection reset by peer")).json(list_response([]))

        response = self.transport().request("GET", "/v1/charges")

        self.assertEqual(200, response.status)
        self.assertEqual(2, len(self.http.requests))

    def test_an_answer_cut_off_while_its_body_is_read_is_retried(self) -> None:
        self.http.queue(http.client.IncompleteRead(b'{"data":', 120)).json({"data": fixture("charge")})

        response = self.transport().request("GET", "/v1/charges/k3v9x2m7q8wz")

        self.assertEqual(200, response.status)
        self.assertEqual(2, len(self.http.requests))

    def test_client_errors_are_not_retried(self) -> None:
        self.http.json({"message": "The given data was invalid.", "errors": []}, 422)

        with self.assertRaises(ValidationError):
            self.transport().request("POST", "/v1/charges", None, {"asset": "BTC"})

        self.assertEqual(1, len(self.http.requests))

    def test_no_idempotency_key_is_added_when_retries_are_off(self) -> None:
        self.http.json({"data": fixture("charge")}, 201)

        self.transport(max_retries=0).request("POST", "/v1/charges", None, {"asset": "BTC"})

        self.assertNotIn("Idempotency-Key", self.http.last_request().headers)

    def test_no_idempotency_key_is_added_to_reads(self) -> None:
        self.http.json(list_response([]))

        self.transport().request("GET", "/v1/charges")

        self.assertNotIn("Idempotency-Key", self.http.last_request().headers)

    def test_a_connection_error_is_not_retried_when_retries_are_off(self) -> None:
        self.http.queue(TimeoutError("timed out"))

        with self.assertRaises(ApiConnectionError):
            self.transport(max_retries=0).request("GET", "/v1/charges")

        self.assertEqual(1, len(self.http.requests))
        self.assertEqual([], self.sleeps)


if __name__ == "__main__":
    unittest.main()
