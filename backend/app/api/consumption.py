from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.db.connection import get_session
from app.db.repositories.data_source import DataSourceRepository
from app.db.repositories.instrument import InstrumentRepository
from app.db.repositories.time_series import TimeSeriesRepository

router = APIRouter()

DEFAULT_LIMIT = 20
MAX_LIMIT = 1000


class Page(BaseModel):
    offset: int
    limit: int
    returned: int
    total: int
    has_more: bool


class AssetPage(BaseModel):
    page: Page
    assets: list[dict[str, Any]]


class DataSourcePage(BaseModel):
    page: Page
    data_sources: list[dict[str, Any]]


class DataRecord(BaseModel):
    businessDate: date
    values: dict[str, Any]
    systemTime: str


class DataResponse(BaseModel):
    data: dict[str, Any]
    attributes: list[str] | None = None
    page: Page


def get_instrument_repo() -> InstrumentRepository:
    return InstrumentRepository(get_session())


def get_source_repo() -> DataSourceRepository:
    return DataSourceRepository(get_session())


def get_ts_repo() -> TimeSeriesRepository:
    return TimeSeriesRepository(get_session())


@router.get("/assets", response_model=AssetPage)
def list_assets(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    repo: InstrumentRepository = Depends(get_instrument_repo),
):
    instruments = _dedupe_assets(list(repo.find_all()))
    selected, page = _page(instruments, offset, limit)
    return {
        "page": page,
        "assets": [
            {
                "assetId": str(item.instrument_id),
                "symbol": item.symbol,
                "name": item.name,
                "assetClass": item.instrument_class,
                "region": item.region,
            }
            for item in selected
        ],
    }


@router.get("/assets/{asset_id}")
def get_asset(
    asset_id: UUID,
    repo: InstrumentRepository = Depends(get_instrument_repo),
):
    asset = repo.find_latest(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {
        "assetId": str(asset.instrument_id),
        "symbol": asset.symbol,
        "name": asset.name,
        "assetClass": asset.instrument_class,
        "region": asset.region,
        "currency": asset.currency,
        "exchangeId": str(asset.exchange_id) if asset.exchange_id else None,
        "description": asset.description,
        "createdAt": asset.created_at.isoformat(),
        "semantics": {"version": "latest_known"},
    }


@router.get("/data-sources", response_model=DataSourcePage)
def list_data_sources(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    repo: DataSourceRepository = Depends(get_source_repo),
):
    sources = _dedupe_data_sources(list(repo.find_all()))
    selected, page = _page(sources, offset, limit)
    return {
        "page": page,
        "data_sources": [
            {
                "dataSourceId": str(item.source_id),
                "name": item.source_name,
                "type": item.source_type,
            }
            for item in selected
        ],
    }


@router.get("/data-sources/{data_source_id}")
def get_data_source(
    data_source_id: UUID,
    repo: DataSourceRepository = Depends(get_source_repo),
):
    source = repo.find_latest(data_source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found")
    return {
        "dataSourceId": str(source.source_id),
        "name": source.source_name,
        "type": source.source_type,
        "baseUrl": source.base_url,
        "apiKeyRequired": source.api_key_required,
        "description": source.description,
        "attributes": sorted(source.attributes) if source.attributes else [],
        "createdAt": source.created_at.isoformat(),
        "semantics": {"version": "latest_known"},
    }


@router.get("/data", response_model=DataResponse)
def get_data(
    assetId: UUID,
    dataSourceId: UUID,
    startBusinessDate: date,
    endBusinessDate: date,
    includeAttributes: bool = False,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    repo: TimeSeriesRepository = Depends(get_ts_repo),
):
    if endBusinessDate <= startBusinessDate:
        raise HTTPException(
            status_code=422,
            detail="endBusinessDate must be after startBusinessDate for [start, end) interval",
        )

    points = repo.find_range(assetId, dataSourceId, startBusinessDate, endBusinessDate)
    latest_points = _latest_by_business_date([
        point for point in points if startBusinessDate <= point.record_date < endBusinessDate
    ])
    selected, page = _page(latest_points, offset, limit)
    records = [_record_to_contract(point, includeAttributes) for point in selected]
    attributes = sorted({key for point in latest_points for key in _record_attributes(point)})

    response: dict[str, Any] = {
        "data": {
            "assetId": str(assetId),
            "dataSourceId": str(dataSourceId),
            "interval": {
                "startBusinessDate": startBusinessDate.isoformat(),
                "endBusinessDate": endBusinessDate.isoformat(),
                "semantics": "[startBusinessDate, endBusinessDate)",
            },
            "ordering": "businessDate descending",
            "version": "latest systemTime per businessDate",
            "records": records,
        },
        "page": page,
    }
    if includeAttributes:
        response["attributes"] = attributes
    return response


def _page(items: list[Any], offset: int, limit: int) -> tuple[list[Any], dict[str, Any]]:
    selected = items[offset : offset + limit]
    return selected, {
        "offset": offset,
        "limit": limit,
        "returned": len(selected),
        "total": len(items),
        "has_more": offset + limit < len(items),
    }


def _dedupe_assets(items: list[Any]) -> list[Any]:
    by_identity = {}
    for item in items:
        key = (item.symbol.upper(), item.instrument_class.lower(), item.region.upper())
        existing = by_identity.get(key)
        if existing is None or item.created_at > existing.created_at:
            by_identity[key] = item
    return sorted(by_identity.values(), key=lambda item: item.symbol)


def _dedupe_data_sources(items: list[Any]) -> list[Any]:
    by_identity = {}
    for item in items:
        key = (
            item.source_name.upper(),
            item.source_type.lower(),
            (item.base_url or "").lower(),
        )
        existing = by_identity.get(key)
        if existing is None or item.created_at > existing.created_at:
            by_identity[key] = item
    return sorted(by_identity.values(), key=lambda item: item.source_name)


def _latest_by_business_date(points) -> list[Any]:
    latest = {}
    for point in points:
        existing = latest.get(point.record_date)
        if existing is None or point.system_date > existing.system_date:
            latest[point.record_date] = point
    return sorted(latest.values(), key=lambda point: point.record_date, reverse=True)


def _record_to_contract(point, include_attributes: bool) -> dict[str, Any]:
    values = {
        "open": _serialize(point.open_price),
        "close": _serialize(point.close_price),
        "high": _serialize(point.high_price),
        "low": _serialize(point.low_price),
        "adjustedClose": _serialize(point.adj_close),
        "volume": point.volume,
    }
    if include_attributes:
        values.update(_record_attributes(point))
    return {
        "businessDate": point.record_date,
        "systemTime": point.system_date.isoformat(),
        "values": values,
    }


def _record_attributes(point) -> dict[str, Any]:
    attributes = {
        "exDividend": _serialize(point.ex_dividend),
        "splitRatio": _serialize(point.split_ratio),
    }
    attributes.update(point.extra_indicators or {})
    return {key: value for key, value in attributes.items() if value is not None}


def _serialize(value):
    if isinstance(value, Decimal):
        return str(value)
    return value
