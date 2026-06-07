from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.models.time_series import TimeSeriesPoint


def test_time_series_extra_indicators_is_not_shared():
    now = datetime.now(timezone.utc)
    first = TimeSeriesPoint(
        instrument_id=uuid4(),
        source_id=uuid4(),
        record_year=2024,
        record_date=date(2024, 1, 1),
        system_date=now,
        open_price=Decimal("1"),
        close_price=Decimal("1"),
        high_price=Decimal("1"),
        low_price=Decimal("1"),
        adj_close=Decimal("1"),
        volume=1,
        ex_dividend=Decimal("0"),
        split_ratio=Decimal("1"),
        ingested_at=now,
    )
    second = TimeSeriesPoint(
        instrument_id=uuid4(),
        source_id=uuid4(),
        record_year=2024,
        record_date=date(2024, 1, 2),
        system_date=now,
        open_price=Decimal("1"),
        close_price=Decimal("1"),
        high_price=Decimal("1"),
        low_price=Decimal("1"),
        adj_close=Decimal("1"),
        volume=1,
        ex_dividend=Decimal("0"),
        split_ratio=Decimal("1"),
        ingested_at=now,
    )

    first.extra_indicators["x"] = "1"

    assert second.extra_indicators == {}
