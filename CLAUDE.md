# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A small library plus a set of Jupyter notebooks for pulling and inspecting IG
Markets price history (currently the NASDAQ 100 index CFD), plus a standalone
notebook for pulling NASDAQ 100 *index* history from Yahoo Finance. Installable
(`pyproject.toml`, `src/` layout, `hatchling` backend) but not published; has a
`pytest` suite, no CI.

Layout:

```
pyproject.toml            # package metadata + [dev] extra; installs ../ig-quant-trading editable (the strategies)
src/trading_toolkit/             # the library the notebooks import
  ig_config.py  ig_session.py  ig_candle_csv.py  ig_candle_db.py  ig_backtest.py
  ig_timeutil.py  yahoo_finance.py  market_db.py
  constants/              # field-name / mapping tables, one concern per module
0N_*.ipynb                # the runnable entry points, at the repo root, numbered in pipeline order
  01_ig_download_prices.ipynb  02_ig_import_csv_to_db.ipynb
  03_ig_view_prices.ipynb      04_ig_backtest_strategy.ipynb
  05_yahoo_download_finance.ipynb  06_ig_list_instruments.ipynb
  07_nasdaq_backtest_db.ipynb  08_ig_nasdaq_daily_backtest_db.ipynb
  09_ig_nasdaq_10min_backtest_db.ipynb
tests/                    # pytest, offline (in-memory sqlite, synthetic frames)
doc/                      # ig-api.md, epics.md, yahoo-finance.md
data/                     # git-ignored: the CSV(s) + SQLite DB
.env                      # git-ignored credentials + run config (see .env.sample)
```

`import trading_toolkit` works only once the package is installed: `uv sync --extra
dev` from the repo root (or `pip install -e ".[dev]"` into a venv), once per
environment, before running any notebook or test. The notebooks no longer
self-install.

## Running notebooks

