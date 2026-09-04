"""Flattened price columns for the per-resolution `candles_<suffix>` SQLite
tables (see candle_db.init_candles_table): (name, SQL type) pairs, kept as
their own list separate from constants/csv_headers.py's CSV_HEADERS so the
DB schema and the CSV schema can diverge independently even though they
match today."""

DB_HEADERS = [
    ("snapshot_time_utc", "TEXT NOT NULL"),
    ("open_bid_price", "REAL"), ("open_ask_price", "REAL"), ("open_mid_price", "REAL"),
    ("high_bid_price", "REAL"), ("high_ask_price", "REAL"), ("high_mid_price", "REAL"),
    ("low_bid_price", "REAL"), ("low_ask_price", "REAL"), ("low_mid_price", "REAL"),
    ("close_bid_price", "REAL"), ("close_ask_price", "REAL"), ("close_mid_price", "REAL"),
    ("last_traded_volume", "INTEGER"),
]
