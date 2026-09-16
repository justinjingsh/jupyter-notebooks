"""candle_db owns the resolution -> table-name mapping and the per-resolution
schema. A round trip through an in-memory SQLite DB exercises all three
public helpers without touching the filesystem or the network."""

import sqlite3

import pytest

from igmarket.candle_csv import candle_to_row
from igmarket.candle_db import (
    INSERT_COLUMNS,
    init_candles_table,
    load_candles,
    table_name_for_resolution,
)

EPIC = "IX.D.NASDAQ.IFA.IP"


def _candle(ts, close_bid, close_ask):
    node = {"bid": close_bid, "ask": close_ask}
    return {
        "snapshotTimeUTC": ts,
        "openPrice": node,
        "highPrice": node,
        "lowPrice": node,
        "closePrice": node,
        "lastTradedVolume": 10,
    }


def test_table_name_for_resolution():
    assert table_name_for_resolution("DAY") == "candles_1d"
    assert table_name_for_resolution("MINUTE_10") == "candles_10min"


def test_unknown_resolution_raises():
    with pytest.raises(KeyError):
        table_name_for_resolution("FORTNIGHT")


def test_init_insert_load_round_trip():
    conn = sqlite3.connect(":memory:")
    table = init_candles_table(conn, "DAY")
    assert table == "candles_1d"

    rows = [
        (EPIC, *candle_to_row(_candle("2024-01-02T00:00:00", 100.0, 102.0))),
        (EPIC, *candle_to_row(_candle("2024-01-01T00:00:00", 90.0, 92.0))),
    ]
    placeholders = ", ".join("?" for _ in INSERT_COLUMNS)
    conn.executemany(
        f"INSERT OR IGNORE INTO {table} ({', '.join(INSERT_COLUMNS)}) "
        f"VALUES ({placeholders})",
        rows,
    )
    conn.commit()

    loaded = list(load_candles(conn, "DAY", epic=EPIC))
    assert [c["snapshot_time_utc"] for c in loaded] == [
        "2024-01-01T00:00:00",
        "2024-01-02T00:00:00",
    ]
    assert loaded[0]["close"] == 91.0
    assert loaded[0]["close"] == loaded[0]["close_mid_price"]
    assert "resolution" not in loaded[0]


def test_insert_or_ignore_is_idempotent_on_epic_time_key():
    conn = sqlite3.connect(":memory:")
    table = init_candles_table(conn, "DAY")
    row = (EPIC, *candle_to_row(_candle("2024-01-01T00:00:00", 90.0, 92.0)))
    placeholders = ", ".join("?" for _ in INSERT_COLUMNS)
    sql = (
        f"INSERT OR IGNORE INTO {table} ({', '.join(INSERT_COLUMNS)}) "
        f"VALUES ({placeholders})"
    )
    conn.execute(sql, row)
    conn.execute(sql, row)
    conn.commit()

    assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 1
