# igmarket

A small library (`src/igmarket/`) plus Jupyter notebooks (`0N_*.ipynb`) for
pulling and inspecting IG Markets price history (currently the NASDAQ 100 index
CFD, `IX.D.NASDAQ.IFA.IP`), plus a standalone notebook for pulling NASDAQ 100
*index* history from Yahoo Finance.

## Data sources

- **[IG Markets](https://www.ig.com/)** — a CFD/spread-betting broker. Its
  REST API (`doc/ig/ig-api.md`) returns **dealing prices** (bid/ask) for the
  instrument you're trading, e.g. `IX.D.NASDAQ.IFA.IP`, IG's CFD tracking the
  NASDAQ 100 — not the underlying index itself. Needs an IG account, an API
  key, and a login (see [Setup](#setup)); demo and live are separate systems.
  Used by `01`–`04`.
- **[Yahoo Finance](https://finance.yahoo.com/)** — free public market data,
  via the `yfinance` package. Returns plain OHLCV for the underlying
  instrument (here, the `^NDX` NASDAQ 100 **index**, not a CFD) — no bid/ask,
  no account, no API key. Used standalone by `05`.

These are different prices for related-but-distinct instruments (IG's CFD
dealing price vs. Yahoo's underlying index price) — don't mix them in the
same analysis without accounting for that.

## Layout

```
src/igmarket/     library: config, ig_session, candle_csv, candle_db, backtest,
                  timeutil, yahoo_finance, constants/
0N_*.ipynb        the runnable entry points (repo root), numbered in pipeline order
tests/            pytest suite (offline)
doc/              IG REST API notes, epic list, Yahoo Finance notes
data/             git-ignored: downloaded CSV(s) + the SQLite DB
```

## Notebooks

| Notebook | Role |
| --- | --- |
| `01_download_prices.ipynb` | Downloads candles from the IG REST API into a timestamped `data/ig_<epic-slug>_<resolution-suffix>_<timestamp>.csv` (load it into the DB with `02_import_csv_to_db.ipynb`). |
| `02_import_csv_to_db.ipynb` | Loads one `data/ig_*.csv` written by the download notebook into `data/ig_market_data.db` (offline; `INSERT OR IGNORE`, so re-running is a no-op). |
| `03_view_ig_prices.ipynb` | Reads `data/ig_market_data.db`, flattens candles to OHLC, and draws a candlestick chart with a volume panel. |
| `04_backtest_strategy.ipynb` | Backtests a long/flat strategy over a chosen window of the `data/ig_market_data.db` history (fixed-size CFD model, engine in `igmarket/backtest.py`); shows a metrics summary, trade list, price / funding / drawdown charts, and a multi-strategy comparison table. |
| `05_download_yahoo_finance.ipynb` | Standalone — downloads OHLCV candles for a Yahoo Finance ticker (default `^NDX`, the NASDAQ 100 index) into a timestamped `data/yahoo_<ticker-slug>_<interval>_<timestamp>.csv`. No `.env`, no credentials, no bid/ask; **not** compatible with `02_import_csv_to_db.ipynb`. |

`01`–`04` are one pipeline; `05` is unrelated and self-contained (see its own
section below). `02`–`04` share `data/ig_market_data.db` (`01` only writes the CSV), where
each resolution gets its own table — `candles_1d` for `DAY`, `candles_10min`
for `MINUTE_10`, etc. (the
`resolution` -> table-name mapping is in `igmarket/candle_db.py` /
`igmarket/constants/resolutions.py`). The resolution isn't stored as a column —
the table name encodes it:

| column | notes |
| --- | --- |
| `epic` | e.g. `IX.D.NASDAQ.IFA.IP` |
| `snapshot_time_utc` | text, UTC, `YYYY-MM-DDTHH:MM:SS` |
| `{open,high,low,close}_{bid,ask,mid}_price`, `last_traded_volume` | flattened price columns, same as the CSV output — directly queryable in SQL |

Prices are the bid/ask mid, `(bid + ask) / 2` — IG dealing prices, not the
underlying cash index.

## Setup

Uses [uv](https://docs.astral.sh/uv/). From the repo root:

```
uv sync --extra dev
```

That creates `.venv/`, installs the pinned deps from `uv.lock` — runtime
(`requests`, `python-dotenv`, `pandas`, `numpy`, `matplotlib`, `yfinance`)
plus the `dev` extra (`pytest`, `jupyter`, `nbconvert`) — and the `igmarket`
package itself, editable. Re-run it after changing dependencies (`uv add …`
or editing `pyproject.toml`). Commands below use `uv run`, which executes in
that environment — no manual `activate` needed.

> No uv? `python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"`,
> then drop the `uv run` prefix from every command below.

Then copy `.env.sample` to `.env` (git-ignored) and fill it in:

```
cp .env.sample .env
```

```
IG_API_KEY=...
IG_USERNAME=...
IG_PASSWORD=...
IG_ACCOUNT_TYPE=demo   # or "live" — completely separate credentials and data
```

`.env` also carries optional settings (each with a default in
`igmarket/config.py`, see `.env.sample`): `IG_EPIC`, `IG_SAVE_CSV`, and
`IG_RESOLUTION` (shared by all four IG notebooks). `01_download_prices.ipynb`
also reads its download window from `.env`: `IG_START` (required, UTC,
`"YYYY-MM-DD"` or `"YYYY-MM-DDTHH:MM:SS"`) and `IG_END` (optional, blank
means now; a bare date is rolled to `23:59:59` that day). `IG_DAYS_BACK` and
`IG_SAVE_DB` are still parsed but unused by any notebook.

## Running

```
uv sync --extra dev                                                                   # once per environment
uv run jupyter lab                                                                    # interactive
uv run jupyter nbconvert --to notebook --execute --inplace 01_download_prices.ipynb   # headless
```

`uv run` executes in the project venv, so the notebook kernel (the default
**Python 3 (ipykernel)**) can `import igmarket`. `igmarket/config.py` anchors
`.env` and `data/` to the repo root, so the notebooks find the same files
even if a kernel starts outside the repo root.

- `01_download_prices.ipynb` needs a valid `.env` and network access to IG.
  The window and resolution (`IG_START`, `IG_END`, `IG_RESOLUTION`) and
  `EPIC` / `SAVE_CSV` toggle all come from `.env` (defaults in
  `igmarket/config.py`) — the config cell prints what it loaded so a stale
  `.env` edit is visible before the API call runs. It writes only the CSV —
  load it into the DB with `02_import_csv_to_db.ipynb`.
- `03_view_ig_prices.ipynb` only needs `data/ig_market_data.db` to exist.
- `02_import_csv_to_db.ipynb` needs a `data/ig_*.csv` to import and a `.env`
  (for `igmarket.config`); it imports the newest such CSV by default.
- `04_backtest_strategy.ipynb` needs `data/ig_market_data.db` populated and a
  `.env`; set `START` / `END` and the strategy in its first config cell.
- `05_download_yahoo_finance.ipynb` needs network access to Yahoo Finance but
  no `.env` — set `TICKER` / `PERIOD` / `INTERVAL` directly in its
  parameters cell. Always writes a CSV; not part of the `data/ig_market_data.db`
  pipeline.

## Tests

```
uv run pytest
```

Offline — in-memory SQLite and synthetic price frames, no `.env` or network.

## Reference

- [`doc/ig/ig-api.md`](doc/ig/ig-api.md) — the IG REST endpoints these notebooks
  use (`POST /session`, paginated `GET /prices/{epic}`): headers, params,
  response shapes, resolutions, allowances.
- [`doc/ig/epics.md`](doc/ig/epics.md) — common IG epic IDs (US Tech 100, DAX,
  EUR/USD, gold, ...) and how to look one up with a market search.
- [`doc/yahoo/yahoo-finance.md`](doc/yahoo/yahoo-finance.md) — Yahoo Finance
  tickers, `period`/`interval` string values, and sub-daily history limits,
  for `05_download_yahoo_finance.ipynb`.
- [`doc/yahoo/yahoo-finance-api.md`](doc/yahoo/yahoo-finance-api.md) — the
  underlying (unofficial) Yahoo endpoint `yfinance` calls: the auth/crumb
  handshake, request/response shape, and reliability caveats.
