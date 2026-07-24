from __future__ import annotations

import logging
import os
from typing import Any, Callable, TypeVar

from cassandra.cluster import Session
from cassandra.cqlengine import connection, management

T = TypeVar("T")

MODEL_REGISTRY: dict[str, type[Any]] = {}

_initialized = False
logger = logging.getLogger(__name__)


def get_configured_keyspace() -> str:
    return os.getenv("SCYLLA_KEYSPACE", "production")


def register_model(
    cls: type[T] | None = None,
    *,
    name: str | None = None,
) -> type[T] | Callable[[type[T]], type[T]]:
    """Register a model for schema synchronization."""

    def decorator(model_cls: type[T]) -> type[T]:
        model_name = name or model_cls.__name__
        MODEL_REGISTRY[model_name] = model_cls
        return model_cls

    if cls is not None:
        return decorator(cls)

    return decorator


def setup_connection() -> None:
    global _initialized

    if _initialized:
        return

    os.environ.setdefault("CQLENG_ALLOW_SCHEMA_MANAGEMENT", "1")

    contact_point = os.getenv("SCYLLA_CONTACT_POINT", "127.0.0.1")
    keyspace = get_configured_keyspace()

    connection.setup(
        hosts=[contact_point],
        default_keyspace=keyspace,
    )

    _initialized = True


def verify_keyspace_exists(session: Session) -> None:
    keyspace = get_configured_keyspace()
    rows = session.execute(
        "SELECT keyspace_name FROM system_schema.keyspaces WHERE keyspace_name = %s",
        (keyspace,),
    )
    if rows.one() is None:
        raise RuntimeError(
            f"ScyllaDB keyspace '{keyspace}' was not found. "
            "Create the keyspace first or set SCYLLA_KEYSPACE to an existing keyspace."
        )


def get_session() -> Session:
    setup_connection()
    return connection.get_session()


def sync_all_tables() -> None:
    setup_connection()
    session = get_session()
    verify_keyspace_exists(session)

    for model_cls in MODEL_REGISTRY.values():
        try:
            management.sync_table(model_cls)
        except Exception:
            logger.exception(
                "Failed to synchronize table for model %s",
                model_cls.__name__,
            )
            raise
