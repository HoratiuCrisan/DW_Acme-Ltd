from uuid import uuid4
from datetime import datetime, timezone

from app.ingestion.transformer import NasdaqTransformer


def test_transform_row_maps_known_fields():
    instrument_id = uuid4()
    source_id = uuid4()
    row = {
        "date": "2024-01-15",
        "open": "100.5",
        "high": "103.0",
        "low": "99.8",
        "close": "102.3",
        "volume": "1500000",
        "ex-dividend": "0.0",
        "split_ratio": "1.0",
        "adj_open": "100.5",
        "adj_high": "103.0",
        "adj_low": "99.8",
        "adj_close": "102.3",
        "adj_volume": "1500000",
        "ticker": "AAPL",
    }
    ingested_at = datetime.now(timezone.utc)

    transformer = NasdaqTransformer()
    point = transformer.transform(row, instrument_id, source_id, ingested_at)

    assert point.instrument_id == instrument_id
    assert point.source_id == source_id
    assert str(point.record_date) == "2024-01-15"
    assert point.record_year == 2024
    assert float(point.open_price) == 100.5
    assert float(point.close_price) == 102.3
    assert point.volume == 1500000


def test_transform_row_puts_unknown_fields_in_extra_indicators():
    instrument_id = uuid4()
    source_id = uuid4()
    row = {
        "date": "2024-03-10",
        "close": "55.0",
        "some_custom_field": "abc",
    }
    ingested_at = datetime.now(timezone.utc)

    transformer = NasdaqTransformer()
    point = transformer.transform(row, instrument_id, source_id, ingested_at)

    assert "some_custom_field" in point.extra_indicators
    assert point.extra_indicators["some_custom_field"] == "abc"


from unittest.mock import patch, MagicMock
from app.ingestion.nasdaq import NasdaqExtractor
from app import config


def _make_response(columns, rows, next_cursor_id=None):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "datatable": {
            "columns": [{"name": c} for c in columns],
            "data": rows,
        },
        "meta": {"next_cursor_id": next_cursor_id},
    }
    return mock_resp


def test_extractor_yields_rows_as_dicts():
    columns = ["date", "close", "volume"]
    rows = [["2024-01-15", "102.3", "1500000"]]
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_client.get.return_value = _make_response(columns, rows)

        extractor = NasdaqExtractor(api_key="test_key")
        result = list(extractor.fetch_table_data("WIKI/PRICES", {"ticker": "AAPL"}))

    assert len(result) == 1
    assert result[0] == {"date": "2024-01-15", "close": "102.3", "volume": "1500000"}


def test_extractor_paginates_via_cursor():
    columns = ["date", "close"]
    page1_rows = [["2024-01-15", "100.0"]]
    page2_rows = [["2024-01-16", "101.0"]]
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_client.get.side_effect = [
            _make_response(columns, page1_rows, next_cursor_id="cursor_abc"),
            _make_response(columns, page2_rows, next_cursor_id=None),
        ]

        extractor = NasdaqExtractor(api_key="test_key")
        result = list(extractor.fetch_table_data("WIKI/PRICES"))

    assert len(result) == 2
    assert result[0]["date"] == "2024-01-15"
    assert result[1]["date"] == "2024-01-16"
    assert mock_client.get.call_count == 2


def test_extractor_uses_configured_base_url(monkeypatch):
    monkeypatch.setattr(config.settings, "nasdaq_base_url", "https://example.test/datatables")

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_client.get.return_value = _make_response(["date"], [])

        extractor = NasdaqExtractor(api_key="test_key")
        list(extractor.fetch_table_data("WIKI/PRICES"))

    mock_client.get.assert_called_once()
    assert mock_client.get.call_args[0][0] == "https://example.test/datatables/WIKI/PRICES.json"
