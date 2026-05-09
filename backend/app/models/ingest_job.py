from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class IngestJob(BaseModel):
    job_id: UUID 
    symbol: str
    datatabel_code: str
    status: str # queued | running | completed | failed
    queued_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    record_count: int | None = None
    error_message: str | None = None