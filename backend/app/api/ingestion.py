from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from uuid import uuid4, UUID
from datetime import datetime, timezone

from app.db.connection import get_session
from app.db.repositories.ingest_job import IngestJobRepository
from app.queue.publisher import publish_ingest_job

router = APIRouter()


def get_ingest_job_repo() -> IngestJobRepository:
    return IngestJobRepository(get_session())


class IngestRequest(BaseModel):
    symbols: list[str]
    datatable_code: str = "WIKI/PRICES"
    instrument_class: str = "stock"
    region: str = "US"
    currency: str = "USD"


class IngestJobQueued(BaseModel):
    job_id: UUID
    symbol: str
    status: str = "queued"


@router.post("", response_model=list[IngestJobQueued])
def trigger_ingestion(request: IngestRequest):
    """Publish ingestion jobs to the queue. Returns job IDs immediately."""
    now = datetime.now(timezone.utc)
    queued = []

    for symbol in request.symbols:
        job_id = uuid4()
        message = {
            "job_id": str(job_id),
            "symbol": symbol,
            "datatable_code": request.datatable_code,
            "instrument_class": request.instrument_class,
            "region": request.region,
            "currency": request.currency,
        }
        try:
            publish_ingest_job(message)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Queue unavailable: {e}")

        queued.append(IngestJobQueued(job_id=job_id, symbol=symbol))

    return queued


@router.get("/status/{job_id}", response_model=dict)
def get_job_status(
    job_id: UUID,
    repo: IngestJobRepository = Depends(get_ingest_job_repo),
):
    """Check the status of an ingestion job."""
    job = repo.find(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.model_dump()
