"""Verifying and reading the webhooks VeliraPay sends."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from collections.abc import Sequence
from datetime import datetime
from typing import Final

from ._enums import Mode
from ._errors import InvalidArgumentError, SignatureVerificationError
from ._resources._base import ApiResource, boolean, mapping, nullable_string, record, string
from ._resources._base import timestamp as read_timestamp
from ._resources.charge import Charge, Transaction
from ._resources.invoice import Invoice
from ._resources.payout import Payout

# Unix time has ten digits until the year 2286, and int() refuses strings of more than 4,300.
_TIMESTAMP = re.compile(r"[0-9]{1,12}")

VERIFICATION_EVENT: Final = "webhook.verification"
"""The event of the challenge sent to an endpoint when it is added or moved: it receives nothing else until it answers."""


class Webhook:
    """Verifies and parses the webhooks VeliraPay sends."""

    SIGNATURE_HEADER: Final = "X-VeliraPay-Signature"
    """The header carrying the delivery's signature."""

    EVENT_HEADER: Final = "X-VeliraPay-Event"
    """The header carrying the event type."""

    DELIVERY_HEADER: Final = "X-VeliraPay-Delivery"
    """The header carrying the delivery's id."""

    DEFAULT_TOLERANCE: Final = 300
    """How many seconds a signature stays valid."""

    VERIFICATION_EVENT: Final = VERIFICATION_EVENT
    """The event of the challenge sent to an endpoint when it is added or moved: it receives nothing else until it answers."""

    @staticmethod
    def construct_event(
        payload: str | bytes,
        signature_header: str | Sequence[str] | None,
        secret: str,
        tolerance: int = DEFAULT_TOLERANCE,
    ) -> WebhookEvent:
        """Verify a delivery's signature and parse its payload.

        payload is the raw request body, exactly as received; signature_header the X-VeliraPay-Signature header; secret the
        endpoint's signing secret, starting with "whsec_"; and tolerance how many seconds old a signature may be, 0 for any age.
        """
        Webhook.verify_signature(payload, signature_header, secret, tolerance)

        return WebhookEvent.from_payload(payload)

    @staticmethod
    def verify_signature(
        payload: str | bytes,
        signature_header: str | Sequence[str] | None,
        secret: str,
        tolerance: int = DEFAULT_TOLERANCE,
        now: int | None = None,
    ) -> None:
        """Check that a payload was signed with the secret, recently. now is the current Unix time in seconds, for tests."""
        # Written this way round so that NaN is refused too.
        if not tolerance >= 0:
            raise InvalidArgumentError("The webhook signature tolerance cannot be negative.")

        if not isinstance(secret, str) or secret.strip() == "":
            raise InvalidArgumentError(
                "A webhook signing secret is required. Copy it from the webhook endpoint in the dashboard."
            )

        body = _raw(payload)
        header = ",".join(signature_header) if isinstance(signature_header, list | tuple) else signature_header

        if not isinstance(header, str) or header.strip() == "":
            raise SignatureVerificationError(f"The {Webhook.SIGNATURE_HEADER} header is missing.")

        signed_at: str | None = None
        signatures: list[str] = []

        for part in header.split(","):
            key, _, value = part.strip().partition("=")

            if key == "t" and signed_at is None:
                signed_at = value
            elif key == "v1" and value != "":
                signatures.append(value)

        if signed_at is None or not _TIMESTAMP.fullmatch(signed_at):
            raise SignatureVerificationError(f"The {Webhook.SIGNATURE_HEADER} header has no timestamp.")

        if not signatures:
            raise SignatureVerificationError(f"The {Webhook.SIGNATURE_HEADER} header has no v1 signature.")

        age = abs((int(time.time()) if now is None else now) - int(signed_at))

        if tolerance > 0 and age > tolerance:
            raise SignatureVerificationError(
                f"The signature is {age} seconds away from now, more than the {tolerance} allowed."
            )

        expected = _sign(body, secret, signed_at).encode("ascii")

        for signature in signatures:
            if hmac.compare_digest(expected, signature.encode("utf-8", "replace")):
                return

        raise SignatureVerificationError(
            "The signature does not match the payload. Check the signing secret and that the raw request body is passed unchanged."
        )

    @staticmethod
    def signature_header(payload: str | bytes, secret: str, timestamp: int | None = None) -> str:
        """Build the signature header VeliraPay would send with a payload, to test a webhook handler."""
        signed_at = str(int(time.time()) if timestamp is None else timestamp)

        return f"t={signed_at},v1={_sign(_raw(payload), secret, signed_at)}"


