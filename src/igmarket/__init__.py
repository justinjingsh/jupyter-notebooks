"""IG Markets price-history toolkit: download candles from the IG REST API,
store them in per-resolution SQLite tables, and backtest long/flat strategies.

The runnable entry points are the ``0N_*.ipynb`` notebooks at the repo root;
this package is the shared library they import (``config``, ``ig_session``,
``candle_csv``, ``candle_db``, ``backtest``, and ``constants``)."""
