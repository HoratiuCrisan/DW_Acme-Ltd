from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.db.repositories.portfolio import PortfolioAssetRepository
from app.models.portfolio import PortfolioAsset


def _make_asset(**kwargs) -> PortfolioAsset:
    now = datetime.now(timezone.utc)
    defaults = dict(
        portfolio_id=uuid4(),
        instrument_id=uuid4(),
        added_at=now,
        symbol="AAPL",
        instrument_class="Equity",
        removed_at=None,
        quantity=Decimal("10"),
        purchase_price=Decimal("100.00"),
        notes=None,
    )
    return PortfolioAsset(**(defaults | kwargs))


def test_delete_all_uses_partition_delete(mock_session):
    repo = PortfolioAssetRepository(mock_session)
    portfolio_id = uuid4()

    repo.delete_all(portfolio_id)

    assert mock_session.execute.call_count == 1
    call = mock_session.execute.call_args
    assert call[0][0] is repo._delete_by_portfolio
    assert call[0][1] == [portfolio_id]
