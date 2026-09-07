"""The backtest engine: next-open fills, fixed-size CFD P&L, and the
BuyHold / SmaCrossover reference strategies."""

import numpy as np
import pandas as pd
import pytest

from igmarket.backtest import BuyHold, SmaCrossover, run_backtest


def _ramp(n=260, start="2021-01-01", step=1.0):
    idx = pd.date_range(start, periods=n, freq="D")
    close = pd.Series(np.arange(n, dtype=float) * step + 100.0, index=idx)
    return pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1, "close": close}
    )


def test_buy_hold_profit_matches_point_move():
    df = _ramp()
    res = run_backtest(df, BuyHold(), initial_funding=20_000.0, point_value=1.0,
                       size=1.0, fee_bps=0.0)
    # entered at bar 1's open (next-open fill), marked out at the last close.
    expected = df["close"].iloc[-1] - df["open"].iloc[1]
    assert res.stats["n_trades"] == 1
    assert res.equity.iloc[-1] == pytest.approx(20_000.0 + expected)
    assert res.stats["final_funding"] == pytest.approx(res.equity.iloc[-1])


def test_signal_is_shifted_one_bar_no_lookahead():
    df = _ramp(n=10)

    class LongFromBar3(SmaCrossover.__bases__[0]):  # subclass Strategy
        name = "long from bar 3"

        def signal(self, d):
            s = pd.Series(0.0, index=d.index)
            s.iloc[3:] = 1.0
            return s

    res = run_backtest(df, LongFromBar3(), fee_bps=0.0)
    # signal flips on bar 3 -> fill on bar 4's open
    assert res.trades.loc[0, "entry_time"] == df.index[4]


def test_fee_is_charged_on_entry_and_exit():
    df = _ramp(n=60)
    free = run_backtest(df, BuyHold(), fee_bps=0.0).equity.iloc[-1]
    charged = run_backtest(df, BuyHold(), fee_bps=10.0).equity.iloc[-1]
    assert charged < free


def test_sma_crossover_rejects_fast_ge_slow():
    with pytest.raises(ValueError):
        SmaCrossover(fast=50, slow=50)


def test_summary_is_text_with_key_lines():
    res = run_backtest(_ramp(), SmaCrossover(10, 30), fee_bps=1.0)
    text = res.summary()
    assert isinstance(text, str)
    assert "final funding" in text
    assert "max drawdown" in text
