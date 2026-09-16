"""Downloads NASDAQ 100 index price history from Yahoo Finance, for
05_download_yahoo_finance.ipynb. Deliberately independent of igmarket.config /
.env - the notebook passes ticker/period/interval as plain arguments, so it
runs without any IG credentials or download window configured.

Yahoo has no separate bid/ask - this is a single OHLCV series (unlike the IG
candles, which carry bid/ask/mid)."""

from datetime import datetime
from pathlib import Path

import yfinance as yf

# src/igmarket/yahoo_finance.py -> repo root is three parents up.
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
    return df.drop(columns=["Dividends", "Stock Splits"], errors="ignore")


def csv_path_for(ticker=NASDAQ_100_TICKER, interval="1d", data_dir=DATA_DIR):
    """A fresh, timestamped CSV path for `ticker`/`interval` under
    `data_dir`, e.g. data/yahoo_ndx_1d_20260916153000.csv."""

    data_dir.mkdir(exist_ok=True)
    slug = ticker.lstrip("^").lower()
    run_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return data_dir / f"yahoo_{slug}_{interval}_{run_timestamp}.csv"


def save_csv(df, csv_path):
    """Write `df` (as returned by download_history) to `csv_path`, indexed
    by date/datetime. Returns `csv_path` for chaining."""

    df.to_csv(csv_path, index_label="Date")
    return csv_path
