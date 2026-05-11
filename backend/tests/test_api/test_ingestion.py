from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.main import app
from app.models.ingest_job import IngestJob


def _make_job(job_id=None) -> IngestJob:
    now = datetime.now(timezone.utc)
    return IngestJob(
        job_id=job_id or uuid4(),
        symbol="AAPL",
        datatable_code="WIKI/PRICES",
        status="completed",
        queued_at=now,
        started_at=now,
        completed_at=now,
        record_count=100,
    )


def test_get_job_status_returns_200():
    job = _make_job()

    from app.api.ingestion import get_ingest_job_repo
    repo = MagicMock()
    repo.find.return_value = job
    app.dependency_overrides[get_ingest_job_repo] = lambda: repo

    try:
        client = TestClient(app)
        response = client.get(f"/ingest/status/{job.job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["status"] == "completed"
        assert data["record_count"] == 100
    finally:
        app.dependency_overrides.pop(get_ingest_job_repo, None)


def test_get_job_status_returns_404_when_not_found():
    from app.api.ingestion import get_ingest_job_repo
    repo = MagicMock()
    repo.find.return_value = None
    app.dependency_overrides[get_ingest_job_repo] = lambda: repo

    try:
        client = TestClient(app)
        response = client.get(f"/ingest/status/{uuid4()}")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_ingest_job_repo, None)
