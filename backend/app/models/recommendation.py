from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class Recommendation(BaseModel):
    user_id: UUID
    created_at: datetime
    recommendation_id: UUID | None = None
    signal_id: UUID | None = None
    action: str
    rationale: str | None = None
    expires_at: datetime | None = None
    was_acted_on: bool = False