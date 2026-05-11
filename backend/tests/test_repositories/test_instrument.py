from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone
import pytest

from app.models.instrument import FinancialInstrument
from app.db.repositories.instrument import InstrumentRepository


def _make_instrument(**kwargs) -> FinancialInstrument:
    defaults = dict(
        instrument_id=uuid4(),
        symbol="TSLA",
        instrument_class="stock",
        name="Tesla Inc",
        region="US",
        currency="USD",
        created_at=datetime.now(timezone.utc),
    )
    return FinancialInstrument(**(defaults | kwargs))


def test_save_returns_entity(mock_session):
    repo = InstrumentRepository(mock_session)
    instrument = _make_instrument()
    result = repo.save(instrument)
    assert result == instrument
    assert mock_session.execute.call_count == 2
    calls = mock_session.execute.call_args_list
    assert calls[0][0][0] is repo._insert
    assert calls[1][0][0] is repo._insert_by_class


def test_find_latest_returns_instrument(mock_session):
    instrument = _make_instrument()
    row = MagicMock()
    row.instrument_id = instrument.instrument_id
    row.symbol = instrument.symbol
    row.instrument_class = instrument.instrument_class
    row.name = instrument.name
    row.region = instrument.region
    row.currency = instrument.currency
    row.exchange_id = None
    row.description = None
    row.created_at = instrument.created_at
    mock_session.execute.return_value.one.return_value = row

    repo = InstrumentRepository(mock_session)
    result = repo.find_latest(instrument.instrument_id)

    assert result is not None
    assert result.symbol == instrument.symbol
    assert result.instrument_id == instrument.instrument_id
    assert result.region == instrument.region
    assert result.currency == instrument.currency
    assert result.created_at == instrument.created_at


def test_find_latest_returns_none_when_missing(mock_session):
    mock_session.execute.return_value.one.return_value = None
    repo = InstrumentRepository(mock_session)
    result = repo.find_latest(uuid4())
    assert result is None


def test_find_all_returns_all_instruments(mock_session):
    instruments = [_make_instrument(symbol=s) for s in ["TSLA", "AAPL"]]
    rows = []
    for inst in instruments:
        row = MagicMock()
        row.instrument_id = inst.instrument_id
        row.symbol = inst.symbol
        row.instrument_class = inst.instrument_class
        row.name = inst.name
        row.region = inst.region
        row.currency = inst.currency
        row.exchange_id = None
        row.description = None
        row.created_at = inst.created_at
        rows.append(row)
    mock_session.execute.return_value.__iter__ = lambda self: iter(rows)

    repo = InstrumentRepository(mock_session)
    result = list(repo.find_all(None))
    assert len(result) == 2
    symbols = {r.symbol for r in result}
    assert symbols == {"TSLA", "AAPL"}
