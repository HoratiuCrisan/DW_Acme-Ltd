from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class AnalyticsResult(BaseModel):
    instrument_id: UUID
    source_id: UUID
    result_id: UUID
    computed_at: datetime
    metric_type: str
    metric_value: Decimal | None = None
    window_days: int | None = None
    notes: str | None = None