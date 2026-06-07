from typing import Iterable

from app.db.repositories.base import WarehouseRepository
from app.models.llm_query_log import LLMQueryLog


class LLMQueryLogRepository(WarehouseRepository[LLMQueryLog, tuple]):
    def __init__(self, session):
        self._session = session
        self._insert = session.prepare(
            """
            INSERT INTO llm_query_log
              (user_id, session_id, asked_at, query_id, user_prompt,
               tools_invoked, llm_response, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
        )
        self._select_latest = session.prepare(
            """
            SELECT * FROM llm_query_log
            WHERE user_id = ? AND session_id = ? LIMIT 1
            """
        )
        self._select_all = session.prepare(
            """
            SELECT * FROM llm_query_log
            WHERE user_id = ? AND session_id = ?
            """
        )

    def save(self, entity: LLMQueryLog) -> LLMQueryLog:
        self._session.execute(self._insert, [
            entity.user_id, entity.session_id, entity.asked_at,
            entity.query_id, entity.user_prompt, entity.tools_invoked,
            entity.llm_response, entity.duration_ms,
        ])
        return entity

    def delete(self, key: tuple) -> None:
        pass  # Append-only

    def delete_all(self, partition_key: tuple) -> None:
        pass

    def find_latest(self, partition_key: tuple) -> LLMQueryLog | None:
        user_id, session_id = partition_key
        row = self._session.execute(self._select_latest, [user_id, session_id]).one()
        return self._row_to_model(row) if row else None

    def find_all(self, partition_key: tuple) -> Iterable[LLMQueryLog]:
        user_id, session_id = partition_key
        rows = self._session.execute(self._select_all, [user_id, session_id])
        return [self._row_to_model(r) for r in rows]

    @staticmethod
    def _row_to_model(row) -> LLMQueryLog:
        return LLMQueryLog(
            user_id=row.user_id,
            session_id=row.session_id,
            asked_at=row.asked_at,
            query_id=row.query_id,
            user_prompt=row.user_prompt,
            tools_invoked=getattr(row, "tools_invoked", None),
            llm_response=getattr(row, "llm_response", None),
            duration_ms=getattr(row, "duration_ms", None),
        )