The project uses [uv](https://docs.astral.sh/uv/); `uv run` executes in
`.venv`:

```
uv sync --extra dev
uv run jupyter lab                                                                    # interactive
uv run jupyter nbconvert --to notebook --execute --inplace 01_ig_download_prices.ipynb   # headless
```

`trading_toolkit.ig_config` anchors `.env` and `data/` to the repo root via
`Path(__file__)`, not the process CWD, so the notebooks resolve the same
files even if a kernel starts somewhere other than the repo root.

`uv run pytest` runs the suite (no network, no `.env`, no DB — it uses
in-memory SQLite and synthetic price frames).

`01_ig_download_prices.ipynb` needs a valid `.env` (see below) and network
access to IG. `06_ig_list_instruments.ipynb` needs the same IG credentials
and network access, but not `IG_START`/`IG_EPIC`/`IG_RESOLUTION`.
`05_yahoo_download_finance.ipynb` needs network access to Yahoo
Finance but no `.env` and no credentials — its `TICKER`/`PERIOD`/`INTERVAL`
are set directly in the notebook. `03_ig_view_prices.ipynb` only needs
`data/ig_market_data.db` to exist. `02_ig_import_csv_to_db.ipynb` loads one
`data/ig_*.csv` (as written by the
download notebook — the newest `data/ig_*.csv` by mtime unless `CSV_PATH` is
set) into `data/ig_market_data.db` — no network; `epic` comes from
`trading_toolkit.ig_config` and `resolution` (also from there) picks the target table,
the rest from the CSV, flattened via the producer's own
`ig_candle_csv.candle_to_row()` / `ig_candle_db.INSERT_COLUMNS` so rows are
indistinguishable from downloaded ones. The CSV header must match
`trading_toolkit/constants/ig_csv_headers.py`'s `CSV_HEADERS` exactly or the import
aborts. `INSERT OR IGNORE`, so re-running is a no-op.
`04_ig_backtest_strategy.ipynb` reads candles for one `epic`/`resolution` from
`data/ig_market_data.db` via `ig_candle_db.load_candles`, clips them to a
`START`/`END` window, and runs them through the `trading_toolkit.ig_backtest` engine
(long/short, next-open fills, flat `fee_bps` cost). The position model is a
fixed-size CFD one: an account funded with `initial_funding` (default
20,000 AUD), `size` contracts held long or short, `point_value` account-currency
per index point per contract (default 1.0 AUD/point). Strategies come from
`ig_quant_trading.strategies` (see "Strategies" below) — `SMAStrategy`
is the worked example, `BuyHoldStrategy` the benchmark. `BacktestResult.summary()` prints initial -> final funding,
profit/loss vs. buy & hold, CAGR, Sharpe, drawdown, trade stats; the notebook
also shows the trade list, charts price / funding curve / drawdown, and runs a
small `BuyHoldStrategy` + `SMAStrategy` parameter sweep into a comparison table.

## Strategies - live in `ig_quant_trading`, backtested here

The strategies are **not** in this repo. They live in the sibling repo
`C:\repos\github.com\ig-quant-trading`, package `ig_quant_trading`, under
`strategies/` - one set that repo both trades live and these notebooks
backtest (SMA, EMA, MACD, RSI, Bollinger, Stochastic, Williams %R, CCI, ADX,
OBV, momentum, Donchian, VWAP, opening range, `SessionFilter`, buy & hold).
Its CLAUDE.md documents them (`VectorizedStrategy`, `signals()` /
`get_signal()`, `min_candles`, `session`, `label`). `pyproject.toml` installs it as an **editable path dependency**
(`[tool.uv.sources] ig-quant-trading = { path = "../ig-quant-trading",
editable = true }`), so a strategy edited there is what the notebooks backtest
on the next kernel restart - nothing is copied. That means the two repos must
sit side by side; `uv sync --extra dev` fails otherwise. Notebooks and
`ig_backtest` import `from ig_quant_trading import strategies as st` (class
names are ig's: `st.SMAStrategy(fast_period, slow_period)`,
`st.BuyHoldStrategy()`, ...) and `ig_quant_trading.constants.direction.Direction`.
`BacktestResult.strategy` is the strategy's `label` (e.g. "SMA 10/30"), not its
short `name` (e.g. "SMA", what ig logs and journals). New or changed strategies
go in that repo (with its tests), not here.

Signals mean what ig_quant_trading means: BUY = be long, SELL = be short, HOLD
= keep what's open; there's no "go flat". `run_backtest` calls
`strategy.signals(df)` once over the whole history and trades it like
ig_quant_trading's live `SignalTrader` with `CLOSE_ON_SIGNAL_REVERSAL = True`:
an opposite signal closes and reverses at the same next-open fill (its own
`BacktestEngine` takes a bar longer to reverse). A strategy's `session` makes
the engine block entries and force-close outside it - live that is
ig_quant_trading's `TRADING_SESSIONS_UTC` (RiskManager check 5 +
`HoldingLimitEnforcer`), which is fixed UTC, so it must be moved when US clocks
change. The engine builds its signal Series element by element with
`dtype=object`: pandas fills (`fillna`, `where`) and `np.full` truncate the
str-backed `Direction` enum.

Runtime dependencies (`requests`, `python-dotenv`, `pandas`, `numpy`,
`matplotlib`, `yfinance`) are declared in `pyproject.toml`; the `dev` extra
(`uv sync --extra dev`) adds `pytest`, `jupyter`, and `nbconvert`. `uv.lock`
pins the full set. The viz cells still guard their
`pandas` / `matplotlib` imports with a `%pip install` hint so a bare kernel
degrades gracefully.

## The notebooks and their shared contract

