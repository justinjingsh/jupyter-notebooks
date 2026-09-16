"""Downloads NASDAQ 100 index price history from Yahoo Finance, for
05_yahoo_download_finance.ipynb. Deliberately independent of trading_toolkit.ig_config /
.env - the notebook passes ticker/period/interval as plain arguments, so it
runs without any IG credentials or download window configured.

Yahoo has no separate bid/ask - this is a single OHLCV series (unlike the IG
candles, which carry bid/ask/mid)."""

from pathlib import Path

import yfinance as yf

from trading_toolkit.constants.yahoo_columns import YahooColumn
from trading_toolkit.constants.yahoo_ticker_slugs import TICKER_SLUGS
from trading_toolkit.utils.csv_utils import CsvUtils

# src/trading_toolkit/yahoo_finance.py -> repo root is three parents up.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

NASDAQ_100_TICKER = "^NDX"  # Yahoo Finance ticker for the NASDAQ 100 index


def download_history(ticker=NASDAQ_100_TICKER, period="1y", interval="1d"):
    """Download OHLCV history for `ticker` from Yahoo Finance. `period`
    (e.g. "1y", "6mo", "max") and `interval` (e.g. "1d", "1h", "15m") follow
    yfinance's own conventions. Returns a DataFrame indexed by date/datetime
    with Open/High/Low/Close/Volume columns - Dividends/Stock Splits are
    dropped, since an index has neither. Raises RuntimeError if Yahoo
    returns no rows (bad ticker, or an interval too fine for the period)."""

    df = yf.Ticker(ticker).history(period=period, interval=interval)
    if df.empty:
        raise RuntimeError(
            f"Yahoo Finance returned no data for {ticker!r} "
            f"(period={period!r}, interval={interval!r})"
        )
    return df.drop(
        columns=[YahooColumn.DIVIDENDS, YahooColumn.STOCK_SPLITS], errors="ignore"
    )


def csv_path_for(ticker=NASDAQ_100_TICKER, interval="1d", data_dir=DATA_DIR):
    """A fresh, timestamped CSV path for `ticker`/`interval` under
    `data_dir`, e.g. data/yahoo_nasdaq100_1d_20260916153000.csv. The slug is
    looked up in `constants/yahoo_ticker_slugs.py`'s `TICKER_SLUGS` for
    tickers in `YahooTicker`; any other ticker falls back to stripping the
    `^` prefix and lowercasing (e.g. `AAPL` -> `aapl`)."""

    slug = TICKER_SLUGS.get(ticker, ticker.lstrip("^").lower())
    return CsvUtils.path_for("yahoo", slug, interval, data_dir)


def save_csv(df, csv_path):
    """Write `df` (as returned by download_history) to `csv_path`, indexed
    by date/datetime. Returns `csv_path` for chaining."""

    return CsvUtils.save(df, csv_path, index_label="Date")
