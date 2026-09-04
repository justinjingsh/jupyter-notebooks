# jupyter-notebooks

Standalone Jupyter notebooks for pulling and inspecting IG Markets price history
(currently the NASDAQ 100 index CFD, `IX.D.NASDAQ.IFA.IP`).

## Notebooks

| Notebook | Role |
| --- | --- |
| `download_ig_prices.ipynb` | Downloads candles from the IG REST API into a timestamped `data/ig_<epic-slug>_<resolution-suffix>_<timestamp>.csv` and/or `data/ig_market_data.db`. |
| `view_ig_prices.ipynb` | Reads `data/ig_market_data.db`, flattens candles to OHLC, and draws a candlestick chart with a volume panel. |
| `import_csv_to_db.ipynb` | Loads one `data/ig_*.csv` written by the download notebook into `data/ig_market_data.db` (offline; `INSERT OR IGNORE`, so re-running is a no-op). |
| `backtest_strategy.ipynb` | Backtests a long/flat strategy over a chosen window of the `data/ig_market_data.db` history (fixed-size CFD model, engine in `backtest.py`); shows a metrics summary, trade list, price / funding / drawdown charts, and a multi-strategy comparison table. |

All four share `data/ig_market_data.db`, where each resolution gets its own
table — `candles_1d` for `DAY`, `candles_10min` for `MINUTE_10`, etc. (the
`resolution` -> table-name mapping is in `candle_db.py` /
`constants/resolutions.py`):

| column | notes |
| --- | --- |
| `epic` | e.g. `IX.D.NASDAQ.IFA.IP` |
| `resolution` | the IG resolution this table holds, e.g. `DAY` — redundant with the table name, kept for convenience |
| `snapshot_time_utc` | text, UTC, `YYYY-MM-DDTHH:MM:SS` |
| `{open,high,low,close}_{bid,ask,mid}_price`, `last_traded_volume` | flattened price columns, same as the CSV output — directly queryable in SQL |
| `data` | raw IG candle JSON (`openPrice`/`closePrice`/`highPrice`/`lowPrice` as `{bid, ask, lastTraded}`, plus `lastTradedVolume`) |

Prices are the bid/ask mid, `(bid + ask) / 2` — IG dealing prices, not the
underlying cash index.

## Setup

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

`.env` also carries `download_ig_prices.ipynb`'s run config — `IG_EPIC`,
`IG_RESOLUTION`, `IG_DAYS_BACK`, `IG_SAVE_CSV`, `IG_SAVE_DB` — each optional,
falling back to a default in `config.py` (see `.env.sample`).

Dependencies are installed ad hoc (no requirements file); each notebook has
`%pip install` fallbacks. The download path needs `requests` + `python-dotenv`;
the chart and backtest cells need `pandas` + `matplotlib`.

## Running

Open in Jupyter, or run headless:

```
python -m jupyter nbconvert --to notebook --execute --inplace download_ig_prices.ipynb
```

`download_ig_prices.ipynb` needs a valid `.env` and network access to IG.
Set `IG_EPIC` / `IG_RESOLUTION` / `IG_DAYS_BACK` (and `IG_SAVE_CSV` /
`IG_SAVE_DB`) in `.env` to change what it pulls; unset, they fall back to the
defaults in `config.py` (`IG_DAYS_BACK` defaults to `1`).
`view_ig_prices.ipynb` only needs `data/ig_market_data.db` to exist.
`import_csv_to_db.ipynb` needs a `data/ig_*.csv` to import and a `.env` (for
`config.py`); it imports the newest such CSV by default.
`backtest_strategy.ipynb` needs `data/ig_market_data.db` populated and a
`.env`; set `START` / `END` and the strategy in its first code cell.

## Reference

- [`doc/ig-api.md`](doc/ig-api.md) — the IG REST endpoints these notebooks use
  (`POST /session`, paginated `GET /prices/{epic}`): headers, params, response
  shapes, resolutions, allowances.
- [`doc/epics.md`](doc/epics.md) — common IG epic IDs (US Tech 100, DAX, EUR/USD,
  gold, ...) and how to look one up with a market search.
