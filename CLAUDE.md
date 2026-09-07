# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A small library plus a set of Jupyter notebooks for pulling and inspecting IG
Markets price history (currently the NASDAQ 100 index CFD). Installable
(`pyproject.toml`, `src/` layout, `hatchling` backend) but not published; has a
`pytest` suite, no CI.

Layout:

```
pyproject.toml            # package metadata + [dev] extra (pytest, jupyter, nbconvert)
src/igmarket/             # the library the notebooks import
  config.py  ig_session.py  candle_csv.py  candle_db.py  backtest.py
  constants/              # field-name / mapping tables, one concern per module
0N_*.ipynb                # the runnable entry points, at the repo root, numbered in pipeline order
  01_download_ig_prices.ipynb  02_import_csv_to_db.ipynb
  03_view_ig_prices.ipynb      04_backtest_strategy.ipynb
tests/                    # pytest, offline (in-memory sqlite, synthetic frames)
doc/                      # ig-api.md, epics.md
data/                     # git-ignored: the CSV(s) + SQLite DB
.env                      # git-ignored credentials + run config (see .env.sample)
```

`import igmarket` works only once the package is installed (`pip install -e
".[dev]"` from the repo root). The notebooks' first cell does this
automatically — it walks up from the kernel's working directory to the repo
root and runs the editable install.

## Running notebooks

Install once, then open in Jupyter or run headless:

```
pip install -e ".[dev]"
python -m jupyter nbconvert --to notebook --execute --inplace 01_download_ig_prices.ipynb
```

`igmarket.config` anchors `.env` and `data/` to the repo root via
`Path(__file__)`, not the process CWD, so the notebooks resolve the same
files even if a kernel starts somewhere other than the repo root.

`python -m pytest` runs the suite (no network, no `.env`, no DB — it uses
in-memory SQLite and synthetic price frames).

`01_download_ig_prices.ipynb` needs a valid `.env` (see below) and network
access to IG. `03_view_ig_prices.ipynb` only needs `data/ig_market_data.db` to
exist. `02_import_csv_to_db.ipynb` loads one `data/ig_*.csv` (as written by the
download notebook — the newest `data/ig_*.csv` by mtime unless `CSV_PATH` is
set) into `data/ig_market_data.db` — no network; `epic` comes from
`igmarket.config` and `resolution` (also from there) picks the target table,
the rest from the CSV, flattened via the producer's own
`candle_csv.candle_to_row()` / `candle_db.INSERT_COLUMNS` so rows are
indistinguishable from downloaded ones. The CSV header must match
`igmarket/constants/csv_headers.py`'s `CSV_HEADERS` exactly or the import
aborts. `INSERT OR IGNORE`, so re-running is a no-op.
`04_backtest_strategy.ipynb` reads candles for one `epic`/`resolution` from
`data/ig_market_data.db` via `candle_db.load_candles`, clips them to a
`START`/`END` window, and runs them through the `igmarket.backtest` engine
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

Runtime dependencies (`requests`, `python-dotenv`, `pandas`, `numpy`,
`matplotlib`) are declared in `pyproject.toml`; `pip install -e ".[dev]"` adds
`pytest`, `jupyter`, and `nbconvert`. The viz cells still guard their
`pandas` / `matplotlib` imports with a `%pip install` hint so a bare kernel
degrades gracefully.

## The notebooks and their shared contract

`data/ig_market_data.db` is the hand-off point:
`01_download_ig_prices.ipynb` and `02_import_csv_to_db.ipynb` write it,
`03_view_ig_prices.ipynb` and `04_backtest_strategy.ipynb` read it. Each IG
`resolution` gets its own table, `candles_<suffix>` — `candles_1d` for
`DAY`, `candles_10min` for `MINUTE_10`, etc. — so the DB can hold multiple
resolutions (and multiple epics) without a `resolution` filter on every
query. The `resolution` -> table-name mapping lives in
`igmarket/candle_db.py` (`table_name_for_resolution()`,
`init_candles_table()`, and `load_candles(conn, resolution, epic=None)` which
the consumers use to read candles back), backed by
`igmarket/constants/resolutions.py` (`RESOLUTION_TABLE_SUFFIX`) — every
notebook imports from there so the mapping can't drift out of sync. The
`resolution` value itself is not stored as a column — it's fixed per table and
recoverable from the table name, so consumers pass it in
(`load_candles(conn, resolution, ...)`) rather than reading it back. Columns of
each `candles_<suffix>` table:

| column | notes |
| --- | --- |
| `epic` | e.g. `IX.D.NASDAQ.IFA.IP` (IG "US Tech 100 Cash") |
| `snapshot_time_utc` | text, UTC, formatted ISO `YYYY-MM-DDTHH:MM:SS` — IG's `snapshotTimeUTC`, not the exchange-local `snapshotTime` |
| `{open,high,low,close}_{bid,ask,mid}_price`, `last_traded_volume` | flattened price columns, matching the CSV output today — `igmarket/constants/db_headers.py`'s `DB_HEADERS`, a copy of `igmarket/constants/csv_headers.py`'s `CSV_HEADERS` kept as its own list so the two schemas can diverge independently; both are built via `candle_csv.candle_to_row()`, so keep `candle_to_row()`'s output order in sync with whichever headers list is in play if they ever do diverge |

