from fastapi import APIRouter, Query
from pydantic import BaseModel
from uuid import UUID
from datetime import date
from decimal import Decimal

from app.db.connection import get_session
from app.db.repositories.time_series import TimeSeriesRepository
from app.analytics.aggregations import compute_aggregations

router = APIRouter()


class AnalyticsResponse(BaseModel):
    instrument_id: UUID
    source_id: UUID
    start_date: date
    end_date: date
    count: int
    min_close: Decimal | None = None
    max_close: Decimal | None = None
    avg_close: Decimal | None = None
    total_volume: int


@router.get("/{instrument_id}/{source_id}", response_model=AnalyticsResponse)
def get_analytics(
    instrument_id: UUID,
    source_id: UUID,
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
):
    """Return min/max/avg close price and total volume for an asset over a date range."""
    if start_date is None:
        start_date = date(2000, 1, 1)
    if end_date is None:
        end_date = date.today()

    session = get_session()
    repo = TimeSeriesRepository(session)
    points = repo.find_range(instrument_id, source_id, start_date, end_date)
    agg = compute_aggregations(points)

    return AnalyticsResponse(
        instrument_id=instrument_id,
        source_id=source_id,
        start_date=start_date,
        end_date=end_date,
        count=agg.count,
        min_close=agg.min_close,
        max_close=agg.max_close,
        avg_close=agg.avg_close,
        total_volume=agg.total_volume,
    )
