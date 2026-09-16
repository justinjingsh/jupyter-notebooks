# Yahoo Finance — tickers, period, interval

`05_yahoo_download_finance.ipynb` pulls OHLCV candles via `yfinance`
(`trading_toolkit/yahoo_finance.py`'s `download_history()`, a thin wrapper over
`yf.Ticker(ticker).history(period=period, interval=interval)`). Unlike the IG
pipeline, there's no auth, no `.env`, and no bid/ask — just a ticker, a
period, and an interval, all set directly in the notebook's `TICKER` /
`PERIOD` / `INTERVAL` parameters.

## Ticker

A Yahoo Finance symbol, e.g. `^NDX`. `csv_path_for()` builds the output
filename's slug from `trading_toolkit/constants/yahoo_ticker_slugs.py`'s
`TICKER_SLUGS` for any ticker in `YahooTicker` (e.g. `^NDX` -> `nasdaq100`,
`^GDAXI` -> `dax40`); any other ticker falls back to stripping the `^` prefix
and lowercasing (e.g. `AAPL` -> `aapl`).

### Major US indexes

| Ticker | Index |
| --- | --- |
| `^NDX` | Nasdaq 100 (default `TICKER` in `05_yahoo_download_finance.ipynb`) |
| `^GSPC` | S&P 500 |
| `^DJI` | Dow Jones Industrial Average — "Wall Street" is the common broker/CFD name for this same index (e.g. IG's epic of that name), not a separate ticker |
| `^IXIC` | Nasdaq Composite |
| `^RUT` | Russell 2000 |
| `^VIX` | CBOE Volatility Index |

### Other major indexes

| Ticker | Index |
| --- | --- |
| `^ATOI` | S&P/ASX 100 (Australia) |
| `^AXJO` | S&P/ASX 200 (Australia) |
| `^N225` | Nikkei 225 (Japan) |
| `^HSI` | Hang Seng Index (Hong Kong) — often called "Hong Kong 50" by CFD brokers |

A few more worth considering if you want broader global coverage:

| Ticker | Index | Description |
| --- | --- | --- |
| `^FTSE` | FTSE 100 (UK) | Index of the 100 largest companies by market cap listed on the London Stock Exchange; London/UK's main benchmark, fills the Europe gap in this list |
| `^GDAXI` | DAX 40 (Germany) | Blue-chip index of Germany's 40 largest listed companies; renamed and expanded from 30 to 40 constituents in 2021, so "DAX 30"/"DAX 40" refer to the same ticker, not separate indexes — main Eurozone benchmark |
| `000001.SS` | Shanghai Composite (China) | Tracks all A- and B-share stocks on the Shanghai Stock Exchange; mainland China's headline benchmark, distinct from Hong Kong's Hang Seng |

Non-index tickers (shares, ETFs, FX pairs like `EURUSD=X`) work the same way —
just set `TICKER` to the Yahoo Finance symbol.

## Period

How much history to pull, a `yfinance` period string:

`"1d"`, `"5d"`, `"1mo"`, `"3mo"`, `"6mo"`, `"1y"`, `"2y"`, `"5y"`, `"10y"`,
`"ytd"`, `"max"`

## Interval

Candle size, a `yfinance` interval string:

`"1m"`, `"2m"`, `"5m"`, `"15m"`, `"30m"`, `"60m"`, `"90m"`, `"1h"`, `"1d"`,
`"5d"`, `"1wk"`, `"1mo"`, `"3mo"`

Intraday intervals (anything under `"1d"`) only cover recent history — Yahoo
limits how far back sub-daily data goes (e.g. `"1m"` is capped around the last
7 days), regardless of `PERIOD`.
