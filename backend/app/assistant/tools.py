import json
from datetime import date
from uuid import UUID

from app.db.repositories.instrument import InstrumentRepository
from app.db.repositories.data_source import DataSourceRepository
from app.db.repositories.time_series import TimeSeriesRepository
from app.analytics.aggregations import compute_aggregations

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_instruments",
            "description": "List all financial instruments in the warehouse. Returns id, symbol, name, class, and region for each.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_instrument",
            "description": "Get full details for a single financial instrument by its UUID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "instrument_id": {
                        "type": "string",
                        "description": "UUID of the instrument",
                    }
                },
                "required": ["instrument_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_sources",
            "description": "List all data sources (providers) available in the warehouse.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time_series",
            "description": "Get OHLCV time series data for an instrument from a data source within a date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "instrument_id": {
                        "type": "string",
                        "description": "UUID of the instrument",
                    },
                    "source_id": {
                        "type": "string",
                        "description": "UUID of the data source",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                    },
                },
                "required": ["instrument_id", "source_id", "start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_analytics",
            "description": "Compute aggregated statistics (min/max/avg close price, total volume, record count) for an instrument over a date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "instrument_id": {
                        "type": "string",
                        "description": "UUID of the instrument",
                    },
                    "source_id": {
                        "type": "string",
                        "description": "UUID of the data source",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                    },
                },
                "required": ["instrument_id", "source_id", "start_date", "end_date"],
            },
        },
    },
]


def execute_tool(name: str, args: dict, session) -> str:
    """Execute a named tool with the given args. Returns a JSON string result."""
    try:
        if name == "list_instruments":
            repo = InstrumentRepository(session)
            instruments = list(repo.find_all())
            return json.dumps([
                {
                    "instrument_id": str(i.instrument_id),
                    "symbol": i.symbol,
                    "name": i.name,
                    "class": i.instrument_class,
                    "region": i.region,
                }
                for i in instruments
            ])

        elif name == "get_instrument":
            repo = InstrumentRepository(session)
            instrument = repo.find_latest(UUID(args["instrument_id"]))
            if instrument is None:
                return json.dumps({"error": "Instrument not found"})
            return json.dumps({
                "instrument_id": str(instrument.instrument_id),
                "symbol": instrument.symbol,
                "name": instrument.name,
                "class": instrument.instrument_class,
                "region": instrument.region,
                "currency": instrument.currency,
            })

        elif name == "list_sources":
            repo = DataSourceRepository(session)
            sources = list(repo.find_all())
            return json.dumps([
                {
                    "source_id": str(s.source_id),
                    "name": s.source_name,
                    "type": s.source_type,
                }
                for s in sources
            ])

        elif name == "get_time_series":
            repo = TimeSeriesRepository(session)
            # The date inputs are validated here so the repositories stay query-focused.
            points = repo.find_range(
                UUID(args["instrument_id"]),
                UUID(args["source_id"]),
                date.fromisoformat(args["start_date"]),
                date.fromisoformat(args["end_date"]),
            )
            return json.dumps([
                {
                    "date": str(p.record_date),
                    "open": str(p.open_price) if p.open_price is not None else None,
                    "close": str(p.close_price) if p.close_price is not None else None,
                    "high": str(p.high_price) if p.high_price is not None else None,
                    "low": str(p.low_price) if p.low_price is not None else None,
                    "volume": p.volume,
                }
                for p in points
            ])

        elif name == "get_analytics":
            # Reuse the time-series repository and compute aggregates in-process.
            repo = TimeSeriesRepository(session)
            points = repo.find_range(
                UUID(args["instrument_id"]),
                UUID(args["source_id"]),
                date.fromisoformat(args["start_date"]),
                date.fromisoformat(args["end_date"]),
            )
            agg = compute_aggregations(points)
            return json.dumps({
                "count": agg.count,
                "min_close": str(agg.min_close) if agg.min_close is not None else None,
                "max_close": str(agg.max_close) if agg.max_close is not None else None,
                "avg_close": str(agg.avg_close) if agg.avg_close is not None else None,
                "total_volume": agg.total_volume,
            })

        else:
            return json.dumps({"error": f"Unknown tool: {name}"})

    except Exception as e:
        return json.dumps({"error": str(e)})
