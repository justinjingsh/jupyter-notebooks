# igmarket

A small library (`src/igmarket/`) plus Jupyter notebooks (`0N_*.ipynb`) for
pulling and inspecting IG Markets price history (currently the NASDAQ 100 index
CFD, `IX.D.NASDAQ.IFA.IP`).

## Layout

```
src/igmarket/     library: config, ig_session, candle_csv, candle_db, backtest, constants/
0N_*.ipynb        the runnable entry points (repo root), numbered in pipeline order
tests/            pytest suite (offline)
doc/              IG REST API notes, epic list
data/             git-ignored: downloaded CSV(s) + the SQLite DB
```

## Notebooks

| Notebook | Role |
| --- | --- |
| `01_download_ig_prices.ipynb` | Downloads candles from the IG REST API into a timestamped `data/ig_<epic-slug>_<resolution-suffix>_<timestamp>.csv` and/or `data/ig_market_data.db`. |
| `02_import_csv_to_db.ipynb` | Loads one `data/ig_*.csv` written by the download notebook into `data/ig_market_data.db` (offline; `INSERT OR IGNORE`, so re-running is a no-op). |
| `03_view_ig_prices.ipynb` | Reads `data/ig_market_data.db`, flattens candles to OHLC, and draws a candlestick chart with a volume panel. |
| `04_backtest_strategy.ipynb` | Backtests a long/flat strategy over a chosen window of the `data/ig_market_data.db` history (fixed-size CFD model, engine in `igmarket/backtest.py`); shows a metrics summary, trade list, price / funding / drawdown charts, and a multi-strategy comparison table. |

All four share `data/ig_market_data.db`, where each resolution gets its own
table — `candles_1d` for `DAY`, `candles_10min` for `MINUTE_10`, etc. (the
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

Install the package (editable) and the notebook toolchain from the repo root:

```
pip install -e ".[dev]"
```

The notebooks' first cell runs this for you (walking up to the repo root), so
you can also just open a notebook and run it.

Copy `.env.sample` to `.env` (git-ignored) and fill it in:

```
cp .env.sample .env
```

```
IG_API_KEY=...
IG_USERNAME=...
IG_PASSWORD=...
IG_ACCOUNT_TYPE=demo   # or "live" — completely separate credentials and data
```

`.env` also carries `01_download_ig_prices.ipynb`'s run config — `IG_EPIC`,
`IG_RESOLUTION`, `IG_DAYS_BACK`, `IG_SAVE_CSV`, `IG_SAVE_DB` — each optional,
falling back to a default in `igmarket/config.py` (see `.env.sample`).

## Running

Open in Jupyter, or run headless:

```
python -m jupyter nbconvert --to notebook --execute --inplace 01_download_ig_prices.ipynb
```

`igmarket/config.py` anchors `.env` and `data/` to the repo root, so the
notebooks find the same files even if a kernel starts outside the repo root.

- `01_download_ig_prices.ipynb` needs a valid `.env` and network access to IG.
  Set `IG_EPIC` / `IG_RESOLUTION` / `IG_DAYS_BACK` (and `IG_SAVE_CSV` /
  `IG_SAVE_DB`) in `.env` to change what it pulls; unset, they fall back to the
  defaults in `igmarket/config.py` (`IG_DAYS_BACK` defaults to `1`).
- `03_view_ig_prices.ipynb` only needs `data/ig_market_data.db` to exist.
- `02_import_csv_to_db.ipynb` needs a `data/ig_*.csv` to import and a `.env`
  (for `igmarket.config`); it imports the newest such CSV by default.
- `04_backtest_strategy.ipynb` needs `data/ig_market_data.db` populated and a
  `.env`; set `START` / `END` and the strategy in its first config cell.

## Tests

```
python -m pytest
```

Offline — in-memory SQLite and synthetic price frames, no `.env` or network.

## Reference

- [`doc/ig-api.md`](doc/ig-api.md) — the IG REST endpoints these notebooks use
  (`POST /session`, paginated `GET /prices/{epic}`): headers, params, response
  shapes, resolutions, allowances.
- [`doc/epics.md`](doc/epics.md) — common IG epic IDs (US Tech 100, DAX, EUR/USD,
  gold, ...) and how to look one up with a market search.
