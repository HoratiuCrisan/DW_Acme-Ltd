from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.models.recommendation import Recommendation
from app.db.repositories.recommendation import RecommendationRepository


def _make_rec(**kwargs) -> Recommendation:
    defaults = dict(
        user_id=uuid4(),
        created_at=datetime.now(timezone.utc),
        recommendation_id=uuid4(),
        action="buy",
    )
    return Recommendation(**(defaults | kwargs))


def test_save_returns_entity(mock_session):
    repo = RecommendationRepository(mock_session)
    rec = _make_rec()
    result = repo.save(rec)
    assert result == rec
    mock_session.execute.assert_called_once()


def test_find_latest_returns_recommendation(mock_session):
    rec = _make_rec()
    row = MagicMock()
    row.user_id = rec.user_id
    row.created_at = rec.created_at
    row.recommendation_id = rec.recommendation_id
    row.portfolio_id = None
    row.signal_id = None
    row.action = rec.action
    row.rationale = None
    row.expires_at = None
    row.was_acted_on = False
    mock_session.execute.return_value.one.return_value = row

    repo = RecommendationRepository(mock_session)
    found = repo.find_latest(rec.user_id)

    assert found is not None
    assert found.action == rec.action
    assert found.recommendation_id == rec.recommendation_id


def test_delete_methods_are_noops(mock_session):
    repo = RecommendationRepository(mock_session)
    repo.delete(uuid4())
    repo.delete_all(uuid4())
    assert mock_session.execute.call_count == 0
