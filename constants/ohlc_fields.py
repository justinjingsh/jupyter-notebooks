"""Key names for the flat OHLC dicts `candle_db.load_candles` yields - and so
the column names of the pandas DataFrame built from them in
view_ig_prices.ipynb. Kept here so the dict builder and the chart code that
indexes those columns can't drift apart."""


class OHLCField:
    """Keys of one flat OHLC candle dict from `candle_db.load_candles`."""
    EPIC = "epic"
    RESOLUTION = "resolution"
    SNAPSHOT_TIME_UTC = "snapshot_time_utc"
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    OPEN_MID_PRICE = "open_mid_price"
    HIGH_MID_PRICE = "high_mid_price"
    LOW_MID_PRICE = "low_mid_price"
    CLOSE_MID_PRICE = "close_mid_price"
    VOLUME = "volume"
