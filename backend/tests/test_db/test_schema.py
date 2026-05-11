from app.db.schema import KEYSPACE_CQL, _replication_cql


def test_simple_strategy_replication_cql_uses_factor(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "cassandra_replication_strategy", "SimpleStrategy")
    monkeypatch.setattr(config.settings, "cassandra_replication_factor", 2)

    assert _replication_cql() == "{'class': 'SimpleStrategy', 'replication_factor': 2}"


def test_network_topology_replication_cql_uses_datacenters(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "cassandra_replication_strategy", "NetworkTopologyStrategy")
    monkeypatch.setattr(config.settings, "cassandra_replication_factor", 3)
    monkeypatch.setattr(config.settings, "cassandra_replication_dcs", "dc1, dc2")

    assert _replication_cql() == "{'class': 'NetworkTopologyStrategy', 'dc1': 3, 'dc2': 3}"


def test_keyspace_template_renders_replication(monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "cassandra_replication_strategy", "SimpleStrategy")
    monkeypatch.setattr(config.settings, "cassandra_replication_factor", 1)

    rendered = KEYSPACE_CQL.format(keyspace="financial_dw", replication=_replication_cql())
    assert "CREATE KEYSPACE IF NOT EXISTS financial_dw" in rendered
    assert "'replication_factor': 1" in rendered
