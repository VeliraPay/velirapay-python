from __future__ import annotations

import unittest

from velirapay import Charge

from .support import MockTransport, client, fixture, list_response, query_of


class PaginationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.http = MockTransport()

    def test_the_iterator_walks_every_page_and_skips_objects_it_already_gave(self) -> None:
        first, second, third = (
            {**fixture("charge"), "id": code} for code in ("charge000001", "charge000002", "charge000003")
        )
        (
            self.http.json(list_response([first, second], current_page=1, last_page=2, per_page=2, total=4)).json(
                list_response([second, third], current_page=2, last_page=2, per_page=2, total=4)
            )
        )

        iterator = client(self.http).charges.iterator({"status": "paid", "per_page": 2})

        self.assertEqual([], self.http.requests)
        self.assertEqual(["charge000001", "charge000002", "charge000003"], [charge.id for charge in iterator])
        self.assertEqual(2, len(self.http.requests))
        self.assertEqual({"status": "paid", "per_page": "2"}, query_of(self.http.requests[0]))
        self.assertEqual({"status": "paid", "per_page": "2", "page": "2"}, query_of(self.http.requests[1]))

    def test_a_page_is_walked_with_for_and_fetches_the_next_one(self) -> None:
        (
            self.http.json(list_response([fixture("charge")], current_page=1, last_page=2, per_page=1, total=2)).json(
                list_response(
                    [{**fixture("charge"), "id": "charge000002"}], current_page=2, last_page=2, per_page=1, total=2
                )
            )
        )

        page = client(self.http).charges.list({"per_page": 1})

        self.assertEqual(["k3v9x2m7q8wz"], [charge.id for charge in page])
        self.assertEqual(1, len(page))
        self.assertTrue(page.has_more())
        self.assertFalse(page.is_empty())

        following = page.next_page()

        assert following is not None
        self.assertIsInstance(following.data[0], Charge)
        self.assertEqual("charge000002", following.data[0].id)
        self.assertFalse(following.has_more())
        self.assertEqual({"per_page": "1", "page": "2"}, query_of(self.http.last_request()))

    def test_the_last_page_has_no_next_page(self) -> None:
        self.http.json(list_response([fixture("charge")]))

        page = client(self.http).charges.list()

        self.assertFalse(page.has_more())
        self.assertIsNone(page.next_page())
        self.assertEqual(1, len(self.http.requests))

    def test_the_iterator_stops_on_a_page_that_does_not_move_forward(self) -> None:
        (
            self.http.json(list_response([fixture("charge")], current_page=1, last_page=3)).json(
                list_response([{**fixture("charge"), "id": "charge000002"}], current_page=1, last_page=3)
            )
        )

        self.assertEqual(["k3v9x2m7q8wz"], [charge.id for charge in client(self.http).charges.iterator()])
        self.assertEqual(2, len(self.http.requests))

    def test_an_empty_list_is_one_empty_page(self) -> None:
        self.http.json(list_response([]))

        page = client(self.http).charges.list()

        self.assertTrue(page.is_empty())
        self.assertEqual(0, len(page))
        self.assertEqual(0, page.total)
        self.assertEqual([], list(page.auto_paging_iterator()))
        self.assertEqual("<Page 1 of 1: 0 of 0>", repr(page))

    def test_a_list_without_its_position_is_one_page(self) -> None:
        self.http.json({"data": [fixture("charge"), fixture("charge")]})

        page = client(self.http).charges.list()

        self.assertEqual(1, page.current_page)
        self.assertEqual(1, page.last_page)
        self.assertEqual(2, page.per_page)
        self.assertEqual(2, page.total)

    def test_every_list_has_an_iterator(self) -> None:
        velirapay = client(self.http)

        for service in (
            velirapay.charges,
            velirapay.payment_links,
            velirapay.invoices,
            velirapay.coupons,
            velirapay.payouts,
            velirapay.events,
            velirapay.webhook_endpoints,
            velirapay.activity,
            velirapay.api_keys,
            velirapay.members,
            velirapay.invitations,
        ):
            with self.subTest(type(service).__name__):
                self.http.json(list_response([{"id": "only"}]))

                self.assertEqual(["only"], [item.get("id") for item in service.iterator()])


if __name__ == "__main__":
    unittest.main()
