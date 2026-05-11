from fastapi import APIRouter, Depends
from uuid import UUID
from datetime import datetime, timezone

from app.db.connection import get_session
from app.db.repositories.ingest_log import IngestLogRepository
from app.models.ingest_log import IngestLog

router = APIRouter()


def get_log_repo() -> IngestLogRepository:
    return IngestLogRepository(get_session())


@router.get("/{source_id}", response_model=list[IngestLog])
def get_logs(
    source_id: UUID,
    limit: int = 50,
    repo: IngestLogRepository = Depends(get_log_repo),
):
    """Return recent ingest logs for a source (current year)."""
    current_year = datetime.now(timezone.utc).year
    logs = repo.find_all((source_id, current_year))
    return list(logs)[:limit]