`UNIQUE(epic, snapshot_time_utc)` per table (resolution no longer needs to be
part of the key — it's fixed per table). Both notebooks create tables via
`candle_db.init_candles_table()` — keep it as the single source of truth for
the schema. `snapshot_time_utc` was renamed from `snapshot_time` (local time)
to UTC, the table was later split from a single `candles` table (keyed on
`epic, resolution, snapshot_time_utc`) into per-resolution
`candles_<suffix>` tables, the flattened price columns were added, and the
redundant `resolution` column and the raw-JSON `data` blob were later dropped
(the table name encodes the resolution; the flattened columns carry
everything the notebooks read) — an existing local `data/ig_market_data.db`
from before any of these changes needs deleting and re-downloading;
`CREATE TABLE IF NOT EXISTS` will not migrate it.

**`01_download_ig_prices.ipynb` (producer).** Downloads candles from the IG REST
API and can write two outputs, each independently toggled: `data/ig_<epic-slug>_<resolution-suffix>_<timestamp>.csv`
(a new timestamped file per run, named from `EPIC` — `_epic_slug()` in
`igmarket/config.py` takes the instrument segment of the dot-separated epic,
e.g. `IX.D.NASDAQ.IFA.IP` -> `nasdaq` — and `RESOLUTION`, mapped to a
filename-friendly suffix by `igmarket/constants/csv_filename_suffix.py`'s
`RESOLUTION_CSV_SUFFIX` (e.g. `DAY` -> `daily`, `MINUTE_10` -> `10min`) —
kept separate from `igmarket/constants/resolutions.py`'s
`RESOLUTION_TABLE_SUFFIX` (`DAY` -> `1d`) so renaming one doesn't rename DB
tables or vice versa; columns are `snapshot_time_utc` plus
`{open,high,low,close}_{bid,ask,mid}_price` and `last_traded_volume` — full
bid/ask, not just mid — row-flattening lives in `igmarket/candle_csv.py`
(`candle_to_row()`), column headers in `igmarket/constants/csv_headers.py`
(`CSV_HEADERS`)) and an upsert into the `candles_<suffix>` table for
`RESOLUTION` in `data/ig_market_data.db` via `INSERT OR IGNORE`. The
`INSERT OR IGNORE` means existing rows are never updated — re-downloading a
still-forming candle keeps the stale row already in the DB. `EPIC`,
`RESOLUTION`, `DAYS_BACK` (lookback window in calendar days), and
`SAVE_CSV`/`SAVE_DB` (whether to write each output) are read from `.env`
(`IG_EPIC`, `IG_RESOLUTION`, `IG_DAYS_BACK`, `IG_SAVE_CSV`, `IG_SAVE_DB`), each
with a default in `igmarket/config.py` so `.env` doesn't have to set them;
`CSV_PATH`/`DB_PATH` are derived in the config cell.

**`03_view_ig_prices.ipynb` (consumer).** Reads a `candles_<suffix>` table with
stdlib `sqlite3` via `candle_db.load_candles(conn, resolution, epic=None)`
(resolution picks the table, optional `epic` filter), taking OHLC straight
from the flattened `*_mid_price` columns (no JSON parsing) into one flat dict
per candle whose keys are `igmarket/constants/ohlc_fields.py`'s `OHLCField` —
the same names the chart code indexes the pandas frame by. Then an optional
pandas view and a hand-drawn matplotlib candlestick chart with a volume panel
(no `mplfinance`). `RESOLUTION` and `DB_PATH` come from `igmarket.config`'s
`Config` (`cfg.resolution`, `cfg.db_path`), the same object the producer
uses, so both point at the same file and table.

## IG REST API, as used here

`doc/ig-api.md` in this repo covers the endpoints the notebooks use (`POST
/session`, paginated `GET /prices/{epic}`). The `IGSession` class
(`igmarket/ig_session.py`, imported by the download notebook) mirrors
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
  `igmarket/constants/allowance_fields.py`'s `AllowanceField`); exceeding it
  returns `403 error.public-api.exceeded-account-historical-data-allowance`.
- **Epics:** `doc/epics.md` lists common epic IDs and their instrument names, plus
  the `GET /markets?searchTerm=` (`Version: 1`) call to resolve others. Epics vary
  by environment (demo/live) and account, so verify before hard-coding.

## Conventions

- **All prices are the bid/ask mid**, `(bid + ask) / 2` — IG dealing prices, not
  the underlying cash index. The producer computes it once (`mid()` in
  `igmarket/candle_csv.py`) into the `*_mid_price` columns; the consumer
  (`candle_db.load_candles`) reads those columns straight back.
- Library modules import each other by absolute path (`from igmarket.constants.
  resolutions import ...`), not relative.
- Notebooks are committed with their executed output.

## Credentials

`.env` at the repo root (git-ignored), loaded with `python-dotenv`.
`.env.sample` is the committed template — `cp .env.sample .env` and fill in:

```
IG_API_KEY=...
IG_USERNAME=...
IG_PASSWORD=...
IG_ACCOUNT_TYPE=demo
```

`.env` also carries `01_download_ig_prices.ipynb`'s config — `IG_EPIC`,
`IG_RESOLUTION`, `IG_DAYS_BACK`, `IG_SAVE_CSV`, `IG_SAVE_DB` — each optional,
falling back to a default in `igmarket/config.py` if unset.
