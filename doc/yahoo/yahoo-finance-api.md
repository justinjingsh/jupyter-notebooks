# Yahoo Finance API — as used by `05_download_yahoo_finance.ipynb`

Scope: what actually happens when `igmarket/yahoo_finance.py`'s
`download_history()` calls `yf.Ticker(ticker).history(period=period,
interval=interval)`. Unlike [`ig-api.md`](ig-api.md), this isn't a documented,
supported API — there's no official Yahoo Finance developer reference, no API
key, and no SLA. `yfinance` reverse-engineers the same endpoints Yahoo's own
finance.yahoo.com web pages call, and has had to adapt more than once when
Yahoo changed how it gates access. Anything here can break on a `yfinance`
upgrade or a Yahoo-side change without notice. Version in use here:
`yfinance==1.7.0` (see `uv.lock`).

Official reference: none. `yfinance` project: <https://github.com/ranaroussi/yfinance>

## No API key, but not anonymous either

There's no `IG_API_KEY`-equivalent to configure — `download_history()` needs
no credentials, which is why `igmarket/yahoo_finance.py` is deliberately
independent of `igmarket.config` / `.env`. But Yahoo still requires a valid
browser-like session: `yfinance` first fetches a Yahoo cookie and a "crumb"
token (a short-lived anti-scraping value) and attaches both to every
subsequent data request. This handshake is internal to `yfinance` — nothing
in this repo touches it directly — but it's why occasional failures look like
auth errors (`401`, or a JSON body with no `chart.result`) even though no
credentials are involved. Retrying, or letting `yfinance` re-fetch the crumb,
usually clears it.

## The call `Ticker(ticker).history()` makes

Under the hood, `history()` calls Yahoo's **chart** endpoint:

```
GET https://query1.finance.yahoo.com/v8/finance/chart/{ticker}
    ?period1=<unix-seconds>&period2=<unix-seconds>
    &interval=<interval>
    &includePrePost=false
    &events=div,splits
```

(`query2.finance.yahoo.com` is used as a fallback host by `yfinance` if
`query1` fails.) `period`/`interval` as passed to `download_history()` are
`yfinance`'s own strings (see [`yahoo-finance.md`](yahoo-finance.md)); a
`period` like `"1y"` is resolved client-side to `period1`/`period2` Unix
timestamps before the request is made — `from`/`to` are never passed through
literally the way `IGSession.get_prices()` does for IG.

### Response shape

```jsonc
{
  "chart": {
    "result": [
      {
        "meta": { "symbol": "^NDX", "currency": "USD", "exchangeTimezoneName": "America/New_York", ... },
        "timestamp": [1704067200, 1704153600, ...],           // Unix seconds, one per candle
        "indicators": {
          "quote": [
            { "open": [...], "high": [...], "low": [...], "close": [...], "volume": [...] }
          ],
          "adjclose": [ { "adjclose": [...] } ]
        }
      }
    ],
    "error": null
  }
}
```

There is no separate bid/ask — Yahoo (and therefore `yfinance`) only ever
returns a single OHLCV series, which is why the downstream CSV
(`igmarket/yahoo_finance.py`'s `save_csv()`) has no `*_bid_price` /
`*_ask_price` columns the way the IG CSVs do. `yfinance` zips the parallel
`timestamp` / `quote` / `adjclose` arrays back into the row-per-candle
DataFrame that `download_history()` receives, converts the Unix timestamps
to the exchange's local timezone (`meta.exchangeTimezoneName`), and adds the
`Dividends` / `Stock Splits` columns from the `events` data —
`download_history()` drops both, since an index has neither.

### Errors

| Symptom | Meaning |
| --- | --- |
| `chart.error` non-null in the JSON, or an HTTP `404` | Bad/unknown ticker |
| Empty `result` / no rows after parsing | Interval too fine for the requested period (e.g. `"1m"` beyond ~7 days back — see [`yahoo-finance.md`](yahoo-finance.md)), or a market with no trading in that window |
| HTTP `401` / `429`, or a crumb-fetch failure | Yahoo's anti-scraping gate — not a credentials problem in the usual sense; see above |

`download_history()` only distinguishes the "no rows" case, and raises its
own `RuntimeError` rather than surfacing Yahoo's response — it doesn't
inspect status codes or `chart.error` directly.

## Rate limiting and reliability

Yahoo doesn't publish a quota the way IG's `metadata.allowance` does. In
practice, high request volumes from one IP get throttled or temporarily
blocked (`429`), especially for anonymous, unauthenticated use. `yfinance`
has no built-in equivalent to `IGSession`'s inter-page `sleep(1)` — a single
`download_history()` call is one request, so this hasn't come up in this
repo, but a loop calling it for many tickers in quick succession should
expect occasional `429`s and back off.

## Not used here (but part of what `yfinance` exposes)

Fundamentals (`Ticker.info`, financials, balance sheet, earnings), options
chains, holders/insider data, news, and the multi-ticker `yf.download()`
batch helper. `05_download_yahoo_finance.ipynb` only ever calls
`Ticker(ticker).history()`.
