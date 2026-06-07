from abc import ABC, abstractmethod
from typing import Generic, Iterable, Optional, TypeVar

E = TypeVar("E")
K = TypeVar("K")

class WarehouseRepository(ABC, Generic[E, K]):
    @abstractmethod
    def save(self, entity: E) -> E: ...

    @abstractmethod
    def delete(self, key: K) -> None: ...

    @abstractmethod
    def delete_all(self, partition_key: K) -> None: ...

    @abstractmethod
    def find_latest(self, partition_key: K) -> Optional[E]: ...

    @abstractmethod
    def find_all(self, partition_key: K) -> Iterable[E]: ...

class CassandraRepository:
    """Cassandra helper for repositories
    
    Keeps the session interaction in one place while leaving query shape 
    and row-to-model mapping to the concrete repo.
    """

    def __init__(self, session):
        self._session = session

    def _execute(self, statement, params=None):
        if params is None:
            return self._session.execute(statement)
        return self._session.execute(statement, params)
    
    def _fetch_one(self, statement, params=None):
        return self._execute(statement, params).one()
    
    def _fetch_all(self, statement, params=None):
        return self._execute(statement, params)
