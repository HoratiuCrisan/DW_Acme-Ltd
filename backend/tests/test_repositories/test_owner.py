from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.models.owner import Owner, User
from app.db.repositories.owner import OwnerRepository, UserRepository


def _make_owner(**kwargs) -> Owner:
    defaults = dict(
        owner_id=uuid4(),
        owner_type="individual",
        name="Alice Smith",
        email="alice@example.com",
        created_at=datetime.now(timezone.utc),
    )
    return Owner(**(defaults | kwargs))


def _make_user(**kwargs) -> User:
    defaults = dict(
        user_id=uuid4(),
        owner_id=uuid4(),
        username="alice",
        role="analyst",
        registered_at=datetime.now(timezone.utc),
    )
    return User(**(defaults | kwargs))


def test_owner_save_returns_entity(mock_session):
    repo = OwnerRepository(mock_session)
    owner = _make_owner()
    result = repo.save(owner)
    assert result == owner
    mock_session.execute.assert_called_once()


def test_owner_find_latest_returns_owner(mock_session):
    owner = _make_owner()
    row = MagicMock()
    row.owner_id = owner.owner_id
    row.owner_type = owner.owner_type
    row.name = owner.name
    row.email = owner.email
    row.phone = None
    row.country = None
    row.created_at = owner.created_at
    mock_session.execute.return_value.one.return_value = row

    repo = OwnerRepository(mock_session)
    result = repo.find_latest(owner.owner_id)

    assert result is not None
    assert result.owner_id == owner.owner_id
    assert result.name == owner.name


def test_user_save_returns_entity(mock_session):
    repo = UserRepository(mock_session)
    user = _make_user()
    result = repo.save(user)
    assert result == user
    mock_session.execute.assert_called_once()


def test_user_find_latest_returns_user(mock_session):
    user = _make_user()
    row = MagicMock()
    row.user_id = user.user_id
    row.owner_id = user.owner_id
    row.username = user.username
    row.role = user.role
    row.registered_at = user.registered_at
    row.last_login_at = None
    mock_session.execute.return_value.one.return_value = row

    repo = UserRepository(mock_session)
    result = repo.find_latest(user.user_id)

    assert result is not None
    assert result.user_id == user.user_id
    assert result.username == user.username


def test_owner_delete_all_uses_owner_partition(mock_session):
    repo = OwnerRepository(mock_session)
    owner_id = uuid4()

    repo.delete_all(owner_id)

    mock_session.execute.assert_called_once()
    assert mock_session.execute.call_args[0][0] is repo._delete_by_id
    assert mock_session.execute.call_args[0][1] == [owner_id]


def test_user_delete_all_uses_user_partition(mock_session):
    repo = UserRepository(mock_session)
    user_id = uuid4()

    repo.delete_all(user_id)

    mock_session.execute.assert_called_once()
    assert mock_session.execute.call_args[0][0] is repo._delete_by_id
    assert mock_session.execute.call_args[0][1] == [user_id]
