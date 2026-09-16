"""market_db talks to a Postgres DB it doesn't own, so these tests fake the
psycopg2 connection/cursor rather than hitting a real database - offline,
like the rest of the suite."""

import pytest

from trading_toolkit.market_db import load_candles, table_name_for_resolution


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows
        self.executed = None

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def execute(self, sql, params):
        self.executed = (sql, params)

    def fetchall(self):
        return self._rows


class _FakeConnection:
    def __init__(self, rows):
        self._cursor = _FakeCursor(rows)

    def cursor(self):
        return self._cursor


def test_table_name_for_resolution():
    assert table_name_for_resolution("DAY") == "candles_day"
    assert table_name_for_resolution("MINUTE_10") == "candles_minute_10"


def test_unknown_resolution_raises():
    with pytest.raises(ValueError):
        table_name_for_resolution("FORTNIGHT")


def test_load_candles_yields_flat_ohlc_dicts_and_filters_by_provider_symbol():
    rows = [
        ("2024-01-02T00:00:00", 100.0, 105.0, 99.0, 102.0, 1_000_000),
        ("2024-01-01T00:00:00", 90.0, 95.0, 89.0, 92.0, 900_000),
    ]
    conn = _FakeConnection(rows)

    candles = list(load_candles(conn, "yahoo", "NASDAQ100", "DAY"))

    assert conn._cursor.executed[1] == ("yahoo", "NASDAQ100")
    assert "candles_day" in conn._cursor.executed[0]
    assert [c["snapshot_time_utc"] for c in candles] == [
        "2024-01-02T00:00:00",
        "2024-01-01T00:00:00",
    ]
    assert candles[0]["open"] == 100.0
    assert candles[0]["close"] == 102.0
    assert candles[0]["volume"] == 1_000_000
