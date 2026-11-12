from __future__ import annotations

import unittest
from datetime import UTC, date, datetime, timedelta, timezone

from velirapay import Coupon

from .support import MockTransport, body, client, fixture, list_response, path_of, query_of


class CouponTest(unittest.TestCase):
    def setUp(self) -> None:
        self.http = MockTransport()

    def test_a_coupon_is_created_with_its_expiry_sent_as_iso_8601(self) -> None:
        self.http.json({"data": fixture("coupon")}, 201)

        coupon = client(self.http).coupons.create(
            {
                "code": "spring10",
                "percent_off": "10",
                "max_redemptions": 100,
                "once_per_customer": True,
                "payment_links": ["p4n8r2t6y1ua"],
                "expires_at": datetime(2026, 12, 31, 23, 59, 59, tzinfo=UTC),
            },
            idempotency_key="spring-sale",
        )

        request = self.http.last_request()
        self.assertEqual("POST", request.method)
        self.assertEqual("/v1/coupons", path_of(request))
        self.assertEqual("spring-sale", request.headers["Idempotency-Key"])
        self.assertEqual(
            {
                "code": "spring10",
                "percent_off": "10",
                "max_redemptions": 100,
                "once_per_customer": True,
                "payment_links": ["p4n8r2t6y1ua"],
                "expires_at": "2026-12-31T23:59:59+00:00",
            },
            body(request),
        )
        self.assertEqual("SPRING10", coupon.code)

    def test_the_discount_and_minimum_of_a_coupon_are_sent_as_decimal_strings(self) -> None:
        self.http.json({"data": fixture("coupon")}, 201).json({"data": fixture("coupon")}, 201)
        velirapay = client(self.http)

        velirapay.coupons.create({"code": "spring10", "percent_off": 12.5})

        self.assertEqual({"code": "spring10", "percent_off": "12.5"}, body(self.http.last_request()))

        velirapay.coupons.create({"code": "five", "amount_off": 5, "currency": "EUR", "min_amount": 20.0})

        self.assertEqual(
            {"code": "five", "amount_off": "5", "currency": "EUR", "min_amount": "20"}, body(self.http.last_request())
        )

    def test_an_expiry_in_another_time_zone_is_sent_as_the_same_moment_in_utc(self) -> None:
        self.http.json({"data": fixture("coupon")}, 201).json({"data": fixture("coupon")})
        velirapay = client(self.http)
        paris = timezone(timedelta(hours=1))

        velirapay.coupons.create(
            {"code": "spring10", "percent_off": "10", "expires_at": datetime(2026, 12, 31, 23, 59, 59, tzinfo=paris)}
        )

        self.assertEqual("2026-12-31T22:59:59+00:00", body(self.http.last_request())["expires_at"])

        velirapay.coupons.update("SPRING10", {"expires_at": datetime(2027, 1, 31, 12, 0)})

        self.assertEqual({"expires_at": "2027-01-31T12:00:00+00:00"}, body(self.http.last_request()))

    def test_a_coupon_can_expire_at_the_end_of_a_day(self) -> None:
        self.http.json({"data": fixture("coupon")}, 201)

        client(self.http).coupons.create({"code": "spring10", "percent_off": "10", "expires_at": date(2026, 12, 31)})

        self.assertEqual("2026-12-31", body(self.http.last_request())["expires_at"])

    def test_a_coupon_is_read_into_typed_attributes(self) -> None:
        self.http.json({"data": fixture("coupon")})

        coupon = client(self.http).coupons.retrieve("spring10")

        self.assertEqual("/v1/coupons/spring10", path_of(self.http.last_request()))
        self.assertEqual("SPRING10", coupon.id)
        self.assertEqual("SPRING10", coupon.code)
        self.assertTrue(coupon.is_percentage())
        self.assertEqual("10.00", coupon.percent_off)
        self.assertIsNone(coupon.amount_off)
        self.assertIsNone(coupon.currency)
        self.assertIsNone(coupon.min_amount)
        self.assertEqual(100, coupon.max_redemptions)
        self.assertEqual(4, coupon.times_redeemed)
        self.assertTrue(coupon.once_per_customer)
        self.assertEqual(["p4n8r2t6y1ua"], coupon.payment_links)
        self.assertTrue(coupon.active)
        self.assertEqual(datetime(2026, 12, 31, 23, 59, 59, tzinfo=UTC), coupon.expires_at)
        self.assertEqual(datetime(2026, 10, 15, 9, 30, tzinfo=UTC), coupon.updated_at)

    def test_an_amount_off_coupon_names_its_currency(self) -> None:
        self.http.json(
            {
                "data": {
                    **fixture("coupon"),
                    "percent_off": None,
                    "amount_off": "5.00",
                    "currency": "EUR",
                    "min_amount": "20.00",
                }
            }
        )

        coupon = client(self.http).coupons.retrieve("SPRING10")

        self.assertFalse(coupon.is_percentage())
        self.assertEqual("5.00", coupon.amount_off)
        self.assertEqual("EUR", coupon.currency)
        self.assertEqual("20.00", coupon.min_amount)

    def test_a_coupons_limits_are_updated(self) -> None:
        self.http.json({"data": {**fixture("coupon"), "active": False, "payment_links": []}})

        coupon = client(self.http).coupons.update(
            "SPRING10", {"active": False, "payment_links": [], "expires_at": None}
        )

        request = self.http.last_request()
        self.assertEqual("PATCH", request.method)
        self.assertEqual("/v1/coupons/SPRING10", path_of(request))
        self.assertEqual({"active": False, "payment_links": [], "expires_at": None}, body(request))
        self.assertFalse(coupon.active)
        self.assertEqual([], coupon.payment_links)

    def test_coupons_are_listed(self) -> None:
        self.http.json(list_response([fixture("coupon")]))

        page = client(self.http).coupons.list({"per_page": 10})

        self.assertEqual("/v1/coupons", path_of(self.http.last_request()))
        self.assertEqual({"per_page": "10"}, query_of(self.http.last_request()))
        self.assertIsInstance(page.data[0], Coupon)

    def test_a_coupon_is_deleted(self) -> None:
        self.http.empty()

        self.assertIsNone(client(self.http).coupons.delete("SPRING10"))  # type: ignore[func-returns-value]

        request = self.http.last_request()
        self.assertEqual("DELETE", request.method)
        self.assertEqual("/v1/coupons/SPRING10", path_of(request))


if __name__ == "__main__":
    unittest.main()
