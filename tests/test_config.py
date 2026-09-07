"""Config helpers that don't need a real .env."""

from datetime import datetime
from pathlib import Path

from igmarket.config import Config, _epic_slug


def _cfg(tmp_path):
    return Config(
        env_path=tmp_path / ".env",
        api_key="k", username="u", password="p", account_type="demo",
        epic="IX.D.NASDAQ.IFA.IP", resolution="DAY", days_back=1,
        save_csv=True, save_db=False,
        data_dir=tmp_path / "data", csv_path=tmp_path / "x.csv",
        db_path=tmp_path / "data" / "ig_market_data.db",
    )


def test_epic_slug():
    assert _epic_slug("IX.D.NASDAQ.IFA.IP") == "nasdaq"
    assert _epic_slug("CS.D.EURUSD.CFD.IP") == "eurusd"
    assert _epic_slug("WEIRD") == "weird"


def test_csv_path_for_uses_resolution_suffix_and_data_dir(tmp_path):
    cfg = _cfg(tmp_path)
    p = cfg.csv_path_for("MINUTE_10")
    assert p.parent == cfg.data_dir
    assert p.name.startswith("ig_nasdaq_10min_")
    assert p.suffix == ".csv"


def test_csv_path_for_epic_override_and_unknown_resolution(tmp_path):
    cfg = _cfg(tmp_path)
    assert cfg.csv_path_for("DAY", epic="CS.D.EURUSD.CFD.IP").name.startswith(
        "ig_eurusd_daily_"
    )
    # unknown resolution falls back to the lowercased value
    assert "_fortnight_" in cfg.csv_path_for("FORTNIGHT").name


def test_csv_path_for_is_timestamped(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)

    class _FixedClock:
        @staticmethod
        def now():
            return datetime(2024, 3, 4, 5, 6, 7)

    monkeypatch.setattr("igmarket.config.datetime", _FixedClock)
    assert cfg.csv_path_for("DAY").name == "ig_nasdaq_daily_20240304050607.csv"
