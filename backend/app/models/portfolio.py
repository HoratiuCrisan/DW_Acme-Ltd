from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class Portfolio(BaseModel):
    owner_id: UUID
    portfolio_id: UUID
    name: str
    base_currency: str
    description: str | None = None
    created_at: datetime
    is_active: bool = True

class PortfolioAsset(BaseModel):
    portfolio_id: UUID
    instrument_id: UUID
    symbol: str
    instrument_class: str
    removed_at: datetime | None = None
    quantity: Decimal | None = None
    purchase_price: Decimal | None = None
    notes: str | None = None