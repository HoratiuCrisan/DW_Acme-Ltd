from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID

from app.db.connection import get_session
from app.db.repositories.data_source import DataSourceRepository
from app.models.data_source import DataSource, DataSourceSummary

router = APIRouter()


def get_source_repo() -> DataSourceRepository:
    return DataSourceRepository(get_session())


@router.get("", response_model=list[DataSourceSummary])
def list_sources(
    page_size: int = Query(default=1000, ge=1, le=10000),
    repo: DataSourceRepository = Depends(get_source_repo),
):
    """Q3: Return limited info about all data sources."""
    sources = list(repo.find_all())[:page_size]
    return [
        DataSourceSummary(
            source_id=s.source_id,
            source_name=s.source_name,
            source_type=s.source_type,
        )
        for s in sources
    ]


@router.get("/{source_id}", response_model=DataSource)
def get_source(
    source_id: UUID,
    repo: DataSourceRepository = Depends(get_source_repo),
):
    """Q4: Return all details of a data source by identifier."""
    source = repo.find_latest(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found")
    return source
