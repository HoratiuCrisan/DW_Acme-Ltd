import threading
from typing import Any

from app.config import settings
from app.db.demo_session import get_demo_session

_cluster = None
_session: Any | None = None
_lock = threading.Lock()


def _load_cassandra_driver():
    """
    Python 3.12+ removed asyncore, which cassandra-driver uses as its fallback
    reactor. Import a supported reactor first and pass it explicitly to Cluster.
    """
    reactor_errors = []

    try:
        # cassandra.cluster still performs default reactor discovery at import
        # time. Patch sockets first so that import succeeds on Python 3.12+,
        # then pass the asyncio reactor explicitly for actual connections.
        from gevent import monkey

        monkey.patch_socket()
        from cassandra.cluster import Cluster
        from cassandra.io.asyncioreactor import AsyncioConnection
        from cassandra.policies import DCAwareRoundRobinPolicy

        return Cluster, DCAwareRoundRobinPolicy, AsyncioConnection
    except Exception as exc:
        reactor_errors.append(f"asyncio: {exc}")

    try:
        from gevent import monkey

        monkey.patch_socket()
        from cassandra.io.geventreactor import GeventConnection
        from cassandra.cluster import Cluster
        from cassandra.policies import DCAwareRoundRobinPolicy

        return Cluster, DCAwareRoundRobinPolicy, GeventConnection
    except Exception as exc:
        reactor_errors.append(f"gevent: {exc}")

    try:
        import eventlet

        eventlet.monkey_patch()
        from cassandra.cluster import Cluster
        from cassandra.io.eventletreactor import EventletConnection
        from cassandra.policies import DCAwareRoundRobinPolicy

        return Cluster, DCAwareRoundRobinPolicy, EventletConnection
    except Exception as exc:
        reactor_errors.append(f"eventlet: {exc}")

    raise RuntimeError(
        "Cassandra driver could not be loaded with a Python 3.12+ compatible "
        "reactor. Install eventlet or gevent, then restart the API. Details: "
        + " | ".join(reactor_errors)
    )


def get_session() -> Any:
    global _cluster, _session
    if _session is None:
        # Double-checked locking avoids creating multiple sessions under load
        with _lock:
            if _session is None:
                try:
                    Cluster, DCAwareRoundRobinPolicy, connection_class = _load_cassandra_driver()
                except Exception as exc:
                    if settings.demo_mode:
                        _session = get_demo_session()
                        return _session
                    raise RuntimeError(
                        "Cassandra driver could not be loaded. On Python 3.13, install "
                        "eventlet or gevent so the driver does not use removed asyncore."
                    ) from exc

                # Create the cluster client once and reuse the shared session.
                _cluster = Cluster(
                    settings.cassandra_hosts_list,
                    port = settings.cassandra_port,
                    load_balancing_policy = DCAwareRoundRobinPolicy(
                        local_dc=settings.cassandra_dc
                    ),
                    connection_class=connection_class,
                )
                _session = _cluster.connect()
                _session.set_keyspace(settings.cassandra_keyspace)
    return _session

def close() -> None:
    global _cluster, _session
    if _cluster is not None:
        # Shutdown the cluster before dropping references so the reconnection starts cleanly
        _cluster.shutdown()
    _cluster = None
    _session = None
