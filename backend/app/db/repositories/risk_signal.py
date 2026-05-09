from typing import Iterable
from uuid import UUID

from app.db.repositories.base import CassandraRepository, WarehouseRepository
from app.models.risk_signal import RiskSignal


class RiskSignalRepository(CassandraRepository, WarehouseRepository[RiskSignal, UUID]):
    def __init__(self, session):
        super().__init__(session)
        self._insert = session.prepare(
            """
            INSERT INTO risk_signals
              (instrument_id, generated_at, signal_id, signal_type,
               severity, value, explanation, result_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
        )
        self._select_latest = session.prepare(
            "SELECT * FROM risk_signals WHERE instrument_id = ? LIMIT 1"
        )
        self._select_all = session.prepare(
            "SELECT * FROM risk_signals WHERE instrument_id = ?"
        )

    def save(self, entity: RiskSignal) -> RiskSignal:
        self._execute(self._insert, [
            entity.instrument_id, entity.generated_at, entity.signal_id,
            entity.signal_type, entity.severity, entity.value,
            entity.explanation, entity.result_id,
        ])
        return entity

    def delete(self, key: UUID) -> None:
        pass  # Append-only

    def delete_all(self, partition_key: UUID) -> None:
        pass

    def find_latest(self, partition_key: UUID) -> RiskSignal | None:
        row = self._fetch_one(self._select_latest, [partition_key])
        return self._row_to_model(row) if row else None

    def find_all(self, partition_key: UUID) -> Iterable[RiskSignal]:
        rows = self._fetch_all(self._select_all, [partition_key])
        return [self._row_to_model(r) for r in rows]

    @staticmethod
    def _row_to_model(row) -> RiskSignal:
        return RiskSignal(
            instrument_id=row.instrument_id,
            generated_at=row.generated_at,
            signal_id=row.signal_id,
            signal_type=row.signal_type,
            severity=row.severity,
            value=getattr(row, "value", None),
            explanation=getattr(row, "explanation", None),
            result_id=getattr(row, "result_id", None),
        )
