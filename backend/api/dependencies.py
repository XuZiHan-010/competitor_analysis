from services.runs.manager import RunManager
from services.storage import store
from services.streaming.bridge import InMemoryStreamBridge, RedisStreamBridge, StreamBridge
from settings import get_settings


def _build_stream_bridge() -> StreamBridge:
    settings = get_settings()
    if settings.redis_dsn:
        try:
            return RedisStreamBridge(
                settings.redis_dsn,
                maxlen=settings.redis_event_stream_maxlen,
                ttl_seconds=settings.redis_event_stream_ttl_seconds,
            )
        except (ImportError, ValueError):
            return InMemoryStreamBridge()
    return InMemoryStreamBridge()


stream_bridge = _build_stream_bridge()


def _build_run_manager() -> RunManager:
    settings = get_settings()
    if settings.database_url:
        try:
            from db.persistence import SqlRunPersistence
            from db.session import create_engine, create_sessionmaker

            engine = create_engine()
            persistence = SqlRunPersistence(create_sessionmaker(engine))
            return RunManager(store=store, bridge=stream_bridge, persistence=persistence)
        except ImportError:
            return RunManager(store=store, bridge=stream_bridge)
    return RunManager(store=store, bridge=stream_bridge)


run_manager = _build_run_manager()
