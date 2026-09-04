"""A minimal long/flat backtester for the candles stored in
`data/ig_market_data.db` (read via `candle_db.load_candles`).

Position model - a CFD-style fixed-size position, not equity fractions:

- **Funding** - the account starts with `initial_funding` in the account
  currency (default 20,000 AUD). This is the balance that P&L is added to /
  taken from; it is not the position notional.
- **Point value** - `point_value` is the account-currency P&L per 1.0 index
  point, per contract (default 1.0 AUD/point). IG's "US Tech 100 Cash" at
  1 AUD/point is the worked case.
- **Size** - `size` contracts are held whenever the strategy is long, and
  0 when it is flat (no shorting, no leverage beyond what `size` implies, no
  pyramiding). P&L of one round trip = `(exit - entry) * point_value * size`.
- **Next-open fills** - a strategy sees data up to a bar's close; the trade
  it implies is executed at the *next* bar's open, so there is no
  look-ahead.
- **Cost** - `fee_bps` basis points of notional (`price * point_value *
  size`) is charged on every entry and every exit; no other slippage /
  spread model (prices are already the bid/ask mid - see `candle_db`).
- Annualised figures use the *observed* bar frequency of the slice.

`run_backtest(df, strategy, ...) -> BacktestResult`. Strategies subclass
`Strategy` and implement `.signal(df) -> Series` of desired position.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from constants.ohlc_fields import OHLCField

_TRADE_COLUMNS = [
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


class Strategy:
    """Base class. `signal(df)` returns a Series aligned to `df.index` giving
    the desired position for each bar in `[0, 1]` (`1` = long `size`
    contracts, `0` = flat), using only data up to and including that bar's
    close. The engine shifts the series one bar so fills land on the next
    open."""

    name = "strategy"

    def signal(self, df):  # pragma: no cover - interface
        raise NotImplementedError


class BuyHold(Strategy):
    """Long from the first bar to the last - the benchmark."""

    name = "buy & hold"

    def signal(self, df):
        return pd.Series(1.0, index=df.index)


class SmaCrossover(Strategy):
    """Long while the fast simple moving average of the close is above the
    slow one, flat otherwise. The classic trend-following starting point."""

    def __init__(self, fast=20, slow=50):
        if fast >= slow:
            raise ValueError(f"fast ({fast}) must be shorter than slow ({slow})")
        self.fast = fast
        self.slow = slow
        self.name = f"SMA {fast}/{slow} crossover"

    def signal(self, df):
        close = df[OHLCField.CLOSE]
        fast = close.rolling(self.fast).mean()
        slow = close.rolling(self.slow).mean()
        # NaN during the warm-up window compares False -> position 0
        return (fast > slow).astype(float)


@dataclass
class BacktestResult:
    strategy: str
    equity: pd.Series           # account value per bar, in account currency
    target_position: pd.Series  # raw strategy signal (pre-shift), 0/1
    trades: pd.DataFrame        # one row per round-trip (last may be still open)
    stats: dict

    def summary(self):
        """A plain-text metrics block, one metric per line."""
        s = self.stats
        cur = s["currency"]
        traded = s["n_trades"]
        rows = [
            ("strategy", self.strategy),
            ("period", f"{s['start']:%Y-%m-%d} -> {s['end']:%Y-%m-%d}  ({s['bars']} bars)"),
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
            ("time in market", f"{s['exposure_pct']:.1f}%"),
            ("trades", f"{traded}"),
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


def _trade(index, entry_i, exit_i, entry_price, exit_price, point_value, size, is_open=False):
    return {
        "entry_time": index[entry_i],
        "exit_time": index[exit_i],
        "entry_price": round(float(entry_price), 2),
        "exit_price": round(float(exit_price), 2),
        "points": round(float(exit_price - entry_price), 2),
        "pnl": round(float((exit_price - entry_price) * point_value * size), 2),
        "return_pct": (exit_price / entry_price - 1) * 100,
        "bars_held": int(exit_i - entry_i),
        "open": is_open,
    }


def _stats(equity, trades, df, exposure, initial_funding, point_value, size, currency):
    start, end = equity.index[0], equity.index[-1]
    years = max((end - start).days / 365.25, 1e-9)
    bars_per_year = len(equity) / years

    final = float(equity.iloc[-1])
    profit = final - initial_funding
    total_return = final / initial_funding - 1
    cagr = (final / initial_funding) ** (1 / years) - 1 if final > 0 else float("nan")

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
        "exposure_pct": exposure * 100,
        "n_trades": n,
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
):
    """Backtest `strategy` over `df` (OHLC mid-price columns, ascending
    DatetimeIndex - as built from `candle_db.load_candles`).

    `size` contracts are held while long; one point of the index is worth
    `point_value` in `currency` per contract. Returns a `BacktestResult`
    whose `.equity` is the account value (starting at `initial_funding`) bar
    by bar.
    """

    df = df.sort_index()
    index = df.index
    opens = df[OHLCField.OPEN].to_numpy(dtype=float)
    closes = df[OHLCField.CLOSE].to_numpy(dtype=float)

    target = strategy.signal(df).reindex(index).fillna(0.0).clip(0, 1)
    # position actually held entering each bar = previous bar's signal
    holding = np.concatenate([[False], (target.to_numpy() >= 0.5)[:-1]])

    balance = float(initial_funding)  # realised: funding +/- closed P&L - fees
    in_pos = False
    entry_price = None
    entry_i = None
    equity = np.empty(len(index))
    trades = []

    for i in range(len(index)):
        px_open = opens[i]
        if holding[i] and not in_pos:
            balance -= px_open * point_value * size * fee_bps / 1e4
            entry_price, entry_i = px_open, i
            in_pos = True
        elif not holding[i] and in_pos:
            pnl = (px_open - entry_price) * point_value * size
            balance += pnl - px_open * point_value * size * fee_bps / 1e4
            trades.append(_trade(index, entry_i, i, entry_price, px_open, point_value, size))
            in_pos = False
            entry_price = entry_i = None
        unrealised = (closes[i] - entry_price) * point_value * size if in_pos else 0.0
        equity[i] = balance + unrealised

    if in_pos:  # still in the market at the end - mark out at the last mid
        trades.append(
            _trade(index, entry_i, len(index) - 1, entry_price, closes[-1], point_value, size, is_open=True)
        )

    equity = pd.Series(equity, index=index, name="equity")
    trades_df = pd.DataFrame(trades, columns=_TRADE_COLUMNS)
    stats = _stats(
        equity, trades_df, df, float(holding.mean()),
        initial_funding, point_value, size, currency,
    )
    return BacktestResult(strategy.name, equity, target, trades_df, stats)