`data/ig_market_data.db` is the hand-off point: `02_ig_import_csv_to_db.ipynb`
writes it (from a CSV `01_ig_download_prices.ipynb` produced),
`03_ig_view_prices.ipynb` and `04_ig_backtest_strategy.ipynb` read it. Each IG
`resolution` gets its own table, `candles_<suffix>` — `candles_1d` for
`DAY`, `candles_10min` for `MINUTE_10`, etc. — so the DB can hold multiple
resolutions (and multiple epics) without a `resolution` filter on every
query. The `resolution` -> table-name mapping lives in
`trading_toolkit/ig_candle_db.py` (`table_name_for_resolution()`,
`init_candles_table()`, and `load_candles(conn, resolution, epic=None)` which
the consumers use to read candles back), backed by
`trading_toolkit/constants/ig_resolutions.py` (`RESOLUTION_TABLE_SUFFIX`) — every
notebook imports from there so the mapping can't drift out of sync. The
`resolution` value itself is not stored as a column — it's fixed per table and
recoverable from the table name, so consumers pass it in
(`load_candles(conn, resolution, ...)`) rather than reading it back. Columns of
each `candles_<suffix>` table:

| column | notes |
| --- | --- |
| `epic` | e.g. `IX.D.NASDAQ.IFA.IP` (IG "US Tech 100 Cash") |
| `snapshot_time_utc` | text, UTC, formatted ISO `YYYY-MM-DDTHH:MM:SS` — IG's `snapshotTimeUTC`, not the exchange-local `snapshotTime` |
| `{open,high,low,close}_{bid,ask,mid}_price`, `last_traded_volume` | flattened price columns, matching the CSV output today — `trading_toolkit/constants/ig_db_headers.py`'s `DB_HEADERS`, a copy of `trading_toolkit/constants/ig_csv_headers.py`'s `CSV_HEADERS` kept as its own list so the two schemas can diverge independently; both are built via `ig_candle_csv.candle_to_row()`, so keep `candle_to_row()`'s output order in sync with whichever headers list is in play if they ever do diverge |

