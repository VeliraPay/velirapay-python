"""The default transport against a real HTTP server on this machine's loopback interface."""

from __future__ import annotations

import json
import socket
import threading
import time
import unittest
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, ClassVar

from velirapay import ApiConnectionError, InvalidRequestError, NotFoundError, VeliraPayClient

from .support import fixture

Answer = Callable[[BaseHTTPRequestHandler], None]


class _Server(ThreadingHTTPServer):
    """A server that answers each request with whatever the running test asks of it."""

    daemon_threads = True
    answer: Answer
    received: list[dict[str, Any]]

    def handle_error(self, request: Any, client_address: Any) -> None:
        """Stay quiet about clients that hung up, as the timeout test's does."""


class _RequestHandler(BaseHTTPRequestHandler):
    """Records each request, then answers it as the server says."""

    server: _Server

    def _respond(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        self.server.received.append(
            {
                "method": self.command,
                "path": self.path,
                "headers": {name.lower(): value for name, value in self.headers.items()},
                "body": self.rfile.read(length) if length else b"",
            }
        )
        self.server.answer(self)

    do_GET = do_POST = do_PATCH = do_PUT = do_DELETE = _respond

    def log_message(self, format: str, *args: Any) -> None:
        """Keep the test output clean."""


class UrllibTransportTest(unittest.TestCase):
    server: ClassVar[_Server]
    base_url: ClassVar[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = _Server(("127.0.0.1", 0), _RequestHandler)
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self) -> None:
        self.server.received = []

    def serve(self, answer: Answer) -> list[dict[str, Any]]:
        """Have the server answer the next requests this way, and return what it receives."""
        self.server.answer = answer

        return self.server.received

    def velirapay(self, *, max_retries: int = 0, timeout: float = 30, app_info: str | None = None) -> VeliraPayClient:
        return VeliraPayClient(
            "vp_test_secret", base_url=self.base_url, max_retries=max_retries, timeout=timeout, app_info=app_info
        )

    def test_a_request_and_its_answer_go_through_urllib(self) -> None:
        def answer(handler: BaseHTTPRequestHandler) -> None:
            content = json.dumps({"data": fixture("charge")}).encode()
            handler.send_response(201)
            handler.send_header("Content-Type", "application/json")
            handler.send_header("Idempotent-Replayed", "true")
            handler.send_header("Content-Length", str(len(content)))
            handler.end_headers()
            handler.wfile.write(content)

        received = self.serve(answer)
        velirapay = self.velirapay(max_retries=2, app_info="MyShop/2.1")

        charge = velirapay.charges.create(
            {"asset": "BTC", "amount": "150.00", "currency": "EUR", "description": "Zoë’s plan"},
            idempotency_key="order-1042",
        )

        self.assertEqual("k3v9x2m7q8wz", charge.id)
        response = velirapay.last_response()
        assert response is not None
        self.assertEqual(201, response.status)
        self.assertTrue(response.was_replayed())

        headers = received[0]["headers"]
        self.assertEqual("POST", received[0]["method"])
        self.assertEqual("/v1/charges", received[0]["path"])
        self.assertEqual("Bearer vp_test_secret", headers["authorization"])
        self.assertEqual("application/json", headers["accept"])
        self.assertEqual("application/json", headers["content-type"])
        self.assertEqual("order-1042", headers["idempotency-key"])
        self.assertTrue(headers["user-agent"].startswith("VeliraPay-Python/"))
        self.assertTrue(headers["user-agent"].endswith(" MyShop/2.1"))
        self.assertEqual(
            {"asset": "BTC", "amount": "150.00", "currency": "EUR", "description": "Zoë’s plan"},
            json.loads(received[0]["body"]),
        )

    def test_a_write_without_a_body_says_so(self) -> None:
        def answer(handler: BaseHTTPRequestHandler) -> None:
            content = json.dumps({"data": {**fixture("charge"), "status": "canceled"}}).encode()
            handler.send_response(200)
            handler.send_header("Content-Length", str(len(content)))
            handler.end_headers()
            handler.wfile.write(content)

        received = self.serve(answer)

        self.assertTrue(self.velirapay().charges.cancel("k3v9x2m7q8wz").is_canceled())
        self.assertEqual("POST", received[0]["method"])
        self.assertEqual("0", received[0]["headers"]["content-length"])
        self.assertNotIn("content-type", received[0]["headers"])

    def test_an_error_status_is_read_as_the_api_answered_it(self) -> None:
        def answer(handler: BaseHTTPRequestHandler) -> None:
            content = b'{"message":"No such object."}'
            handler.send_response(404)
            handler.send_header("Content-Type", "application/json")
            handler.send_header("Content-Length", str(len(content)))
            handler.end_headers()
            handler.wfile.write(content)

        received = self.serve(answer)

        with self.assertRaisesRegex(NotFoundError, "^No such object.$"):
            self.velirapay().charges.retrieve("k3v9x2m7q8wz")

        self.assertEqual("/v1/charges/k3v9x2m7q8wz", received[0]["path"])

    def test_a_redirect_is_not_followed(self) -> None:
        def answer(handler: BaseHTTPRequestHandler) -> None:
            handler.send_response(301)
            handler.send_header("Location", "https://elsewhere.example/v1/charges")
            handler.send_header("Content-Length", "0")
            handler.end_headers()

        received = self.serve(answer)

        with self.assertRaises(InvalidRequestError) as caught:
            self.velirapay().charges.list()

        self.assertEqual(301, caught.exception.status)
        self.assertEqual("https://elsewhere.example/v1/charges", caught.exception.header("Location"))
        self.assertEqual(1, len(received))

    def test_an_answer_that_takes_too_long_is_a_connection_error(self) -> None:
        def answer(handler: BaseHTTPRequestHandler) -> None:
            time.sleep(1)

        self.serve(answer)

        with self.assertRaisesRegex(ApiConnectionError, "no answer within 0.2 seconds."):
            self.velirapay(timeout=0.2).charges.list()

    def test_an_answer_cut_off_is_retried_then_a_connection_error(self) -> None:
        def answer(handler: BaseHTTPRequestHandler) -> None:
            handler.send_response(200)
            handler.send_header("Content-Type", "application/json")
            handler.send_header("Content-Length", "100")
            handler.end_headers()
            handler.wfile.write(b'{"data":')
            handler.close_connection = True

        received = self.serve(answer)
        velirapay = self.velirapay(max_retries=1)
        velirapay._requester._sleep = lambda seconds: None

        with self.assertRaisesRegex(ApiConnectionError, "IncompleteRead"):
            velirapay.charges.list()

        self.assertEqual(2, len(received))

    def test_a_refused_connection_is_a_connection_error(self) -> None:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]

        velirapay = VeliraPayClient("vp_test_secret", base_url=f"http://127.0.0.1:{port}", max_retries=0, timeout=5)

        with self.assertRaisesRegex(ApiConnectionError, "^Could not reach the VeliraPay API: "):
            velirapay.charges.list()


if __name__ == "__main__":
    unittest.main()
