"""The backtest engine: next-open fills, long/short reversals, session
force-close, fixed-size CFD P&L."""

import numpy as np
import pandas as pd
import pytest

from ig_quant_trading.constants.direction import Direction
from ig_quant_trading.strategies import (
    BuyHoldStrategy,
    OpeningRangeBreakoutStrategy,
    SessionFilter,
    SMAStrategy,
    VectorizedStrategy,
)

from trading_toolkit.ig_backtest import run_backtest


def _ramp(n=260, start="2021-01-01", step=1.0):
    idx = pd.date_range(start, periods=n, freq="D")
    close = pd.Series(np.arange(n, dtype=float) * step + 100.0, index=idx)
    return pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1, "close": close}
    )


class _Scripted(VectorizedStrategy):
    """Emits a fixed list of signals, one per bar."""

    name = "scripted"

    def __init__(self, script, session=None):
        self.script = script
        self.session = session

    def signals(self, frame):
        return pd.Series(self.script, index=frame.index, dtype=object)


B, S, H = Direction.BUY, Direction.SELL, Direction.HOLD


def test_buy_hold_profit_matches_point_move():
    df = _ramp()
    res = run_backtest(df, BuyHoldStrategy(), initial_funding=20_000.0, point_value=1.0,
                       size=1.0, fee_bps=0.0)
    # entered at bar 1's open (next-open fill), marked out at the last close.
    expected = df["close"].iloc[-1] - df["open"].iloc[1]
    assert res.stats["n_trades"] == 1
    assert res.equity.iloc[-1] == pytest.approx(20_000.0 + expected)
    assert res.stats["final_funding"] == pytest.approx(res.equity.iloc[-1])


def test_signal_is_shifted_one_bar_no_lookahead():
    df = _ramp(n=10)
    res = run_backtest(df, _Scripted([H, H, H, B, B, B, B, B, B, B]), fee_bps=0.0)
    # BUY first seen on bar 3 -> fill on bar 4's open
    assert res.trades.loc[0, "entry_time"] == df.index[4]
    assert list(res.position.iloc[:5]) == [0, 0, 0, 0, 1]


def test_hold_keeps_the_open_position():
    df = _ramp(n=8)
    res = run_backtest(df, _Scripted([B, H, H, H, H, H, H, H]), fee_bps=0.0)
    assert list(res.position) == [0, 1, 1, 1, 1, 1, 1, 1]
    assert res.stats["n_trades"] == 1 and res.trades.loc[0, "open"]


def test_opposite_signal_reverses_at_the_same_price():
    df = _ramp(n=8)  # rising 1 point a bar
    res = run_backtest(df, _Scripted([B, H, S, H, H, H, H, H]), fee_bps=0.0)
    assert list(res.position) == [0, 1, 1, -1, -1, -1, -1, -1]
    long_, short = res.trades.iloc[0], res.trades.iloc[1]
    assert long_["direction"] == "BUY" and short["direction"] == "SELL"
    assert long_["exit_time"] == short["entry_time"] == df.index[3]
    assert long_["pnl"] == pytest.approx(2.0)     # 101 -> 103
    assert short["pnl"] == pytest.approx(-4.0)    # short 103, marked at 107
    assert res.equity.iloc[-1] == pytest.approx(20_000.0 - 2.0)
    assert res.stats["n_long_trades"] == 1 and res.stats["n_short_trades"] == 1


def test_session_blocks_entries_and_force_closes():
    idx = pd.date_range("2026-09-01 13:00", periods=8, freq="10min")  # 09:00 NY
    df = pd.DataFrame({"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0}, index=idx)
    # 13:30 UTC = 09:30 NY opens it; close it at 14:10 = 10:10 NY
    res = run_backtest(df, _Scripted([B] * 8, session=("09:30", "10:10", "America/New_York")),
                       fee_bps=0.0)
    assert list(res.position) == [0, 0, 0, 1, 1, 1, 1, 0]
    assert res.trades.loc[0, "exit_time"] == idx[7] and not res.trades.loc[0, "open"]


def _bars_10min(close):
    close = np.asarray(close, dtype=float)
    idx = pd.date_range("2026-09-01 00:00", periods=len(close), freq="10min")
    open_ = np.concatenate([[close[0]], close[:-1]])
    return pd.DataFrame({"open": open_, "high": np.maximum(open_, close) + 0.5,
                         "low": np.minimum(open_, close) - 0.5, "close": close,
                         "volume": 100}, index=idx)


def test_strategy_session_is_applied_by_default():
    df = _bars_10min(np.linspace(100, 110, 144))  # one full UTC day
    res = run_backtest(df, SessionFilter(BuyHoldStrategy()), fee_bps=0.0)
    assert res.stats["n_trades"] == 1
    trade = res.trades.iloc[0]
    assert trade["entry_time"] == pd.Timestamp("2026-09-01 13:40")  # signal 13:30, next open
    assert trade["exit_time"] == pd.Timestamp("2026-09-01 20:00")   # 16:00 New York
    assert not trade["open"]


@pytest.mark.parametrize("direction, side", [(1, "BUY"), (-1, "SELL")])
def test_orb_trades_one_side_a_day_and_closes_by_16h(direction, side):
    close = np.full(144, 100.0)
    open_i = 13 * 6 + 3            # 13:30 UTC bar
    close[open_i + 3:] = 100 + direction * np.linspace(1, 20, 144 - open_i - 3)
    res = run_backtest(_bars_10min(close), OpeningRangeBreakoutStrategy(range_minutes=30), fee_bps=0.0)
    assert list(res.trades["direction"]) == [side]
    assert res.trades.iloc[0]["pnl"] > 0
    assert res.trades.iloc[0]["exit_time"] == pd.Timestamp("2026-09-01 20:00")


def test_fee_is_charged_on_entry_and_exit():
    df = _ramp(n=60)
    free = run_backtest(df, BuyHoldStrategy(), fee_bps=0.0).equity.iloc[-1]
    charged = run_backtest(df, BuyHoldStrategy(), fee_bps=10.0).equity.iloc[-1]
    assert charged < free


def test_summary_is_text_with_key_lines():
    res = run_backtest(_ramp(), SMAStrategy(10, 30), fee_bps=1.0)
    text = res.summary()
    assert res.strategy == "SMA 10/30"
    assert isinstance(text, str)
    assert "final funding" in text
    assert "max drawdown" in text
