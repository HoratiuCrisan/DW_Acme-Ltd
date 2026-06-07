from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.db.repositories.data_source import DataSourceRepository
from app.db.repositories.instrument import InstrumentRepository
from app.db.repositories.time_series import TimeSeriesRepository

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 1000
DEFAULT_TIME_SERIES_LIMIT = 1000
MAX_TIME_SERIES_LIMIT = 5000
MAX_TIME_SERIES_DAYS = 366


class MCPToolError(Exception):
    def __init__(self, message: str, code: str = "invalid_params"):
        super().__init__(message)
        self.code = code


class PageArgs(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT)


class AssetDetailsArgs(BaseModel):
    assetId: UUID


class DataSourceDetailsArgs(BaseModel):
    dataSourceId: UUID


class TimeSeriesArgs(BaseModel):
    assetId: UUID
    dataSourceId: UUID
    startBusinessDate: date
    endBusinessDate: date
    includeAttributes: bool = False
    limit: int = Field(default=DEFAULT_TIME_SERIES_LIMIT, ge=1, le=MAX_TIME_SERIES_LIMIT)

    @field_validator("endBusinessDate")
    @classmethod
    def _valid_range(cls, end_date: date, info):
        start_date = info.data.get("startBusinessDate")
        if start_date is None:
            return end_date
        if end_date < start_date:
            raise ValueError("endBusinessDate must be on or after startBusinessDate")
        if (end_date - start_date).days > MAX_TIME_SERIES_DAYS:
            raise ValueError(f"time-series range may not exceed {MAX_TIME_SERIES_DAYS} days")
        return end_date


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "list_assets",
        "description": "Return a page of warehouse asset identifiers and compact metadata. Use offset and limit for pagination.",
        "inputSchema": PageArgs.model_json_schema(),
    },
    {
        "name": "get_asset_details",
        "description": "Return the latest known warehouse asset details for one assetId UUID.",
        "inputSchema": AssetDetailsArgs.model_json_schema(),
    },
    {
        "name": "list_data_sources",
        "description": "Return a page of data-source identifiers and compact metadata. Use offset and limit for pagination.",
        "inputSchema": PageArgs.model_json_schema(),
    },
    {
        "name": "get_data_source_details",
        "description": "Return details for one dataSourceId UUID, including supported attributes when available.",
        "inputSchema": DataSourceDetailsArgs.model_json_schema(),
    },
    {
        "name": "get_time_series_data",
        "description": (
            "Return latest-version time-series records for an asset and data source in an inclusive business-date range. "
            f"Ranges are capped at {MAX_TIME_SERIES_DAYS} days and results are capped by limit."
        ),
        "inputSchema": TimeSeriesArgs.model_json_schema(),
    },
]


def execute_mcp_tool(name: str, arguments: dict[str, Any], session) -> dict[str, Any]:
    try:
        if name == "list_assets":
            args = _validate(PageArgs, arguments)
            return _list_assets(args, session)
        if name == "get_asset_details":
            args = _validate(AssetDetailsArgs, arguments)
            return _get_asset_details(args, session)
        if name == "list_data_sources":
            args = _validate(PageArgs, arguments)
            return _list_data_sources(args, session)
        if name == "get_data_source_details":
            args = _validate(DataSourceDetailsArgs, arguments)
            return _get_data_source_details(args, session)
        if name == "get_time_series_data":
            args = _validate(TimeSeriesArgs, arguments)
            return _get_time_series_data(args, session)
    except ValidationError as exc:
        raise MCPToolError(_format_validation_error(exc)) from exc

    raise MCPToolError(f"Unknown tool: {name}", code="not_found")


def _validate(model: type[BaseModel], arguments: dict[str, Any]) -> Any:
    if not isinstance(arguments, dict):
        raise MCPToolError("Tool arguments must be an object")
    return model.model_validate(arguments)


def _page(items: list[Any], args: PageArgs) -> tuple[list[Any], dict[str, Any]]:
    selected = items[args.offset : args.offset + args.limit]
    return selected, {
        "offset": args.offset,
        "limit": args.limit,
        "returned": len(selected),
        "total": len(items),
        "has_more": args.offset + args.limit < len(items),
    }


