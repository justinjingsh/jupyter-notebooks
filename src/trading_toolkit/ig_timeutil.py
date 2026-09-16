"""Date/time parsing shared by the notebooks. The download notebook takes
`START` / `END` as `"YYYY-MM-DD"` or `"YYYY-MM-DDTHH:MM:SS"` strings and needs
them as timezone-aware UTC datetimes; the bare-date rules (start of day vs.
end of day) live here so every notebook resolves a window the same way."""

from datetime import datetime, timezone


def parse_utc(ts, *, end_of_day=False):
    """Parse "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM:SS" as UTC. A bare date is
    00:00:00, or 23:59:59 when end_of_day - so a date-only END covers the
    whole day rather than stopping at its first instant."""
    dt = datetime.fromisoformat(ts)
    if end_of_day and ":" not in ts:
        dt = dt.replace(hour=23, minute=59, second=59)
    return dt.replace(tzinfo=timezone.utc)


def resolve_window(start, end):
    """Resolve a (START, END) pair of notebook strings into timezone-aware
    UTC datetimes. `end=None` means "now"; a bare-date `end` covers its whole
    day (see parse_utc)."""
    start_dt = parse_utc(start)
    end_dt = datetime.now(timezone.utc) if end is None else parse_utc(end, end_of_day=True)
    return start_dt, end_dt
