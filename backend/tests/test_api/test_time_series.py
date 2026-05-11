from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import date, datetime, timezone
from decimal import Decimal

from app.main import app
from app.api.time_series import get_ts_repo
from app.models.time_series import TimeSeriesPoint

client = TestClient(app)


def _make_point(instrument_id, source_id) -> TimeSeriesPoint:
    now = datetime.now(timezone.utc)
    return TimeSeriesPoint(
        instrument_id=instrument_id,
        source_id=source_id,
        record_year=2024,
        record_date=date(2024, 1, 15),
        system_date=now,
        open_price=Decimal("100.5"),
        close_price=Decimal("102.3"),
        high_price=Decimal("103.0"),
        low_price=Decimal("99.8"),
        adj_close=Decimal("102.3"),
        volume=1500000,
        ex_dividend=Decimal("0"),
        split_ratio=Decimal("1.0"),
        extra_indicators={},
        ingested_at=now,
    )


def test_get_timeseries_returns_200():
    instrument_id = uuid4()
    source_id = uuid4()
    point = _make_point(instrument_id, source_id)

    repo = MagicMock()
    repo.find_range.return_value = [point]
    app.dependency_overrides[get_ts_repo] = lambda: repo

    try:
        response = client.get(
            f"/timeseries/{instrument_id}/{source_id}",
            params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["record_date"] == "2024-01-15"
    finally:
        app.dependency_overrides.pop(get_ts_repo, None)
