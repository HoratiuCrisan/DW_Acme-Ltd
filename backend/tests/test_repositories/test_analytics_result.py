from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from app.models.analytics_result import AnalyticsResult
from app.db.repositories.analytics_result import AnalyticsResultRepository


def _make_result(**kwargs) -> AnalyticsResult:
    defaults = dict(
        instrument_id=uuid4(),
        source_id=uuid4(),
        computed_at=datetime.now(timezone.utc),
        result_id=uuid4(),
        metric_type="avg_close",
        metric_value=Decimal("150.00"),
        window_days=30,
    )
    return AnalyticsResult(**(defaults | kwargs))


def test_save_returns_entity(mock_session):
    repo = AnalyticsResultRepository(mock_session)
    result = _make_result()
    saved = repo.save(result)
    assert saved == result
    mock_session.execute.assert_called_once()


def test_find_latest_returns_result(mock_session):
    ar = _make_result()
    row = MagicMock()
    row.instrument_id = ar.instrument_id
    row.source_id = ar.source_id
    row.computed_at = ar.computed_at
    row.result_id = ar.result_id
    row.metric_type = ar.metric_type
    row.metric_value = ar.metric_value
    row.window_days = ar.window_days
    row.notes = None
    mock_session.execute.return_value.one.return_value = row

    repo = AnalyticsResultRepository(mock_session)
    found = repo.find_latest((ar.instrument_id, ar.source_id))

    assert found is not None
    assert found.metric_type == ar.metric_type
    assert found.metric_value == ar.metric_value
