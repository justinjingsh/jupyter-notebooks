"""Generic, provider-agnostic CSV path/save helpers (used today by
yahoo_finance.py's `csv_path_for`/`save_csv`), so callers needing a
timestamped CSV path and a way to write a DataFrame to it don't
reimplement that logic themselves."""

from datetime import datetime

from trading_toolkit.constants.datetime_formats import TIMESTAMP_FORMAT


class CsvUtils:
    """Generic CSV helpers - building a fresh, timestamped download path and
    writing a DataFrame to one - with no provider-specific logic, so any
    caller can reuse them for its own CSV naming/writing needs."""

    @staticmethod
    def path_for(provider, slug, interval, data_dir):
        """A fresh, timestamped CSV path under `data_dir`, named
        `{provider}_{slug}_{interval}_{timestamp}.csv` (e.g.
        data/yahoo_ndx_1d_20260916153000.csv for provider="yahoo",
        slug="ndx", interval="1d"). `slug` is the caller's own
        filename-safe identifier - provider-specific slugging (e.g.
        stripping Yahoo's "^" ticker prefix) is not this function's
        concern."""

        data_dir.mkdir(exist_ok=True)
        run_timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        return data_dir / f"{provider}_{slug}_{interval}_{run_timestamp}.csv"

    @staticmethod
    def save(df, csv_path, index_label="Date"):
        """Write `df` to `csv_path`, indexed by `index_label`. Returns
        `csv_path` for chaining."""

        df.to_csv(csv_path, index_label=index_label)
        return csv_path
