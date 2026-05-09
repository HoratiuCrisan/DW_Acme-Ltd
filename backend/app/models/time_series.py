from pydantic import BaseModel
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal

class TimeSeriesPoint(BaseModel):
    instrument_id: UUID
    source_id: UUID
    record_year: int # Cassandra partition bucket derives from record_date.year
    record_date: datetime
    system_date: datetime
    open_price: Decimal | None = None
    close_price: Decimal | None = None
    high_price: Decimal | None = None
    low_price: Decimal | None = None
    adj_close: Decimal | None = None
    volume: int | None = None
    ex_divided: Decimal | None = None
    split_ration: Decimal | None = None
    extra_indicators: dict[str, str] = {}
    ingested_at: datetime