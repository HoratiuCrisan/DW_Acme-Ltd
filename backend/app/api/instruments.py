from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID

from app.db.connection import get_session
from app.db.repositories.instrument import InstrumentRepository
from app.models.instrument import FinancialInstrument, InstrumentSummary

router = APIRouter()


def get_instrument_repo() -> InstrumentRepository:
    return InstrumentRepository(get_session())


@router.get("", response_model=list[InstrumentSummary])
def list_instruments(
    page_size: int = Query(default=1000, ge=1, le=10000),
    repo: InstrumentRepository = Depends(get_instrument_repo),
):
    """Q1: Return limited info about all financial assets."""
    instruments = list(repo.find_all())[:page_size]
    return [
        InstrumentSummary(
            instrument_id=i.instrument_id,
            symbol=i.symbol,
            instrument_class=i.instrument_class,
            name=i.name,
            region=i.region,
        )
        for i in instruments
    ]


@router.get("/{instrument_id}", response_model=FinancialInstrument)
def get_instrument(
    instrument_id: UUID,
    repo: InstrumentRepository = Depends(get_instrument_repo),
):
    """Q2: Return all details of an asset by identifier."""
    instrument = repo.find_latest(instrument_id)
    if instrument is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return instrument
