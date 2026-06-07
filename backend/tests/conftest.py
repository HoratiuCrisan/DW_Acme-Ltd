import sys
from unittest.mock import MagicMock
import pytest

for _mod in(
    "cassandra",
    "cassandra.cluster",
    "cassandra.policies",
    "cassandra.auth",
    "cassandra.query"
):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

@pytest.fixture
def mock_session():
    session = MagicMock()
    prepared = MagicMock()
    session.prepare.return_value = prepared
    rows = MagicMock()
    rows.one.return_value = None
    rows.__iter__ = lambda self: iter([])
    session.execute.return_value = rows
    return session