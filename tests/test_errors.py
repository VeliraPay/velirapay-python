from __future__ import annotations

import pickle
import unittest
import urllib.error
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

from velirapay import (
    ApiConnectionError,
    ApiError,
    ApiResponse,
    AuthenticationError,
    ConflictError,
    HttpRequest,
    InvalidRequestError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ServerError,
    UnexpectedResponseError,
    ValidationError,
    VeliraPayClient,
    VeliraPayError,
)

from .support import MockTransport, client


class ErrorsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.http = MockTransport()

    def test_each_error_status_has_its_own_error(self) -> None:
        statuses: list[tuple[int, type[ApiError]]] = [
            (400, InvalidRequestError),
            (401, AuthenticationError),
            (403, PermissionDeniedError),
            (404, NotFoundError),
            (409, ConflictError),
            (422, ValidationError),
            (429, RateLimitError),
            (500, ServerError),
            (503, ServerError),
            (301, InvalidRequestError),
        ]

        for status, error in statuses:
            with self.subTest(status):
                self.http.json({"message": "Something went wrong."}, status)

                with self.assertRaises(ApiError) as caught:
                    client(self.http).charges.retrieve("k3v9x2m7q8wz")

                self.assertIs(error, type(caught.exception))
                self.assertIsInstance(caught.exception, VeliraPayError)
                self.assertEqual(status, caught.exception.status)
                self.assertEqual("Something went wrong.", str(caught.exception))
                self.assertEqual("Something went wrong.", caught.exception.message)
                self.assertEqual({"message": "Something went wrong."}, caught.exception.body)
                self.assertEqual(status, caught.exception.response.status)

    def test_an_object_of_another_account_or_mode_is_not_found(self) -> None:
        self.http.json({"message": "No such object."}, 404)

        with self.assertRaisesRegex(NotFoundError, "^No such object.$"):
            client(self.http).charges.retrieve("k3v9x2m7q8wz")

    def test_an_error_without_a_json_message_still_explains_itself(self) -> None:
        self.http.queue(ApiResponse(502, {"Content-Type": "text/html"}, "<html>Bad Gateway</html>"))

        with self.assertRaises(ServerError) as caught:
            client(self.http).charges.retrieve("k3v9x2m7q8wz")

        self.assertEqual("The VeliraPay API answered with HTTP 502.", str(caught.exception))
        self.assertEqual({}, caught.exception.body)

    def test_validation_errors_are_keyed_by_field(self) -> None:
        self.http.json(
            {
                "message": "The asset field is required. (and 1 more error)",
                "errors": {
                    "asset": ["The asset field is required."],
                    "items.0.quantity": ["The items.0.quantity field must be at least 0.001."],
                },
            },
            422,
        )

        with self.assertRaises(ValidationError) as caught:
            client(self.http).charges.create({"asset": ""})

        self.assertEqual(
            {
                "asset": ["The asset field is required."],
                "items.0.quantity": ["The items.0.quantity field must be at least 0.001."],
            },
            caught.exception.errors(),
        )
        self.assertEqual("The asset field is required.", caught.exception.first_error("asset"))
        self.assertIsNone(caught.exception.first_error("amount"))

    def test_validation_errors_of_another_shape_are_read_as_far_as_they_go(self) -> None:
        response = ApiResponse(422, {}, '{"message":"Invalid.","errors":{"amount":"Too low.","asset":[1,"Unknown."]}}')
        empty = ApiResponse(422, {}, '{"message":"Invalid.","errors":[]}')

        self.assertEqual(
            {"amount": ["Too low."], "asset": ["Unknown."]}, ValidationError("Invalid.", response).errors()
        )
        self.assertEqual({}, ValidationError("Invalid.", empty).errors())

    def test_a_rate_limit_says_when_to_try_again(self) -> None:
        self.http.json({"message": "Too Many Attempts."}, 429, {"Retry-After": "42"})

        with self.assertRaises(RateLimitError) as caught:
            client(self.http).charges.list()

        self.assertEqual(42, caught.exception.retry_after())
        self.assertEqual("42", caught.exception.header("Retry-After"))
        self.assertEqual("42", caught.exception.header("retry-after"))

    def test_a_retry_after_given_as_a_date_is_read_in_seconds(self) -> None:
        at = format_datetime(datetime.now(UTC) + timedelta(seconds=30), usegmt=True)
        self.http.json({"message": "Service Unavailable"}, 503, {"Retry-After": at})

        with self.assertRaises(ServerError) as caught:
            client(self.http).charges.list()

        retry_after = caught.exception.retry_after()
        self.assertIsNotNone(retry_after)
        assert retry_after is not None
        self.assertGreaterEqual(retry_after, 29)
        self.assertLessEqual(retry_after, 31)

    def test_a_retry_after_of_any_length_is_read(self) -> None:
        self.assertEqual(5, ApiResponse(429, {"Retry-After": "0" * 5000 + "5"}).retry_after())
        self.assertEqual(10**18, ApiResponse(429, {"Retry-After": "9" * 5000}).retry_after())

        self.http.json({"message": "Too Many Attempts."}, 429, {"Retry-After": "9" * 5000})

        with self.assertRaises(RateLimitError):
            client(self.http, max_retries=2).charges.list()

        self.assertEqual(1, len(self.http.requests))

    def test_a_retry_after_that_is_neither_seconds_nor_a_date_is_ignored(self) -> None:
        for value in ("soon", "-5", "1.5", "Thu, 32 Foo 2026 25:61:61 GMT"):
            with self.subTest(value):
                self.assertIsNone(ApiResponse(429, {"Retry-After": value}).retry_after())

    def test_a_successful_response_that_is_not_json_is_reported(self) -> None:
        self.http.queue(ApiResponse(200, {"Content-Type": "text/html"}, "<html>Maintenance</html>"))

        with self.assertRaises(UnexpectedResponseError):
            client(self.http).charges.retrieve("k3v9x2m7q8wz")

    def test_a_successful_response_without_the_object_asked_for_is_reported(self) -> None:
        self.http.json({"data": []})

        with self.assertRaisesRegex(UnexpectedResponseError, "without the object"):
            client(self.http).charges.retrieve("k3v9x2m7q8wz")

    def test_a_successful_response_without_the_list_asked_for_is_reported(self) -> None:
        self.http.json({"data": {"id": "k3v9x2m7q8wz"}})

        with self.assertRaisesRegex(UnexpectedResponseError, "without the list"):
            client(self.http).charges.list()

    def test_an_unreachable_api_is_reported(self) -> None:
        failure = urllib.error.URLError(OSError(11001, "getaddrinfo failed"))
        self.http.queue(failure)

        with self.assertRaises(ApiConnectionError) as caught:
            client(self.http).charges.list()

        self.assertIsInstance(caught.exception, VeliraPayError)
        self.assertEqual("Could not reach the VeliraPay API: [Errno 11001] getaddrinfo failed", str(caught.exception))
        self.assertIs(failure, caught.exception.__cause__)

    def test_a_request_that_takes_too_long_is_reported(self) -> None:
        def slow(request: HttpRequest) -> ApiResponse:
            raise TimeoutError("timed out")

        velirapay = VeliraPayClient("vp_test_secret", transport=slow, max_retries=0, timeout=0.05)

        with self.assertRaisesRegex(
            ApiConnectionError, r"^Could not reach the VeliraPay API: no answer within 0.05 seconds.$"
        ):
            velirapay.charges.list()

    def test_a_connection_that_times_out_is_reported_the_same_way(self) -> None:
        self.http.queue(urllib.error.URLError(TimeoutError("timed out")))

        with self.assertRaisesRegex(ApiConnectionError, "no answer within 30 seconds."):
            client(self.http).charges.list()

    def test_an_error_the_transport_raises_for_another_reason_is_not_taken_for_a_network_error(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "No response was queued"):
            client(self.http, max_retries=2).charges.list()

        self.assertEqual(1, len(self.http.requests))

    def test_an_error_can_be_pickled_with_its_response(self) -> None:
        self.http.json({"message": "Too Many Attempts."}, 429, {"Retry-After": "42"})

        with self.assertRaises(RateLimitError) as caught:
            client(self.http).charges.list()

        restored = pickle.loads(pickle.dumps(caught.exception))

        self.assertIsInstance(restored, RateLimitError)
        self.assertEqual("Too Many Attempts.", str(restored))
        self.assertEqual(429, restored.status)
        self.assertEqual(42, restored.retry_after())


if __name__ == "__main__":
    unittest.main()
