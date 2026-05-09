from typing import Iterable
from uuid import UUID

from app.db.repositories.base import CassandraRepository, WarehouseRepository
from app.models.owner import Owner, User


class OwnerRepository(CassandraRepository, WarehouseRepository[Owner, UUID]):
    def __init__(self, session):
        super().__init__(session)
        self._insert = session.prepare(
            """
            INSERT INTO owners
              (owner_id, owner_type, name, email, phone, country, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
        )
        self._select_by_id = session.prepare(
            "SELECT * FROM owners WHERE owner_id = ?"
        )
        self._select_all = session.prepare("SELECT * FROM owners")
        self._delete_by_id = session.prepare(
            "DELETE FROM owners WHERE owner_id = ?"
        )

    def save(self, entity: Owner) -> Owner:
        self._execute(self._insert, [
            entity.owner_id, entity.owner_type, entity.name,
            entity.email, entity.phone, entity.country, entity.created_at,
        ])
        return entity

    def delete(self, key: UUID) -> None:
        self._execute(self._delete_by_id, [key])

    def delete_all(self, partition_key: UUID) -> None:
        self._execute(self._delete_by_id, [partition_key])

    def find_latest(self, partition_key: UUID) -> Owner | None:
        row = self._fetch_one(self._select_by_id, [partition_key])
        return self._row_to_model(row) if row else None

    def find_all(self, partition_key=None) -> Iterable[Owner]:
        rows = self._fetch_all(self._select_all)
        return [self._row_to_model(r) for r in rows]

    @staticmethod
    def _row_to_model(row) -> Owner:
        return Owner(
            owner_id=row.owner_id,
            owner_type=row.owner_type,
            name=row.name,
            email=getattr(row, "email", None),
            phone=getattr(row, "phone", None),
            country=getattr(row, "country", None),
            created_at=row.created_at,
        )


class UserRepository(CassandraRepository, WarehouseRepository[User, UUID]):
    def __init__(self, session):
        super().__init__(session)
        self._insert = session.prepare(
            """
            INSERT INTO users
              (user_id, owner_id, username, role, registered_at, last_login_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """
        )
        self._select_by_id = session.prepare(
            "SELECT * FROM users WHERE user_id = ?"
        )
        self._select_all = session.prepare("SELECT * FROM users")
        self._delete_by_id = session.prepare(
            "DELETE FROM users WHERE user_id = ?"
        )

    def save(self, entity: User) -> User:
        self._execute(self._insert, [
            entity.user_id, entity.owner_id, entity.username,
            entity.role, entity.registered_at, entity.last_login_at,
        ])
        return entity

    def delete(self, key: UUID) -> None:
        self._execute(self._delete_by_id, [key])

    def delete_all(self, partition_key: UUID) -> None:
        self._execute(self._delete_by_id, [partition_key])

    def find_latest(self, partition_key: UUID) -> User | None:
        row = self._fetch_one(self._select_by_id, [partition_key])
        return self._row_to_model(row) if row else None

    def find_all(self, partition_key=None) -> Iterable[User]:
        rows = self._fetch_all(self._select_all)
        return [self._row_to_model(r) for r in rows]

    @staticmethod
    def _row_to_model(row) -> User:
        return User(
            user_id=row.user_id,
            owner_id=row.owner_id,
            username=row.username,
            role=row.role,
            registered_at=row.registered_at,
            last_login_at=getattr(row, "last_login_at", None),
        )
