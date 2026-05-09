from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from app.models.time_series import TimeSeriesPoint

# Mapping Nasdaq column name into TimeSeriesPoint field name 
# None - in case it is known but not mapped

_FIELD_MAP: dict[str, str | None] = {
    "date": None,
    "open": "open_price",
    "high": "high_price",
    "low": "low_price",
    "close": "close_price",
    "adj_close": "adj_close",
    "volume": "volume",
    "ex-dividend": "ex_dividend",
    "split_ratio": "split_ratio",
    "adj_open": None,
    "adj_high": None,
    "adj_low": None,
    "adj_volume": None,
    "ticker": None,
}

def _to_decimal(value: str | None) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None
    
def _to_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return None
    
class NasdaqTransformer:
    def transform(
        self,
        row: dict,
        instrument_id: UUID,
        source_id: UUID,
        ingested_at: datetime,
    ) -> TimeSeriesPoint:
        try:
            record_date = date.fromisoformat(row["date"])
        except KeyError:
            raise ValueError(f"Row is missing requried 'date' field: {row}")
        
        extra = {k: str(v) for k, v in row.items() if k not in _FIELD_MAP}

        return TimeSeriesPoint(
            instrument_id = instrument_id,
            source_id = source_id,
            record_year = record_date.year,
            record_date = record_date,
            system_date = ingested_at,
            open_price = _to_decimal(row.get("open")),
            close_price = _to_decimal(row.get("close")),
            high_price = _to_decimal(row.get("high")),
            low_price = _to_decimal(row.get("low")),
            adj_close = _to_decimal(row.get("adj_close")),
            volume = _to_int(row.get("volume")),
            ex_dividend = _to_decimal(row.get("ex-dividend")),
            split_ratio = _to_decimal(row.get("split_ratio")),
            extra_indicators = extra,
            ingested_at = ingested_at,
        )