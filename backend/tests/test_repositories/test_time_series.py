from unittest.mock import MagicMock
from uuid import uuid4
from datetime import date, datetime, timezone
from decimal import Decimal

from app.models.time_series import TimeSeriesPoint
from app.db.repositories.time_series import TimeSeriesRepository


def _make_point(**kwargs) -> TimeSeriesPoint:
    now = datetime.now(timezone.utc)
    defaults = dict(
        instrument_id=uuid4(),
        source_id=uuid4(),
        record_year=2024,
        record_date=date(2024, 1, 15),
        system_date=now,
        open_price=Decimal("100.50"),
        close_price=Decimal("102.30"),
        high_price=Decimal("103.00"),
        low_price=Decimal("99.80"),
        adj_close=Decimal("102.30"),
        volume=1500000,
        ex_dividend=Decimal("0"),
        split_ratio=Decimal("1.0"),
        extra_indicators={},
        ingested_at=now,
    )
    return TimeSeriesPoint(**(defaults | kwargs))


def test_save_returns_entity(mock_session):
    repo = TimeSeriesRepository(mock_session)
    point = _make_point()
    result = repo.save(point)
    assert result == point
    assert mock_session.execute.call_count == 1
    assert mock_session.execute.call_args[0][0] is repo._insert


def test_find_latest_returns_point(mock_session):
    point = _make_point()
    row = MagicMock()
    for field, value in point.model_dump().items():
        setattr(row, field, value)
    mock_session.execute.return_value.one.return_value = row

    repo = TimeSeriesRepository(mock_session)
    key = (point.instrument_id, point.source_id, point.record_year, point.record_date)
    result = repo.find_latest(key)

    assert result is not None
    assert result.record_date == date(2024, 1, 15)
    assert result.close_price == Decimal("102.30")


def test_find_latest_returns_none_when_missing(mock_session):
    mock_session.execute.return_value.one.return_value = None
    repo = TimeSeriesRepository(mock_session)
    key = (uuid4(), uuid4(), 2024, date(2024, 1, 15))
    assert repo.find_latest(key) is None


def test_find_all_returns_points(mock_session):
    points = [_make_point(record_date=date(2024, 1, d)) for d in [15, 16, 17]]
    rows = []
    for p in points:
        row = MagicMock()
        for field, value in p.model_dump().items():
            setattr(row, field, value)
        rows.append(row)
    mock_session.execute.return_value.__iter__ = lambda self: iter(rows)

    repo = TimeSeriesRepository(mock_session)
    key = (points[0].instrument_id, points[0].source_id, 2024)
    result = list(repo.find_all(key))
    assert len(result) == 3


def test_find_range_single_year(mock_session):
    point = _make_point()
    row = MagicMock()
    for field, value in point.model_dump().items():
        setattr(row, field, value)
    mock_session.execute.return_value.__iter__ = lambda self: iter([row])

    repo = TimeSeriesRepository(mock_session)
    results = repo.find_range(
        point.instrument_id,
        point.source_id,
        date(2024, 1, 1),
        date(2024, 12, 31),
    )
    assert len(results) == 1
    # For a single year range, execute should be called once (after __init__ prepares)
    # The last execute call uses _select_range
    last_call = mock_session.execute.call_args_list[-1]
    assert last_call[0][0] is repo._select_range


def test_find_range_cross_year_calls_execute_twice(mock_session):
    instrument_id = uuid4()
    source_id = uuid4()
    mock_session.execute.return_value.__iter__ = lambda self: iter([])

    repo = TimeSeriesRepository(mock_session)
    # Reset call count after __init__
    mock_session.execute.reset_mock()

    repo.find_range(instrument_id, source_id, date(2023, 11, 1), date(2024, 3, 31))

    # Should execute once for year 2023, once for year 2024
    assert mock_session.execute.call_count == 2
    calls = mock_session.execute.call_args_list
    # First call: year=2023
    assert calls[0][0][1][2] == 2023
    # Second call: year=2024
    assert calls[1][0][1][2] == 2024


def test_delete_writes_tombstone(mock_session):
    point = _make_point()
    row = MagicMock()
    for field, value in point.model_dump().items():
        setattr(row, field, value)
    mock_session.execute.return_value.one.return_value = row

    repo = TimeSeriesRepository(mock_session)
    mock_session.execute.reset_mock()

    key = (point.instrument_id, point.source_id, point.record_year, point.record_date)
    repo.delete(key)

    # Should call execute twice: once for find_latest (SELECT), once for save (INSERT tombstone)
    assert mock_session.execute.call_count == 2
    # The second call is the tombstone INSERT
    insert_call = mock_session.execute.call_args_list[1]
    tombstone_params = insert_call[0][1]
    # extra_indicators is the 14th parameter (index 13) in the INSERT
    assert tombstone_params[13] == {"_deleted": "true"}


def test_delete_on_missing_key_does_nothing(mock_session):
    mock_session.execute.return_value.one.return_value = None

    repo = TimeSeriesRepository(mock_session)
    mock_session.execute.reset_mock()

    key = (uuid4(), uuid4(), 2024, date(2024, 1, 15))
    repo.delete(key)  # Should not raise

    # Only the find_latest SELECT should be called, no INSERT
    assert mock_session.execute.call_count == 1


def test_save_batch_executes_concurrently(mock_session):
    from unittest.mock import patch

    points = [_make_point(record_date=date(2024, 1, d)) for d in range(1, 6)]

    repo = TimeSeriesRepository(mock_session)

    fake_results = [(True, None)] * len(points)
    with patch("app.db.repositories.time_series.execute_concurrent_with_args", return_value=fake_results) as mock_exec:
        count = repo.save_batch(points)

    assert count == 5
    mock_exec.assert_called_once()
    call_args = mock_exec.call_args
    assert call_args[0][0] is mock_session          # session
    assert call_args[0][1] is repo._insert           # prepared statement
    assert len(call_args[0][2]) == 5                 # 5 param lists
