import json
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

from app.assistant.tools import execute_tool


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


def _make_source_row():
    row = MagicMock()
    row.source_id = uuid4()
    row.source_name = "NASDAQ_WIKI"
    row.source_type = "rest"
    row.base_url = "https://data.nasdaq.com"
    row.api_key_required = True
    row.description = None
    row.attributes = None
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
    row.ex_dividend = None
    row.split_ratio = None
    row.extra_indicators = {}
    row.ingested_at = datetime.now(timezone.utc)
    return row


def test_list_instruments_returns_json_list(mock_session):
    row = _make_instrument_row()
    mock_session.execute.return_value = [row]

    result = execute_tool("list_instruments", {}, mock_session)

    data = json.loads(result)
    assert len(data) == 1
    assert data[0]["symbol"] == "AAPL"
    assert "instrument_id" in data[0]


def test_get_instrument_returns_json_object(mock_session):
    row = _make_instrument_row()
    mock_session.execute.return_value.one.return_value = row

    result = execute_tool("get_instrument", {"instrument_id": str(row.instrument_id)}, mock_session)

    data = json.loads(result)
    assert data["symbol"] == "AAPL"
    assert data["currency"] == "USD"


def test_list_sources_returns_json_list(mock_session):
    row = _make_source_row()
    mock_session.execute.return_value = [row]

    result = execute_tool("list_sources", {}, mock_session)

    data = json.loads(result)
    assert len(data) == 1
    assert data[0]["name"] == "NASDAQ_WIKI"


def test_get_time_series_returns_json_list(mock_session):
    instrument_id = uuid4()
    source_id = uuid4()
    row = _make_ts_row(instrument_id, source_id)
    mock_session.execute.return_value = [row]

    result = execute_tool("get_time_series", {
        "instrument_id": str(instrument_id),
        "source_id": str(source_id),
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
    }, mock_session)

    data = json.loads(result)
    assert len(data) == 1
    assert data[0]["close"] == "150.0"
    assert data[0]["volume"] == 1000000


def test_get_analytics_returns_aggregation_dict(mock_session):
    instrument_id = uuid4()
    source_id = uuid4()
    row = _make_ts_row(instrument_id, source_id)
    mock_session.execute.return_value = [row]

    result = execute_tool("get_analytics", {
        "instrument_id": str(instrument_id),
        "source_id": str(source_id),
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
    }, mock_session)

    data = json.loads(result)
    assert data["count"] == 1
    assert data["avg_close"] == "150.0"
    assert data["total_volume"] == 1000000
