from typing import Iterable
from uuid import UUID

from app.db.repositories.base import CassandraRepository, WarehouseRepository
from app.models.exchange import Exchange


class ExchangeRepository(CassandraRepository, WarehouseRepository[Exchange, UUID]):
    def __init__(self, session):
        super().__init__(session)
        self._insert = session.prepare(
            """
            INSERT INTO exchanges
              (exchange_id, exchange_name, country, timezone, currency, open_time, close_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
        )
        self._select_by_id = session.prepare(
            "SELECT * FROM exchanges WHERE exchange_id = ?"
        )
        self._select_all = session.prepare(
            "SELECT * FROM exchanges"
        )
        self._delete_by_id = session.prepare(
            "DELETE FROM exchanges WHERE exchange_id = ?"
        )

    def save(self, entity: Exchange) -> Exchange:
        self._execute(self._insert, [
            entity.exchange_id, entity.exchange_name, entity.country,
            entity.timezone, entity.currency, entity.open_time, entity.close_time,
        ])
        return entity

    def delete(self, key: UUID) -> None:
        self._execute(self._delete_by_id, [key])

    def delete_all(self, partition_key: UUID) -> None:
        self._execute(self._delete_by_id, [partition_key])

    def find_latest(self, partition_key: UUID) -> Exchange | None:
        row = self._fetch_one(self._select_by_id, [partition_key])
        return self._row_to_model(row) if row else None

    def find_all(self, partition_key=None) -> Iterable[Exchange]:
        rows = self._fetch_all(self._select_all)
        return [self._row_to_model(r) for r in rows]

    @staticmethod
    def _row_to_model(row) -> Exchange:
        return Exchange(
            exchange_id=row.exchange_id,
            exchange_name=row.exchange_name,
            country=getattr(row, "country", None),
            timezone=getattr(row, "timezone", None),
            currency=getattr(row, "currency", None),
            open_time=getattr(row, "open_time", None),
            close_time=getattr(row, "close_time", None),
        )
