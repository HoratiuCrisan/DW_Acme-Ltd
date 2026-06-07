from fastapi import APIRouter, Depends, Query
from uuid import UUID
from datetime import date

from app.db.connection import get_session
from app.db.repositories.time_series import TimeSeriesRepository
from app.models.time_series import TimeSeriesPoint

router = APIRouter()


def get_ts_repo() -> TimeSeriesRepository:
    return TimeSeriesRepository(get_session())


@router.get("/{instrument_id}/{source_id}", response_model=list[TimeSeriesPoint])
def get_timeseries(
    instrument_id: UUID,
    source_id: UUID,
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    page_size: int = Query(default=1000, ge=1, le=10000),
    repo: TimeSeriesRepository = Depends(get_ts_repo),
):
    """Q5: Return time series data for a given asset and source."""
    if start_date is None:
        start_date = date(2000, 1, 1)
    if end_date is None:
        end_date = date.today()
    points = repo.find_range(instrument_id, source_id, start_date, end_date)
    return list(points)[:page_size]