def _list_assets(args: PageArgs, session) -> dict[str, Any]:
    repo = InstrumentRepository(session)
    instruments = list(repo.find_all())
    selected, page = _page(instruments, args)
    return {
        "page": page,
        "assets": [
            {
                "assetId": str(i.instrument_id),
                "symbol": i.symbol,
                "name": i.name,
                "assetClass": i.instrument_class,
                "region": i.region,
            }
            for i in selected
        ],
    }


def _get_asset_details(args: AssetDetailsArgs, session) -> dict[str, Any]:
    repo = InstrumentRepository(session)
    instrument = repo.find_latest(args.assetId)
    if instrument is None:
        raise MCPToolError("Asset not found", code="not_found")
    return {
        "asset": {
            "assetId": str(instrument.instrument_id),
            "symbol": instrument.symbol,
            "name": instrument.name,
            "assetClass": instrument.instrument_class,
            "region": instrument.region,
            "currency": instrument.currency,
            "exchangeId": str(instrument.exchange_id) if instrument.exchange_id else None,
            "description": instrument.description,
            "createdAt": _serialize(instrument.created_at),
        },
        "semantics": {"version": "latest_known"},
    }


def _list_data_sources(args: PageArgs, session) -> dict[str, Any]:
    repo = DataSourceRepository(session)
    sources = list(repo.find_all())
    selected, page = _page(sources, args)
    return {
        "page": page,
        "dataSources": [
            {
                "dataSourceId": str(s.source_id),
                "name": s.source_name,
                "type": s.source_type,
            }
            for s in selected
        ],
    }


def _get_data_source_details(args: DataSourceDetailsArgs, session) -> dict[str, Any]:
    repo = DataSourceRepository(session)
    source = repo.find_latest(args.dataSourceId)
    if source is None:
        raise MCPToolError("Data source not found", code="not_found")
    return {
        "dataSource": {
            "dataSourceId": str(source.source_id),
            "name": source.source_name,
            "type": source.source_type,
            "baseUrl": source.base_url,
            "apiKeyRequired": source.api_key_required,
            "description": source.description,
            "attributes": sorted(source.attributes) if source.attributes else [],
            "createdAt": _serialize(source.created_at),
        },
        "semantics": {"version": "latest_known"},
    }


def _get_time_series_data(args: TimeSeriesArgs, session) -> dict[str, Any]:
    repo = TimeSeriesRepository(session)
    points = list(repo.find_range(args.assetId, args.dataSourceId, args.startBusinessDate, args.endBusinessDate))
    selected = points[: args.limit]
    return {
        "selection": {
            "assetId": str(args.assetId),
            "dataSourceId": str(args.dataSourceId),
            "startBusinessDate": args.startBusinessDate.isoformat(),
            "endBusinessDate": args.endBusinessDate.isoformat(),
            "includeAttributes": args.includeAttributes,
            "limit": args.limit,
            "returned": len(selected),
            "truncated": len(points) > len(selected),
            "ordering": "record_date_desc_system_date_desc_from_storage",
            "dateInterval": "inclusive",
            "version": "latest_known_per_record_date",
        },
        "records": [_time_series_record(p, args.includeAttributes) for p in selected],
        "provenance": {
            "dataSourceId": str(args.dataSourceId),
            "sourceField": "source_id",
        },
    }


def _time_series_record(point, include_attributes: bool) -> dict[str, Any]:
    record = {
        "assetId": str(point.instrument_id),
        "dataSourceId": str(point.source_id),
        "businessDate": _serialize(point.record_date),
        "systemDate": _serialize(point.system_date),
        "open": _serialize(point.open_price),
        "close": _serialize(point.close_price),
        "high": _serialize(point.high_price),
        "low": _serialize(point.low_price),
        "adjustedClose": _serialize(point.adj_close),
        "volume": point.volume,
        "ingestedAt": _serialize(point.ingested_at),
    }
    if include_attributes:
        record["attributes"] = {
            "exDividend": _serialize(point.ex_dividend),
            "splitRatio": _serialize(point.split_ratio),
            "extraIndicators": point.extra_indicators or {},
        }
    return record


def _serialize(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _format_validation_error(exc: ValidationError) -> str:
    first = exc.errors()[0]
    loc = ".".join(str(part) for part in first.get("loc", []))
    message = first.get("msg", "Invalid value")
    return f"{loc}: {message}" if loc else message
