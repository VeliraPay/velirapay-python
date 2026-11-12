# Changelog

All notable changes to this library are documented here. It follows [Semantic Versioning](https://semver.org).

## Unreleased

- Amounts given as numbers are sent as decimal strings without an exponent: the amounts of charges, refunds, simulated payments, invoices and their items, payment links and coupons, and the payment tolerances. A float is rounded to 14 significant digits first, the precision the API reads a number with, so `0.00005` is sent as `"0.00005"` rather than as the `5e-05` the API refused, and `0.1 + 0.2` as `"0.3"`. A float that is not a number, or is infinite, raises an `InvalidArgumentError` before anything is sent. Metadata is sent as it is given.
- A `datetime` is sent in UTC, such as `created_from` and `created_to` or an `expires_at`, so one in another time zone means the same moment to the API, which read its time as UTC and moved the filter by the offset. A `datetime` without a time zone is taken as UTC, where it raised an `InvalidArgumentError`. A `date` is still sent as its day.
- `activity.list()` and `iterator()` take a `date` for `from` and `to`, and a `datetime` as its day in its own time zone; `ActivityListParams` types them as `str | date`.

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
