# Changelog

All notable changes to this library are documented here. It follows [Semantic Versioning](https://semver.org).

## Unreleased

- `charge.switched_from`, an `OriginalQuote` with `asset`, `asset_amount`, `exchange_rate` and `switched_at` (a `datetime`), in the API's answers, the charges events carry and webhooks alike. TRX and USDT on Tron share deposit addresses, and when a charge in one of them closes, expired or canceled, with nothing of its own coin while the other arrived at its address, VeliraPay quotes it again in the coin that arrived: `asset`, `asset_amount`, `exchange_rate` and `network_surcharge` then describe that coin, `fiat_amount` stays the same, and `switched_from` keeps the first quote. The transfer waits as a late payment (`charge.late_payment`) for the merchant to accept, and `charge.paid` and what follows it are in the new coin. A charge switches at most once, so `charge.asset` can change once: read the coin from each payload rather than the one the charge was created with. `switched_from` is `None` for every other charge, and in a payload that leaves it out. Its amounts carry all 18 decimal places in webhooks, like the charge's own.
- `charge.processing_terms`, a `ProcessingTerms` with `percent`, the processing fee fixed when the charge was quoted, in percent of what is paid and leaving out any network surcharge, a string such as `"1.75"`, and `max_forwarding_percent`, the most managed forwarding may cost, in percent of the merchant's share after the fee, an `int` such as `10`. It is `None` for older charges, VeliraPay's own billing and a payload that leaves it out.
- Both are read only, and `OriginalQuote` and `ProcessingTerms` are importable from `velirapay`.

## 0.2.2 - 2026-11-12

- `charge.customer.ip_country`, `ip_asn` and `ip_network`: what VeliraPay works out from the customer's IP address, in the API's answers and in webhooks alike. `ip_country` is the country the hosted checkout placed the address in, as an ISO 3166 two-letter code or `T1` for Tor, and `None` for a charge created through the API; `ip_asn` is the number of the network (autonomous system) the address belongs to, an `int`, and `ip_network` who runs it, such as `24940` and `"Hetzner Online GmbH"`. A customer on a hosting company's network is often a bot or someone hiding behind a server. They are read only, and `None` in a payload that leaves them out.

## 0.2.1 - 2026-11-12

- `invoices.create()` takes `success_url` and `cancel_url`, public https:// addresses the invoice's page and its charges' checkout offer the customer a way back to: a button once they have paid, and a link while it is open. `invoice.success_url` and `invoice.cancel_url` read them back, and are `None` in webhooks, which leave them out.

## 0.2.0 - 2026-11-12

- Amounts given as numbers are sent as decimal strings without an exponent: the amounts of charges, refunds, simulated payments, invoices and their items, payment links and coupons, and the payment tolerances. A float is rounded to 14 significant digits first, the precision the API reads a number with, so `0.00005` is sent as `"0.00005"` rather than as the `5e-05` the API refused, and `0.1 + 0.2` as `"0.3"`. A float that is not a number, or is infinite, raises an `InvalidArgumentError` before anything is sent. Metadata is sent as it is given.
- A `datetime` is sent in UTC, such as `created_from` and `created_to` or an `expires_at`, so one in another time zone means the same moment to the API, which read its time as UTC and moved the filter by the offset. A `datetime` without a time zone is taken as UTC, where it raised an `InvalidArgumentError`. A `date` is still sent as its day.
- `activity.list()` and `iterator()` take a `date` for `from` and `to`, and a `datetime` as its day in its own time zone; `ActivityListParams` types them as `str | date`.
- Enums for the other values the API uses: `Currency`, `MemberRole`, `AddressNetwork` (the networks `payout_addresses.update()` and `delete()` take), `CheckoutAppearance`, `WebhookDeliveryStatus`, `PlanName`, `AccountType`, `CheckoutLocale` and `ActivityAction`, every action the activity log records, `team.second_factor_requirement_changed` included. `MemberRole.OWNER` only appears in answers: invitations and role changes take the other four. Every parameter that takes one of these values, or one of the earlier enums', is typed as the enum or a `str`, and a plain string still works; the attributes of answers stay strings, since the API can add values.
- The overview's other figures are typed: `overview.period` (`from_`, since `from` is a Python keyword, and `to`), `funnel`, `attention`, `assets`, `top_payment_links`, `setup` and `daily`, as `OverviewPeriod`, `OverviewFunnel` with `OverviewFunnelAsset`, `OverviewAttention` with `OverviewChargeAmount` and `OverviewWaitingPayouts`, `OverviewAsset`, `OverviewPaymentLink`, `OverviewSetup` and `OverviewDay`. Amounts stay strings, and days are `date` objects. `get()` still reads them as the API sent them.
- What the API sends under `meta` can be read. Every `Page` has `meta`, with `mode` for the lists that say it (the coins on offer and the activity log) and `currencies`, the currencies `assets.list()` can price coins in. `payouts.summary()` answers with a `PayoutSummaryList` and `payout_addresses.list()` with a `PayoutAddressList`: lists as before, which also have `meta` and `mode`, and on the payout addresses `api_payout_address_changes`, whether an owner lets API keys change them. `overview.retrieve()` has `mode` too.
- `charge.payment_link_title` and `charge.invoice_number`, which the charges in webhooks carry beside the payment link's and the invoice's codes. They are `None` for the charges the API answers with, which give the codes alone.
- `ConflictError.was_replayed()`, true when an earlier request with the same idempotency key succeeded but its answer carried a secret, which the API shows once and does not replay: the key of `api_keys.create()`, or the signing secret of `webhook_endpoints.create()` and `rotate_secret()`. A retry after a lost answer gets this conflict, which means the write was carried out; their docstrings and the README say how to recover. The README said a repeated key always gets the first response, which is not true for these three.
- Cloudflare's 520 to 524, its answers when it gets nothing from VeliraPay, are retried like 502, 503 and 504, reads and writes alike, since a retried write carries the same idempotency key.
- The README covers the whole library, each part with an example that runs: the coins on offer and the lowest price in each currency, charges with their customer details, the network surcharge and Lightning's `payment_request`, short and late payments, invoices, payment links, coupons, payouts and payout addresses, events, webhooks and their endpoints, the account and its payment settings, the overview, the activity log, API keys, members and invitations, Pro, the enums, and testing an integration. Its charge examples no longer use the bare order number as the idempotency key, which would send a customer coming back after the charge expired to that expired charge for a day: reuse a key only to retry the same request, and give a new attempt, such as a charge replacing an expired one, a new key.

### Breaking

- `activity.list()` and `iterator()` raise an `InvalidArgumentError` for a `from` or `to` that is not a day written as YYYY-MM-DD, such as `"2026-11-01T00:00:00Z"`, before anything is sent: the API ignored it and listed the whole log. A blank one is still sent, and read as no limit.

## 0.1.0 - 2026-11-12

The first version, covering what the PHP library covers as of its 0.6.5:

- `VeliraPayClient` with `account`, `assets`, `charges`, `payment_links`, `invoices`, `coupons`, `payouts`, `payout_addresses`, `events`, `webhook_endpoints`, `overview`, `activity`, `api_keys`, `members`, `invitations` and `billing`, each answering with typed objects that keep every attribute the API sent (`get()`, `to_dict()`).
- Parameters as dicts under the API's own names, typed with a `TypedDict` per endpoint, in which a key set to `None` is sent as `null`. Enum members, a `datetime` with a time zone, a `date` and a `Decimal` are sent the way the API expects.
- `Page` for lists, with `next_page()` and `auto_paging_iterator()`, and `iterator()` on every paged list.
- An error per kind of failure, all of them a `VeliraPayError`: `AuthenticationError`, `PermissionDeniedError`, `NotFoundError`, `ConflictError`, `ValidationError`, `RateLimitError`, `ServerError`, `InvalidRequestError`, `UnexpectedResponseError`, `ApiConnectionError`, `SignatureVerificationError` and `InvalidArgumentError`.
- Retries of network errors, rate limits and outages, with an `Idempotency-Key` on every write so a retried one is carried out once.
- `Webhook.construct_event()`, which checks the signature, the second one sent for a day after a secret is rotated, and its age.
- `Asset` also has `BTC_LIGHTNING`, `ETH_BASE`, `ETH_ARBITRUM` and `POL`, which the API defines, charges and coins read the `network_surcharge` the API sends, and charges their `payment_request`.
- Requests through `urllib` from the standard library, or any transport you give the client, for Python 3.11 or later, without dependencies.
