import logging
import re
from cassandra.cluster import Session

from app.config import settings

_log = logging.getLogger(__name__)

def _replication_cql() -> str:
    strategy = settings.cassandra_replication_strategy.strip()
    if strategy == "NetworkTopologyStrategy":
        dcs = [dc.strip() for dc in settings.cassandra_replication_dcs.split(",") if dc.strip()]
        if not dcs:
            dcs = [settings.cassandra_dc]
        replication = {"class": strategy, **{dc: settings.cassandra_replication_factor for dc in dcs}}
    else:
        replication = {"class": "SimpleStrategy", "replication_factor": settings.cassandra_replication_factor}
    return str(replication)


KEYSPACE_CQL = """
CREATE KEYSPACE IF NOT EXISTS {keyspace}
WITH replication = {replication};
"""

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS exchanges (
        exchange_id UUID PRIMARY KEY,
        exchange_name TEXT,
        country TEXT,
        timezone TEXT,
        currency TEXT,
        open_time TEXT,
        close_time TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS financial_instruments (
        instrument_id UUID PRIMARY KEY,
        symbol TEXT,
        instrument_class TEXT,
        name TEXT,
        region TEXT,
        currency TEXT,
        exchange_id UUID,
        description TEXT,
        created_at TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS instruments_by_class (
        instrument_class TEXT,
        symbol TEXT,
        instrument_id UUID,
        name TEXT,
        region TEXT,
        exchange_id UUID,
        PRIMARY KEY (instrument_class, symbol)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS instrument_versions (
        instrument_id UUID,
        valid_from TIMESTAMP,
        version_id UUID,
        change_type TEXT,
        is_delete_marker BOOLEAN,
        snapshot TEXT,
        valid_to TIMESTAMP,
        changed_by TEXT,
        PRIMARY KEY (instrument_id, valid_from)
    ) WITH CLUSTERING ORDER BY (valid_from DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS data_sources (
        source_id UUID PRIMARY KEY,
        source_name TEXT,
        source_type TEXT,
        base_url TEXT,
        api_key_required BOOLEAN,
        description TEXT,
        attributes SET<TEXT>,
        created_at TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS time_series_by_instrument (
        instrument_id UUID,
        source_id UUID,
        record_year INT,
        record_date DATE,
        system_date TIMESTAMP,
        open_price DECIMAL,
        close_price DECIMAL,
        high_price DECIMAL,
        low_price DECIMAL,
        adj_close DECIMAL,
        volume BIGINT,
        ex_dividend DECIMAL,
        split_ratio DECIMAL,
        extra_indicators MAP<TEXT, TEXT>,
        ingested_at TIMESTAMP,
        PRIMARY KEY ((instrument_id, source_id, record_year), record_date, system_date)
    ) WITH CLUSTERING ORDER BY (record_date DESC, system_date DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS ingest_jobs (
        job_id UUID PRIMARY KEY,
        symbol TEXT,
        datatable_code TEXT,
        status TEXT,
        queued_at TIMESTAMP,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        record_count INT,
        error_message TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ingest_log (
        source_id UUID,
        log_year INT,
        ingested_at TIMESTAMP,
        log_id UUID,
        instrument_id UUID,
        status TEXT,
        record_count INT,
        error_message TEXT,
        duration_ms BIGINT,
        PRIMARY KEY ((source_id, log_year), ingested_at)
    ) WITH CLUSTERING ORDER BY (ingested_at DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS owners (
        owner_id UUID PRIMARY KEY,
        owner_type TEXT,
        name TEXT,
        email TEXT,
        phone TEXT,
        country TEXT,
        created_at TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id UUID PRIMARY KEY,
        owner_id UUID,
        username TEXT,
        role TEXT,
        registered_at TIMESTAMP,
        last_login_at TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS portfolios_by_owner (
        owner_id UUID,
        portfolio_id UUID,
        name TEXT,
        base_currency TEXT,
        description TEXT,
        created_at TIMESTAMP,
        is_active BOOLEAN,
        PRIMARY KEY (owner_id, portfolio_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS portfolio_assets (
        portfolio_id UUID,
        instrument_id UUID,
        added_at TIMESTAMP,
        symbol TEXT,
        instrument_class TEXT,
        removed_at TIMESTAMP,
        quantity DECIMAL,
        purchase_price DECIMAL,
        notes TEXT,
        PRIMARY KEY (portfolio_id, instrument_id, added_at)
    ) WITH CLUSTERING ORDER BY (instrument_id ASC, added_at DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS analytics_results (
        instrument_id UUID,
        source_id UUID,
        computed_at TIMESTAMP,
        result_id UUID,
        metric_type TEXT,
        metric_value DECIMAL,
        window_days INT,
        notes TEXT,
        PRIMARY KEY ((instrument_id, source_id), computed_at)
    ) WITH CLUSTERING ORDER BY (computed_at DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS risk_signals (
        instrument_id UUID,
        generated_at TIMESTAMP,
        signal_id UUID,
        signal_type TEXT,
        severity TEXT,
        value DECIMAL,
        explanation TEXT,
        result_id UUID,
        PRIMARY KEY (instrument_id, generated_at)
    ) WITH CLUSTERING ORDER BY (generated_at DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS recommendations (
        user_id UUID,
        created_at TIMESTAMP,
        recommendation_id UUID,
        portfolio_id UUID,
        signal_id UUID,
        action TEXT,
        rationale TEXT,
        expires_at TIMESTAMP,
        was_acted_on BOOLEAN,
        PRIMARY KEY (user_id, created_at)
    ) WITH CLUSTERING ORDER BY (created_at DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS llm_query_log (
        user_id UUID,
        session_id UUID,
        asked_at TIMESTAMP,
        query_id UUID,
        user_prompt TEXT,
        tools_invoked TEXT,
        llm_response TEXT,
        duration_ms BIGINT,
        PRIMARY KEY ((user_id, session_id), asked_at)
    ) WITH CLUSTERING ORDER BY (asked_at DESC)
    """,
]


def apply_schema(session: Session, keyspace: str) -> None:
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]{0,47}", keyspace):
        raise ValueError(f"Invalid keyspace name: {keyspace!r}")
    session.execute(KEYSPACE_CQL.format(keyspace=keyspace, replication=_replication_cql()))
    session.set_keyspace(keyspace)
    for i, stmt in enumerate(SCHEMA_STATEMENTS):
        try:
            session.execute(stmt)
        except Exception as exc:
            raise RuntimeError(
                f"Schema statement {i} failed: {stmt.strip()[:80]!r}"
            ) from exc
    _log.info("Schema applied to keyspace %r (%d tables)", keyspace, len(SCHEMA_STATEMENTS))
