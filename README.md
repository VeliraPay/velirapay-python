# VeliraPay for Python

[![Tests](https://github.com/VeliraPay/velirapay-python/actions/workflows/tests.yml/badge.svg)](https://github.com/VeliraPay/velirapay-python/actions/workflows/tests.yml)
[![Latest version](https://img.shields.io/pypi/v/velirapay)](https://pypi.org/project/velirapay/)
[![License](https://img.shields.io/github/license/VeliraPay/velirapay-python)](https://github.com/VeliraPay/velirapay-python/blob/main/LICENSE)

The official Python library for [VeliraPay](https://velirapay.com), the crypto payment processor. It covers the whole v1 API: the coins on offer, charges, invoices, payment links, coupons, payouts and payout addresses, events, webhook endpoints, your account and its payment settings, the overview, the activity log, API keys, members and invitations, and paying for Pro. It also verifies the webhooks VeliraPay sends you. It is fully typed and has no dependencies.

- [Requirements](#requirements)
- [Installation](#installation)
- [Charging a customer](#charging-a-customer)
- [Which one to use](#which-one-to-use)
- [Supported coins](#supported-coins)
- [Charges](#charges)
- [Invoices](#invoices)
- [Payment links](#payment-links)
- [Coupons](#coupons)
- [Payouts](#payouts)
- [Events](#events)
- [Webhooks](#webhooks)
- [Webhook endpoints](#webhook-endpoints)
- [Your account](#your-account)
- [What the client covers](#what-the-client-covers)
- [Lists and pagination](#lists-and-pagination)
- [Constants](#constants)
- [Errors](#errors)
- [Retries and idempotency](#retries-and-idempotency)
- [Test mode](#test-mode)
- [Configuration](#configuration)
- [Testing your integration](#testing-your-integration)

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

They pay there, and VeliraPay tells your server about it with a [webhook](#webhooks). The exchange rate is locked when the charge is created, and the customer has 30 minutes to pay.

Parameters are a dict under the names the API gives them, as the [API reference](https://velirapay.com/docs) lists them. A key you leave out is not sent and a key set to `None` is sent as `null`, which is how a field is cleared; that difference is why they are not keyword arguments, and so is `from`, a Python keyword the activity log filters by. They are typed (`ChargeCreateParams` and so on), so your editor and type checker know every key. [Enum members](#constants) such as `Asset.BTC` can stand in for their values, and a `datetime`, a `date` or a `Decimal` is sent the way the API expects: a `datetime` in UTC, one without a time zone being taken as UTC already.

Objects come back with typed attributes: `charge.checkout_url`, `charge.asset_amount`, `charge.customer.ip_address`. Amounts are always strings, such as `"49.90"`, never floats, so no precision is lost; `Decimal(charge.asset_amount)` does arithmetic with them. Times are `datetime` objects in UTC, and a day such as `invoice.due_at` is a `date`. `checkout_url` is typed `str | None` because the charges in webhooks leave it out; a charge the API answers with always has one, which the `assert` tells your type checker.

Amounts you send are best given as strings or `Decimal`s too. A number is sent as a decimal string, a float rounded to 14 significant digits first, the precision the API reads a number with: `0.00005` goes out as `"0.00005"`, and `0.1 + 0.2` as `"0.3"`.

Each group of endpoints is an attribute of the client, such as `velirapay.charges`, and answers with an object such as a `Charge`. `get("field")` reads an attribute this version of the library does not know yet, and `to_dict()` gives the object as the API sent it, such as to store it.

## Which one to use

| When | Use | |
| --- | --- | --- |
| You are asking one customer for one payment | A [charge](#charges) | The default. It has one checkout page for that one payment, with the rate locked for 30 minutes. |
| The customer should choose the coin, or pays later | An [invoice](#invoices) | It needs their name and email, has no timer, can be itemised and reminded, and lets them pick the coin on its page. |
| Many customers pay through the same public page | A [payment link](#payment-links), created once | A product sold again and again, a tip jar, a link on your site. |

Do not create a new payment link for each customer or each order.

A charge needs its coin up front, because its exchange rate, amount and deposit address depend on it. Ask the customer on your own page, and offer them the coins from [`velirapay.assets.list()`](#supported-coins).

## Supported coins

`assets.list()` gives the coins that can be paid in the key's mode, whether your account takes each, and the lowest price a charge in each can have.

```python
from velirapay import Currency

coins = velirapay.assets.list({"currency": Currency.EUR})

for coin in coins:
    coin.id                 # "USDT": what to pass as asset, and coin.asset() is the Asset member
    coin.name               # "Tether USD"
    coin.network            # "Ethereum (ERC-20)", the network the customer has to send it on
    coin.accepted           # whether your account takes it, which needs a payout address for that network
    coin.minimum_amount     # "10", in the coin, or None when it has no minimum of its own
    coin.minimum_price      # "8.71", the lowest price in EUR right now
    coin.exchange_rate      # "0.8709"
    coin.confirmation_wait  # "about a minute"
    coin.network_surcharge  # None, or what a charge in it asks on top of the price, in the coin

coins.currencies  # ["USD", "EUR", "GBP", "CAD", "AUD", "CHF", "TRY"], the currencies prices can be asked in
```

Without `currency`, prices are in your account's default currency. The list is not paged.

No charge, payment link or invoice asks for less than the lowest price of its currency, about half a dollar: 0.50 in USD, EUR, GBP and CHF, 0.70 in CAD, 0.80 in AUD and 25.00 in TRY. A few coins start higher: USDT and USDC on Ethereum at 10 of the token, because paying one out costs enough in gas that a smaller payment would leave you with little. A coin's minimum is in the coin, so `minimum_price` moves a little with the market: leave some room. `charges.create()` raises a `ValidationError` on `amount` below the lowest price, and on `asset` below a coin's minimum.

A coin with a `network_surcharge`, such as USDT on Tron, asks the customer for that much more than the price, to pay for passing the payment on, so tell them before they choose it. VeliraPay keeps it: it is not part of your payout, and no refund can include it. A charge in such a coin counts it in `asset_amount` and gives it again as `charge.network_surcharge`.

## Charges

A charge is how you ask a customer for a payment, in one coin. The exchange rate is locked when it is created, and the customer has 30 minutes to pay.

```python
from datetime import date

from velirapay import Asset, ChargeStatus, Currency

# For an amount you set, with whatever you already know.
charge = velirapay.charges.create(
    {
        "amount": "150.00",
        "currency": Currency.USD,
        "asset": Asset.USDC,  # USD Coin on Ethereum
        "description": "Pro plan, 1 year",
        "metadata": {"order_id": "1042"},
        "customer": {"email": "ada@example.com", "name": "Ada Lovelace"},
        "custom_fields": [{"label": "Company", "value": "Analytical Engines"}],  # shown with the charge in the dashboard
        "success_url": "https://example.com/orders/1042",  # a button back once they have paid
        "cancel_url": "https://example.com/cart",  # a link back from the checkout
        "success_message": "Thank you, your licence is on its way.",  # on the page and in the receipt
        "send_email": True,  # email them the payment page straight away
    }
)

# For one of your payment links: the currency comes from the link, and so does the price when it is fixed.
charge = velirapay.charges.create({"payment_link": "p4n8r2t6y1ua", "asset": Asset.ETH})

# With one of your coupons: fiat_amount is the lower price, and discount_amount what the coupon took off.
charge = velirapay.charges.create({"payment_link": "p4n8r2t6y1ua", "asset": Asset.ETH, "coupon": "SPRING10"})
charge.coupon           # "SPRING10"
charge.discount_amount  # "15.00"

charge = velirapay.charges.retrieve("k3v9x2m7q8wz")

charge.status           # "pending", "underpaid", "paid", "expired" or "canceled"
charge.is_paid()
charge.asset_amount     # "0.0025", what the customer has to send
charge.received_amount  # what arrived so far
charge.deposit_address
charge.transactions     # the transfers seen, as Transaction objects
charge.metadata         # {"order_id": "1042"}

paid = velirapay.charges.list({"status": ChargeStatus.PAID})
hers = velirapay.charges.list({"search": "ada@example.com", "created_from": date(2026, 10, 1), "asset": Asset.BTC})

# Email the customer the payment page, if you did not pass send_email.
velirapay.charges.send("k3v9x2m7q8wz")

# Only while the charge is pending and no transfer to it has been seen.
velirapay.charges.cancel("k3v9x2m7q8wz")
```

`send()` needs a customer email and only works while the charge is pending, or it raises a `ConflictError`. Creating a charge with `send_email` but no customer email raises a `ValidationError` on `customer_email` and creates nothing. A charge can be emailed once every 10 minutes, and the emails count towards the limits under [Invoices](#invoices). In test mode, charge emails can only go to members of your account.

`asset` takes an `Asset` member or its value, such as `"BTC"`. The enum lists every coin the API knows, but not all of them can be paid in at any given time: a coin is only offered while VeliraPay can also pay it out, and a network can be switched off. `account.accepted_assets` lists the coins your account takes right now ([Your account](#your-account)); a charge in any other coin raises a `ValidationError`. The coins of BNB Chain, Base, Arbitrum One and Polygon can only be used with a live key.

A charge in `BTC_LIGHTNING`, Bitcoin over Lightning when it is on offer, is paid with a Lightning invoice: `charge.payment_request` is the BOLT11 invoice to show the customer, as a `lightning:` link or a QR code, and `charge.deposit_address` its payment hash. `payment_request` is `None` for every other coin.

`metadata` holds up to 20 keys of at most 40 characters each. Values are strings, numbers, booleans or `None`, and a string is at most 500 characters.

The accounts of one owner can create 300 charges in each mode within 30 minutes, through the API, the MCP server and the dashboard together, and 30 until one of them has been paid in live mode. Canceled charges count, paid live ones do not, and payments customers start on the hosted checkout are not counted. Past that, `create()` raises a `RateLimitError` whose `retry_after()` says how many seconds to wait.

### Customer details

`charge.customer` holds what is known about who pays, to help you spot fraud before you ship anything. When the customer starts the payment on the hosted checkout, VeliraPay records the IP address and browser they did it from. A charge you create from your server comes from your server rather than the customer, so pass what you know:

```python
charge = velirapay.charges.create(
    {
        "amount": "150.00",
        "currency": "USD",
        "asset": "BTC",
        "customer": {
            "email": "ada@example.com",
            "name": "Ada Lovelace",
            "ip_address": "203.0.113.7",  # the customer's, from their request to your server
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15",
            "reference": "cus_1042",  # your own id for the customer
            "phone": "+44 20 7946 0958",
            "country": "GB",  # ISO 3166 two-letter code
            "metadata": {"orders": 7},  # the same limits as the charge's metadata
        },
    }
)

charge.customer.ip_address  # "203.0.113.7"
charge.customer.user_agent
charge.customer.country     # "GB"
charge.customer.metadata    # {"orders": 7}
```

Every field is optional, and any other key is refused with a `ValidationError`. The older `customer_email` parameter still works.

### Short and late payments

A customer who sends less than a charge asks for leaves it `underpaid`, announced with `charge.underpaid`. One who pays after the rate lock ran out, to an expired or canceled charge or as a top-up to an underpaid one, makes a late payment, announced with `charge.late_payment`. Both wait for you to decide; a late payment on top of a paid charge is counted on its own.

```python
# Settle an underpaid charge, or a late payment on an expired or canceled one, for what arrived and confirmed.
velirapay.charges.accept("k3v9x2m7q8wz")

# Record a refund you sent from your own wallet, in the charge's coin.
velirapay.charges.record_refund("k3v9x2m7q8wz", {"amount": "0.0005", "txid": "7d1c5e9a…", "reason": "Returned item"})
```

`accept()` raises a `ConflictError` while a payment to an underpaid charge is still confirming, and for a charge that is neither underpaid nor late. VeliraPay never sends money back on its own: `record_refund()` records a refund you made yourself, and tells the customer by email when the charge has their address. An underpaid charge or a late payment has to be accepted before it can be refunded, and the network surcharge never can be.

## Invoices

An invoice is a bill with a hosted page, where the customer pays in the coin of their choice. Use it for a bill to pay later, or when the customer should choose the coin.

```python
from datetime import date, timedelta

invoice = velirapay.invoices.create(
    {
        "customer_name": "Grace Hopper",
        "customer_email": "grace@example.com",
        "currency": "USD",
        "items": [
            {"description": "Consulting", "quantity": "10", "unit_amount": "100.00"},
            {"description": "Hosting", "quantity": "1", "unit_amount": "250.00"},
        ],
        "due_at": date.today() + timedelta(days=14),
        "send_email": True,
    }
)

invoice.number      # "INV-0042"
invoice.hosted_url  # the page where the customer pays

velirapay.invoices.send(invoice.id)  # email it, or send a reminder
velirapay.invoices.void(invoice.id)

overdue = velirapay.invoices.list({"overdue": True})
hers = velirapay.invoices.list({"search": "grace@example.com"})
```

Pass `amount` instead of `items` to bill a single total. Either way the invoice comes to at least the lowest price of its currency, though its items may each cost less.

An invoice can be emailed once every 10 minutes, and an account can send 100 emails to customers an hour, 10 until one of its owner's accounts has been paid in live mode: invoices, charges emailed to their customers and refund notices together, shared with the other accounts its owner owns. Past either limit, `send()` raises a `RateLimitError` whose `retry_after()` says how many seconds to wait, and `create()` with `send_email` raises it and creates nothing. In test mode, invoices are only emailed to members of your account: anyone else is refused with a `ValidationError` on `customer_email`, by `send()` as by `create()` with `send_email`.

## Payment links

A payment link is one reusable public checkout page, for a fixed price or one the customer chooses, opened by many customers who each pick their own coin. Create it once and share it. To charge one customer, [create a charge](#charges) instead.

```python
from velirapay import Asset, PaymentLinkStatus, PricingType

link = velirapay.payment_links.create(
    {
        "title": "Pro plan",
        "pricing_type": PricingType.FIXED,
        "amount": "150.00",
        "currency": "EUR",
        "accepted_assets": [Asset.BTC, Asset.ETH, Asset.USDC],  # None accepts every coin the account takes
        "success_url": "https://example.com/thanks",
        "custom_fields": [{"label": "Company", "required": False}],
    }
)

link.checkout_url  # "https://velirapay.com/pay/…"

tip_jar = velirapay.payment_links.create(
    {
        "title": "Tip jar",
        "pricing_type": PricingType.OPEN,
        "currency": "USD",
        "suggested_amounts": ["5.00", "10.00", "25.00"],
        "min_amount": "1.00",
    }
)

velirapay.payment_links.update(link.id, {"title": "Pro plan (yearly)"})
velirapay.payment_links.archive(link.id)  # stops taking payments
velirapay.payment_links.restore(link.id)

existing = velirapay.payment_links.list({"status": PaymentLinkStatus.ACTIVE, "search": "Pro plan"})
```

## Coupons

A coupon takes a percentage or a fixed amount off a payment. Customers type its code on the hosted checkout of a payment link, you add it to the link's URL so it is already applied (`https://velirapay.com/pay/p4n8r2t6y1ua?coupon=SPRING10`), or you pass it as `coupon` when you [create a charge](#charges).

```python
from datetime import date

coupon = velirapay.coupons.create(
    {
        "code": "SPRING10",  # 3 to 32 letters, digits, dashes or underscores, stored in capitals
        "percent_off": "10",  # or "amount_off": "5.00" with a "currency"
        "max_redemptions": 100,  # an open charge holds a use until it is paid, expires or is canceled
        "once_per_customer": True,  # the customer's email is then required to use it
        "payment_links": ["p4n8r2t6y1ua"],  # empty for every link, and charges made without one
        "expires_at": date(2026, 12, 31),  # a day ends at 23:59:59 UTC
    }
)

coupon.id              # "SPRING10": the code is the id, and is matched in any case
coupon.times_redeemed  # how many paid charges used it

velirapay.coupons.update("SPRING10", {"active": False})  # pause it
velirapay.coupons.delete("SPRING10")  # charges that used it keep its code and their discount

found = velirapay.coupons.list({"search": "spring"})
```

`currency` is required with `amount_off` or `min_amount`, and the coupon then only works on payments in that currency. Once a coupon exists, its code, discount, currency and `min_amount` cannot change: `update()` takes `max_redemptions`, `once_per_customer`, `payment_links` (which replaces the whole list), `active` and `expires_at`.

A coupon that cannot be used raises a `ValidationError` on `coupon` from `charges.create()`, saying why: it does not exist in this mode, is paused, has expired, is limited to other links, is for another currency, needs a higher price, would leave nothing to pay or is used up, or it is once per customer and the charge has no customer email or that customer already used it.

## Payouts

Every paid charge has one payout: what came in, what was kept, what you are owed, what actually landed and the transaction that carried it. These only read: payouts go out on their own, and nothing here can raise, redirect or reverse one.

```python
from velirapay import Asset, PayoutStatus

payout = velirapay.payouts.retrieve("k3v9x2m7q8wz")  # by the charge's id; a NotFoundError until it is paid

payout.status         # "pending", "sending", "sent", "failed" or "manual"
payout.is_sent()      # confirmed: the money is in your wallet
payout.gross_amount   # what the customer paid
payout.fee_amount     # what was kept
payout.net_amount     # what you are owed, before the chain's own fee
payout.network_fee    # what the chain charged
payout.sent_amount    # what therefore reached you
payout.payout_txid    # the transaction, and payout.explorer_url its page on a block explorer
payout.last_error     # why the last try did not work, or why it is held
payout.next_attempt_at

failed = velirapay.payouts.list({"status": PayoutStatus.FAILED})
tether = velirapay.payouts.list({"asset": Asset.USDT, "search": "0x9a4f"})  # a charge id or a transaction hash

summary = velirapay.payouts.summary()

for row in summary:
    row.asset                # one row per coin you have been paid in
    row.paid_out_amount      # what has reached you
    row.in_flight_amount     # what is on its way
    row.owed_amount          # what has not left yet
    row.fee_amount
    row.waiting_for_address  # how many payouts wait for you to give an address

summary.mode  # "live" or "test"
```

### Payout addresses

Payouts go to one address per network family rather than per coin: one Ethereum-style address (`evm`) takes ETH, USDT and USDC on Ethereum, and BNB Chain, Base, Arbitrum One and Polygon each have their own, so nobody is paid on a chain they did not choose. A payout in a coin whose family has no address waits for one, and is never lost.

```python
from velirapay import AddressNetwork

addresses = velirapay.payout_addresses.list()  # needs payout_addresses:read

for address in addresses:
    address.network             # "bitcoin", "evm", …: an AddressNetwork value
    address.address             # None while there is none: payouts in its coins wait for one
    address.assets              # the coins on offer on that network
    address.payouts_held_until  # until when payouts to a newly saved address wait

addresses.api_payout_address_changes  # whether an owner lets API keys and AI apps change them

velirapay.payout_addresses.update(AddressNetwork.BITCOIN, {"address": "bc1q…"})
velirapay.payout_addresses.delete(AddressNetwork.SOLANA)
```

`list()` answers with a `PayoutAddressList`: a list with one entry per family on offer in the key's mode, which also has `mode` and `api_payout_address_changes`. Changing an address needs the sensitive `payout_addresses:write` permission and an owner switching on "Let API keys and AI apps change payout addresses" under Payment settings; until then `update()` and `delete()` raise a `PermissionDeniedError` saying so. Owners and admins are emailed about every change, and once the account has been paid out, payouts to a new address wait 48 hours.

## Events

Every change to a charge or an invoice is recorded as an event, such as `charge.paid` or `invoice.viewed`. Webhooks carry the same events.

```python
from velirapay import EventType

events = velirapay.events.list({"charge": "k3v9x2m7q8wz"})
payments = velirapay.events.list({"type": EventType.CHARGE_PAYMENT_DETECTED})

event = velirapay.events.retrieve("9b1f7a3e-2c4d-4e8f-a6b0-1d2c3e4f5a6b")
event.is_type(EventType.CHARGE_PAID)
event.details  # what was recorded, such as the amount and txid of a payment or a refund
event.charge   # the charge as it is now, without its timeline
```

## Webhooks

Add an endpoint in the dashboard under **Developers → Webhooks**, or [with the API](#webhook-endpoints), and keep its signing secret (`whsec_…`). Each delivery is a POST with a JSON body and these headers:

| Header | |
| --- | --- |
| `X-VeliraPay-Signature` | `t={timestamp},v1={signature}` |
| `X-VeliraPay-Event` | The event type, such as `charge.paid` |
| `X-VeliraPay-Delivery` | The delivery's id |

`Webhook.construct_event()` checks a delivery's signature and parses it. Pass it the **raw** body: a body parsed and encoded again no longer matches its signature. With Flask:

```python
import os

from flask import Flask, request
from flask.typing import ResponseReturnValue
from velirapay import EventType, SignatureVerificationError, Webhook

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

    if event.is_type(EventType.CHARGE_PAID) and event.charge is not None:
        # None for a charge made without one, such as through a payment link.
        order_id = event.charge.metadata.get("order_id")

        # A test-mode payment moved no real money: never ship anything for it.
        if event.is_live_mode() and order_id is not None:
            ...  # Fulfil the order.

    return "", 200
```

With FastAPI, read the body as bytes before anything parses it:

```python
import os

from fastapi import FastAPI, Request, Response
from velirapay import EventType, SignatureVerificationError, Webhook

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

    if event.is_type(EventType.CHARGE_PAID) and event.charge is not None and event.is_live_mode():
        order_id = event.charge.metadata.get("order_id")  # None for a charge made without one
        ...  # Fulfil the order.

    return Response(status_code=200)
```

In Django, the raw body is `request.body` and the header `request.headers.get(Webhook.SIGNATURE_HEADER)`.

Some things to know:

- **Answer the verification challenge.** When an endpoint is added, or its URL changes, VeliraPay sends it a signed `webhook.verification` delivery and sends it nothing else until it answers with HTTP 200 and the challenge, as `event.challenge_response()` gives it. Endpoint URLs must use `https://`.
- **Test mode has its own deliveries.** Each mode has its own endpoints, and `event.mode` says which a delivery belongs to. A handler that serves both, or a URL added in both, should check `event.is_live_mode()` before it ships anything.
- **Read your metadata defensively.** A charge has the metadata it was created with, so one made through a payment link, or without your `order_id`, has none: `event.charge.metadata.get("order_id")` is then `None`.
- **A second signature for a day after a rotation.** For a day after you rotate the signing secret, the `X-VeliraPay-Signature` header carries a `v1` made with the old secret too, so a receiver that still has the old one keeps working. `construct_event()` accepts a delivery whichever `v1` matches.
- **Signatures expire.** A signature more than 5 minutes from the current time is rejected, which stops an intercepted delivery from being replayed. Change the limit with the `tolerance` argument, in seconds; `0` turns the age check off.
- **Answer quickly.** A delivery counts as delivered when your endpoint answers with a 2xx status within 15 seconds, so queue slow work. Redirects are not followed, so a 3xx counts as a failure: give the endpoint's final URL.
- **Failed deliveries are retried.** A delivery is tried 14 times over about 3 days: after 1 minute, 5 minutes, 30 minutes, 1 hour, 2 hours, 4 hours and 8 hours, then every 10 hours. When one runs out of attempts, the account's owners and admins are emailed, at most once a day per endpoint, and an endpoint that fails 15 deliveries in a row is switched off until you switch it back on. The endpoint's delivery log keeps every attempt for 30 days, and can send a delivery again.
- **Skip duplicates by event.** A retried delivery keeps its id (`event.id`, also the `X-VeliraPay-Delivery` header), but each endpoint gets its own copy of an event under its own id. `event.event_id` is the same on every copy and is the event's id in the events API, so `event.event_id or event.id` is the key to remember.
- **Fulfil once.** A paid invoice sends both `charge.paid`, for the charge that paid it, and `invoice.paid`. Fulfil on one of them, not both.
- **Deliveries can arrive out of order.** When the order matters, fetch the current state with `velirapay.charges.retrieve(event.charge.id)` rather than trusting the payload.
- **Test deliveries.** `webhook_endpoints.test()` and the dashboard's "Send test event" button send a sample `charge.paid` with `event.test` set to `True` and no `event_id`. Its charge is a made-up sample without many of a real one's fields, such as `transactions` and `customer`.

`charge.payment_detected` arrives as soon as a transfer to a charge is seen, before it is confirmed: tell the customer, but do not fulfil. It and `charge.late_payment` carry that transfer as `event.transaction` (`txid`, `amount`, `confirmations`, `required_confirmations`, `credited`, `explorer_url`, `seen_at`); for every other event it is `None`.

`payout.sent` arrives when your share of a paid charge has been broadcast, and `payout.confirmed` when the chain has confirmed it. Both carry the charge as `event.charge` and the payout as `event.payout`, the same object `velirapay.payouts.retrieve()` answers with. Book the money on `payout.confirmed`: a broadcast payout can still be dropped and go out again, so `payout.sent` can arrive more than once for a charge, and the `payout_txid` that counts is the one in `payout.confirmed`.

The charge and invoice in a delivery are not quite the ones the API answers with:

- A charge's coin amounts and exchange rate carry all 18 decimal places (`"0.002500000000000000"` rather than `"0.0025"`). Compare amounts as numbers, such as with `Decimal`, not as strings.
- A charge has no `timeline`, `refunds`, `checkout_url`, `receipt_url`, `success_url`, `cancel_url` or `success_message`. Its payment link and invoice carry more than their codes: `charge.payment_link_title` and `charge.invoice_number`, which are `None` on the charges the API answers with.
- An invoice has no `overdue` or `document_url`; both are `None`.
- `charge.refunded` carries no refund. Read its amount, txid and reason from the event, with `velirapay.events.retrieve(event.event_id).details`.

Fetch the object when you need what a delivery leaves out. The charges that events carry, in the events API, have no `timeline` either.

## Webhook endpoints

List them to see from your code why deliveries are not arriving:

```python
from velirapay import WebhookDeliveryStatus

for endpoint in velirapay.webhook_endpoints.list():
    endpoint.url
    endpoint.events                   # the event types it takes
    endpoint.active
    endpoint.verified                 # it receives nothing until it has answered the challenge
    endpoint.is_receiving()           # both of those
    endpoint.deliveries_count         # of the last 30 days
    endpoint.failed_deliveries_count

for delivery in velirapay.webhook_endpoints.deliveries("12", {"status": WebhookDeliveryStatus.FAILED}):
    delivery.event            # "charge.paid"
    delivery.response_status  # what the endpoint last answered
    delivery.error
```

Retrieve one delivery to see every attempt to send it, the latest first, and the JSON body it carried:

```python
delivery = velirapay.webhook_endpoints.retrieve_delivery("12", "9d2e0b8a-6c1f-4e3a-8b7d-5f3a2c1e0d9b")

for attempt in delivery.attempt_log:
    attempt.request_headers   # the signatures cut out, the timestamp they signed kept
    attempt.response_status   # None when nothing answered
    attempt.response_headers  # a few dozen at most, never cookies
    attempt.response_body     # the first 2,000 characters
    attempt.duration_ms
    attempt.error             # such as a timeout

delivery.payload  # the JSON body, or None for a key without events:read
```

A key with the sensitive `webhook_endpoints:write` permission ticked can also add and change them, up to 10 in each mode. A new endpoint is sent its verification challenge at once, and the answer that adds it, or rotates its secret, is the only one that carries the signing secret:

```python
from velirapay import EventType

endpoint = velirapay.webhook_endpoints.create(
    {"url": "https://example.com/webhooks/velirapay", "events": [EventType.CHARGE_PAID, EventType.INVOICE_PAID]}
)

endpoint.secret              # "whsec_…", store it now: it is never returned again
endpoint.verification_error  # None once the endpoint answered the challenge

velirapay.webhook_endpoints.update("12", {"active": False})
velirapay.webhook_endpoints.verify("12")  # send the challenge again
velirapay.webhook_endpoints.test("12")    # a sample charge.paid, marked test

rotated = velirapay.webhook_endpoints.rotate_secret("12")
rotated.secret                      # the new one, shown this once
rotated.previous_secret_expires_at  # until when the old one keeps signing too

velirapay.webhook_endpoints.retry_delivery("12", "9d2e0b8a-6c1f-4e3a-8b7d-5f3a2c1e0d9b")
velirapay.webhook_endpoints.delete("12")
```

Adding an endpoint, giving one a new `url`, `verify()`, `test()` and `retry_delivery()` each send the endpoint a request, so together they are limited to 10 a minute per key. Past that the API answers 429: a short wait is [retried](#retries-and-idempotency) for you, and a longer one raises a `RateLimitError` whose `retry_after()` says how many seconds to wait.

If the answer to `create()` or `rotate_secret()` is lost, a retry raises a `ConflictError` rather than giving the secret again: see [Retries and idempotency](#retries-and-idempotency) for what to do.

## Your account

```python
account = velirapay.account.retrieve()

account.display_name
account.support_email
account.support_phone      # "+442071234567", shown to customers next to the support email
account.logo_dark_url      # the logo for a dark background, or None
account.terms_url
account.refund_policy_url
account.accepted_assets    # ["BTC", "ETH", …], the coins it takes right now, in the key's mode
account.mode               # "live" or "test"
account.checkout           # appearance, coin_order, default_coin, success_url, cancel_url, success_message, hide_powered_by
account.invoices           # number_prefix, footer, show_business_details
account.checkout_locale    # a CheckoutLocale value, or None
account.invoice_reminders
account.api_payout_address_changes  # whether an owner lets API keys and AI apps change payout addresses

business = account.business    # as entered under Business details in the dashboard's settings
business.type                  # a BusinessType, such as BusinessType.COMPANY
business.legal_name
business.registration_number
business.tax_id
business.address.line1         # also line2, city, postal_code, state and country (ISO 3166 two-letter code)
business.industry              # an Industry, such as Industry.SOFTWARE
business.product_description
business.monthly_volume        # a MonthlyVolume, such as MonthlyVolume.UNDER_50K ("10k_50k")
business.phone                 # in international format
```

Every business field is `None` until it is filled in. `type`, `industry` and `monthly_volume` are also `None` for a value the API adds after this version of the library; `business.get("industry")` still returns it as sent.

The business details are only sent to a key with the sensitive `account:write` permission, which full access does not include. For any other key every business field is `None`, and so is `account.get("business")`, while details that were never filled in come as an object of `None` fields.

The plan is on the account too: `account.plan` (`"free"` or `"pro"`, a `PlanName` value), `account.fee_percent` and `account.pro_ends_at`, with `account.is_pro()`.

A key with the sensitive `account:write` or `payment_settings:write` permission can change the account, in the shape it is read in, with `None` to clear a field:

```python
from velirapay import CheckoutAppearance, CheckoutLocale, Currency

velirapay.account.update({"display_name": "Acme", "checkout": {"appearance": CheckoutAppearance.DARK}})
velirapay.account.update_payment_settings(
    {
        "default_currency": Currency.EUR,
        "underpayment_tolerance": "2",  # in percent: a charge this short still counts as paid
        "checkout_locale": CheckoutLocale.FR,
        "invoice_reminders": True,
    }
)
```

### Overview

```python
overview = velirapay.overview.retrieve()  # the dashboard's last 30 days, in the key's mode; needs overview:read

overview.volume                   # in overview.currency
overview.volume_change_percent    # against the 30 days before; None when nothing was paid then
overview.sent_volume              # what the payouts confirmed in the period came to
overview.paid_charges
overview.conversion_rate_percent  # the share of paid, expired and canceled charges paid; None when none
overview.period.from_             # the first day, a date: the API calls it "from", a Python keyword
overview.funnel.abandoned         # charges that expired or were canceled before any transfer arrived
overview.funnel.assets            # the same per coin
overview.attention.underpaid_charges  # what waits on a person, such as short payments to accept
overview.attention.failing_webhook_endpoints
overview.assets                   # each coin's share of the paid charges
overview.top_payment_links
overview.setup.payout_address     # whether there is one, to tell what is left to set up

for day in overview.daily:
    print(day.date, day.volume, day.paid_charges)
```

Each block is a frozen dataclass, such as `OverviewFunnel` or `OverviewDay`; amounts are strings and days `date` objects.

### Activity log

```python
from datetime import date

from velirapay import ActivityAction

for entry in velirapay.activity.list({"action": "sensitive", "from": date(2026, 11, 1)}):  # needs activity:read
    entry.action      # "api_key.created", an ActivityAction value
    entry.actor       # a member's name, or 'API key "Shop server"'
    entry.ip_address

revoked = velirapay.activity.list({"action": ActivityAction.API_KEY_REVOKED})
```

The log holds what was done in the key's mode and what belongs to no mode, such as sign-ins; pass the key's mode as `network` to leave those out. `from` and `to` take a day, as a `date` or written as YYYY-MM-DD, and any other string raises an `InvalidArgumentError`, since the API would ignore it and list the whole log.

### API keys

```python
from velirapay import ApiKeyPermission

api_key = velirapay.api_keys.create(
    {
        "name": "Shop server",
        "permissions": [ApiKeyPermission.CHARGES_READ, ApiKeyPermission.CHARGES_WRITE],
        "allowed_ips": ["203.0.113.7", "2001:db8::/48"],
    }
)
api_key.key  # "vp_live_…", shown this once

velirapay.api_keys.update(api_key.id, {"allowed_ips": None})  # usable from anywhere again
velirapay.api_keys.revoke(api_key.id)
```

Reading keys needs the sensitive `api_keys:read` permission and changing them `api_keys:write`. Leaving `permissions` out, or `None`, gives full access, which never includes the sensitive permissions: `activity:read`, `account:write`, `payment_settings:write`, `payout_addresses:write`, `webhook_endpoints:write`, `api_keys:read`, `api_keys:write`, `members:read` and `members:write`. `allowed_ips` takes up to 20 IPv4 or IPv6 addresses or ranges. A key can make or change no key with a permission or an address it does not have itself, nor touch a key that reaches further. An account has up to 10 active keys in each mode, and a key is made in the mode of the one that asks. If the answer to `create()` is lost, see [Retries and idempotency](#retries-and-idempotency).

### Members and invitations

```python
from velirapay import MemberRole

for member in velirapay.members.list():  # needs members:read
    member.name
    member.role  # "owner", "admin", "finance", "support" or "viewer"

velirapay.invitations.create({"email": "grace@example.com", "role": MemberRole.ADMIN})
velirapay.members.update("3", {"role": MemberRole.FINANCE})
velirapay.members.remove("3")  # also revokes the API keys they made
```

Changing members and invitations needs the sensitive `members:write` permission, and happens in the name of whoever made the key: an owner's or admin's key invites people and cancels invitations, and only an owner's key changes a role or removes a member. Owners are never changed or removed this way, and nobody is made one: invitations and role changes take `MemberRole.ADMIN`, `FINANCE`, `SUPPORT` or `VIEWER`.

### Pro

```python
from velirapay import Asset

payment = velirapay.billing.start_pro_payment({"asset": Asset.BTC})  # with a live key
payment.checkout_url  # where to pay a month of Pro
payment.started       # False when a payment in that coin was already waiting
```

Paying for Pro needs `billing:write`, which full access includes.

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
page.meta                     # everything the API sent with the list, its position included
```

`iterator()` walks every page, fetching each one as it is reached:

```python
for charge in velirapay.charges.iterator({"status": "paid"}):
    ...
```

`assets.list()` answers with a single page holding every coin, whose `currencies` lists the currencies prices can be asked in. It and the activity log's pages have `mode`, the mode of the key that asked. `payouts.summary()` answers with a `PayoutSummaryList` and `payout_addresses.list()` with a `PayoutAddressList`: lists like any other, which also have the answer's `meta` and `mode`, and on the payout addresses `api_payout_address_changes`. `overview.retrieve()` has `mode` too, and anything else an answer carries is in `velirapay.last_response().json()`.

## Constants

Every set of values the API uses is an enum, and each member is also a `str`, so a member and its value can be used interchangeably:

| Enum | Values |
| --- | --- |
| `Asset` | The coins, each on one network, such as `BTC`, `USDT` (on Ethereum) and `USDT_TRON` |
| `ChargeStatus` | `pending`, `underpaid`, `paid`, `expired`, `canceled` |
| `InvoiceStatus` | `open`, `paid`, `void` |
| `PaymentLinkStatus` | `active`, `archived` |
| `PricingType` | `fixed`, `open` |
| `PayoutStatus` | `pending`, `sending`, `sent`, `failed`, `manual` |
| `EventType` | The events webhooks and the events API report, such as `charge.paid` |
| `WebhookDeliveryStatus` | `pending`, `succeeded`, `failed` |
| `Currency` | `USD`, `EUR`, `GBP`, `CAD`, `AUD`, `CHF`, `TRY` |
| `AddressNetwork` | The network families of payout addresses: `bitcoin`, `litecoin`, `dogecoin`, `bitcoincash`, `evm`, `bsc`, `base`, `arbitrum`, `polygon`, `tron`, `monero`, `solana`, `lightning` |
| `MemberRole` | `owner`, `admin`, `finance`, `support`, `viewer` |
| `ApiKeyPermission` | What a restricted API key may do, such as `charges:read` |
| `ActivityAction` | What the activity log records, such as `api_key.created` |
| `Mode` | `live`, `test` |
| `PlanName` | `free`, `pro` |
| `AccountType` | `personal`, `organization` |
| `CheckoutAppearance` | `auto`, `light`, `dark` |
| `CheckoutLocale` | `en`, `fr`, `de`, `es`, `tr`, `pt`, `ru`, `ar` |
| `BusinessType`, `Industry`, `MonthlyVolume` | An account's business details |

Parameters take a member or a plain string. The attributes of answers stay strings, such as `charge.status`, because the API adds values over time: compare them with a member, as in `charge.status == ChargeStatus.PAID`, or use a helper such as `charge.is_paid()`. A few attributes are the enum itself, and `None` for a value this version of the library does not know: `business.type`, `business.industry`, `business.monthly_volume` and `coin.asset()`.

## Errors

A failed request raises an error carrying the API's message. They are all importable from `velirapay` and are all a `VeliraPayError`:

| Error | When |
| --- | --- |
| `AuthenticationError` | The API key is missing, wrong or revoked (401). |
| `PermissionDeniedError` | The API key may not do this (403): a restricted key without the permission the endpoint needs, such as `charges:write`, or a key used from an IP address it does not allow. The message names which. An owner or admin can change the key's permissions and addresses in the dashboard; the key itself stays the same. |
| `NotFoundError` | The object does not exist, or belongs to the other mode (404). |
| `ConflictError` | The object cannot make that change (409), such as canceling a charge once a transfer to it has been seen, accepting one that is neither underpaid nor late, paying a live charge by simulation, or sending or voiding an invoice that is no longer open. Also an idempotency key used for a different request, or held by a request still being processed, which is [retried](#retries-and-idempotency) for you, and a repeated write whose answer carried a secret, for which `was_replayed()` is true. |
| `ValidationError` | The request has invalid fields (422). `errors()` lists them by field, and `first_error("amount")` gives the first message for one. |
| `RateLimitError` | Too many requests (429), including an invoice or a charge emailed again within 10 minutes, more than 100 emails to customers an hour, and more than 300 charges created in 30 minutes. `retry_after()` says how many seconds to wait. |
| `ServerError` | VeliraPay had a problem (5xx), such as no exchange rate being available to create a charge with (503). |
| `InvalidRequestError` | Any other 4xx, such as an `Idempotency-Key` longer than 255 characters (400), or a redirect, which is not followed. |
| `UnexpectedResponseError` | A successful answer this library cannot read, such as one that is not JSON. |
| `ApiConnectionError` | The API could not be reached, or its answer not read, after any retries. |
| `SignatureVerificationError` | A webhook's signature is missing, does not match, or is too old. |
| `InvalidArgumentError` | The library was given something it cannot use, such as an API key that does not start with `vp_live_` or `vp_test_`, or an amount that is not a number. It is a `ValueError` too. |

Every error from an API answer is an `ApiError`, with `status`, `body` (the decoded response), `response`, `header(name)` and `retry_after()`.

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

Requests that fail with a network error, a rate limit (429) or an outage (502, 503, 504) are tried again up to twice, waiting a little longer each time, or as long as the API's `Retry-After` header asks. A 500 is retried for reads only, since a write may have been carried out. A 409 is retried only when it carries a `Retry-After`: that is the API still working on an earlier request with the same idempotency key, and the retry gets that request's response once it is done. A `Retry-After` longer than `max_retry_after` (10 seconds unless [configured](#configuration) otherwise) is not waited out: the error is raised straight away, and its `retry_after()` says how long to wait.

While retries are on, each write carries an `Idempotency-Key` header, so the API carries out a retried request once. The library makes up a key per call; pass your own, such as an order number, to make a call safe to repeat across processes:

```python
charge = velirapay.charges.create(
    {"amount": "49.90", "currency": "EUR", "asset": "BTC"},
    idempotency_key="order-1042",
)

response = velirapay.last_response()
response is not None and response.was_replayed()  # True when the API answered from an earlier request
```

For 24 hours, a request repeating a key gets the first successful response, and `velirapay.last_response().was_replayed()` is then true. A request that failed stores nothing, so repeating it runs it again. Reusing a key with a different body raises a `ConflictError`. A key covers one account, one mode, one method and one path, and is at most 255 characters; every API key of that account and mode shares it, so two servers using different API keys still create one charge for one idempotency key.

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

Keys starting with `vp_test_` work in test mode: charges are paid with test coins on each chain's test network, and nothing touches real funds. Test and live objects are fully separate: a live key cannot see test charges, and each mode has its own webhooks. Invoices and charge emails only go to members of your account.

```python
velirapay.is_test_mode()  # read from the key's prefix

# Pay a test charge without any coins: it becomes paid, and the webhooks go out as for a real payment.
velirapay.charges.simulate("k3v9x2m7q8wz")
velirapay.charges.simulate("k3v9x2m7q8wz", {"amount": "0.001"})  # less than is due, to try an underpayment
```

BNB Chain, Base, Arbitrum One and Polygon have no test mode, so their coins can only be used with a live key.

Every key starts with `vp_live_` or `vp_test_`, and the client raises an `InvalidArgumentError` for any other, which the API would refuse.

## Configuration

```python
velirapay = VeliraPayClient(
    os.environ["VELIRAPAY_API_KEY"],
    base_url="https://api.velirapay.com",  # the default
    max_retries=2,          # 0 turns retries off
    max_retry_after=10,     # the longest Retry-After, in seconds, waited out before trying again
    timeout=30,             # seconds an attempt may wait to connect, and each time it waits for more of the answer
    app_info="MyShop/2.1",  # added to the User-Agent
)
```

Requests go through `urllib` from the standard library, which follows the `HTTPS_PROXY` and `NO_PROXY` environment variables. To trust other certificates, pass `transport=UrllibTransport(ssl_context=...)`. Any callable that takes an `HttpRequest` and answers with an `ApiResponse` can be the `transport`, such as one that sends requests through your own HTTP client or one that answers your tests; it raises an `OSError` when the API cannot be reached, which is retried like any network error.

A client can be shared between threads, and `last_response()` gives the response to the most recent request of the thread that asks. The client is synchronous; from async code, run its calls in a thread, such as with `await asyncio.to_thread(velirapay.charges.create, params)`.

## Testing your integration

To test your webhook handler, sign a payload yourself: `Webhook.signature_header()` gives the header VeliraPay would send with it.

```python
import json

from velirapay import Webhook

payload = json.dumps(
    {
        "id": "a5f4b1c2-6d7e-4f80-9a1b-2c3d4e5f6a7b",
        "event_id": None,
        "event": "charge.paid",
        "mode": "test",
        "created_at": "2026-11-12T10:00:00.000000Z",
        "data": {"charge": {"code": "k3v9x2m7q8wz", "status": "paid", "metadata": {"order_id": "1042"}}},
    }
)
headers = {Webhook.SIGNATURE_HEADER: Webhook.signature_header(payload, "whsec_test")}

# Post the payload with these headers to your endpoint, such as with your framework's test client.
```

To test code that calls the API, give the client a transport that answers for it:

```python
from velirapay import ApiResponse, HttpRequest, VeliraPayClient


def transport(request: HttpRequest) -> ApiResponse:
    return ApiResponse(200, {"Content-Type": "application/json"}, '{"data": {"id": "k3v9x2m7q8wz", "status": "paid"}}')


velirapay = VeliraPayClient("vp_test_example", transport=transport)

assert velirapay.charges.retrieve("k3v9x2m7q8wz").is_paid()
```

## Development

```bash
python -m pip install -e . --group dev
python -m unittest   # the tests
mypy                 # the types, in strict mode
ruff format --check && ruff check
```

## License

MIT. See [LICENSE](https://github.com/VeliraPay/velirapay-python/blob/main/LICENSE).
