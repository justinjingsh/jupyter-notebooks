"""Maps IG `resolution` values (GET /prices/{epic}, see doc/ig-api.md) to the
short suffix used in per-resolution `candles_<suffix>` table names."""

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
