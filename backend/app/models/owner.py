from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class Owner(BaseModel):
    owner_id: UUID
    owner_type: str
    name: str
    email: str | None = None
    phone: str | None = None
    country: str | None = None
    created_at: datetime

class User(BaseModel):
    user_id: UUID
    owner_id: UUID
    username: str
    role: str
    registered_at: datetime
    last_login_at: datetime | None = None