"""UTC window parsing shared by the notebooks (no .env, no network)."""

from datetime import datetime, timezone

from igmarket.timeutil import parse_utc, resolve_window


def test_parse_utc_bare_date_is_start_of_day():
    assert parse_utc("2024-01-02") == datetime(2024, 1, 2, tzinfo=timezone.utc)


def test_parse_utc_bare_date_end_of_day():
    assert parse_utc("2024-01-02", end_of_day=True) == datetime(
        2024, 1, 2, 23, 59, 59, tzinfo=timezone.utc
    )


def test_parse_utc_full_timestamp_ignores_end_of_day():
    ts = "2024-01-02T13:30:00"
    assert parse_utc(ts) == datetime(2024, 1, 2, 13, 30, tzinfo=timezone.utc)
    assert parse_utc(ts, end_of_day=True) == datetime(
        2024, 1, 2, 13, 30, tzinfo=timezone.utc
    )


def test_resolve_window_rolls_bare_date_end_to_end_of_day():
    start_dt, end_dt = resolve_window("2024-01-01", "2024-01-31")
    assert start_dt == datetime(2024, 1, 1, tzinfo=timezone.utc)
    assert end_dt == datetime(2024, 1, 31, 23, 59, 59, tzinfo=timezone.utc)


def test_resolve_window_none_end_is_now_utc():
    before = datetime.now(timezone.utc)
    _, end_dt = resolve_window("2024-01-01", None)
    after = datetime.now(timezone.utc)
    assert end_dt.tzinfo == timezone.utc
    assert before <= end_dt <= after
