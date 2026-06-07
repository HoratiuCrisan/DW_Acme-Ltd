from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.mcp import get_db_session
from app.main import app

client = TestClient(app)


def _make_instrument_row():
    row = MagicMock()
    row.instrument_id = uuid4()
    row.symbol = "AAPL"
    row.name = "Apple Inc"
    row.instrument_class = "stock"
    row.region = "US"
    row.currency = "USD"
    row.exchange_id = None
    row.description = None
    row.created_at = datetime.now(timezone.utc)
    return row


def _make_ts_row(instrument_id, source_id):
    row = MagicMock()
    row.instrument_id = instrument_id
    row.source_id = source_id
    row.record_year = 2024
    row.record_date = date(2024, 1, 15)
    row.system_date = datetime.now(timezone.utc)
    row.open_price = Decimal("100.0")
    row.close_price = Decimal("150.0")
    row.high_price = Decimal("155.0")
    row.low_price = Decimal("98.0")
    row.adj_close = None
    row.volume = 1000000
    row.ex_dividend = Decimal("0")
    row.split_ratio = Decimal("1")
    row.extra_indicators = {"quality": "raw"}
    row.ingested_at = datetime.now(timezone.utc)
    return row


def test_mcp_lists_required_tools():
    response = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    assert response.status_code == 200
    tools = response.json()["result"]["tools"]
    names = {tool["name"] for tool in tools}
    assert {
        "list_assets",
        "get_asset_details",
        "list_data_sources",
        "get_data_source_details",
        "get_time_series_data",
    }.issubset(names)


def test_mcp_list_assets_returns_page_metadata(mock_session):
    rows = [_make_instrument_row(), _make_instrument_row()]
    mock_session.execute.return_value = rows
    app.dependency_overrides[get_db_session] = lambda: mock_session

    try:
        response = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "list_assets", "arguments": {"offset": 0, "limit": 1}},
        })
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200
    structured = response.json()["result"]["structuredContent"]
    assert structured["page"]["returned"] == 1
    assert structured["page"]["total"] == 2
    assert structured["page"]["has_more"] is True
    assert structured["assets"][0]["symbol"] == "AAPL"


def test_mcp_get_time_series_data_returns_structured_records(mock_session):
    instrument_id = uuid4()
    source_id = uuid4()
    mock_session.execute.return_value = [_make_ts_row(instrument_id, source_id)]
    app.dependency_overrides[get_db_session] = lambda: mock_session

    try:
        response = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_time_series_data",
                "arguments": {
                    "assetId": str(instrument_id),
                    "dataSourceId": str(source_id),
                    "startBusinessDate": "2024-01-01",
                    "endBusinessDate": "2024-01-31",
                    "includeAttributes": True,
                },
            },
        })
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200
    structured = response.json()["result"]["structuredContent"]
    assert structured["selection"]["dateInterval"] == "inclusive"
    assert structured["provenance"]["dataSourceId"] == str(source_id)
    assert structured["records"][0]["close"] == "150.0"
    assert structured["records"][0]["attributes"]["extraIndicators"] == {"quality": "raw"}


def test_mcp_rejects_too_broad_time_series_range(mock_session):
    app.dependency_overrides[get_db_session] = lambda: mock_session

    try:
        response = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "get_time_series_data",
                "arguments": {
                    "assetId": str(uuid4()),
                    "dataSourceId": str(uuid4()),
                    "startBusinessDate": "2022-01-01",
                    "endBusinessDate": "2024-01-31",
                },
            },
        })
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    body = response.json()
    assert response.status_code == 200
    assert body["error"]["code"] == -32602
    assert "may not exceed" in body["error"]["data"]
