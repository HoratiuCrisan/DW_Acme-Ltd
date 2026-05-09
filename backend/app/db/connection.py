import threading
from cassandra.cluster import Cluster, Session
from cassandra.policies import DCAwareRoundRobinPolicy
from app.config import settings

_cluster = None
_session: Session | None = None
_lock = threading.Lock()

def get_session() -> Session:
    global _cluster, _session
    if _session is None:
        # Double-checked locking avoids creating multiple sessions under load
        with _lock:
            if _session is None:
                # Create teh cluster client once and reuse the shared session
                _cluster = Cluster(
                    settings.cassandra_hosts_list,
                    port = settings.cassandra_port,
                    load_balancing_policy = DCAwareRoundRobinPolicy(
                        local_dc=settings.cassandra_dc
                    ),
                    _session = _cluster.connect()
                )
    return _session

def close() -> None:
    global _cluster, _session
    if _cluster is not None:
        # Shutdown the cluster before dropping references so the reconnection starts cleanly
        _cluster.shutdown()
    _cluster = None
    _session = None