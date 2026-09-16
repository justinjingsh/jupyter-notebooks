"""yahoo_finance path/save helpers that don't need network access."""

from datetime import datetime

import pandas as pd

from igmarket import yahoo_finance


def test_csv_path_for_uses_ticker_slug_and_interval(tmp_path):
    p = yahoo_finance.csv_path_for("^NDX", "1d", data_dir=tmp_path)
    assert p.parent == tmp_path
    assert p.name.startswith("yahoo_ndx_1d_")
    assert p.suffix == ".csv"


def test_csv_path_for_creates_data_dir(tmp_path):
    data_dir = tmp_path / "data"
    assert not data_dir.exists()
    yahoo_finance.csv_path_for("^NDX", "1d", data_dir=data_dir)
    assert data_dir.exists()


def test_csv_path_for_is_timestamped(tmp_path, monkeypatch):
    class _FixedClock:
        @staticmethod
        def now():
            return datetime(2024, 3, 4, 5, 6, 7)

    monkeypatch.setattr("igmarket.yahoo_finance.datetime", _FixedClock)
    p = yahoo_finance.csv_path_for("^NDX", "1d", data_dir=tmp_path)
    assert p.name == "yahoo_ndx_1d_20240304050607.csv"


def test_save_csv_writes_indexed_frame(tmp_path):
    df = pd.DataFrame(
        {"Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5], "Volume": [100]},
        index=pd.DatetimeIndex(["2024-01-02"], name="Date"),
    )
    path = tmp_path / "out.csv"
    result = yahoo_finance.save_csv(df, path)

    assert result == path
    written = pd.read_csv(path)
    assert list(written.columns) == ["Date", "Open", "High", "Low", "Close", "Volume"]
    assert written.loc[0, "Close"] == 1.5
