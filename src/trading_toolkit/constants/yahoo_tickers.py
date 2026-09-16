"""Common Yahoo Finance index tickers, for use as `TICKER` in
05_yahoo_download_finance.ipynb. See doc/yahoo/yahoo-finance.md for details
on each index and where the ticker was confirmed."""


class YahooTicker:
    """Common Yahoo Finance index tickers. Any other ticker `yfinance`
    supports also works as a plain string."""
    NASDAQ_100 = "^NDX"
    SP500 = "^GSPC"
    DOW_JONES = "^DJI"
    NASDAQ_COMPOSITE = "^IXIC"
    RUSSELL_2000 = "^RUT"
    VIX = "^VIX"
    ASX_100 = "^ATOI"
    ASX_200 = "^AXJO"
    NIKKEI_225 = "^N225"
    HANG_SENG = "^HSI"
    FTSE_100 = "^FTSE"
    DAX40 = "^GDAXI"
    SHANGHAI_COMPOSITE = "000001.SS"
