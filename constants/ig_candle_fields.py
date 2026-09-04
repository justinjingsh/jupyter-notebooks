"""Raw IG candle JSON field names, as returned by GET /prices/{epic}."""


class CandleField:
    """Raw IG candle JSON field names."""
    SNAPSHOT_TIME_UTC = "snapshotTimeUTC"
    OPEN_PRICE = "openPrice"
    HIGH_PRICE = "highPrice"
    LOW_PRICE = "lowPrice"
    CLOSE_PRICE = "closePrice"
    LAST_TRADED_VOLUME = "lastTradedVolume"


class PriceField:
    """Field names within an IG candle's open/high/low/close price node."""
    BID = "bid"
    ASK = "ask"
