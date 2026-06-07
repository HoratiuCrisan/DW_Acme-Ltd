from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.main import app
from app.api.data_sources import get_source_repo
from app.models.data_source import DataSource

client = TestClient(app)


def _make_source() -> DataSource:
    return DataSource(
        source_id=uuid4(),
        source_name="QUANDL_NYSE",
        source_type="REST",
        base_url="https://quandl.com/api",
        api_key_required=True,
        description="Quandl NYSE data feed",
        created_at=datetime.now(timezone.utc),
    )


def test_list_sources_returns_200():
    source = _make_source()
    repo = MagicMock()
    repo.find_all.return_value = [source]
    app.dependency_overrides[get_source_repo] = lambda: repo

    try:
        response = client.get("/sources")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["source_name"] == "QUANDL_NYSE"
        assert "description" not in data[0]
    finally:
        app.dependency_overrides.pop(get_source_repo, None)


def test_get_source_by_id_returns_200():
    source = _make_source()
    repo = MagicMock()
    repo.find_latest.return_value = source
    app.dependency_overrides[get_source_repo] = lambda: repo

    try:
        response = client.get(f"/sources/{source.source_id}")
        assert response.status_code == 200
        assert response.json()["source_name"] == "QUANDL_NYSE"
    finally:
        app.dependency_overrides.pop(get_source_repo, None)


def test_get_source_by_id_returns_404_when_missing():
    repo = MagicMock()
    repo.find_latest.return_value = None
    app.dependency_overrides[get_source_repo] = lambda: repo

    try:
        response = client.get(f"/sources/{uuid4()}")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_source_repo, None)
