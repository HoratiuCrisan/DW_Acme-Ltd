from datetime import date, datetime, timezone
from typing import Iterable
from uuid import UUID

try:
    from cassandra.concurrent import execute_concurrent_with_args
except Exception:  # pragma: no cover – driver unavailable in test env
    execute_concurrent_with_args = None  # type: ignore[assignment]

from app.db.repositories.base import WarehouseRepository
from app.models.time_series import TimeSeriesPoint


class TimeSeriesRepository(WarehouseRepository[TimeSeriesPoint, tuple]):
    def __init__(self, session):
        self._session = session
        self._insert = session.prepare(
            """
            INSERT INTO time_series_by_instrument
              (instrument_id, source_id, record_year, record_date, system_date,
               open_price, close_price, high_price, low_price, adj_close,
               volume, ex_dividend, split_ratio, extra_indicators, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        )
        self._select_latest = session.prepare(
            """
            SELECT * FROM time_series_by_instrument
            WHERE instrument_id = ? AND source_id = ? AND record_year = ?
              AND record_date = ?
            LIMIT 1
            """
        )
        self._select_by_partition = session.prepare(
            """
            SELECT * FROM time_series_by_instrument
            WHERE instrument_id = ? AND source_id = ? AND record_year = ?
            """
        )
        self._select_range = session.prepare(
            """
            SELECT * FROM time_series_by_instrument
            WHERE instrument_id = ? AND source_id = ? AND record_year = ?
              AND record_date >= ? AND record_date <= ?
            """
        )

    def save(self, entity: TimeSeriesPoint) -> TimeSeriesPoint:
        self._session.execute(self._insert, [
            entity.instrument_id, entity.source_id, entity.record_year,
            entity.record_date, entity.system_date,
            entity.open_price, entity.close_price, entity.high_price,
            entity.low_price, entity.adj_close, entity.volume,
            entity.ex_dividend, entity.split_ratio,
            entity.extra_indicators or {}, entity.ingested_at,
        ])
        return entity

    def save_batch(self, entities: list[TimeSeriesPoint]) -> int:
        """Insert a batch of points concurrently. Returns count of stored rows."""
        if not entities:
            return 0
        params = [
            [
                e.instrument_id, e.source_id, e.record_year, e.record_date,
                e.system_date, e.open_price, e.close_price, e.high_price,
                e.low_price, e.adj_close, e.volume, e.ex_dividend,
                e.split_ratio, e.extra_indicators or {}, e.ingested_at,
            ]
            for e in entities
        ]
        results = execute_concurrent_with_args(
            self._session, self._insert, params, concurrency=50, raise_on_first_error=False
        )
        errors = [e for success, e in results if not success]
        if errors:
            raise RuntimeError(f"Batch write had {len(errors)} failures: {errors[0]}")
        return len(entities)

    def delete(self, key: tuple) -> None:
        # Temporal DWH: preserve history by writing a tombstone row.
        instrument_id, source_id, record_year, record_date = key
        point = self.find_latest(key)
        if point is not None:
            tombstone = TimeSeriesPoint(
                **point.model_dump() | {
                    "extra_indicators": {"_deleted": "true"},
                    "system_date": datetime.now(timezone.utc),
                    "ingested_at": datetime.now(timezone.utc),
                }
            )
            self.save(tombstone)

    def delete_all(self, partition_key: tuple) -> None:
        # Bulk deletes would erase history, so force callers to delete rows explicitly.
        raise NotImplementedError("Temporal DWH: use delete markers, not bulk deletes")

    def find_latest(self, partition_key: tuple) -> TimeSeriesPoint | None:
        # partition_key = (instrument_id, source_id, record_year, record_date)
        instrument_id, source_id, record_year, record_date = partition_key
        row = self._session.execute(
            self._select_latest, [instrument_id, source_id, record_year, record_date]
        ).one()
        return self._row_to_model(row) if row else None

    def find_all(self, partition_key: tuple) -> Iterable[TimeSeriesPoint]:
        # partition_key = (instrument_id, source_id, record_year)
        instrument_id, source_id, record_year = partition_key
        rows = self._session.execute(
            self._select_by_partition, [instrument_id, source_id, record_year]
        )
        return [self._row_to_model(r) for r in rows]

    def find_range(
        self,
        instrument_id: UUID,
        source_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[TimeSeriesPoint]:
        results = []
        for year in range(start_date.year, end_date.year + 1):
            rows = self._session.execute(
                self._select_range,
                [instrument_id, source_id, year, start_date, end_date],
            )
            results.extend([self._row_to_model(r) for r in rows])
        return results

    @staticmethod
    def _row_to_model(row) -> TimeSeriesPoint:
        return TimeSeriesPoint(
            instrument_id=row.instrument_id,
            source_id=row.source_id,
            record_year=row.record_year,
            record_date=row.record_date,
            system_date=row.system_date,
            open_price=getattr(row, "open_price", None),
            close_price=getattr(row, "close_price", None),
            high_price=getattr(row, "high_price", None),
            low_price=getattr(row, "low_price", None),
            adj_close=getattr(row, "adj_close", None),
            volume=getattr(row, "volume", None),
            ex_dividend=getattr(row, "ex_dividend", None),
            split_ratio=getattr(row, "split_ratio", None),
            extra_indicators=getattr(row, "extra_indicators", None),
            ingested_at=row.ingested_at,
        )
