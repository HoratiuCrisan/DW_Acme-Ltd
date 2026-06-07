from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from app.models.portfolio import Portfolio, PortfolioAsset
from app.db.repositories.portfolio import PortfolioRepository, PortfolioAssetRepository


def _make_portfolio(**kwargs) -> Portfolio:
    defaults = dict(
        owner_id=uuid4(),
        portfolio_id=uuid4(),
        name="Growth Portfolio",
        base_currency="USD",
        created_at=datetime.now(timezone.utc),
    )
    return Portfolio(**(defaults | kwargs))


def _make_asset(**kwargs) -> PortfolioAsset:
    defaults = dict(
        portfolio_id=uuid4(),
        instrument_id=uuid4(),
        added_at=datetime.now(timezone.utc),
        symbol="AAPL",
        instrument_class="stock",
    )
    return PortfolioAsset(**(defaults | kwargs))


def test_portfolio_save_returns_entity(mock_session):
    repo = PortfolioRepository(mock_session)
    portfolio = _make_portfolio()
    result = repo.save(portfolio)
    assert result == portfolio
    mock_session.execute.assert_called_once()


def test_portfolio_find_latest_returns_portfolio(mock_session):
    portfolio = _make_portfolio()
    row = MagicMock()
    row.owner_id = portfolio.owner_id
    row.portfolio_id = portfolio.portfolio_id
    row.name = portfolio.name
    row.base_currency = portfolio.base_currency
    row.description = None
    row.created_at = portfolio.created_at
    row.is_active = True
    mock_session.execute.return_value.one.return_value = row

    repo = PortfolioRepository(mock_session)
    result = repo.find_latest((portfolio.owner_id, portfolio.portfolio_id))

    assert result is not None
    assert result.portfolio_id == portfolio.portfolio_id
    assert result.name == portfolio.name


def test_asset_save_returns_entity(mock_session):
    repo = PortfolioAssetRepository(mock_session)
    asset = _make_asset()
    result = repo.save(asset)
    assert result == asset
    mock_session.execute.assert_called_once()


def test_asset_find_latest_returns_asset(mock_session):
    asset = _make_asset()
    row = MagicMock()
    row.portfolio_id = asset.portfolio_id
    row.instrument_id = asset.instrument_id
    row.added_at = asset.added_at
    row.symbol = asset.symbol
    row.instrument_class = asset.instrument_class
    row.removed_at = None
    row.quantity = None
    row.purchase_price = None
    row.notes = None
    mock_session.execute.return_value.one.return_value = row

    repo = PortfolioAssetRepository(mock_session)
    result = repo.find_latest((asset.portfolio_id, asset.instrument_id))

    assert result is not None
    assert result.instrument_id == asset.instrument_id
    assert result.symbol == asset.symbol


def test_portfolio_delete_all_uses_owner_partition(mock_session):
    repo = PortfolioRepository(mock_session)
    owner_id = uuid4()

    repo.delete_all(owner_id)

    mock_session.execute.assert_called_once()
    assert mock_session.execute.call_args[0][0] is repo._delete_by_owner
    assert mock_session.execute.call_args[0][1] == [owner_id]


def test_asset_delete_all_uses_portfolio_partition(mock_session):
    repo = PortfolioAssetRepository(mock_session)
    portfolio_id = uuid4()

    repo.delete_all(portfolio_id)

    mock_session.execute.assert_called_once()
    assert mock_session.execute.call_args[0][0] is repo._delete_by_portfolio
    assert mock_session.execute.call_args[0][1] == [portfolio_id]
