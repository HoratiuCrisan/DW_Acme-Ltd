from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID


ASSET_ID = UUID("11111111-1111-1111-1111-111111111111")
SOURCE_ID = UUID("22222222-2222-2222-2222-222222222222")


class DemoResult(list):
    def one(self):
        return self[0] if self else None


class DemoSession:
    def prepare(self, statement: str) -> str:
        return statement

    def execute(self, statement: str, params=None):
        query = " ".join(statement.lower().split())
        params = params or []

        if "from financial_instruments where instrument_id" in query:
            return DemoResult([_instrument()]) if params and params[0] == ASSET_ID else DemoResult()
        if "from financial_instruments" in query:
            return DemoResult([_instrument()])

        if "from data_sources where source_id" in query:
            return DemoResult([_source()]) if params and params[0] == SOURCE_ID else DemoResult()
        if "from data_sources" in query:
            return DemoResult([_source()])

        if "from time_series_by_instrument" in query:
            return DemoResult(_time_series(params))

        if "from ingest_log" in query:
            return DemoResult([_ingest_log()])
        if "from ingest_jobs" in query:
            return DemoResult([_ingest_job()])
        if "from analytics_results" in query:
            return DemoResult()

        return DemoResult()


def get_demo_session() -> DemoSession:
    return DemoSession()


def _instrument():
    return SimpleNamespace(
        instrument_id=ASSET_ID,
        symbol="AAPL",
        instrument_class="stock",
        name="Apple Inc",
        region="US",
        currency="USD",
        exchange_id=None,
        description="Demo financial instrument",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _source():
    return SimpleNamespace(
        source_id=SOURCE_ID,
        source_name="NASDAQ_DEMO",
        source_type="REST",
        base_url="https://data.nasdaq.com/api/v3/datatables",
        api_key_required=True,
        description="Demo Nasdaq Data Link source",
        attributes={"open", "close", "high", "low", "volume", "quality"},
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _time_series(params):
    points = [
        _point(date(2024, 1, 17), datetime(2024, 1, 17, 16, tzinfo=timezone.utc), "188.50", 980000),
        _point(date(2024, 1, 16), datetime(2024, 1, 16, 16, tzinfo=timezone.utc), "185.20", 1100000),
        _point(date(2024, 1, 15), datetime(2024, 1, 15, 15, tzinfo=timezone.utc), "181.10", 1250000),
        _point(date(2024, 1, 15), datetime(2024, 1, 15, 16, tzinfo=timezone.utc), "182.75", 1265000),
    ]
    if len(params) >= 5:
        start_date = params[3]
        end_date = params[4]
        points = [p for p in points if start_date <= p.record_date <= end_date]
    return points


def _point(record_date: date, system_date: datetime, close: str, volume: int):
    close_price = Decimal(close)
    return SimpleNamespace(
        instrument_id=ASSET_ID,
        source_id=SOURCE_ID,
        record_year=record_date.year,
        record_date=record_date,
        system_date=system_date,
        open_price=close_price - Decimal("1.25"),
        close_price=close_price,
        high_price=close_price + Decimal("2.10"),
        low_price=close_price - Decimal("3.05"),
        adj_close=close_price,
        volume=volume,
        ex_dividend=Decimal("0"),
        split_ratio=Decimal("1"),
        extra_indicators={"quality": "demo"},
        ingested_at=system_date,
    )


def _ingest_log():
    return SimpleNamespace(
        source_id=SOURCE_ID,
        log_year=2024,
        ingested_at=datetime(2024, 1, 17, 17, tzinfo=timezone.utc),
        log_id=UUID("33333333-3333-3333-3333-333333333333"),
        instrument_id=ASSET_ID,
        status="success",
        record_count=4,
        error_message=None,
        duration_ms=1200,
    )


def _ingest_job():
    return SimpleNamespace(
        job_id=UUID("44444444-4444-4444-4444-444444444444"),
        symbol="AAPL",
        datatable_code="WIKI/PRICES",
        status="completed",
        queued_at=datetime(2024, 1, 17, 16, tzinfo=timezone.utc),
        started_at=datetime(2024, 1, 17, 16, 1, tzinfo=timezone.utc),
        completed_at=datetime(2024, 1, 17, 16, 2, tzinfo=timezone.utc),
        record_count=4,
        error_message=None,
    )
