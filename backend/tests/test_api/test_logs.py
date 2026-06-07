from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.main import app
from app.models.ingest_log import IngestLog


def _make_log(source_id) -> IngestLog:
    return IngestLog(
        source_id=source_id,
        ingested_at=datetime.now(timezone.utc),
        log_id=uuid4(),
        instrument_id=uuid4(),
        status="success",
        record_count=42,
        duration_ms=1200,
    )


def test_get_logs_returns_200():
    source_id = uuid4()
    log = _make_log(source_id)

    from app.api.logs import get_log_repo
    repo = MagicMock()
    repo.find_all.return_value = [log]
    app.dependency_overrides[get_log_repo] = lambda: repo

    try:
        client = TestClient(app)
        response = client.get(f"/logs/{source_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "success"
        assert data[0]["record_count"] == 42
    finally:
        app.dependency_overrides.pop(get_log_repo, None)


def test_get_logs_returns_empty_list_when_none():
    source_id = uuid4()

    from app.api.logs import get_log_repo
    repo = MagicMock()
    repo.find_all.return_value = []
    app.dependency_overrides[get_log_repo] = lambda: repo

    try:
        client = TestClient(app)
        response = client.get(f"/logs/{source_id}")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.pop(get_log_repo, None)
