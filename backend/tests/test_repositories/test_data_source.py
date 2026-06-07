from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.models.data_source import DataSource
from app.db.repositories.data_source import DataSourceRepository


def _make_source(**kwargs) -> DataSource:
    defaults = dict(
        source_id=uuid4(),
        source_name="QUANDL_NYSE",
        source_type="rest",
        base_url="https://data.nasdaq.com",
        api_key_required=True,
        description="Nasdaq NYSE data",
        attributes={"Open", "High", "Low", "Close"},
        created_at=datetime.now(timezone.utc),
    )
    return DataSource(**(defaults | kwargs))


def test_save_returns_entity(mock_session):
    repo = DataSourceRepository(mock_session)
    source = _make_source()
    result = repo.save(source)
    assert result == source
    assert mock_session.execute.call_count == 1
    assert mock_session.execute.call_args[0][0] is repo._insert


def test_find_latest_returns_source(mock_session):
    source = _make_source()
    row = MagicMock()
    row.source_id = source.source_id
    row.source_name = source.source_name
    row.source_type = source.source_type
    row.base_url = source.base_url
    row.api_key_required = source.api_key_required
    row.description = source.description
    row.attributes = source.attributes
    row.created_at = source.created_at
    mock_session.execute.return_value.one.return_value = row

    repo = DataSourceRepository(mock_session)
    result = repo.find_latest(source.source_id)

    assert result is not None
    assert result.source_name == "QUANDL_NYSE"
    assert result.source_id == source.source_id
    assert result.source_type == source.source_type


def test_find_latest_returns_none_when_missing(mock_session):
    mock_session.execute.return_value.one.return_value = None
    repo = DataSourceRepository(mock_session)
    assert repo.find_latest(uuid4()) is None


def test_find_all_returns_sources(mock_session):
    sources = [_make_source(source_name=n) for n in ["QUANDL_NYSE", "BITFINEX"]]
    rows = []
    for s in sources:
        row = MagicMock()
        row.source_id = s.source_id
        row.source_name = s.source_name
        row.source_type = s.source_type
        row.base_url = s.base_url
        row.api_key_required = s.api_key_required
        row.description = s.description
        row.attributes = s.attributes
        row.created_at = s.created_at
        rows.append(row)
    mock_session.execute.return_value.__iter__ = lambda self: iter(rows)

    repo = DataSourceRepository(mock_session)
    result = list(repo.find_all(None))
    assert len(result) == 2
    names = {r.source_name for r in result}
    assert names == {"QUANDL_NYSE", "BITFINEX"}
