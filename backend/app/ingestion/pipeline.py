import time
import uuid
from datetime import datetime, timezone

BATCH_SIZE = 500

from app.db.repositories.instrument import InstrumentRepository
from app.db.repositories.data_source import DataSourceRepository
from app.db.repositories.time_series import TimeSeriesRepository
from app.db.repositories.ingest_log import IngestLogRepository
from app.ingestion.nasdaq import NasdaqExtractor
from app.ingestion.transformer import NasdaqTransformer
from app.models.ingest_log import IngestLog
from app.models.data_source import DataSource
from app.models.instrument import FinancialInstrument
from app.models.time_series import TimeSeriesPoint


class IngestionResult:
    def __init__(self):
        self.fetched = 0
        self.stored = 0
        self.skipped = 0
        self.errors: list[str] = []


class IngestionPipeline:
    def __init__(
        self,
        instrument_repo: InstrumentRepository,
        source_repo: DataSourceRepository,
        ts_repo: TimeSeriesRepository,
        log_repo: IngestLogRepository,
        extractor: NasdaqExtractor | None = None,
    ):
        self._instruments = instrument_repo
        self._sources = source_repo
        self._ts = ts_repo
        self._logs = log_repo
        self._extractor = extractor or NasdaqExtractor()
        self._transformer = NasdaqTransformer()

    def ingest(
        self,
        instrument: FinancialInstrument,
        source: DataSource,
        datatable_code: str,
        filters: dict | None = None,
    ) -> IngestionResult:
        result = IngestionResult()
        ingested_at = datetime.now(timezone.utc)
        start_ms = int(time.time() * 1000)

        # 1. Ensure instrument and source exist (idempotent saves)
        self._instruments.save(instrument)
        self._sources.save(source)

        # 2. Extract + transform + load
        batch: list[TimeSeriesPoint] = []
        try:
            filters = filters or {"ticker": instrument.symbol}
            observed_columns: set[str] = set()
            for raw_row in self._extractor.fetch_table_data(datatable_code, filters):
                result.fetched += 1
                observed_columns.update(raw_row.keys())
                try:
                    point = self._transformer.transform(
                        raw_row, instrument.instrument_id, source.source_id, ingested_at
                    )
                    batch.append(point)
                    if len(batch) >= BATCH_SIZE:
                        result.stored += self._ts.save_batch(batch)
                        batch.clear()
                except Exception as e:
                    result.skipped += 1
                    result.errors.append(f"Row transform error: {e}")

            # Flush remaining
            if batch:
                result.stored += self._ts.save_batch(batch)
                batch.clear()

            if observed_columns:
                updated_source = source.model_copy(update={"attributes": observed_columns})
                self._sources.save(updated_source)

            status = "success"
        except Exception as e:
            status = "error"
            result.errors.append(str(e))

        # 3. Log result
        duration_ms = int(time.time() * 1000) - start_ms
        self._logs.save(IngestLog(
            source_id=source.source_id,
            ingested_at=ingested_at,
            log_id=uuid.uuid4(),
            instrument_id=instrument.instrument_id,
            status=status,
            record_count=result.stored,
            error_message="; ".join(result.errors) if result.errors else None,
            duration_ms=duration_ms,
        ))

        return result
