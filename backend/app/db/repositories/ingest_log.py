from typing import Iterable

from app.db.repositories.base import CassandraRepository, WarehouseRepository
from app.models.ingest_log import IngestLog


class IngestLogRepository(CassandraRepository, WarehouseRepository[IngestLog, tuple]):
    def __init__(self, session):
        super().__init__(session)
        self._insert = session.prepare(
            """
            INSERT INTO ingest_log
              (source_id, log_year, ingested_at, log_id, instrument_id,
               status, record_count, error_message, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        )
        self._select_latest = session.prepare(
            "SELECT * FROM ingest_log WHERE source_id = ? AND log_year = ? LIMIT 1"
        )
        self._select_all = session.prepare(
            "SELECT * FROM ingest_log WHERE source_id = ? AND log_year = ?"
        )

    def save(self, entity: IngestLog) -> IngestLog:
        self._execute(self._insert, [
            entity.source_id, entity.log_year, entity.ingested_at,
            entity.log_id, entity.instrument_id, entity.status,
            entity.record_count, entity.error_message, entity.duration_ms,
        ])
        return entity

    def delete(self, key: tuple) -> None:
        pass  # Logs are immutable

    def delete_all(self, partition_key: tuple) -> None:
        pass

    def find_latest(self, partition_key: tuple) -> IngestLog | None:
        source_id, log_year = partition_key
        row = self._fetch_one(self._select_latest, [source_id, log_year])
        return self._row_to_model(row) if row else None

    def find_all(self, partition_key: tuple) -> Iterable[IngestLog]:
        source_id, log_year = partition_key
        rows = self._fetch_all(self._select_all, [source_id, log_year])
        return [self._row_to_model(r) for r in rows]

    @staticmethod
    def _row_to_model(row) -> IngestLog:
        return IngestLog(
            source_id=row.source_id,
            log_year=row.log_year,
            ingested_at=row.ingested_at,
            log_id=row.log_id,
            instrument_id=row.instrument_id,
            status=row.status,
            record_count=getattr(row, "record_count", 0),
            error_message=getattr(row, "error_message", None),
            duration_ms=getattr(row, "duration_ms", None),
        )
