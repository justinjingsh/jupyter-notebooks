"""candle_csv flattens raw IG candle dicts into CSV/DB rows; the row order
must line up with CSV_HEADERS."""

from igmarket.candle_csv import bid_ask_mid, candle_to_row, mid
from igmarket.constants.csv_headers import CSV_HEADERS


def _node(bid, ask):
    return {"bid": bid, "ask": ask}


def _candle():
    return {
        "snapshotTimeUTC": "2024-01-02T00:00:00",
        "openPrice": _node(100.0, 102.0),
        "highPrice": _node(110.0, 112.0),
        "lowPrice": _node(90.0, 92.0),
        "closePrice": _node(104.0, 106.0),
        "lastTradedVolume": 1234,
    }


def test_mid_averages_bid_and_ask():
    assert mid(_node(100.0, 102.0)) == 101.0


def test_mid_is_none_when_a_side_is_missing():
    assert mid(_node(100.0, None)) is None
    assert mid(None) is None
    assert mid({}) is None


def test_bid_ask_mid_triplet():
    assert bid_ask_mid(_node(100.0, 102.0)) == (100.0, 102.0, 101.0)
    assert bid_ask_mid(None) == (None, None, None)


def test_candle_to_row_matches_csv_header_width_and_order():
    row = candle_to_row(_candle())
    assert len(row) == len(CSV_HEADERS)

    by_name = dict(zip(CSV_HEADERS, row))
    assert by_name["snapshot_time_utc"] == "2024-01-02T00:00:00"
    assert by_name["open_bid_price"] == 100.0
    assert by_name["open_ask_price"] == 102.0
    assert by_name["open_mid_price"] == 101.0
    assert by_name["close_mid_price"] == 105.0
    assert by_name["last_traded_volume"] == 1234


def test_candle_to_row_tolerates_missing_volume():
    candle = _candle()
    del candle["lastTradedVolume"]
    row = candle_to_row(candle)
    assert dict(zip(CSV_HEADERS, row))["last_traded_volume"] is None
