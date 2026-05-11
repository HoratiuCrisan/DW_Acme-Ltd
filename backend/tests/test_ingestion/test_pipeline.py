from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal
from datetime import date

from app.ingestion.pipeline import IngestionPipeline
from app.models.instrument import FinancialInstrument
from app.models.data_source import DataSource


def _make_instrument() -> FinancialInstrument:
    return FinancialInstrument(
        instrument_id=uuid4(),
        symbol="AAPL",
        instrument_class="stock",
        name="Apple Inc",
        region="US",
        currency="USD",
        created_at=datetime.now(timezone.utc),
    )


def _make_source() -> DataSource:
    return DataSource(
        source_id=uuid4(),
        source_name="NASDAQ_WIKI",
        source_type="rest",
        base_url="https://data.nasdaq.com/api/v3/datatables",
        api_key_required=True,
        created_at=datetime.now(timezone.utc),
    )


def _make_pipeline(raw_rows):
    instrument_repo = MagicMock()
    source_repo = MagicMock()
    ts_repo = MagicMock()
    log_repo = MagicMock()
    extractor = MagicMock()
    extractor.fetch_table_data.return_value = iter(raw_rows)
    ts_repo.save_batch.return_value = len(raw_rows)
    pipeline = IngestionPipeline(
        instrument_repo=instrument_repo,
        source_repo=source_repo,
        ts_repo=ts_repo,
        log_repo=log_repo,
        extractor=extractor,
    )
    return pipeline, instrument_repo, source_repo, ts_repo, log_repo


_VALID_ROW = {
    "date": "2024-01-15",
    "close": "150.0",
    "open": "149.0",
    "high": "151.0",
    "low": "148.0",
    "volume": "1000000",
    "ticker": "AAPL",
}


def test_ingest_stores_transformed_rows():
    pipeline, _, _, ts_repo, log_repo = _make_pipeline([_VALID_ROW])
    result = pipeline.ingest(_make_instrument(), _make_source(), "WIKI/PRICES")

    assert result.fetched == 1
    assert result.stored == 1
    assert result.skipped == 0
    ts_repo.save_batch.assert_called_once()
    log_repo.save.assert_called_once()


def test_ingest_skips_rows_with_transform_errors():
    bad_row = {"no_date_field": "bad", "ticker": "AAPL"}
    pipeline, _, _, ts_repo, log_repo = _make_pipeline([bad_row])
    ts_repo.save_batch.return_value = 0

    result = pipeline.ingest(_make_instrument(), _make_source(), "WIKI/PRICES")

    assert result.fetched == 1
    assert result.skipped == 1
    assert len(result.errors) == 1
    log_repo.save.assert_called_once()


def test_ingest_logs_success_status_when_no_errors():
    instrument = _make_instrument()
    source = _make_source()
    pipeline, _, _, ts_repo, log_repo = _make_pipeline([_VALID_ROW])

    pipeline.ingest(instrument, source, "WIKI/PRICES")

    saved_log = log_repo.save.call_args[0][0]
    assert saved_log.status == "success"
    assert saved_log.instrument_id == instrument.instrument_id
    assert saved_log.source_id == source.source_id


def test_ingest_logs_error_status_when_extractor_raises():
    instrument_repo = MagicMock()
    source_repo = MagicMock()
    ts_repo = MagicMock()
    log_repo = MagicMock()
    extractor = MagicMock()
    extractor.fetch_table_data.side_effect = RuntimeError("API down")

    pipeline = IngestionPipeline(
        instrument_repo=instrument_repo,
        source_repo=source_repo,
        ts_repo=ts_repo,
        log_repo=log_repo,
        extractor=extractor,
    )
    result = pipeline.ingest(_make_instrument(), _make_source(), "WIKI/PRICES")

    assert result.stored == 0
    saved_log = log_repo.save.call_args[0][0]
    assert saved_log.status == "error"
    assert "API down" in saved_log.error_message
