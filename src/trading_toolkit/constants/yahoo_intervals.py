"""Valid `interval` strings for yfinance's Ticker.history(interval=...), used
as `INTERVAL` in 05_yahoo_download_finance.ipynb. Intraday intervals only
cover recent history - see doc/yahoo/yahoo-finance.md."""


class YahooInterval:
    """`interval` values yfinance's Ticker.history() accepts."""
    MINUTE_1 = "1m"
    MINUTE_2 = "2m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    MINUTE_60 = "60m"
    MINUTE_90 = "90m"
    HOUR_1 = "1h"
    DAY_1 = "1d"
    DAY_5 = "5d"
    WEEK_1 = "1wk"
    MONTH_1 = "1mo"
    MONTH_3 = "3mo"


VALID_INTERVALS = (
    YahooInterval.MINUTE_1, YahooInterval.MINUTE_2, YahooInterval.MINUTE_5,
    YahooInterval.MINUTE_15, YahooInterval.MINUTE_30, YahooInterval.MINUTE_60,
    YahooInterval.MINUTE_90, YahooInterval.HOUR_1,
    YahooInterval.DAY_1, YahooInterval.DAY_5,
    YahooInterval.WEEK_1, YahooInterval.MONTH_1, YahooInterval.MONTH_3,
)
