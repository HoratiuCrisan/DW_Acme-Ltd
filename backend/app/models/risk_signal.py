from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class RiskSignal(BaseModel):
    instrument_id: UUID
    generated_at: datetime
    signal_id: UUID
    signal_type: str
    severity: str
    value: Decimal | None = None
    explanation: str | None = None
    result_id: UUID | None = None