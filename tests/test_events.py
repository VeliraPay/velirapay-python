from __future__ import annotations

import unittest
from datetime import UTC, datetime
from typing import Any

from velirapay import Event, EventType

from .support import MockTransport, client, fixture, list_response, path_of, query_of


def event() -> dict[str, Any]:
    """An event as the API sends it."""
    return {
        "id": "9b1f7a3e-2c4d-4e8f-a6b0-1d2c3e4f5a6b",
        "object": "event",
        "type": "charge.paid",
        "details": {"amount": "0.0025"},
        "created_at": "2026-09-20T10:05:41.000000Z",
        "charge": fixture("charge"),
        "invoice": None,
    }


class EventTest(unittest.TestCase):
    def setUp(self) -> None:
        self.http = MockTransport()

    def test_an_event_is_retrieved_with_its_charge(self) -> None:
        self.http.json({"data": event()})

        read = client(self.http).events.retrieve("9b1f7a3e-2c4d-4e8f-a6b0-1d2c3e4f5a6b")

        self.assertEqual("/v1/events/9b1f7a3e-2c4d-4e8f-a6b0-1d2c3e4f5a6b", path_of(self.http.last_request()))
        self.assertEqual("9b1f7a3e-2c4d-4e8f-a6b0-1d2c3e4f5a6b", read.id)
        self.assertEqual("charge.paid", read.type)
        self.assertTrue(read.is_type(EventType.CHARGE_UNDERPAID, "charge.paid"))
        self.assertFalse(read.is_type(EventType.CHARGE_EXPIRED))
        self.assertEqual({"amount": "0.0025"}, read.details)
        self.assertEqual(datetime(2026, 9, 20, 10, 5, 41, tzinfo=UTC), read.created_at)
        assert read.charge is not None
        self.assertEqual("k3v9x2m7q8wz", read.charge.id)
        self.assertIsNone(read.invoice)

    def test_events_are_listed_with_filters(self) -> None:
        self.http.json(list_response([event()]))

        page = client(self.http).events.list({"type": EventType.CHARGE_PAID, "charge": "k3v9x2m7q8wz"})

        self.assertEqual("/v1/events", path_of(self.http.last_request()))
        self.assertEqual({"type": "charge.paid", "charge": "k3v9x2m7q8wz"}, query_of(self.http.last_request()))
        self.assertIsInstance(page.data[0], Event)


if __name__ == "__main__":
    unittest.main()
