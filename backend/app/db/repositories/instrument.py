from typing import Iterable
from uuid import UUID

from app.db.repositories.base import CassandraRepository, WarehouseRepository
from app.models.instrument import FinancialInstrument, InstrumentSummary


class InstrumentRepository(CassandraRepository, WarehouseRepository[FinancialInstrument, UUID]):
    def __init__(self, session):
        super().__init__(session)
        self._insert = session.prepare(
            """
            INSERT INTO financial_instruments
              (instrument_id, symbol, instrument_class, name, region, currency,
               exchange_id, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        )
        self._insert_by_class = session.prepare(
            """
            INSERT INTO instruments_by_class
              (instrument_class, symbol, instrument_id, name, region, exchange_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """
        )
        self._select_by_id = session.prepare(
            "SELECT * FROM financial_instruments WHERE instrument_id = ?"
        )
        self._delete_by_id = session.prepare(
            "DELETE FROM financial_instruments WHERE instrument_id = ?"
        )
        self._select_all = session.prepare(
            "SELECT * FROM financial_instruments"
        )
        self._select_by_class = session.prepare(
            "SELECT * FROM instruments_by_class WHERE instrument_class = ?"
        )
        self._delete_by_class = session.prepare(
            "DELETE FROM instruments_by_class WHERE instrument_class = ? AND symbol = ?"
        )

    def save(self, entity: FinancialInstrument) -> FinancialInstrument:
        self._execute(self._insert, [
            entity.instrument_id, entity.symbol, entity.instrument_class,
            entity.name, entity.region, entity.currency,
            entity.exchange_id, entity.description, entity.created_at,
        ])
        self._execute(self._insert_by_class, [
            entity.instrument_class, entity.symbol, entity.instrument_id,
            entity.name, entity.region, entity.exchange_id,
        ])
        return entity

    def delete(self, key: UUID) -> None:
        instrument = self.find_latest(key)
        if instrument is not None:
            self._execute(self._delete_by_class, [instrument.instrument_class, instrument.symbol])
        self._execute(self._delete_by_id, [key])

    def delete_all(self, partition_key: UUID) -> None:
        self._execute(self._delete_by_id, [partition_key])

    def find_latest(self, partition_key: UUID) -> FinancialInstrument | None:
        row = self._fetch_one(self._select_by_id, [partition_key])
        return self._row_to_model(row) if row else None

    def find_all(self, partition_key=None) -> Iterable[FinancialInstrument]:
        rows = self._fetch_all(self._select_all)
        return [self._row_to_model(r) for r in rows]

    def find_all_by_class(self, instrument_class: str) -> Iterable[InstrumentSummary]:
        rows = self._fetch_all(self._select_by_class, [instrument_class])
        return [
            InstrumentSummary(
                instrument_id=r.instrument_id,
                symbol=r.symbol,
                instrument_class=r.instrument_class,
                name=r.name,
                region=r.region,
                exchange_id=getattr(r, "exchange_id", None),
            )
            for r in rows
        ]

    @staticmethod
    def _row_to_model(row) -> FinancialInstrument:
        return FinancialInstrument(
            instrument_id=row.instrument_id,
            symbol=row.symbol,
            instrument_class=row.instrument_class,
            name=row.name,
            region=row.region,
            currency=row.currency,
            exchange_id=getattr(row, "exchange_id", None),
            description=getattr(row, "description", None),
            created_at=row.created_at,
        )
