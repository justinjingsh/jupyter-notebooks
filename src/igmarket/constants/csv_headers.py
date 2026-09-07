"""CSV column headers for the flattened IG candle rows written by
download_ig_prices.ipynb (see candle_csv.candle_to_row)."""

CSV_HEADERS = [
    "snapshot_time_utc",
    "open_bid_price", "open_ask_price", "open_mid_price",
    "high_bid_price", "high_ask_price", "high_mid_price",
    "low_bid_price", "low_ask_price", "low_mid_price",
    "close_bid_price", "close_ask_price", "close_mid_price",
    "last_traded_volume",
]
