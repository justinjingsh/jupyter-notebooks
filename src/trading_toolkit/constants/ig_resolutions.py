"""IG `resolution` values (GET /prices/{epic}, see doc/ig/ig-api.md), and the
map from each to the short suffix used in per-resolution `candles_<suffix>`
table names."""


class IGResolution:
    """`resolution` values IG's GET /prices/{epic} accepts."""
    SECOND = "SECOND"
    MINUTE = "MINUTE"
    MINUTE_2 = "MINUTE_2"
    MINUTE_3 = "MINUTE_3"
    MINUTE_5 = "MINUTE_5"
    MINUTE_10 = "MINUTE_10"
    MINUTE_15 = "MINUTE_15"
    MINUTE_30 = "MINUTE_30"
    HOUR = "HOUR"
    HOUR_2 = "HOUR_2"
    HOUR_3 = "HOUR_3"
    HOUR_4 = "HOUR_4"
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"


RESOLUTION_TABLE_SUFFIX = {
    "SECOND": "1s",
    "MINUTE": "1min",
    "MINUTE_2": "2min",
    "MINUTE_3": "3min",
    "MINUTE_5": "5min",
    "MINUTE_10": "10min",
    "MINUTE_15": "15min",
    "MINUTE_30": "30min",
    "HOUR": "1h",
    "HOUR_2": "2h",
    "HOUR_3": "3h",
    "HOUR_4": "4h",
    "DAY": "1d",
    "WEEK": "1w",
    "MONTH": "1mo",
}
