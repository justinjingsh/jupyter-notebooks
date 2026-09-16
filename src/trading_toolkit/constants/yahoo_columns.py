"""Columns yfinance's Ticker.history() returns that an index ticker doesn't
have, dropped by yahoo_finance.download_history()."""


class YahooColumn:
    """Yahoo Finance history columns absent for index tickers."""
    DIVIDENDS = "Dividends"
    STOCK_SPLITS = "Stock Splits"
