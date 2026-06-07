from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class DataSource(BaseModel):
    source_id: UUID
    source_name: str
    source_type: str
    base_url: str | None = None
    api_key_required: bool = False
    description: str | None = None
    attributes: set[str] | None = None
    created_at: datetime


class DataSourceSummary(BaseModel):
    source_id: UUID
    source_name: str
    source_type: str
