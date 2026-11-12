# VeliraPay for Python

[![Tests](https://github.com/VeliraPay/velirapay-python/actions/workflows/tests.yml/badge.svg)](https://github.com/VeliraPay/velirapay-python/actions/workflows/tests.yml)
[![Latest version](https://img.shields.io/pypi/v/velirapay)](https://pypi.org/project/velirapay/)
[![License](https://img.shields.io/github/license/VeliraPay/velirapay-python)](https://github.com/VeliraPay/velirapay-python/blob/main/LICENSE)

The official Python library for [VeliraPay](https://velirapay.com), the crypto payment processor. It covers the v1 API (the coins on offer, charges, invoices, payment links, coupons, payouts, events, webhook endpoints and your account) and verifies the webhooks VeliraPay sends you. It is fully typed and has no dependencies.

- [Requirements](#requirements)
- [Installation](#installation)
- [Charging a customer](#charging-a-customer)
- [Verifying webhooks](#verifying-webhooks)
- [Which one to use](#which-one-to-use)
- [What the client covers](#what-the-client-covers)
- [Lists and pagination](#lists-and-pagination)
- [Errors](#errors)
- [Retries and idempotency](#retries-and-idempotency)
- [Test mode](#test-mode)
- [Configuration](#configuration)

The full API reference is at [velirapay.com/docs](https://velirapay.com/docs).

## Requirements

Python 3.11 or later. The library uses the standard library alone.

## Installation

```bash
pip install velirapay
```

## Charging a customer

Create an API key in the dashboard under **Developers → API keys**. Keep it on your server: anyone holding it can create charges and read your payments.

To charge a customer, create a charge with what you already know about them, and send them to its checkout page. With Flask:

```python
import os

from flask import Flask, redirect
from flask.typing import ResponseReturnValue
from velirapay import VeliraPayClient

app = Flask(__name__)
velirapay = VeliraPayClient(os.environ["VELIRAPAY_API_KEY"])


@app.post("/orders/1042/pay")
def pay() -> ResponseReturnValue:
    charge = velirapay.charges.create(
        {
            "amount": "49.90",
            "currency": "EUR",
            "asset": "BTC",
            "customer": {"email": "ada@example.com", "name": "Ada Lovelace"},
            "metadata": {"order_id": "1042"},
            "success_url": "https://example.com/orders/1042",
        },
        idempotency_key="order-1042",
    )

    assert charge.checkout_url is not None

    return redirect(charge.checkout_url, code=303)
```

They pay there, and VeliraPay tells your server about it with a [webhook](#verifying-webhooks). The exchange rate is locked when the charge is created, and the customer has 30 minutes to pay.

Parameters are a dict under the names the API gives them, as the [API reference](https://velirapay.com/docs) lists them. A key you leave out is not sent and a key set to `None` is sent as `null`, which is how a field is cleared; that difference is why they are not keyword arguments, and so is `from`, a Python keyword the activity log filters by. They are typed (`ChargeCreateParams` and so on), so your editor and type checker know every key. Enum members such as `Asset.BTC` can stand in for their values, and a `datetime`, a `date` or a `Decimal` is sent the way the API expects: a `datetime` in UTC, one without a time zone being taken as UTC already.

Objects come back with typed attributes: `charge.checkout_url`, `charge.asset_amount`, `charge.customer.ip_address`. Amounts are always strings, such as `"49.90"`, never floats, so no precision is lost; `Decimal(charge.asset_amount)` does arithmetic with them. Times are `datetime` objects in UTC, and a day such as `invoice.due_at` is a `date`. `checkout_url` is typed `str | None` because the charges in webhooks leave it out; a charge the API answers with always has one, which the `assert` tells your type checker.

A charge from your server comes from your server rather than the customer, so pass what you know about them as `customer` (`email`, `name`, `ip_address`, `user_agent`, `reference`, `phone`, `country` and `metadata`); it helps you spot fraud before you ship anything. `charge.customer` reads it back.

## Verifying webhooks

Add an endpoint in the dashboard under **Developers → Webhooks** and copy its signing secret (`whsec_…`). `Webhook.construct_event()` checks a delivery's signature and parses it. Pass it the **raw** body: a body parsed and encoded again no longer matches its signature. With Flask:

```python
import os

from flask import Flask, request
from flask.typing import ResponseReturnValue
from velirapay import SignatureVerificationError, Webhook

app = Flask(__name__)


@app.post("/webhooks/velirapay")
def velirapay_webhook() -> ResponseReturnValue:
    try:
        event = Webhook.construct_event(
            request.get_data(),
            request.headers.get(Webhook.SIGNATURE_HEADER),
            os.environ["VELIRAPAY_WEBHOOK_SECRET"],
        )
    except SignatureVerificationError:
        return "", 400

    # Sent when the endpoint is added or moved: it receives nothing else until it answers.
    challenge = event.challenge_response()

    if challenge is not None:
        return challenge, 200, {"Content-Type": "application/json"}

    # The same event can arrive more than once: remember this key, and skip the events you have handled.
    key = event.event_id or event.id

    if event.is_type("charge.paid") and event.charge is not None:
        ...  # Fulfil the order event.charge.metadata.get("order_id"), None for a charge made without one.

    return "", 200
```

With FastAPI, read the body as bytes before anything parses it:

```python
import os

from fastapi import FastAPI, Request, Response
from velirapay import SignatureVerificationError, Webhook

app = FastAPI()


@app.post("/webhooks/velirapay")
async def velirapay_webhook(request: Request) -> Response:
    try:
        event = Webhook.construct_event(
            await request.body(),
            request.headers.get(Webhook.SIGNATURE_HEADER),
            os.environ["VELIRAPAY_WEBHOOK_SECRET"],
        )
    except SignatureVerificationError:
        return Response(status_code=400)

    challenge = event.challenge_response()

    if challenge is not None:
        return Response(challenge, media_type="application/json")

    if event.is_type("charge.paid") and event.charge is not None:
        ...  # Fulfil the order event.charge.metadata.get("order_id"), None for a charge made without one.

    return Response(status_code=200)
```

In Django, the raw body is `request.body` and the header `request.headers.get(Webhook.SIGNATURE_HEADER)`.

Some things to know:

- **Answer the verification challenge.** When an endpoint is added, or its URL changes, VeliraPay sends it a signed `webhook.verification` delivery and sends it nothing else until it answers with HTTP 200 and the challenge, as `event.challenge_response()` gives it. Endpoint URLs must use `https://`.
- **A second signature for a day after a rotation.** For a day after you rotate the signing secret, the `X-VeliraPay-Signature` header carries a `v1` made with the old secret too, so a receiver that still has the old one keeps working. `construct_event()` accepts a delivery whichever `v1` matches.
- **Signatures expire.** A signature more than 5 minutes from the current time is rejected, which stops an intercepted delivery from being replayed. Change the limit with the `tolerance` argument, in seconds; `0` turns the age check off.
- **Answer quickly.** A delivery counts as delivered when your endpoint answers with a 2xx status within 15 seconds, so queue slow work. Redirects are not followed.
- **Failed deliveries are retried.** A delivery is tried 14 times over about 3 days.
- **Skip duplicates by event.** A retried delivery keeps its id (`event.id`), but each endpoint gets its own copy of an event under its own id. `event.event_id` is the same on every copy, so `event.event_id or event.id` is the key to remember.
- **Fulfil once.** A paid invoice sends both `charge.paid`, for the charge that paid it, and `invoice.paid`. Fulfil on one of them.
- **Deliveries can arrive out of order.** When the order matters, fetch the current state with `velirapay.charges.retrieve(event.charge.id)`.

`charge.payment_detected` arrives as soon as a transfer is seen, before it is confirmed: tell the customer, but do not fulfil. It and `charge.late_payment` carry that transfer as `event.transaction`; `payout.sent` and `payout.confirmed` carry the payout as `event.payout`.

To test your handler, sign a payload yourself: `Webhook.signature_header(payload, "whsec_test")` gives the header VeliraPay would send.

## Which one to use

| When | Use | |
| --- | --- | --- |
| You are asking one customer for one payment | A charge | The default. It has one checkout page for that one payment, with the rate locked for 30 minutes. |
| The customer should choose the coin, or pays later | An invoice | It needs their name and email, has no timer, can be itemised and reminded, and lets them pick the coin on its page. |
| Many customers pay through the same public page | A payment link, created once | A product sold again and again, a tip jar, a link on your site. |

Do not create a new payment link for each customer or each order.

A charge needs its coin up front, because its exchange rate, amount and deposit address depend on it. Ask the customer on your own page, and offer them the coins from `velirapay.assets.list()`, which also gives the lowest price each can be charged at.

## What the client covers

| Attribute | Methods |
| --- | --- |
| `charges` | `create`, `retrieve`, `list`, `iterator`, `send`, `cancel`, `accept`, `record_refund`, `simulate` |
| `invoices` | `create`, `retrieve`, `list`, `iterator`, `send`, `void` |
| `payment_links` | `create`, `retrieve`, `update`, `list`, `iterator`, `archive`, `restore` |
| `coupons` | `create`, `retrieve`, `update`, `list`, `iterator`, `delete` |
| `assets` | `list` |
| `payouts` | `retrieve` (by the charge's id), `list`, `iterator`, `summary` |
| `payout_addresses` | `list`, `update`, `delete` |
| `events` | `retrieve`, `list`, `iterator` |
| `webhook_endpoints` | `create`, `retrieve`, `update`, `delete`, `list`, `iterator`, `verify`, `test`, `rotate_secret`, `deliveries`, `retrieve_delivery`, `retry_delivery` |
| `account` | `retrieve`, `update`, `update_payment_settings` |
| `overview` | `retrieve` |
| `activity` | `list`, `iterator` |
| `api_keys` | `create`, `update`, `revoke`, `list`, `iterator` |
| `members` | `update`, `remove`, `list`, `iterator` |
| `invitations` | `create`, `cancel`, `list`, `iterator` |
| `billing` | `start_pro_payment` |

Each answers with an object such as a `Charge`. `get("field")` reads an attribute this version of the library does not know yet, and `to_dict()` gives the object as the API sent it, such as to store it. Status values are in enums, such as `ChargeStatus.PAID` and `Asset.USDT`, and objects have helpers such as `charge.is_paid()` and `event.is_type(EventType.CHARGE_PAID)`.

Most endpoints need a permission, which a key with full access has, except the sensitive ones, such as `webhook_endpoints:write` and `api_keys:write`: only a key made with them ticked has those. A key without the permission an endpoint needs gets a `PermissionDeniedError` naming it.

For an endpoint the library has no method for yet, send the request yourself: `velirapay.request("GET", "/v1/charges", {"per_page": 5})` answers with the response, whose `json()` decodes it.

## Lists and pagination

`list()` methods answer with one page, newest first (members oldest first). Pass `page` and `per_page` (up to 100, 25 by default):

```python
page = velirapay.charges.list({"status": "paid", "per_page": 100})

for charge in page:
    ...

page.total
page.has_more()
following = page.next_page()  # None on the last page
```

`iterator()` walks every page, fetching each one as it is reached:

```python
for charge in velirapay.charges.iterator({"status": "paid"}):
    ...
```

`assets.list()` answers with a single page holding every coin, and `payout_addresses.list()` and `payouts.summary()` with lists.

## Errors

A failed request raises an error carrying the API's message. They are all importable from `velirapay` and are all a `VeliraPayError`:

| Error | When |
| --- | --- |
| `AuthenticationError` | The API key is missing, wrong or revoked (401). |
| `PermissionDeniedError` | The API key may not do this (403): a restricted key without the permission the endpoint needs, or a key used from an IP address it does not allow. |
| `NotFoundError` | The object does not exist, or belongs to the other mode (404). |
| `ConflictError` | The object cannot make that change (409), such as canceling a charge that is no longer pending, or an idempotency key reused for a different request. |
| `ValidationError` | The request has invalid fields (422). `errors()` lists them by field, and `first_error("amount")` gives the first message for one. |
| `RateLimitError` | Too many requests (429). `retry_after()` says how many seconds to wait. |
| `ServerError` | VeliraPay had a problem (5xx). |
| `InvalidRequestError` | Any other 4xx, or a redirect, which is not followed. |
| `ApiConnectionError` | The API could not be reached, or its answer not read, after any retries. |
| `SignatureVerificationError` | A webhook's signature is missing, does not match, or is too old. |
| `InvalidArgumentError` | The library was given something it cannot use, such as an API key that does not start with `vp_live_` or `vp_test_`. It is a `ValueError` too. |

Every error from an API answer is an `ApiError`, with `status`, `body` (the decoded response), `header(name)` and `retry_after()`.

```python
from velirapay import ApiError, ValidationError

try:
    velirapay.charges.create({"amount": "0", "currency": "EUR", "asset": "BTC"})
except ValidationError as error:
    error.errors()  # {"amount": ["…"]}
except ApiError as error:
    error.status
```

## Retries and idempotency

Requests that fail with a network error, a rate limit (429) or an outage (502, 503, 504) are tried again up to twice, waiting a little longer each time, or as long as the API's `Retry-After` header asks. A 500 is retried for reads only, since a write may have been carried out. A `Retry-After` longer than `max_retry_after` (10 seconds unless [configured](#configuration) otherwise) is not waited out: the error is raised straight away, and its `retry_after()` says how long to wait.

While retries are on, each write carries an `Idempotency-Key` header, so the API carries out a retried request once. The library makes up a key per call; pass your own, such as an order number, to make a call safe to repeat across processes:

```python
charge = velirapay.charges.create(params, idempotency_key="order-1042")
```

For 24 hours, a request repeating a key gets the first successful response, and `velirapay.last_response().was_replayed()` is then true. Reusing a key with a different body raises a `ConflictError`. A key covers one account, one mode, one method and one path, and is at most 255 characters.

Three answers carry a secret that is shown once and never kept, so they cannot be replayed: the key that `api_keys.create()` makes, and the signing secret of `webhook_endpoints.create()` and `rotate_secret()`. Repeating one of these, which a retry after a lost answer does, raises a `ConflictError` whose `was_replayed()` is true. The write was carried out, but its secret is gone:

- **`api_keys.create()`**: the key exists. Find it with `api_keys.list()`, revoke it, and create another.
- **`webhook_endpoints.create()`**: the endpoint exists with a secret nobody holds. Rotate its secret, since nothing depends on it yet, or delete the endpoint and add it again.
- **`webhook_endpoints.rotate_secret()`**: the secret was rotated, and the one your receiver has keeps signing for a day. Rotate again only when you can put the new secret into the receiver straight away: only one earlier secret is kept, so a second rotation stops the receiver's from signing at once.

```python
from velirapay import ConflictError

try:
    endpoint = velirapay.webhook_endpoints.create(
        {"url": "https://example.com/webhooks/velirapay", "events": ["charge.paid"]},
        idempotency_key="endpoint-1",
    )
except ConflictError as error:
    if not error.was_replayed():
        raise

    ...  # The endpoint was added, but its secret is lost: rotate it.
```

## Test mode

Keys starting with `vp_test_` work in test mode: charges are paid with test coins on each chain's test network, and nothing touches real funds. Test and live objects are fully separate, and each mode has its own webhooks.

```python
velirapay.is_test_mode()  # read from the key's prefix

# Pay a test charge without any coins: it becomes paid, and the webhooks go out as for a real payment.
velirapay.charges.simulate("k3v9x2m7q8wz")
velirapay.charges.simulate("k3v9x2m7q8wz", {"amount": "0.001"})  # less than is due, to try an underpayment
```

## Configuration

```python
velirapay = VeliraPayClient(
    os.environ["VELIRAPAY_API_KEY"],
    max_retries=2,          # 0 turns retries off
    max_retry_after=10,     # the longest Retry-After, in seconds, waited out before trying again
    timeout=30,             # seconds an attempt may wait to connect, and each time it waits for more of the answer
    app_info="MyShop/2.1",  # added to the User-Agent
)
```

Requests go through `urllib` from the standard library, which follows the `HTTPS_PROXY` and `NO_PROXY` environment variables. To trust other certificates, pass `transport=UrllibTransport(ssl_context=...)`. Any callable that takes an `HttpRequest` and answers with an `ApiResponse` can be the `transport`, such as one that sends requests through your own HTTP client or one that answers your tests; it raises an `OSError` when the API cannot be reached, which is retried like any network error.

A client can be shared between threads, and `last_response()` gives the response to the most recent request of the thread that asks. The client is synchronous; from async code, run its calls in a thread, such as with `await asyncio.to_thread(velirapay.charges.create, params)`.

## Development

```bash
python -m pip install -e . --group dev
python -m unittest   # the tests
mypy                 # the types, in strict mode
ruff format --check && ruff check
```

## License

MIT. See [LICENSE](https://github.com/VeliraPay/velirapay-python/blob/main/LICENSE).
