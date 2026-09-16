"""A long/short backtester for the strategies in
`ig_quant_trading.strategies` (the sibling ig-quant-trading repo,
installed editable - see pyproject.toml), over the candles stored in
`data/ig_market_data.db` (via `ig_candle_db.load_candles`) or
`quant-market-data` (via `market_db.load_candles`).

Trading rules - the same ones ig_quant_trading applies live
(`SignalTrader` with `CLOSE_ON_SIGNAL_REVERSAL = True`, one position per
epic), so a strategy copied there trades the way it backtested here:

- **Signals** - each bar the strategy says BUY (be long), SELL (be short) or
  HOLD (keep whatever is open). An opposite signal closes the open position
  and opens the reverse one at the same price.
- **Next-open fills** - a strategy sees data up to a bar's close; the trade
  it implies is executed at the *next* bar's open, so there is no
  look-ahead.
- **Session** - if the strategy has a `session` (or one is passed in), no
  position is opened outside it and any open one is closed at the first bar
  that starts outside it - ig_quant_trading's `TRADING_SESSIONS_UTC` does
  the same live.

Position model - a CFD-style fixed-size position, not equity fractions:

- **Funding** - the account starts with `initial_funding` in the account
  currency (default 20,000 AUD). This is the balance that P&L is added to /
  taken from; it is not the position notional.
- **Point value** - `point_value` is the account-currency P&L per 1.0 index
  point, per contract (default 1.0 AUD/point). IG's "US Tech 100 Cash" at
  1 AUD/point is the worked case.
- **Size** - `size` contracts, long or short; no pyramiding. P&L of one
  round trip = `(exit - entry) * point_value * size`, sign-flipped for a short.
- **Cost** - `fee_bps` basis points of notional (`price * point_value *
  size`) is charged on every entry and every exit (so a reversal pays twice);
  no other slippage / spread model (prices are already the bid/ask mid) and
  no overnight financing.
- Annualised figures use the *observed* bar frequency of the slice.

`run_backtest(df, strategy, ...) -> BacktestResult`.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ig_quant_trading.constants.direction import Direction
from ig_quant_trading.strategies.sessions import in_session

from trading_toolkit.constants.ig_ohlc_fields import OHLCField

_TRADE_COLUMNS = [
    "direction",
    "entry_time",
    "exit_time",
    "entry_price",
    "exit_price",
    "points",
    "pnl",
    "return_pct",
    "bars_held",
    "open",
]

_SIDE = {Direction.BUY: 1, Direction.SELL: -1}


@dataclass
class BacktestResult:
    strategy: str        # strategy.label, e.g. "SMA 10/30"
    equity: pd.Series    # account value per bar, in account currency
    signals: pd.Series   # raw strategy signal per bar (pre-shift): BUY / SELL / HOLD
    position: pd.Series  # position held during each bar: 1 long, -1 short, 0 flat
    trades: pd.DataFrame # one row per round-trip (last may be still open)
    stats: dict

    def summary(self):
        """A plain-text metrics block, one metric per line."""
        s = self.stats
        cur = s["currency"]
        traded = s["n_trades"]
        # daily bars -> dates only; intraday bars -> include the time
        daily = s["start"] == s["start"].normalize() and s["end"] == s["end"].normalize()
        fmt = "%Y-%m-%d" if daily else "%Y-%m-%d %H:%M"
        rows = [
            ("strategy", self.strategy),
            ("period", f"{s['start']:{fmt}} -> {s['end']:{fmt}}  ({s['bars']} bars)"),
            ("initial funding", f"{s['initial_funding']:,.2f} {cur}"),
            ("final funding", f"{s['final_funding']:,.2f} {cur}"),
            ("profit / loss", f"{s['profit']:+,.2f} {cur}  ({s['total_return_pct']:+.2f}%)"),
            ("buy & hold", f"{s['buy_hold_profit']:+,.2f} {cur}  ({s['buy_hold_return_pct']:+.2f}%)"),
            (
                "position size",
                f"{s['position_size']:g} @ {s['point_value']:g} {cur}/point"
                f"   (~{s['entry_leverage']:.2f}x funding at entry)",
            ),
            ("CAGR", f"{s['cagr_pct']:+.2f}%"),
            ("ann. volatility", f"{s['ann_volatility_pct']:.2f}%"),
            ("Sharpe (rf=0)", f"{s['sharpe']:.2f}"),
            ("max drawdown", f"{s['max_drawdown_pct']:.2f}%"),
            (
                "time in market",
                f"{s['exposure_pct']:.1f}%  (long {s['long_exposure_pct']:.1f}%, "
                f"short {s['short_exposure_pct']:.1f}%)",
            ),
            ("trades", f"{traded}  ({s['n_long_trades']} long, {s['n_short_trades']} short)"),
            ("win rate", f"{s['win_rate_pct']:.1f}%" if traded else "-"),
            (
                "avg / best / worst",
                (
                    f"{s['avg_trade_pnl']:+,.2f} / {s['best_trade_pnl']:+,.2f} / "
                    f"{s['worst_trade_pnl']:+,.2f} {cur}"
                    if traded
                    else "-"
                ),
            ),
        ]
        width = max(len(k) for k, _ in rows)
        return "\n".join(f"{k:<{width}} : {v}" for k, v in rows)


def _trade(index, side, entry_i, exit_i, entry_price, exit_price, point_value, size, is_open=False):
    points = (exit_price - entry_price) * side
    return {
        "direction": (Direction.BUY if side > 0 else Direction.SELL).value,
        "entry_time": index[entry_i],
        "exit_time": index[exit_i],
        "entry_price": round(float(entry_price), 2),
        "exit_price": round(float(exit_price), 2),
        "points": round(float(points), 2),
        "pnl": round(float(points * point_value * size), 2),
        "return_pct": points / entry_price * 100,
        "bars_held": int(exit_i - entry_i),
        "open": is_open,
    }


def _stats(equity, trades, df, held, initial_funding, point_value, size, currency):
    start, end = equity.index[0], equity.index[-1]
    # exact elapsed time, not whole days - intraday slices can span < 1 day
    years = max((end - start).total_seconds() / (365.25 * 86400), 1e-9)
    bars_per_year = len(equity) / years

    final = float(equity.iloc[-1])
    profit = final - initial_funding
    total_return = final / initial_funding - 1
    try:
        cagr = (final / initial_funding) ** (1 / years) - 1 if final > 0 else float("nan")
    except OverflowError:  # a tiny window annualises to an absurd number
        cagr = float("inf")

    per_bar = equity.pct_change().dropna()
    std = per_bar.std()
    ann_vol = std * np.sqrt(bars_per_year)
    sharpe = (per_bar.mean() / std * np.sqrt(bars_per_year)) if std else float("nan")

    drawdown = equity / equity.cummax() - 1

    close = df[OHLCField.CLOSE]
    buy_hold_profit = float((close.iloc[-1] - close.iloc[0]) * point_value * size)
    entry_notional = float(close.iloc[0] * point_value * size)

    n = len(trades)
    pnl = trades["pnl"] if n else pd.Series(dtype=float)
    ret = trades["return_pct"] if n else pd.Series(dtype=float)
    return {
        "start": start,
        "end": end,
        "bars": len(equity),
        "currency": currency,
        "initial_funding": float(initial_funding),
        "final_funding": final,
        "profit": profit,
        "total_return_pct": total_return * 100,
        "buy_hold_profit": buy_hold_profit,
        "buy_hold_return_pct": buy_hold_profit / initial_funding * 100,
        "position_size": float(size),
        "point_value": float(point_value),
        "entry_notional": entry_notional,
        "entry_leverage": entry_notional / initial_funding,
        "cagr_pct": cagr * 100,
        "ann_volatility_pct": ann_vol * 100,
        "sharpe": sharpe,
        "max_drawdown_pct": drawdown.min() * 100,
        "exposure_pct": float((held != 0).mean() * 100),
        "long_exposure_pct": float((held > 0).mean() * 100),
        "short_exposure_pct": float((held < 0).mean() * 100),
        "n_trades": n,
        "n_long_trades": int((trades["direction"] == Direction.BUY.value).sum()) if n else 0,
        "n_short_trades": int((trades["direction"] == Direction.SELL.value).sum()) if n else 0,
        "win_rate_pct": float((pnl > 0).mean() * 100) if n else float("nan"),
        "avg_trade_pnl": float(pnl.mean()) if n else float("nan"),
        "best_trade_pnl": float(pnl.max()) if n else float("nan"),
        "worst_trade_pnl": float(pnl.min()) if n else float("nan"),
        "avg_trade_pct": float(ret.mean()) if n else float("nan"),
    }


def run_backtest(
    df,
    strategy,
    initial_funding=20_000.0,
    point_value=1.0,
    size=1.0,
    fee_bps=1.0,
    currency="AUD",
    session=None,
):
    """Backtest `strategy` (an `ig_quant_trading.strategies.VectorizedStrategy`) over
    `df` (OHLC mid-price columns, ascending naive-UTC DatetimeIndex - as
    built from `ig_candle_db.load_candles` / `market_db.load_candles`).

    `size` contracts are held while long or short; one point of the index is
    worth `point_value` in `currency` per contract. `session` is an
    `(open, close, tz)` tuple (see `ig_quant_trading.strategies.sessions`), defaulting
    to `strategy.session`. Returns a `BacktestResult` whose `.equity` is the
    account value (starting at `initial_funding`) bar by bar.
    """

    df = df.sort_index()
    index = df.index
    n = len(index)
    opens = df[OHLCField.OPEN].to_numpy(dtype=float)
    closes = df[OHLCField.CLOSE].to_numpy(dtype=float)

    # built element by element: numpy/pandas fills (fillna, np.full, ...)
    # truncate a str-backed enum to its dtype width
    signals = pd.Series(
        [Direction.HOLD if pd.isna(v) else Direction(v) for v in strategy.signals(df).reindex(index)],
        index=index, dtype=object,
    )
    # signal acted on at each bar's open = previous bar's signal
    acted = np.empty(n, dtype=object)
    acted.fill(Direction.HOLD)
    acted[1:] = signals.to_numpy()[:-1]
    session = session if session is not None else getattr(strategy, "session", None)
    tradable = in_session(index, *session) if session else np.ones(n, dtype=bool)

    balance = float(initial_funding)  # realised: funding +/- closed P&L - fees
    side = 0  # 1 long, -1 short, 0 flat
    entry_price = entry_i = None
    equity = np.empty(n)
    held = np.zeros(n, dtype=int)
    trades = []

    def fee(price):
        return price * point_value * size * fee_bps / 1e4

    for i in range(n):
        px_open = opens[i]
        target = _SIDE.get(acted[i], side) if tradable[i] else 0
        if target != side:
            if side:
                balance += (px_open - entry_price) * side * point_value * size - fee(px_open)
                trades.append(_trade(index, side, entry_i, i, entry_price, px_open, point_value, size))
            if target:
                balance -= fee(px_open)
                entry_price, entry_i = px_open, i
            else:
                entry_price = entry_i = None
            side = target
        held[i] = side
        unrealised = (closes[i] - entry_price) * side * point_value * size if side else 0.0
        equity[i] = balance + unrealised

    if side:  # still in the market at the end - mark out at the last mid
        trades.append(
            _trade(index, side, entry_i, n - 1, entry_price, closes[-1], point_value, size, is_open=True)
        )

    equity = pd.Series(equity, index=index, name="equity")
    position = pd.Series(held, index=index, name="position")
    trades_df = pd.DataFrame(trades, columns=_TRADE_COLUMNS)
    stats = _stats(equity, trades_df, df, held, initial_funding, point_value, size, currency)
    return BacktestResult(strategy.label, equity, signals, position, trades_df, stats)
