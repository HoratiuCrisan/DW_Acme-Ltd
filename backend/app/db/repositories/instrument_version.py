from typing import Iterable
from uuid import UUID

from app.db.repositories.base import WarehouseRepository
from app.models.instrument import InstrumentVersion


class InstrumentVersionRepository(WarehouseRepository[InstrumentVersion, UUID]):
    def __init__(self, session):
        self._session = session
        self._insert = session.prepare(
            """
            INSERT INTO instrument_versions
              (instrument_id, valid_from, version_id, change_type,
               is_delete_marker, snapshot, valid_to, changed_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
        )
        self._select_latest = session.prepare(
            "SELECT * FROM instrument_versions WHERE instrument_id = ? LIMIT 1"
        )
        self._select_all = session.prepare(
            "SELECT * FROM instrument_versions WHERE instrument_id = ?"
        )

    def save(self, entity: InstrumentVersion) -> InstrumentVersion:
        self._session.execute(self._insert, [
            entity.instrument_id, entity.valid_from, entity.version_id,
            entity.change_type, entity.is_delete_marker, entity.snapshot,
            entity.valid_to, entity.changed_by,
        ])
        return entity

    def delete(self, key: UUID) -> None:
        pass  # Versions are immutable

    def delete_all(self, partition_key: UUID) -> None:
        pass

    def find_latest(self, partition_key: UUID) -> InstrumentVersion | None:
        row = self._session.execute(self._select_latest, [partition_key]).one()
        return self._row_to_model(row) if row else None

    def find_all(self, partition_key: UUID) -> Iterable[InstrumentVersion]:
        rows = self._session.execute(self._select_all, [partition_key])
        return [self._row_to_model(r) for r in rows]

    @staticmethod
    def _row_to_model(row) -> InstrumentVersion:
        return InstrumentVersion(
            instrument_id=row.instrument_id,
            valid_from=row.valid_from,
            version_id=row.version_id,
            change_type=row.change_type,
            is_delete_marker=row.is_delete_marker,
            snapshot=getattr(row, "snapshot", None),
            valid_to=getattr(row, "valid_to", None),
            changed_by=getattr(row, "changed_by", None),
        )
