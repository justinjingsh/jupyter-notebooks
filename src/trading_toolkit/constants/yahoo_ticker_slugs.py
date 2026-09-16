"""Maps well-known Yahoo Finance tickers (`YahooTicker`) to the filename slug
`yahoo_finance.csv_path_for()` uses, e.g. `^NDX` -> `nasdaq100`, `^GDAXI` ->
`dax40`. A ticker not in this mapping (a share, ETF, FX pair, or any other
index not listed here) falls back to stripping the `^` prefix and
lowercasing - see `csv_path_for()`."""

from trading_toolkit.constants.yahoo_tickers import YahooTicker

TICKER_SLUGS = {
    YahooTicker.NASDAQ_100: "nasdaq100",
    YahooTicker.SP500: "sp500",
    YahooTicker.DOW_JONES: "dowjones",
    YahooTicker.NASDAQ_COMPOSITE: "nasdaqcomposite",
    YahooTicker.RUSSELL_2000: "russell2000",
    YahooTicker.VIX: "vix",
    YahooTicker.ASX_100: "asx100",
    YahooTicker.ASX_200: "asx200",
    YahooTicker.NIKKEI_225: "nikkei225",
    YahooTicker.HANG_SENG: "hangseng",
    YahooTicker.FTSE_100: "ftse100",
    YahooTicker.DAX40: "dax40",
    YahooTicker.SHANGHAI_COMPOSITE: "shanghaicomposite",
}
