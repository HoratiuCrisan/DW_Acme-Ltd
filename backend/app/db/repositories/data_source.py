from typing import Iterable
from uuid import UUID

from app.db.repositories.base import CassandraRepository, WarehouseRepository
from app.models.data_source import DataSource

class DataSourceRepository(CassandraRepository, WarehouseRepository[DataSource, UUID]):
    def __init__(self, session):
        super().__init__(session)
        self._insert = session.prepare(
            """
            INSERT INTO data_sources
              (source_id, source_name, source_type, base_url,
               api_key_required, description, attributes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
        )
        self._select_by_id = session.prepare(
            "SELECT * FROM data_sources WHERE source_id = ?"
        )
        self._select_all = session.prepare(
            "SELECT * FROM data_sources"
        )
        self._delete_by_id = session.prepare(
            "DELETE FROM data_sources WHERE source_id = ?"
        )

    def save(self, entity: DataSource) -> DataSource:
        self._execute(self._insert, [
            entity.source_id, entity.source_name, entity.source_type,
            entity.base_url, entity.api_key_required, entity.description,
            entity.attributes, entity.created_at,
        ])
        return entity

    def delete(self, key: UUID) -> None:
        self._execute(self._delete_by_id, [key])

    def delete_all(self, partition_key: UUID) -> None:
        self._execute(self._delete_by_id, [partition_key])

    def find_latest(self, partition_key: UUID) -> DataSource | None:
        row = self._fetch_one(self._select_by_id, [partition_key])
        return self._row_to_model(row) if row else None

    def find_all(self, partition_key=None) -> Iterable[DataSource]:
        rows = self._fetch_all(self._select_all)
        return [self._row_to_model(r) for r in rows]

    @staticmethod
    def _row_to_model(row) -> DataSource:
        return DataSource(
            source_id=row.source_id,
            source_name=row.source_name,
            source_type=row.source_type,
            base_url=getattr(row, "base_url", None),
            api_key_required=getattr(row, "api_key_required", False),
            description=getattr(row, "description", None),
            attributes=getattr(row, "attributes", None),
            created_at=row.created_at,
        )