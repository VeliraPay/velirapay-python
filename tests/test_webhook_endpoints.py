from __future__ import annotations

import unittest
from datetime import UTC, datetime
from typing import Any

from .support import MockTransport, body, client, path_of, query_of

ENDPOINT: dict[str, Any] = {
    "id": "12",
    "object": "webhook_endpoint",
    "url": "https://example.com/hooks",
    "description": None,
    "events": ["charge.paid"],
    "active": True,
    "verified": True,
    "deliveries_count": 0,
    "failed_deliveries_count": 0,
    "verified_at": "2026-10-20T10:00:00.000000Z",
    "created_at": "2026-10-20T09:00:00.000000Z",
}

DELIVERY: dict[str, Any] = {
    "id": "9d2e0b8a-0000-4000-8000-5f3a00000000",
    "object": "webhook_delivery",
    "event": "charge.paid",
    "event_id": None,
    "test": True,
    "status": "succeeded",
    "attempts": 1,
    "response_status": 200,
    "error": None,
    "charge": None,
    "invoice": None,
    "created_at": "2026-11-06T09:00:00.000000Z",
    "last_attempted_at": "2026-11-06T09:00:01.000000Z",
    "delivered_at": "2026-11-06T09:00:01.000000Z",
}


class WebhookEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.http = MockTransport()

    def test_endpoints_are_listed_with_whether_they_can_receive(self) -> None:
        self.http.json(
            {
                "data": [
                    {**ENDPOINT, "description": "Orders", "deliveries_count": 2, "failed_deliveries_count": 1},
                    {
                        **ENDPOINT,
                        "id": "13",
                        "url": "https://example.com/new",
                        "events": [],
                        "verified": False,
                        "verified_at": None,
                    },
                ],
                "meta": {"current_page": 1, "last_page": 1, "per_page": 25, "total": 2},
            }
        )

        verified, unverified = client(self.http).webhook_endpoints.list().data

        self.assertEqual("/v1/webhook-endpoints", path_of(self.http.last_request()))
        self.assertEqual("12", verified.id)
        self.assertEqual("https://example.com/hooks", verified.url)
        self.assertEqual("Orders", verified.description)
        self.assertEqual(["charge.paid"], verified.events)
        self.assertTrue(verified.is_receiving())
        self.assertEqual(2, verified.deliveries_count)
        self.assertEqual(1, verified.failed_deliveries_count)
        self.assertEqual(datetime(2026, 10, 20, 10, 0, tzinfo=UTC), verified.verified_at)
        self.assertIsNone(verified.secret)

        self.assertFalse(unverified.is_receiving())
        self.assertIsNone(unverified.verified_at)

    def test_an_endpoint_is_added_with_its_secret_and_whether_it_answered(self) -> None:
        self.http.json(
            {
                "data": {**ENDPOINT, "verified": False, "secret": "whsec_abc"},
                "meta": {"verification_error": "The endpoint answered the challenge with HTTP 404."},
            },
            201,
        )

        endpoint = client(self.http).webhook_endpoints.create(
            {"url": "https://example.com/hooks", "events": ["charge.paid"], "active": True}, idempotency_key="add-hook"
        )

        request = self.http.last_request()
        self.assertEqual("POST", request.method)
        self.assertEqual("/v1/webhook-endpoints", path_of(request))
        self.assertEqual("add-hook", request.headers["Idempotency-Key"])
        self.assertEqual({"url": "https://example.com/hooks", "events": ["charge.paid"], "active": True}, body(request))
        self.assertEqual("whsec_abc", endpoint.secret)
        self.assertEqual("The endpoint answered the challenge with HTTP 404.", endpoint.verification_error)

    def test_an_endpoint_is_changed_verified_tested_rotated_and_deleted(self) -> None:
        (
            self.http.json({"data": {**ENDPOINT, "active": False}, "meta": {"verification_error": None}})
            .json({"data": ENDPOINT})
            .json({"data": DELIVERY}, 201)
            .json(
                {
                    "data": {**ENDPOINT, "secret": "whsec_new"},
                    "meta": {"previous_secret_expires_at": "2026-11-07T09:00:00.000000Z"},
                }
            )
            .empty()
        )
        velirapay = client(self.http)

        self.assertFalse(velirapay.webhook_endpoints.update("12", {"active": False}).active)
        self.assertEqual("PATCH", self.http.last_request().method)
        self.assertEqual("/v1/webhook-endpoints/12", path_of(self.http.last_request()))
        self.assertEqual({"active": False}, body(self.http.last_request()))

        self.assertTrue(velirapay.webhook_endpoints.verify("12").verified)
        self.assertEqual("/v1/webhook-endpoints/12/verify", path_of(self.http.last_request()))

        self.assertTrue(velirapay.webhook_endpoints.test("12").test)
        self.assertEqual("/v1/webhook-endpoints/12/test", path_of(self.http.last_request()))

        rotated = velirapay.webhook_endpoints.rotate_secret("12")

        self.assertEqual("whsec_new", rotated.secret)
        self.assertEqual(datetime(2026, 11, 7, 9, 0, tzinfo=UTC), rotated.previous_secret_expires_at)
        self.assertEqual("/v1/webhook-endpoints/12/secret", path_of(self.http.last_request()))

        velirapay.webhook_endpoints.delete("12")

        self.assertEqual("DELETE", self.http.last_request().method)
        self.assertEqual("/v1/webhook-endpoints/12", path_of(self.http.last_request()))

    def test_deliveries_are_listed_and_retried(self) -> None:
        (
            self.http.json(
                {
                    "data": [
                        {**DELIVERY, "test": False, "status": "failed", "response_status": 500, "charge": "abc123"}
                    ],
                    "meta": {"current_page": 1, "last_page": 1, "per_page": 25, "total": 1},
                }
            ).json({"data": {**DELIVERY, "status": "pending"}})
        )
        velirapay = client(self.http)

        delivery = velirapay.webhook_endpoints.deliveries("12", {"status": "failed"}).data[0]

        self.assertEqual("/v1/webhook-endpoints/12/deliveries", path_of(self.http.last_request()))
        self.assertEqual({"status": "failed"}, query_of(self.http.last_request()))
        self.assertFalse(delivery.succeeded())
        self.assertEqual(500, delivery.response_status)
        self.assertEqual("abc123", delivery.charge)
        self.assertIsNone(delivery.payload)
        self.assertEqual([], delivery.attempt_log)

        velirapay.webhook_endpoints.retry_delivery("12", delivery.id)

        self.assertEqual("POST", self.http.last_request().method)
        self.assertEqual(f"/v1/webhook-endpoints/12/deliveries/{delivery.id}/retry", path_of(self.http.last_request()))

    def test_a_delivery_is_retrieved_with_every_attempt_and_its_body(self) -> None:
        self.http.json(
            {
                "data": {
                    **DELIVERY,
                    "attempts": 2,
                    "payload": {"id": "whd_1", "event": "charge.paid", "data": {"charge": {"id": "abc123"}}},
                    "attempt_log": [
                        {
                            "object": "webhook_delivery_attempt",
                            "attempt": 2,
                            "url": "https://example.com/hooks",
                            "request_headers": {
                                "Content-Type": "application/json",
                                "X-VeliraPay-Signature": "t=1762419601,v1=…",
                            },
                            "response_status": 200,
                            "response_headers": {"Content-Type": "text/plain"},
                            "response_body": "ok",
                            "error": None,
                            "duration_ms": 84,
                            "created_at": "2026-11-06T09:05:00.000000Z",
                        },
                        {
                            "object": "webhook_delivery_attempt",
                            "attempt": 1,
                            "url": "https://example.com/hooks",
                            "request_headers": {"Content-Type": "application/json"},
                            "response_status": None,
                            "response_headers": None,
                            "response_body": None,
                            "error": "Timed out after 10 seconds.",
                            "duration_ms": 10003,
                            "created_at": "2026-11-06T09:00:00.000000Z",
                        },
                    ],
                }
            }
        )

        delivery = client(self.http).webhook_endpoints.retrieve_delivery("12", "9d2e0b8a-0000-4000-8000-5f3a00000000")

        self.assertEqual("GET", self.http.last_request().method)
        self.assertEqual(
            "/v1/webhook-endpoints/12/deliveries/9d2e0b8a-0000-4000-8000-5f3a00000000",
            path_of(self.http.last_request()),
        )
        self.assertEqual(
            {"id": "whd_1", "event": "charge.paid", "data": {"charge": {"id": "abc123"}}}, delivery.payload
        )
        self.assertEqual(2, len(delivery.attempt_log))

        latest, first = delivery.attempt_log

        self.assertTrue(latest.succeeded())
        self.assertEqual(2, latest.attempt)
        self.assertEqual("https://example.com/hooks", latest.url)
        self.assertEqual(
            {"Content-Type": "application/json", "X-VeliraPay-Signature": "t=1762419601,v1=…"}, latest.request_headers
        )
        self.assertEqual({"Content-Type": "text/plain"}, latest.response_headers)
        self.assertEqual("ok", latest.response_body)
        self.assertEqual(84, latest.duration_ms)
        self.assertEqual(datetime(2026, 11, 6, 9, 5, tzinfo=UTC), latest.created_at)
        self.assertFalse(first.succeeded())
        self.assertIsNone(first.response_headers)
        self.assertEqual("Timed out after 10 seconds.", first.error)


if __name__ == "__main__":
    unittest.main()
