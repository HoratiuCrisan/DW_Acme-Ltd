from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.models.llm_query_log import LLMQueryLog
from app.db.repositories.llm_query_log import LLMQueryLogRepository


def _make_log(**kwargs) -> LLMQueryLog:
    defaults = dict(
        user_id=uuid4(),
        session_id=uuid4(),
        asked_at=datetime.now(timezone.utc),
        query_id=uuid4(),
        user_prompt="What is the avg close price of AAPL?",
    )
    return LLMQueryLog(**(defaults | kwargs))


def test_save_returns_entity(mock_session):
    repo = LLMQueryLogRepository(mock_session)
    log = _make_log()
    result = repo.save(log)
    assert result == log
    mock_session.execute.assert_called_once()


def test_find_latest_returns_log(mock_session):
    log = _make_log()
    row = MagicMock()
    row.user_id = log.user_id
    row.session_id = log.session_id
    row.asked_at = log.asked_at
    row.query_id = log.query_id
    row.user_prompt = log.user_prompt
    row.tools_invoked = None
    row.llm_response = None
    row.duration_ms = None
    mock_session.execute.return_value.one.return_value = row

    repo = LLMQueryLogRepository(mock_session)
    found = repo.find_latest((log.user_id, log.session_id))

    assert found is not None
    assert found.user_prompt == log.user_prompt
    assert found.query_id == log.query_id
