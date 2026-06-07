from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class FinancialInstrument(BaseModel):
    instrument_id: UUID
    exchange_id: UUID | None = None
    symbol: str
    instrument_class: str
    name: str
    region: str
    currency: str
    description: str | None = None
    created_at: datetime

class InstrumentVersion(BaseModel):
    instrument_id: UUID
    version_id: UUID
    valid_from: datetime
    change_type: str
    is_delete_marker: bool = False
    snapshot: str | None = None
    valid_to: datetime | None = None
    changed_by: str | None = None

class InstrumentSummary(BaseModel):
    instrument_id: UUID
    symbol: str
    instrument_class: str
    name: str
    region: str
