from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.consumption import get_instrument_repo, get_ts_repo
from app.main import app
from app.models.instrument import FinancialInstrument
from app.models.time_series import TimeSeriesPoint

client = TestClient(app)


def _instrument(symbol: str) -> FinancialInstrument:
    return FinancialInstrument(
        instrument_id=uuid4(),
        symbol=symbol,
        instrument_class="stock",
        name=f"{symbol} Inc",
        region="US",
        currency="USD",
        created_at=datetime.now(timezone.utc),
    )


def _point(instrument_id, source_id, business_date, system_time, close="100.0"):
    return TimeSeriesPoint(
        instrument_id=instrument_id,
        source_id=source_id,
        record_year=business_date.year,
        record_date=business_date,
        system_date=system_time,
        open_price=Decimal("90.0"),
        close_price=Decimal(close),
        high_price=Decimal("110.0"),
        low_price=Decimal("80.0"),
        volume=100,
        extra_indicators={"quality": "checked"},
        ingested_at=system_time,
    )


def test_assets_endpoint_supports_offset_limit_metadata():
    repo = MagicMock()
    repo.find_all.return_value = [_instrument("MSFT"), _instrument("AAPL")]
    app.dependency_overrides[get_instrument_repo] = lambda: repo

    try:
        response = client.get("/assets", params={"offset": 0, "limit": 1})
    finally:
        app.dependency_overrides.pop(get_instrument_repo, None)

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == {
        "offset": 0,
        "limit": 1,
        "returned": 1,
        "total": 2,
        "has_more": True,
    }
    assert body["assets"][0]["symbol"] == "AAPL"


def test_data_endpoint_uses_half_open_range_and_latest_version():
    instrument_id = uuid4()
    source_id = uuid4()
    older = _point(
        instrument_id,
        source_id,
        date(2024, 1, 15),
        datetime(2024, 1, 15, 10, tzinfo=timezone.utc),
        close="100.0",
    )
    newer = _point(
        instrument_id,
        source_id,
        date(2024, 1, 15),
        datetime(2024, 1, 15, 12, tzinfo=timezone.utc),
        close="120.0",
    )
    excluded_end = _point(
        instrument_id,
        source_id,
        date(2024, 2, 1),
        datetime(2024, 2, 1, 12, tzinfo=timezone.utc),
        close="130.0",
    )
    repo = MagicMock()
    repo.find_range.return_value = [older, newer, excluded_end]
    app.dependency_overrides[get_ts_repo] = lambda: repo

    try:
        response = client.get("/data", params={
            "assetId": str(instrument_id),
            "dataSourceId": str(source_id),
            "startBusinessDate": "2024-01-01",
            "endBusinessDate": "2024-02-01",
            "includeAttributes": "true",
        })
    finally:
        app.dependency_overrides.pop(get_ts_repo, None)

    assert response.status_code == 200
    body = response.json()
    assert body["page"]["total"] == 1
    assert body["data"]["records"][0]["businessDate"] == "2024-01-15"
    assert body["data"]["records"][0]["values"]["close"] == "120.0"
    assert "quality" in body["attributes"]
