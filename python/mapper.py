from __future__ import annotations

from .models import MODEL_REGISTRY, UserModel, register_model, sync_all_tables


class UserMapper:
    """Compatibility export for shared table models."""

    UserModel = UserModel


__all__ = [
    "MODEL_REGISTRY",
    "UserMapper",
    "UserModel",
    "register_model",
    "sync_all_tables",
]
