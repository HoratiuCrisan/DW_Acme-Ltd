from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from app.models.risk_signal import RiskSignal
from app.db.repositories.risk_signal import RiskSignalRepository


def _make_signal(**kwargs) -> RiskSignal:
    defaults = dict(
        instrument_id=uuid4(),
        generated_at=datetime.now(timezone.utc),
        signal_id=uuid4(),
        signal_type="volatility",
        severity="high",
        value=Decimal("0.85"),
    )
    return RiskSignal(**(defaults | kwargs))


def test_save_returns_entity(mock_session):
    repo = RiskSignalRepository(mock_session)
    signal = _make_signal()
    result = repo.save(signal)
    assert result == signal
    mock_session.execute.assert_called_once()


def test_find_latest_returns_signal(mock_session):
    signal = _make_signal()
    row = MagicMock()
    row.instrument_id = signal.instrument_id
    row.generated_at = signal.generated_at
    row.signal_id = signal.signal_id
    row.signal_type = signal.signal_type
    row.severity = signal.severity
    row.value = signal.value
    row.explanation = None
    row.result_id = None
    mock_session.execute.return_value.one.return_value = row

    repo = RiskSignalRepository(mock_session)
    found = repo.find_latest(signal.instrument_id)

    assert found is not None
    assert found.signal_type == signal.signal_type
    assert found.severity == signal.severity


def test_delete_methods_are_noops(mock_session):
    repo = RiskSignalRepository(mock_session)
    repo.delete(uuid4())
    repo.delete_all(uuid4())
    assert mock_session.execute.call_count == 0
