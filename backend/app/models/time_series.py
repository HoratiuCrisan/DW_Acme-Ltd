from pydantic import BaseModel, Field
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal

class TimeSeriesPoint(BaseModel):
    instrument_id: UUID
    source_id: UUID
    record_year: int # Cassandra partition bucket derives from record_date.year
    record_date: date
    system_date: datetime
    open_price: Decimal | None = None
    close_price: Decimal | None = None
    high_price: Decimal | None = None
    low_price: Decimal | None = None
    adj_close: Decimal | None = None
    volume: int | None = None
    ex_dividend: Decimal | None = None
    split_ratio: Decimal | None = None
    extra_indicators: dict[str, str] = Field(default_factory=dict)
    ingested_at: datetime
