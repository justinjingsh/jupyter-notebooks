# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A small set of standalone Jupyter notebooks for pulling and inspecting IG Markets
price history (currently the NASDAQ 100 index CFD). Not a package — there is no
`pyproject.toml`, no test suite, no CI. Tracked: `README.md`, `.gitignore`,
`CLAUDE.md`, `.env.sample`, `candle_csv.py`, `candle_db.py`, `config.py`,
`ig_session.py`, `backtest.py`, `constants/`, the four notebooks
(`download_ig_prices.ipynb`, `view_ig_prices.ipynb`,
`import_csv_to_db.ipynb`, `backtest_strategy.ipynb`), and `doc/`.
Local only (git-ignored): `.env` and `data/` (the CSV + SQLite DB).

## Running notebooks

Open in Jupyter, or run headless:

```
python -m jupyter nbconvert --to notebook --execute --inplace <notebook>.ipynb
```

`download_ig_prices.ipynb` needs a valid `.env` (see below) and network access
to IG. `view_ig_prices.ipynb` only needs `data/ig_market_data.db` to exist.
`import_csv_to_db.ipynb` loads one `data/ig_*.csv` (as written by the download
notebook — the newest `data/ig_*.csv` by mtime unless `CSV_PATH` is set) into
`data/ig_market_data.db` — no network; `epic`/`resolution`
come from `config.py`, the rest from the CSV, and the raw-JSON `data` blob is
reconstructed from the CSV's bid/ask columns via the producer's own
`candle_csv.candle_to_row()` / `candle_db.INSERT_COLUMNS` (so `snapshotTime`
and per-node `lastTraded` are absent/`null`, but rows are otherwise
indistinguishable from downloaded ones). The CSV header must match
`constants/csv_headers.py`'s `CSV_HEADERS` exactly or the import aborts.
`INSERT OR IGNORE`, so re-running is a no-op.
`backtest_strategy.ipynb` reads candles for one `epic`/`resolution` from
`data/ig_market_data.db` via `candle_db.load_candles`, clips them to a
`START`/`END` window, and runs them through the `backtest.py` engine
(long-or-flat, next-open fills, flat `fee_bps` cost). The position model is a
fixed-size CFD one: an account funded with `initial_funding` (default
20,000 AUD), `size` contracts held while long, `point_value` account-currency
per index point per contract (default 1.0 AUD/point). Strategies are a
pluggable `Strategy` subclass (`.signal(df)` -> a 0/1 position Series the
engine shifts one bar) — `SmaCrossover` is the worked example, `BuyHold` the
benchmark. `BacktestResult.summary()` prints initial -> final funding,
profit/loss vs. buy & hold, CAGR, Sharpe, drawdown, trade stats; the notebook
also shows the trade list, charts price / funding curve / drawdown, and runs a
small `BuyHold` + `SmaCrossover` parameter sweep into a comparison table.

Dependencies are installed ad hoc (no requirements file); each notebook has
`%pip install` fallbacks. Download path needs `requests` + `python-dotenv`; the
viz cells need `pandas` + `matplotlib`; the backtester needs `pandas` (+
`numpy`, which ships with it) and `matplotlib`.

## The notebooks and their shared contract

`data/ig_market_data.db` is the hand-off point: `download_ig_prices.ipynb`
and `import_csv_to_db.ipynb` write it, `view_ig_prices.ipynb` and
`backtest_strategy.ipynb` read it. Each IG
`resolution` gets its own table, `candles_<suffix>` — `candles_1d` for
`DAY`, `candles_10min` for `MINUTE_10`, etc. — so the DB can hold multiple
resolutions (and multiple epics) without a `resolution` filter on every
query. The `resolution` -> table-name mapping lives in `candle_db.py`
(`table_name_for_resolution()`, `init_candles_table()`, and
`load_candles(conn, resolution, epic=None)` which the consumers use to read
candles back), backed by `constants/resolutions.py`
(`RESOLUTION_TABLE_SUFFIX`) — every notebook imports from there so the mapping
can't drift out of sync. Columns of each `candles_<suffix>` table:

| column | notes |
| --- | --- |
| `epic` | e.g. `IX.D.NASDAQ.IFA.IP` (IG "US Tech 100 Cash") |
| `resolution` | the IG `resolution` value this table holds (e.g. `DAY`); redundant with the table name itself, kept for convenience |
| `snapshot_time_utc` | text, UTC, formatted ISO `YYYY-MM-DDTHH:MM:SS` — IG's `snapshotTimeUTC`, not the exchange-local `snapshotTime` |
| `{open,high,low,close}_{bid,ask,mid}_price`, `last_traded_volume` | flattened price columns, matching the CSV output today — `constants/db_headers.py`'s `DB_HEADERS`, a copy of `constants/csv_headers.py`'s `CSV_HEADERS` kept as its own list so the two schemas can diverge independently; both are built via `candle_csv.candle_to_row()`, so keep `candle_to_row()`'s output order in sync with whichever headers list is in play if they ever do diverge |
| `data` | raw IG candle JSON: `openPrice`/`closePrice`/`highPrice`/`lowPrice`, each `{bid, ask, lastTraded}`, plus `lastTradedVolume` — kept alongside the flattened columns for anything they don't capture |

