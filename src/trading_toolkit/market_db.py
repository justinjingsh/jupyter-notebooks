"""Reads candles from the separate `quant-market-data` Postgres database
(https://github.com/.../quant-market-data, checked out locally at
`C:\\repos\\github.com\\quant-market-data`) — a shared schema of `providers` /
`instruments` / `resolutions` plus one `candles_<resolution code, lowercased>`
table per resolution (e.g. `DAY` -> `candles_day`, `MINUTE_10` ->
`candles_minute_10` — that repo's own CLAUDE.md and
`db/migrations/001_init_schema.sql` are the source of truth for this mapping
and the schema itself).

Unrelated to `ig_candle_db.py` / `data/ig_market_data.db` (this repo's own
SQLite pipeline, `01`-`04`) — this module is a read-only client of the other
repo's database, for notebooks that want to backtest against its seeded data
(e.g. Yahoo's `^NDX` NASDAQ 100 history) instead of downloading anything
here. `load_candles()` yields the same flat-dict shape as
`ig_candle_db.load_candles` (keyed by `constants.ig_ohlc_fields.OHLCField`),
so `ig_backtest.py` runs against either source unmodified.

Connects with `psycopg2.connect()` and no arguments, which reads libpq's
standard `PGHOST`/`PGPORT`/`PGUSER`/`PGPASSWORD`/`PGDATABASE` environment
variables — the same names `quant-market-data`'s own `.env.sample` uses.
`connect()` just loads this repo's `.env` (see `.env.sample`) into the
environment first, anchored to the repo root like `ig_config.Config` does,
so a notebook works regardless of where its kernel started."""

from pathlib import Path

import psycopg2
from dotenv import load_dotenv

from trading_toolkit.constants.ig_ohlc_fields import OHLCField

# src/trading_toolkit/market_db.py -> repo root is three parents up.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Matches quant-market-data/db/migrations/002_seed_data.sql's `resolutions`
# rows - kept here only to reject a typo'd resolution before it's
# interpolated into a table name, not as this module's source of truth.
VALID_RESOLUTIONS = {
    "MINUTE_1", "MINUTE_2", "MINUTE_3", "MINUTE_5", "MINUTE_10", "MINUTE_15",
    "MINUTE_30", "HOUR", "HOUR_2", "HOUR_3", "HOUR_4", "DAY", "WEEK", "MONTH",
}


def connect(env_path=None):
    """Load `env_path` (default `<repo root>/.env`) and return a psycopg2
    connection to the quant-market-data Postgres database, via the standard
    PG* libpq environment variables it sets (see .env.sample)."""

    env_path = Path(env_path) if env_path is not None else PROJECT_ROOT / ".env"
    load_dotenv(env_path, override=True)
    return psycopg2.connect()


def table_name_for_resolution(resolution):
    """Map a resolution code (e.g. "DAY") to its quant-market-data table
    name (e.g. "candles_day"). Raises ValueError for an unrecognized code."""

    if resolution not in VALID_RESOLUTIONS:
        raise ValueError(f"unknown resolution {resolution!r}")
    return f"candles_{resolution.lower()}"


def load_candles(connection, provider, symbol, resolution):
    """Yield one flat OHLC dict per candle for `provider`/`symbol` (e.g.
    "yahoo"/"NASDAQ100" - see quant-market-data's `instruments` table) at
    `resolution`, oldest first.

    Reads the canonical `*_price` columns, populated for every provider
    (unlike `*_bid_price`/`*_ask_price`, which only IG quotes) - there is no
    mid to compute, so `open`/`high`/`low`/`close` are that instrument's own
    close/last-traded price, not a bid/ask mid like `ig_candle_db`'s."""

    table = table_name_for_resolution(resolution)
    sql = (
        "SELECT c.snapshot_time, c.open_price, c.high_price, c.low_price, "
        "c.close_price, c.volume "
        f"FROM {table} c "
        "JOIN instruments i ON i.id = c.instrument_id "
        "JOIN providers p ON p.id = i.provider_id "
        "WHERE p.code = %s AND i.symbol = %s "
        "ORDER BY c.snapshot_time"
    )
    with connection.cursor() as cur:
        cur.execute(sql, (provider, symbol))
        for snapshot_time, open_, high, low, close, volume in cur.fetchall():
            yield {
                OHLCField.SNAPSHOT_TIME_UTC: snapshot_time,
                OHLCField.OPEN: float(open_),
                OHLCField.HIGH: float(high),
                OHLCField.LOW: float(low),
                OHLCField.CLOSE: float(close),
                OHLCField.VOLUME: volume,
            }
