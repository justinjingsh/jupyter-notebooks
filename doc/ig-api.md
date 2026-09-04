# IG REST API — as used by these notebooks

Scope: what `download_ig_prices.ipynb` actually calls — `POST /session` to
authenticate, then paginated `GET /prices/{epic}` for historical candles. The
`IGSession` class in that notebook is the reference implementation; this file
describes the wire contract it depends on.

Official reference: <https://labs.ig.com/rest-trading-api-reference>

A fuller write-up (dealing, positions, confirms, retry behaviour) lives in the
sibling repo at `C:\repos\github.com\ig-quant-trading\doc\ig-api.md`.

## Environments and base URLs

`IG_ACCOUNT_TYPE` in `.env` selects the gateway:

| `IG_ACCOUNT_TYPE` | Base URL | Notes |
| --- | --- | --- |
| `demo` | `https://demo-api.ig.com/gateway/deal` | Paper trading. Separate login + API key from live. |
| `live` | `https://api.ig.com/gateway/deal` | Real money. |

Demo and live are **completely separate systems** — separate credentials, API
keys, and data. All paths below are relative to the base URL.

## Authentication — `POST /session` (`Version: 1`)

Request headers:

```
X-IG-API-KEY: <IG_API_KEY>
Content-Type: application/json; charset=UTF-8
Version:      1
```

Request body: `{ "identifier": "<IG_USERNAME>", "password": "<IG_PASSWORD>" }`

The two session tokens come back as **response headers**, not in the body:

| Header | Meaning | Lifetime |
| --- | --- | --- |
| `CST` | Client Session Token — identifies the authenticated session | Expires after inactivity (~6h; sooner if another login supersedes it) |
| `X-SECURITY-TOKEN` | Identifies the active account within that session | Same |

Both are sent on every later call.

### Auth failures

| Status on `/session` | Meaning |
| --- | --- |
| `401` | Bad username / password |
| `403` | API key rejected, or not enabled for this environment (`demo` vs `live` mismatch) |

`IGSession._authenticate` raises a `RuntimeError` for each of these.

## Standard headers on authenticated requests

Set by `IGSession._headers(version)`:

```
X-IG-API-KEY:     <IG_API_KEY>
CST:              <from POST /session>
X-SECURITY-TOKEN: <from POST /session>
Content-Type:     application/json; charset=UTF-8
Accept:           application/json; charset=UTF-8
Version:          <per-endpoint>
```

### The `Version` header

IG versions **individual endpoints**, not the API as a whole — the same path
returns a different shape per `Version`. Values these notebooks rely on:

| Endpoint | Version |
| --- | --- |
| `POST /session` | 1 |
| `GET /markets?searchTerm=` | 1 |
| `GET /markets/{epic}` | 3 |
| `GET /prices/{epic}` | 3 |

## `GET /prices/{epic}` — `Version: 3`

Historical candles for one epic. This is the only data call the download
notebook makes.

### Query parameters

| Param | Sent as | Meaning |
| --- | --- | --- |
| `resolution` | `RESOLUTION` (`"DAY"`) | Candle size — see list below |
| `from` | `start.strftime("%Y-%m-%dT%H:%M:%S")` | Range start, ISO-8601, **no timezone suffix** |
| `to` | `end.strftime("%Y-%m-%dT%H:%M:%S")` | Range end, same format |
| `pageSize` | `200` | Candles per page |
| `pageNumber` | `1`, `2`, ... | 1-based page cursor |

> IG also accepts `max=<n>` (most-recent N candles) instead of `from`/`to`. The
> notebook uses the explicit range so re-runs cover a deterministic window.

### Pagination

Response `metadata.pageData` carries `{ pageSize, pageNumber, totalPages }`.
`IGSession.get_prices` loops `pageNumber` until `pageNumber >= totalPages` (or a
page returns no `prices`), sleeping **1s between pages** to stay under the
per-minute request allowance.

### Response shape

```jsonc
{
  "prices": [ /* candle, ... */ ],
  "metadata": {
    "allowance": {
      "remainingAllowance": 8967,
      "totalAllowance": 10000,
      "allowanceExpiry": 592259     // seconds until the weekly quota resets
    },
    "pageData": { "pageSize": 200, "pageNumber": 1, "totalPages": 1 },
    "size": 1
  }
}
```

### Candle shape

```jsonc
{
  "snapshotTime":    "2026/09/04 00:00:00",   // exchange local, "YYYY/MM/DD HH:MM:SS"
  "snapshotTimeUTC": "2026-09-04T00:00:00",
  "openPrice":  { "bid": 29289.5, "ask": 29291.5, "lastTraded": null },
  "closePrice": { "bid": 29615.4, "ask": 29617.4, "lastTraded": null },
  "highPrice":  { "bid": 29653.3, "ask": 29655.3, "lastTraded": null },
  "lowPrice":   { "bid": 29199.8, "ask": 29201.8, "lastTraded": null },
  "lastTradedVolume": 379979
}
```

Both notebooks reduce each OHLC node to its **mid price**, `(bid + ask) / 2`
(`mid()`). A node missing `bid` or `ask` yields `None`. `snapshotTimeUTC` (not
the exchange-local `snapshotTime`) is the key stored in `candles.snapshot_time_utc`;
the whole object is stored verbatim in `candles.data`.

### Resolutions

`SECOND`, `MINUTE`, `MINUTE_2`, `MINUTE_3`, `MINUTE_5`, `MINUTE_10`, `MINUTE_15`,
`MINUTE_30`, `HOUR`, `HOUR_2`, `HOUR_3`, `HOUR_4`, `DAY`, `WEEK`, `MONTH`.

### Allowances

Two separate limits, both surfaced as `403`:

| `errorCode` | Meaning | Mitigation in these notebooks |
| --- | --- | --- |
| `error.public-api.exceeded-account-allowance` | Per-minute request cap | `time.sleep(1)` between pages |
| `error.public-api.exceeded-account-historical-data-allowance` | Weekly historical-price-point cap (demo / retail keys) | Small `DAYS_BACK`; the DB keeps prior candles so you don't re-download history |

`IGSession._get` raises `RuntimeError("IG historical-data allowance exceeded: …")`
when a `403` body mentions `allowance`. `metadata.allowance` in a *successful*
response tells you how much is left before you hit it.

## `GET /markets?searchTerm=<term>` — `Version: 1`

Free-text market search — the way to resolve an epic you don't already know.
Returns `{ "markets": [ { epic, instrumentName, expiry, ... } ] }`. Not called by
the notebooks directly; see [`epics.md`](epics.md) for a snippet that runs it
through `IGSession._get`.

## `GET /markets/{epic}` — `Version: 3`

Full instrument detail plus a live bid/offer snapshot for one market
(`instrument.*`, `snapshot.bid` / `snapshot.offer`, `dealingRules.*`). Not used
here — listed because it is the natural next call after a market search.

## Not used here (but part of the API)

Live streaming prices over the **Lightstreamer** feed (push, not polling),
dealing (`POST` / `DELETE /positions/otc`), open positions (`GET /positions`),
deal confirmation (`GET /confirms/{dealReference}`), working orders, watchlists,
and activity/transaction history.
