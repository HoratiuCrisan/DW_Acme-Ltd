from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.main import app
from app.api.instruments import get_instrument_repo
from app.models.instrument import FinancialInstrument

client = TestClient(app)


def _make_instrument() -> FinancialInstrument:
    return FinancialInstrument(
        instrument_id=uuid4(),
        symbol="TSLA",
        instrument_class="stock",
        name="Tesla Inc",
        region="US",
        currency="USD",
        created_at=datetime.now(timezone.utc),
    )


def test_list_instruments_returns_200():
    instrument = _make_instrument()
    repo = MagicMock()
    repo.find_all.return_value = [instrument]
    app.dependency_overrides[get_instrument_repo] = lambda: repo

    try:
        response = client.get("/instruments")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "TSLA"
        assert "currency" not in data[0]
        assert "description" not in data[0]
    finally:
        app.dependency_overrides.pop(get_instrument_repo, None)


def test_get_instrument_by_id_returns_200():
    instrument = _make_instrument()
    repo = MagicMock()
    repo.find_latest.return_value = instrument
    app.dependency_overrides[get_instrument_repo] = lambda: repo

    try:
        response = client.get(f"/instruments/{instrument.instrument_id}")
        assert response.status_code == 200
        assert response.json()["symbol"] == "TSLA"
    finally:
        app.dependency_overrides.pop(get_instrument_repo, None)


def test_get_instrument_by_id_returns_404_when_missing():
    repo = MagicMock()
    repo.find_latest.return_value = None
    app.dependency_overrides[get_instrument_repo] = lambda: repo

    try:
        response = client.get(f"/instruments/{uuid4()}")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_instrument_repo, None)
