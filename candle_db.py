"""The per-resolution `candles_<suffix>` SQLite tables shared between
download_ig_prices.ipynb (producer) and view_ig_prices.ipynb (consumer):
table naming (`table_name_for_resolution`), schema creation
(`init_candles_table`), and reading candles back (`load_candles`), so both
notebooks derive the same table name from a `resolution` value.

Each table carries the flattened price columns from constants/db_headers.py
(DB_HEADERS) alongside the raw JSON blob (`data`), so prices are directly
queryable in SQL without duplicating the flattening logic in candle_csv.py."""

from constants.db_headers import DB_HEADERS
from constants.ohlc_fields import OHLCField
from constants.resolutions import RESOLUTION_TABLE_SUFFIX

# Columns for one INSERT, in order: epic/resolution, then DB_HEADERS' names
# (which start with snapshot_time_utc), then the raw JSON blob.
INSERT_COLUMNS = ["epic", "resolution", *(name for name, _ in DB_HEADERS), "data"]


def table_name_for_resolution(resolution):
    """Map an IG `resolution` value (e.g. "DAY") to its table name (e.g.
    "candles_1d"). Raises KeyError for an unrecognized resolution."""
    
    return f"candles_{RESOLUTION_TABLE_SUFFIX[resolution]}"


def init_candles_table(conn, resolution):
    """Create the candles table for `resolution` if it doesn't exist yet, and return its name."""

    table = table_name_for_resolution(resolution)
    price_columns = ",\n            ".join(
        f"{name} {sql_type}" for name, sql_type in DB_HEADERS
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            epic              TEXT NOT NULL,
            resolution        TEXT NOT NULL,
            {price_columns},
            data              TEXT NOT NULL,
            UNIQUE(epic, snapshot_time_utc)
        )
        """
    )
    return table


def load_candles(connection, resolution, epic=None):
    """Yield one flat OHLC dict per candle from the `resolution` table, oldest first.

    Reads the precomputed mid-price columns the producer writes (see
    init_candles_table / constants/db_headers.py) - no JSON parsing.
    `open`/`high`/`low`/`close` are the bid/ask mid; the same values are also
    exposed under their explicit `*_mid_price` names. Pass `epic` to filter to
    a single instrument.
    """
    table = table_name_for_resolution(resolution)
    sql = (
        "SELECT epic, resolution, snapshot_time_utc, "
        "open_mid_price, high_mid_price, low_mid_price, close_mid_price, "
        "last_traded_volume "
        f"FROM {table}"
    )
    params = ()
    if epic is not None:
        sql += " WHERE epic = ?"
        params = (epic,)
    sql += " ORDER BY snapshot_time_utc"

    for (
        row_epic,
        row_resolution,
        snapshot_time_utc,
        open_mid,
        high_mid,
        low_mid,
        close_mid,
        volume,
    ) in connection.execute(sql, params):
        yield {
            OHLCField.EPIC: row_epic,
            OHLCField.RESOLUTION: row_resolution,
            OHLCField.SNAPSHOT_TIME_UTC: snapshot_time_utc,
            OHLCField.OPEN: open_mid,
            OHLCField.HIGH: high_mid,
            OHLCField.LOW: low_mid,
            OHLCField.CLOSE: close_mid,
            OHLCField.OPEN_MID_PRICE: open_mid,
            OHLCField.HIGH_MID_PRICE: high_mid,
            OHLCField.LOW_MID_PRICE: low_mid,
            OHLCField.CLOSE_MID_PRICE: close_mid,
            OHLCField.VOLUME: volume,
        }
