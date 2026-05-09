from typing import Iterable

from app.db.repositories.base import CassandraRepository, WarehouseRepository
from app.models.analytics_result import AnalyticsResult

class AnalyticsResultRepository(CassandraRepository, WarehouseRepository[AnalyticsResult, tuple]):
    def __init__(self, session):
        super().__init__(session)
        self._insert = session.prepare(
            """
            INSERT INTO analytics_results
              (instrument_id, source_id, computed_at, result_id,
               metric_type, metric_value, window_days, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
        )
        self._select_latest = session.prepare(
            """
            SELECT * FROM analytics_results
            WHERE instrument_id = ? AND source_id = ? LIMIT 1
            """
        )
        self._select_all = session.prepare(
            """
            SELECT * FROM analytics_results
            WHERE instrument_id = ? AND source_id = ?
            """
        )

    def save(self, entity: AnalyticsResult) -> AnalyticsResult:
        self._execute(self._insert, [
            entity.instrument_id, entity.source_id, entity.computed_at,
            entity.result_id, entity.metric_type, entity.metric_value,
            entity.window_days, entity.notes,
        ])
        return entity

    def delete(self, key: tuple) -> None:
        pass  # Append-only

    def delete_all(self, partition_key: tuple) -> None:
        pass

    def find_latest(self, partition_key: tuple) -> AnalyticsResult | None:
        instrument_id, source_id = partition_key
        row = self._fetch_one(self._select_latest, [instrument_id, source_id])
        return self._row_to_model(row) if row else None

    def find_all(self, partition_key: tuple) -> Iterable[AnalyticsResult]:
        instrument_id, source_id = partition_key
        rows = self._fetch_all(self._select_all, [instrument_id, source_id])
        return [self._row_to_model(r) for r in rows]

    @staticmethod
    def _row_to_model(row) -> AnalyticsResult:
        return AnalyticsResult(
            instrument_id=row.instrument_id,
            source_id=row.source_id,
            computed_at=row.computed_at,
            result_id=row.result_id,
            metric_type=row.metric_type,
            metric_value=getattr(row, "metric_value", None),
            window_days=getattr(row, "window_days", None),
            notes=getattr(row, "notes", None),
        )
