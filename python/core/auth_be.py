from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import NamedTuple
from uuid import UUID

from python.models.model import Client


class AuthorizationResult(NamedTuple):
    allowed: bool
    status_code: int
    message: str
    client_id: str | None
    quota_limit: int
    quota_remaining: int


class AuthorizationServiceBE:
    _lock = Lock()
    _quota_limit = 1000
    _quota_remaining = 1000
    _quota_reset_date = datetime.now(timezone.utc).date()

    def __init__(self) -> None:
        self.quota_limit = self._read_quota_limit()

    @staticmethod
    def _read_quota_limit() -> int:
        import os

        raw_value = os.getenv("GLOBAL_API_QUOTA_LIMIT", "1000")
        try:
            limit = int(raw_value)
        except ValueError:
            return 1000
        return max(limit, 1)

    @classmethod
    def _reset_if_needed(cls) -> None:
        today = datetime.now(timezone.utc).date()
        if cls._quota_reset_date != today:
            cls._quota_reset_date = today
            cls._quota_limit = cls().quota_limit
            cls._quota_remaining = cls._quota_limit

    @staticmethod
    def _normalize_client_id(client_id: str) -> UUID:
        return UUID(client_id)

    @staticmethod
    def _get_client(client_id: UUID) -> Client | None:
        return Client.objects(id=client_id).first()

    def validate_client(self, client_id: str) -> Client | None:
        client_uuid = self._normalize_client_id(client_id)
        return self._get_client(client_uuid)

    @classmethod
    def quota_snapshot(cls) -> tuple[int, int]:
        with cls._lock:
            cls._reset_if_needed()
            return cls._quota_limit, cls._quota_remaining

    def authorize_request(self, client_id: str) -> AuthorizationResult:
        try:
            client_uuid = self._normalize_client_id(client_id)
        except ValueError:
            quota_limit, quota_remaining = self.quota_snapshot()
            return AuthorizationResult(
                allowed=False,
                status_code=400,
                message="client_id must be a valid UUID",
                client_id=None,
                quota_limit=quota_limit,
                quota_remaining=quota_remaining,
            )

        client = self._get_client(client_uuid)
        if client is None:
            quota_limit, quota_remaining = self.quota_snapshot()
            return AuthorizationResult(
                allowed=False,
                status_code=404,
                message="client not found",
                client_id=str(client_uuid),
                quota_limit=quota_limit,
                quota_remaining=quota_remaining,
            )

        with self._lock:
            self._reset_if_needed()
            quota_limit = self._quota_limit
            if self._quota_remaining <= 0:
                return AuthorizationResult(
                    allowed=False,
                    status_code=429,
                    message="global quota exhausted",
                    client_id=str(client_uuid),
                    quota_limit=quota_limit,
                    quota_remaining=0,
                )
            self._quota_remaining -= 1
            quota_remaining = self._quota_remaining

        return AuthorizationResult(
            allowed=True,
            status_code=200,
            message="authorized",
            client_id=str(client_uuid),
            quota_limit=quota_limit,
            quota_remaining=quota_remaining,
        )

    def build_quota_headers(self) -> dict[str, str]:
        quota_limit, quota_remaining = self.quota_snapshot()
        return {
            "X-Global-Quota-Limit": str(quota_limit),
            "X-Global-Quota-Remaining": str(quota_remaining),
        }
