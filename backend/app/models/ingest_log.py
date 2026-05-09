from pydantic import BaseModel, model_validator
from uuid import UUID
from datetime import datetime

class IngestLog(BaseModel): 
    source_id: UUID
    log_id: UUID
    ingested_at: datetime
    log_year: int = 0
    status: str
    record_count: int = 0
    error_message: str | None = None
    duration_ms: int | None = None