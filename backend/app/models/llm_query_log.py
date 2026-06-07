from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class LLMQueryLog(BaseModel):
    user_id: UUID
    session_id: UUID
    asked_at: datetime
    query_id: UUID 
    user_prompt: str
    tools_invoked: str | None = None
    llm_response: str | None = None
    duration_ms: int | None = None