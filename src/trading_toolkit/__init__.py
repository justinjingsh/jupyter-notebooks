"""IG Markets price-history toolkit: download candles from the IG REST API,
store them in per-resolution SQLite tables, and backtest long/short strategies
from ig_quant_trading (``ig_quant_trading.strategies``).

The runnable entry points are the ``0N_*.ipynb`` notebooks at the repo root;
this package is the shared library they import (``ig_config``, ``ig_session``,
``ig_candle_csv``, ``ig_candle_db``, ``ig_backtest``, ``ig_timeutil``,
``constants``, and ``yahoo_finance``)."""
