"""Valid `period` strings for yfinance's Ticker.history(period=...), used as
`PERIOD` in 05_yahoo_download_finance.ipynb."""


class YahooPeriod:
    """`period` values yfinance's Ticker.history() accepts."""
    DAY_1 = "1d"
    DAY_5 = "5d"
    MONTH_1 = "1mo"
    MONTH_3 = "3mo"
    MONTH_6 = "6mo"
    YEAR_1 = "1y"
    YEAR_2 = "2y"
    YEAR_5 = "5y"
    YEAR_10 = "10y"
    YTD = "ytd"
    MAX = "max"


VALID_PERIODS = (
    YahooPeriod.DAY_1, YahooPeriod.DAY_5,
    YahooPeriod.MONTH_1, YahooPeriod.MONTH_3, YahooPeriod.MONTH_6,
    YahooPeriod.YEAR_1, YahooPeriod.YEAR_2, YahooPeriod.YEAR_5, YahooPeriod.YEAR_10,
    YahooPeriod.YTD, YahooPeriod.MAX,
)