`UNIQUE(epic, snapshot_time_utc)` per table (resolution no longer needs to be
part of the key — it's fixed per table). Both notebooks create tables via
`candle_db.init_candles_table()` — keep it as the single source of truth for
the schema. This column was renamed from `snapshot_time` (local time) to
`snapshot_time_utc` (UTC), the table was later split from a single
`candles` table (keyed on `epic, resolution, snapshot_time_utc`) into
per-resolution `candles_<suffix>` tables, and the flattened price columns
were added alongside the existing `data` blob — an existing local
`data/ig_market_data.db` from before any of these changes needs deleting and
re-downloading; `CREATE TABLE IF NOT EXISTS` will not migrate it.

**`download_ig_prices.ipynb` (producer).** Downloads candles from the IG REST
API and can write two outputs, each independently toggled: `data/ig_<epic-slug>_<resolution-suffix>_<timestamp>.csv`
(a new timestamped file per run, named from `EPIC` — `_epic_slug()` in
`config.py` takes the instrument segment of the dot-separated epic, e.g.
`IX.D.NASDAQ.IFA.IP` -> `nasdaq` — and `RESOLUTION`, mapped to a
filename-friendly suffix by `constants/csv_filename_suffix.py`'s
`RESOLUTION_CSV_SUFFIX` (e.g. `DAY` -> `daily`, `MINUTE_10` -> `10min`) —
kept separate from `constants/resolutions.py`'s `RESOLUTION_TABLE_SUFFIX`
(`DAY` -> `1d`) so renaming one doesn't rename DB tables or vice versa;
columns are `snapshot_time_utc` plus
`{open,high,low,close}_{bid,ask,mid}_price` and `last_traded_volume` — full
bid/ask, not just mid — row-flattening lives in `candle_csv.py` (`candle_to_row()`),
column headers in `constants/csv_headers.py` (`CSV_HEADERS`)) and an upsert into
the `candles_<suffix>` table for `RESOLUTION` in `data/ig_market_data.db` via
`INSERT OR IGNORE`. The `INSERT OR IGNORE` means existing rows are never
updated — re-downloading a still-forming candle keeps the stale `data` blob
in the DB. `EPIC`, `RESOLUTION`, `DAYS_BACK` (lookback window in calendar
days), and `SAVE_CSV`/`SAVE_DB` (whether to write each output) are read from
`.env` (`IG_EPIC`, `IG_RESOLUTION`, `IG_DAYS_BACK`, `IG_SAVE_CSV`,
`IG_SAVE_DB`), each with a default in the config cell so `.env` doesn't have
to set them; `CSV_PATH`/`DB_PATH` are derived in that same cell.

**`view_ig_prices.ipynb` (consumer).** Reads a `candles_<suffix>` table with
stdlib `sqlite3` via `candle_db.load_candles(conn, resolution, epic=None)`
(resolution picks the table, optional `epic` filter), taking OHLC straight
from the flattened `*_mid_price` columns (no JSON parsing) into one flat dict
per candle whose keys are `constants/ohlc_fields.py`'s `OHLCField` — the same
names the chart code indexes the pandas frame by. Then an optional pandas
view and a hand-drawn matplotlib candlestick chart with a volume panel (no
`mplfinance`). `RESOLUTION` and `DB_PATH` come from `config.py`'s
`Config` (`cfg.resolution`, `cfg.db_path`), the same object the producer
uses, so both point at the same file and table.

## IG REST API, as used here

`doc/ig-api.md` in this repo covers the endpoints the notebooks use (`POST
/session`, paginated `GET /prices/{epic}`). The `IGSession` class (`ig_session.py`,
imported by the download notebook) mirrors
`C:\repos\github.com\ig-quant-trading\src\ig_quant_trading\client.py`;
that repo's `doc/ig-api.md` is the fullest reference (dealing, positions, retry
behaviour).

- **Environments are fully separate systems** — demo (`https://demo-api.ig.com/gateway/deal`)
  and live (`https://api.ig.com/gateway/deal`) have distinct credentials, API
  keys, and data. `IG_ACCOUNT_TYPE` (`demo` | `live`) selects the base URL.
- **Auth:** `POST /session` (`Version: 1`) returns `CST` and `X-SECURITY-TOKEN`
  as response *headers*; every later call sends them plus `X-IG-API-KEY`.
- **The `Version` header is per-endpoint and load-bearing** — the same path
  returns a different shape per version. `POST /session` → 1, `GET /prices/{epic}`
  → 3.
- **Prices:** `GET /prices/{epic}` (`Version: 3`) with `resolution`, `from`/`to`
  (`YYYY-MM-DDTHH:MM:SS`), `pageSize`, `pageNumber`. Paginate until
  `metadata.pageData.pageNumber >= totalPages`.
- **Historical-data allowance:** IG caps historical price points per week on
  demo/retail keys. `metadata.allowance` reports what's left (field names in
  `constants/allowance_fields.py`'s `AllowanceField`); exceeding it returns
  `403 error.public-api.exceeded-account-historical-data-allowance`.
- **Epics:** `doc/epics.md` lists common epic IDs and their instrument names, plus
  the `GET /markets?searchTerm=` (`Version: 1`) call to resolve others. Epics vary
  by environment (demo/live) and account, so verify before hard-coding.

## Conventions

- **All prices are the bid/ask mid**, `(bid + ask) / 2` — IG dealing prices, not
  the underlying cash index. The producer computes it once (`mid()` in
  `candle_csv.py`) into the `*_mid_price` columns; the consumer
  (`candle_db.load_candles`) reads those columns straight back.
- Notebooks are committed with their executed output.

## Credentials

`.env` in this folder (git-ignored), loaded with `python-dotenv`. `.env.sample`
is the committed template — `cp .env.sample .env` and fill in:

```
IG_API_KEY=...
IG_USERNAME=...
IG_PASSWORD=...
IG_ACCOUNT_TYPE=demo
```

`.env` also carries `download_ig_prices.ipynb`'s config — `IG_EPIC`,
`IG_RESOLUTION`, `IG_DAYS_BACK`, `IG_SAVE_CSV`, `IG_SAVE_DB` — each optional,
falling back to a default in the notebook's config cell if unset.
