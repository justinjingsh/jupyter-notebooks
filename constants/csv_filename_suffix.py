"""Maps IG `resolution` values (GET /prices/{epic}, see doc/ig-api.md) to the
suffix used in the timestamped download CSV filename (see config.py's
Config.csv_path). Separate from constants/resolutions.py's
RESOLUTION_TABLE_SUFFIX, which names DB tables and favours compact suffixes
(`1d`) over the more readable ones used here (`daily`)."""

RESOLUTION_CSV_SUFFIX = {
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
    "DAY": "daily",
    "WEEK": "weekly",
    "MONTH": "monthly",
}
