# Yahoo Finance — tickers, period, interval

`05_download_nasdaq_yahoo.ipynb` pulls OHLCV candles via `yfinance`
(`igmarket/yahoo_finance.py`'s `download_history()`, a thin wrapper over
`yf.Ticker(ticker).history(period=period, interval=interval)`). Unlike the IG
pipeline, there's no auth, no `.env`, and no bid/ask — just a ticker, a
period, and an interval, all set directly in the notebook's `TICKER` /
`PERIOD` / `INTERVAL` parameters.

## Ticker

A Yahoo Finance symbol, e.g. `^NDX`. Index tickers are prefixed `^`; the
prefix is stripped when building the output filename (`csv_path_for()`:
`^NDX` -> `ndx`).

### Major US indexes

| Ticker | Index |
| --- | --- |
| `^NDX` | Nasdaq 100 (default `TICKER` in `05_download_nasdaq_yahoo.ipynb`) |
| `^GSPC` | S&P 500 |
| `^DJI` | Dow Jones Industrial Average |
| `^IXIC` | Nasdaq Composite |
| `^RUT` | Russell 2000 |
| `^VIX` | CBOE Volatility Index |

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
