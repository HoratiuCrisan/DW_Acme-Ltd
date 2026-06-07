from pydantic import BaseModel
from uuid import UUID

class Exchange(BaseModel):
    exchange_id: UUID
    exchange_name: str
    country: str | None = None
    timezone: str | None = None
    currency: str | None = None
    open_time: str | None = None
    close_time: str | None = None