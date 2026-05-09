from typing import Iterable
from uuid import UUID

from app.db.repositories.base import CassandraRepository, WarehouseRepository
from app.models.portfolio import Portfolio, PortfolioAsset


class PortfolioRepository(CassandraRepository, WarehouseRepository[Portfolio, tuple]):
    def __init__(self, session):
        super().__init__(session)
        self._insert = session.prepare(
            """
            INSERT INTO portfolios_by_owner
              (owner_id, portfolio_id, name, base_currency,
               description, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
        )
        self._select_by_key = session.prepare(
            """
            SELECT * FROM portfolios_by_owner
            WHERE owner_id = ? AND portfolio_id = ? LIMIT 1
            """
        )
        self._select_by_owner = session.prepare(
            "SELECT * FROM portfolios_by_owner WHERE owner_id = ?"
        )
        self._delete_by_key = session.prepare(
            "DELETE FROM portfolios_by_owner WHERE owner_id = ? AND portfolio_id = ?"
        )
        self._delete_by_owner = session.prepare(
            "DELETE FROM portfolios_by_owner WHERE owner_id = ?"
        )

    def save(self, entity: Portfolio) -> Portfolio:
        self._execute(self._insert, [
            entity.owner_id, entity.portfolio_id, entity.name,
            entity.base_currency, entity.description,
            entity.created_at, entity.is_active,
        ])
        return entity

    def delete(self, key: tuple) -> None:
        owner_id, portfolio_id = key
        self._execute(self._delete_by_key, [owner_id, portfolio_id])

    def delete_all(self, partition_key: UUID) -> None:
        self._execute(self._delete_by_owner, [partition_key])

    def find_latest(self, partition_key: tuple) -> Portfolio | None:
        owner_id, portfolio_id = partition_key
        row = self._fetch_one(self._select_by_key, [owner_id, portfolio_id])
        return self._row_to_model(row) if row else None

    def find_all(self, partition_key: UUID) -> Iterable[Portfolio]:
        rows = self._fetch_all(self._select_by_owner, [partition_key])
        return [self._row_to_model(r) for r in rows]

    @staticmethod
    def _row_to_model(row) -> Portfolio:
        return Portfolio(
            owner_id=row.owner_id,
            portfolio_id=row.portfolio_id,
            name=row.name,
            base_currency=row.base_currency,
            description=getattr(row, "description", None),
            created_at=row.created_at,
            is_active=getattr(row, "is_active", True),
        )


class PortfolioAssetRepository(CassandraRepository, WarehouseRepository[PortfolioAsset, tuple]):
    def __init__(self, session):
        super().__init__(session)
        self._insert = session.prepare(
            """
            INSERT INTO portfolio_assets
              (portfolio_id, instrument_id, added_at, symbol,
               instrument_class, removed_at, quantity, purchase_price, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        )
        self._select_latest = session.prepare(
            """
            SELECT * FROM portfolio_assets
            WHERE portfolio_id = ? AND instrument_id = ? LIMIT 1
            """
        )
        self._select_by_portfolio = session.prepare(
            "SELECT * FROM portfolio_assets WHERE portfolio_id = ?"
        )
        self._delete_by_key = session.prepare(
            """
            DELETE FROM portfolio_assets
            WHERE portfolio_id = ? AND instrument_id = ? AND added_at = ?
            """
        )
        self._delete_by_portfolio = session.prepare(
            "DELETE FROM portfolio_assets WHERE portfolio_id = ?"
        )

    def save(self, entity: PortfolioAsset) -> PortfolioAsset:
        self._execute(self._insert, [
            entity.portfolio_id, entity.instrument_id, entity.added_at,
            entity.symbol, entity.instrument_class, entity.removed_at,
            entity.quantity, entity.purchase_price, entity.notes,
        ])
        return entity

    def delete(self, key: tuple) -> None:
        portfolio_id, instrument_id, added_at = key
        self._execute(self._delete_by_key, [portfolio_id, instrument_id, added_at])

    def delete_all(self, partition_key: tuple) -> None:
        portfolio_id = partition_key
        self._execute(self._delete_by_portfolio, [portfolio_id])

    def find_latest(self, partition_key: tuple) -> PortfolioAsset | None:
        portfolio_id, instrument_id = partition_key
        row = self._fetch_one(self._select_latest, [portfolio_id, instrument_id])
        return self._row_to_model(row) if row else None

    def find_all(self, partition_key: UUID) -> Iterable[PortfolioAsset]:
        rows = self._fetch_all(self._select_by_portfolio, [partition_key])
        return [self._row_to_model(r) for r in rows]

    @staticmethod
    def _row_to_model(row) -> PortfolioAsset:
        return PortfolioAsset(
            portfolio_id=row.portfolio_id,
            instrument_id=row.instrument_id,
            added_at=row.added_at,
            symbol=row.symbol,
            instrument_class=row.instrument_class,
            removed_at=getattr(row, "removed_at", None),
            quantity=getattr(row, "quantity", None),
            purchase_price=getattr(row, "purchase_price", None),
            notes=getattr(row, "notes", None),
        )
