from __future__ import annotations

import os
from typing import Any, Callable, TypeVar

from cassandra.cqlengine import connection, management

T = TypeVar("T")

MODEL_REGISTRY: dict[str, type[Any]] = {}


def register_model(cls: type[T] | None = None, *, name: str | None = None) -> type[T] | Callable[[type[T]], type[T]]:
    """Register a dataclass model for reuse across the Python/Rust boundary."""

    def decorator(model_cls: type[T]) -> type[T]:
        model_name = name or model_cls.__name__
        MODEL_REGISTRY[model_name] = model_cls
        return model_cls

    if cls is not None:
        return decorator(cls)

    return decorator


class TableModelMeta:
    table_name: str
    model_name: str


def setup_connection() -> None:
    os.environ.setdefault("CQLENG_ALLOW_SCHEMA_MANAGEMENT", "1")
    contact_point = os.getenv("SCYLLA_CONTACT_POINT", "127.0.0.1")
    keyspace = os.getenv("SCYLLA_KEYSPACE", "demo")
    connection.setup([contact_point], default_keyspace=keyspace)


def sync_all_tables() -> None:
    setup_connection()

    for model_cls in MODEL_REGISTRY.values():
        management.sync_table(model_cls)