`UNIQUE(epic, snapshot_time_utc)` per table (resolution no longer needs to be
part of the key — it's fixed per table). `02_ig_import_csv_to_db.ipynb` creates
tables via `ig_candle_db.init_candles_table()` — keep it as the single source of
truth for the schema. `snapshot_time_utc` was renamed from `snapshot_time` (local time)
to UTC, the table was later split from a single `candles` table (keyed on
`epic, resolution, snapshot_time_utc`) into per-resolution
`candles_<suffix>` tables, the flattened price columns were added, and the
redundant `resolution` column and the raw-JSON `data` blob were later dropped
(the table name encodes the resolution; the flattened columns carry
everything the notebooks read) — an existing local `data/ig_market_data.db`
from before any of these changes needs deleting and re-downloading;
`CREATE TABLE IF NOT EXISTS` will not migrate it.

**`01_ig_download_prices.ipynb` (producer).** Downloads candles from the IG REST
API and, when `SAVE_CSV` is set, writes them to
`data/ig_<epic-slug>_<resolution-suffix>_<timestamp>.csv` (a new timestamped
file per run, named from `EPIC` — `_epic_slug()` in `trading_toolkit/ig_config.py`
takes the instrument segment of the dot-separated epic, e.g.
`IX.D.NASDAQ.IFA.IP` -> `nasdaq` — and `RESOLUTION`, mapped to a
filename-friendly suffix by `trading_toolkit/constants/ig_csv_filename_suffix.py`'s
`RESOLUTION_CSV_SUFFIX` (e.g. `DAY` -> `daily`, `MINUTE_10` -> `10min`) —
kept separate from `trading_toolkit/constants/ig_resolutions.py`'s
`RESOLUTION_TABLE_SUFFIX` (`DAY` -> `1d`) so renaming one doesn't rename DB
tables or vice versa; columns are `snapshot_time_utc` plus
`{open,high,low,close}_{bid,ask,mid}_price` and `last_traded_volume` — full
bid/ask, not just mid — row-flattening lives in `trading_toolkit/ig_candle_csv.py`
(`candle_to_row()`), column headers in `trading_toolkit/constants/ig_csv_headers.py`
(`CSV_HEADERS`)). It does **not** touch the DB — run
`02_ig_import_csv_to_db.ipynb` to load the CSV into `data/ig_market_data.db`
(`INSERT OR IGNORE`, so re-running is a no-op). The **download window and
resolution are read from `.env`** via `Config.from_env()`: `IG_START` /
`IG_END` (UTC, `"YYYY-MM-DD"` or `"YYYY-MM-DDTHH:MM:SS"`; a bare-date
`IG_END` is rolled to `23:59:59` that day; a blank `IG_END` means now —
`IG_START` is required, raising `KeyError` if unset) and `IG_RESOLUTION`
(shared with `02`/`03`/`04`, default `DAY`). `EPIC` and the `SAVE_CSV` toggle
are likewise read from `.env` (`IG_EPIC`, `IG_SAVE_CSV`), each with a default
in `trading_toolkit/ig_config.py`; `IG_DAYS_BACK` / `IG_SAVE_DB` are still parsed but
unused. `CSV_PATH` comes from `cfg.csv_path_for(RESOLUTION)` — a fresh
timestamped path named for the resolution. Because the window lives in
`.env` rather than the notebook, a forgotten edit there silently re-downloads
the same window and spends historical-data allowance — the config cell
prints what it loaded so this is visible before the API call runs.

**`03_ig_view_prices.ipynb` (consumer).** Reads a `candles_<suffix>` table with
stdlib `sqlite3` via `ig_candle_db.load_candles(conn, resolution, epic=None)`
(resolution picks the table, optional `epic` filter), taking OHLC straight
from the flattened `*_mid_price` columns (no JSON parsing) into one flat dict
per candle whose keys are `trading_toolkit/constants/ig_ohlc_fields.py`'s `OHLCField` —
the same names the chart code indexes the pandas frame by. Then an optional
pandas view and a hand-drawn matplotlib candlestick chart with a volume panel
(no `mplfinance`). `RESOLUTION` and `DB_PATH` come from `trading_toolkit.ig_config`'s
`Config` (`cfg.resolution`, `cfg.db_path`), the same object the producer
uses, so both point at the same file and table.

## `05_yahoo_download_finance.ipynb` (standalone, unrelated to the DB pipeline)

Pulls OHLCV candles for a Yahoo Finance ticker (default `^NDX`, the NASDAQ
100 *index* — not the IG CFD `01`–`04` use) via `trading_toolkit/yahoo_finance.py`'s
`download_history()`, a thin wrapper over
`yf.Ticker(ticker).history(period=period, interval=interval)`, dropping the
`Dividends`/`Stock Splits` columns and raising `RuntimeError` if Yahoo
returns no rows. Deliberately independent of `trading_toolkit.ig_config` / `.env` —
`TICKER`/`PERIOD`/`INTERVAL` are set directly in the notebook's own
parameters cell, so it needs no IG credentials and doesn't touch
`data/ig_market_data.db`. `csv_path_for()` writes a fresh, timestamped
`data/yahoo_<ticker-slug>_<interval>_<timestamp>.csv` — the slug comes from
`trading_toolkit/constants/yahoo_ticker_slugs.py`'s `TICKER_SLUGS` for tickers
in `YahooTicker` (e.g. `^NDX` -> `nasdaq100`, `^GDAXI` -> `dax40`), falling
back to stripping the `^` prefix and lowercasing for any other ticker — via
`save_csv()`. Yahoo has no bid/ask, so this CSV is a single
`Open`/`High`/`Low`/`Close`/`Volume` series — a different shape from the IG
CSVs (`trading_toolkit/constants/ig_csv_headers.py`) and **not** importable by
`02_ig_import_csv_to_db.ipynb`. `trading_toolkit/ig_timeutil.py` (`parse_utc`,
`resolve_window`) has no bearing here — it's the `IG_START`/`IG_END` window
parser used by `01`/`04`, not by `05`. See `doc/yahoo/yahoo-finance.md` for
ticker examples, period/interval string values, and Yahoo's sub-daily history
limits, and `doc/yahoo/yahoo-finance-api.md` for the underlying (unofficial)
Yahoo endpoint `yfinance` calls.

## `06_ig_list_instruments.ipynb` (standalone, discovery tool)

IG has no endpoint that lists every instrument; the only documented way to
discover epics is free-text search — `GET /markets?searchTerm=<term>`
(`Version: 1`, see `doc/ig/epics.md`) — one term per call. This notebook runs
that search for a `SEARCH_TERMS` list (set directly in the notebook, e.g.
`"cash"` for undated stock indices, currency codes, commodity names),
aggregates the results via the new `IGSession.search_markets(term)`
(`trading_toolkit/ig_session.py`), de-duplicates by `epic`, and displays them
as a pandas table — optionally saving `data/ig_instruments_<timestamp>.csv`.
**Not exhaustive** — only instruments matching one of `SEARCH_TERMS` for the
logged-in account's environment (demo/live differ) are found. Uses
`Config.from_env()` for IG credentials only (`IG_EPIC`/`IG_RESOLUTION`/
`IG_START`/`IG_END` are loaded as part of the same `Config` but unused here);
doesn't touch `data/ig_market_data.db` or the `01`–`04` pipeline.

## `07_nasdaq_backtest_db.ipynb` (standalone, backtests against `quant-market-data`)

Same backtest engine as `04_ig_backtest_strategy.ipynb` (`trading_toolkit/ig_backtest.py`
— `run_backtest`, with `BuyHoldStrategy` / `SMAStrategy` from `ig_quant_trading.strategies`), but reads candles
from a different, external source: the separate
`quant-market-data` repo's Postgres database (schema: `providers` /
`instruments` / `resolutions` / one `candles_<resolution code, lowercased>`
table per resolution — that repo's own CLAUDE.md is authoritative), not this
repo's `data/ig_market_data.db`. This notebook uses that database's Yahoo
Finance history (`yahoo` / `NASDAQ100`, i.e. `^NDX`), so it backtests the raw
index level, not an IG CFD — there's no bid/ask to average into a mid, and
the CFD-style point-value/funding model the engine applies is a
simplification on top of it, not a real product. For the IG CFD itself, see
`08_ig_nasdaq_daily_backtest_db.ipynb` below.

`trading_toolkit/market_db.py` is the read-only client: `connect()` loads this
repo's `.env` (see `.env.sample`) and connects via `psycopg2.connect()` with
no arguments, which reads the standard `PGHOST`/`PGPORT`/`PGUSER`/
`PGPASSWORD`/`PGDATABASE` environment variables (same names
`quant-market-data`'s own `.env.sample` uses); `load_candles(conn, provider,
symbol, resolution)` joins `providers`/`instruments` and reads the target
`candles_<resolution>` table, yielding the same flat OHLC dict shape as
`ig_candle_db.load_candles` (keyed by `constants.ig_ohlc_fields.OHLCField`)
so `ig_backtest.py` runs against either source unmodified. `PROVIDER` /
`SYMBOL` (e.g. `"yahoo"` / `"NASDAQ100"`) and `RESOLUTION` are set directly
in the notebook's first config cell, not read from `.env`. Needs the
`quant-market-data` Postgres database running and seeded (`docker compose up
-d` in that repo, or a local Postgres per its own README) — no IG
credentials, and doesn't touch `data/ig_market_data.db` or the `01`–`06`
pipeline.

## `08_ig_nasdaq_daily_backtest_db.ipynb` (standalone, IG CFD backtest against `quant-market-data`)

Same as `07`, but for IG's NASDAQ 100 CFD: `PROVIDER = "ig"` / `SYMBOL =
"NASDAQ100"` — `instrument_id = 1` in `quant-market-data`'s `instruments`
table, epic `IX.D.NASDAQ.IFA.IP` ("US Tech 100 Cash (A$1)"), daily history
in `candles_day`. It reads candles via the same `market_db.load_candles`;
for IG rows the canonical `*_price` columns are the bid/ask mid, matching
this repo's convention. One extra cell queries the instrument row and the
`close_bid_price`/`close_ask_price` columns directly to measure the spread:
`FEE_BPS = None` (the default) sets the per-side cost to half the median
spread, so a round trip costs one spread. It also adds a calendar-year
returns table (strategy vs. buy & hold). Same prerequisites as `07`; IG
daily bars include short Sunday sessions, which slightly skew the
bar-count-based annualisation.

## `09_ig_nasdaq_10min_backtest_db.ipynb` (standalone, intraday IG CFD backtest against `quant-market-data`)

Same as `08` but `RESOLUTION = "MINUTE_10"` (`candles_minute_10`), with the
intraday strategies from `ig_quant_trading.strategies`: `EMAStrategy`,
`RSIStrategy`, `BollingerBandsStrategy`, `DonchianBreakoutStrategy`,
`VWAPTrendStrategy`, `OpeningRangeBreakoutStrategy`, and `SessionFilter(inner)`, which wraps any strategy
so it only holds during the US cash session and is flat by the close.
Session times are exchange-local (`America/New_York`, DST-aware) while the
candle timestamps are naive UTC; `to_local()` / `in_session()` /
`session_dates()` do the conversion. The engine applies a strategy's
`session`: no entries on a bar that starts outside it, and an open position
is closed at the open of the first such bar (16:00 New York). The spread cell splits the median
spread into in-session vs. outside; `FEE_BPS = None` still uses half the
overall median. Extra outputs: P&L per New York day, P&L by New York hour,
and a comparison of all the intraday strategies. The DB only holds a few weeks
of 10-minute history, so annualised figures (CAGR, Sharpe, volatility) are
unreliable - `ig_backtest._stats` measures the window in exact elapsed time
(not whole days) so sub-day windows don't break, and `summary()` prints
times as well as dates when the bars aren't daily.

## IG REST API, as used here

`doc/ig/ig-api.md` in this repo covers the endpoints the notebooks use (`POST
/session`, paginated `GET /prices/{epic}`). The `IGSession` class
(`trading_toolkit/ig_session.py`, imported by the download notebook) mirrors
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
  `trading_toolkit/constants/ig_allowance_fields.py`'s `AllowanceField`); exceeding it
  returns `403 error.public-api.exceeded-account-historical-data-allowance`.
  `IGSession.get_allowance(epic, resolution)` checks it cheaply (`max=1`, one
  candle) before a real download — `01_ig_download_prices.ipynb` calls it and
  logs the result before calling `get_prices()`.
- **Epics:** `doc/ig/epics.md` lists common epic IDs and their instrument names, plus
  the `GET /markets?searchTerm=` (`Version: 1`) call to resolve others, wrapped by
  `IGSession.search_markets(term)` and used by `06_ig_list_instruments.ipynb`.
  Epics vary by environment (demo/live) and account, so verify before hard-coding.

## Conventions

- **All prices are the bid/ask mid**, `(bid + ask) / 2` — IG dealing prices, not
  the underlying cash index. The producer computes it once (`mid()` in
  `trading_toolkit/ig_candle_csv.py`) into the `*_mid_price` columns; the consumer
  (`ig_candle_db.load_candles`) reads those columns straight back.
- Library modules import each other by absolute path (`from trading_toolkit.constants.
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

`.env` also carries optional settings, each falling back to a default in
`trading_toolkit/ig_config.py`: `IG_EPIC`, `IG_SAVE_CSV`, and `IG_RESOLUTION` (used by
all four notebooks). `IG_START` (required, no default — `01_ig_download_prices.ipynb`'s
download window start) and `IG_END` (optional, blank means now) have no
`.env.sample` default beyond a placeholder, since they're expected to change
per run. `IG_DAYS_BACK` and `IG_SAVE_DB` are still parsed (`cfg.days_back`,
`cfg.save_db`) but no notebook reads them.
