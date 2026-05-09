from typing import Iterable
from uuid import UUID

from app.db.repositories.base import CassandraRepository, WarehouseRepository
from app.models.recommendation import Recommendation


class RecommendationRepository(CassandraRepository, WarehouseRepository[Recommendation, UUID]):
    def __init__(self, session):
        super().__init__(session)
        self._insert = session.prepare(
            """
            INSERT INTO recommendations
              (user_id, created_at, recommendation_id, portfolio_id,
               signal_id, action, rationale, expires_at, was_acted_on)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        )
        self._select_latest = session.prepare(
            "SELECT * FROM recommendations WHERE user_id = ? LIMIT 1"
        )
        self._select_all = session.prepare(
            "SELECT * FROM recommendations WHERE user_id = ?"
        )

    def save(self, entity: Recommendation) -> Recommendation:
        self._execute(self._insert, [
            entity.user_id, entity.created_at, entity.recommendation_id,
            entity.portfolio_id, entity.signal_id, entity.action,
            entity.rationale, entity.expires_at, entity.was_acted_on,
        ])
        return entity

    def delete(self, key: UUID) -> None:
        pass  # Append-only

    def delete_all(self, partition_key: UUID) -> None:
        pass

    def find_latest(self, partition_key: UUID) -> Recommendation | None:
        row = self._fetch_one(self._select_latest, [partition_key])
        return self._row_to_model(row) if row else None

    def find_all(self, partition_key: UUID) -> Iterable[Recommendation]:
        rows = self._fetch_all(self._select_all, [partition_key])
        return [self._row_to_model(r) for r in rows]

    @staticmethod
    def _row_to_model(row) -> Recommendation:
        return Recommendation(
            user_id=row.user_id,
            created_at=row.created_at,
            recommendation_id=row.recommendation_id,
            portfolio_id=getattr(row, "portfolio_id", None),
            signal_id=getattr(row, "signal_id", None),
            action=row.action,
            rationale=getattr(row, "rationale", None),
            expires_at=getattr(row, "expires_at", None),
            was_acted_on=getattr(row, "was_acted_on", False),
        )
