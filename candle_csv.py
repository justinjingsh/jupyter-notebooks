"""Flattens raw IG candle dicts into CSV rows for download_ig_prices.ipynb.
Column headers live in constants/csv_headers.py (CSV_HEADERS); row-building
here must match that column order."""

from constants.ig_candle_fields import CandleField, PriceField


def mid(node):
    if not node or node.get(PriceField.BID) is None or node.get(PriceField.ASK) is None:
        return None
    return (node[PriceField.BID] + node[PriceField.ASK]) / 2


def bid_ask_mid(node):
    if not node:
        return None, None, None
    return node.get(PriceField.BID), node.get(PriceField.ASK), mid(node)


def candle_to_row(c):
    """Flatten one raw IG candle dict into a row matching CSV_HEADERS."""
    return [
        c[CandleField.SNAPSHOT_TIME_UTC],
        *bid_ask_mid(c[CandleField.OPEN_PRICE]),
        *bid_ask_mid(c[CandleField.HIGH_PRICE]),
        *bid_ask_mid(c[CandleField.LOW_PRICE]),
        *bid_ask_mid(c[CandleField.CLOSE_PRICE]),
        c.get(CandleField.LAST_TRADED_VOLUME),
    ]