class WebhookEvent(ApiResource):
    """A webhook delivery's payload."""

    __slots__ = ()

    @staticmethod
    def from_payload(payload: str | bytes) -> WebhookEvent:
        """Read a delivery's raw body, without checking its signature."""
        try:
            decoded = json.loads(_raw(payload).decode("utf-8"))
        except (ValueError, RecursionError) as error:
            raise InvalidArgumentError(f"The webhook payload is not valid JSON: {error}") from error

        if not isinstance(decoded, dict):
            raise InvalidArgumentError("The webhook payload is not a JSON object.")

        return WebhookEvent(decoded)

    @property
    def id(self) -> str:
        """The delivery's id, also sent as the X-VeliraPay-Delivery header; retries keep it, but every endpoint's copy of an event has its own."""
        return string(self._attributes, "id")

    @property
    def event_id(self) -> str | None:
        """The event's id in the events API, the same on every endpoint's copy, so the one to skip duplicates by; None for test deliveries."""
        return nullable_string(self._attributes, "event_id")

    @property
    def type(self) -> str:
        """One of the EventType values, such as "charge.paid", or "webhook.verification"."""
        return string(self._attributes, "event")

    @property
    def mode(self) -> str:
        """Either "live" or "test"."""
        return string(self._attributes, "mode")

    @property
    def test(self) -> bool:
        """Whether this is a sample sent with the dashboard's "Send test event" button."""
        return boolean(self._attributes, "test")

    @property
    def created_at(self) -> datetime | None:
        """When the delivery was created."""
        return read_timestamp(self._attributes, "created_at")

    @property
    def charge(self) -> Charge | None:
        """The charge, for charge.* and payout.* events."""
        charge = record(mapping(self._attributes, "data"), "charge")

        return None if charge is None else Charge(charge)

    @property
    def invoice(self) -> Invoice | None:
        """The invoice, for invoice.* events."""
        invoice = record(mapping(self._attributes, "data"), "invoice")

        return None if invoice is None else Invoice(invoice)

    @property
    def transaction(self) -> Transaction | None:
        """The transfer the event is about, for charge.payment_detected and charge.late_payment."""
        transaction = record(mapping(self._attributes, "data"), "transaction")

        return None if transaction is None else Transaction(transaction)

    @property
    def payout(self) -> Payout | None:
        """The payout the event is about, for payout.* events."""
        payout = record(mapping(self._attributes, "data"), "payout")

        return None if payout is None else Payout(payout)

    def is_type(self, *types: str) -> bool:
        """Whether the event is of any of the given types, such as EventType.CHARGE_PAID."""
        return self.type in types

    def is_live_mode(self) -> bool:
        """Whether the event concerns real funds."""
        return self.mode == Mode.LIVE

    def is_verification(self) -> bool:
        """Whether this is the challenge VeliraPay sends when an endpoint is added or moved, to be answered with challenge_response()."""
        return self.is_type(VERIFICATION_EVENT)

    def challenge(self) -> str | None:
        """The value a verification delivery must be answered with, or None for every other delivery."""
        if not self.is_verification():
            return None

        challenge = mapping(self._attributes, "data").get("challenge")

        return challenge if isinstance(challenge, str) else None

    def challenge_response(self) -> str | None:
        """The JSON body that answers a verification delivery, or None for every other delivery."""
        challenge = self.challenge()

        return None if challenge is None else json.dumps({"challenge": challenge}, separators=(",", ":"))


def _raw(payload: object) -> bytes:
    """The bytes of a delivery's body, given as bytes or as a str."""
    if isinstance(payload, str):
        return payload.encode("utf-8")

    if isinstance(payload, bytes | bytearray | memoryview):
        return bytes(payload)

    raise InvalidArgumentError(
        "Pass the raw request body, as bytes or a str, exactly as received, rather than parsed JSON."
    )


def _sign(body: bytes, secret: str, timestamp: str) -> str:
    """The HMAC-SHA256, in hex, of "{timestamp}.{body}" under the secret."""
    return hmac.new(secret.encode("utf-8"), f"{timestamp}.".encode("ascii") + body, hashlib.sha256).hexdigest()
