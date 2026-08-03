from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from redis.exceptions import RedisError
from redis.asyncio import Redis


class QuotaStoreUnavailableError(RuntimeError):
    """Raised when the shared quota store cannot be reached."""


class QuotaStoreConfigurationError(RuntimeError):
    """Raised when quota store configuration is invalid."""


@dataclass(frozen=True)
class QuotaSnapshot:
    limit: int
    remaining: int
    allowed: bool = True


_CONSUME_QUOTA_SCRIPT = """
local value = redis.call('GET', KEYS[1])
if not value then
    redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2], 'NX')
    value = redis.call('GET', KEYS[1])
end

local remaining = tonumber(value)
if remaining <= 0 then
    return {0, 0}
end

remaining = redis.call('DECR', KEYS[1])
return {1, remaining}
"""


class RedisQuotaStore:
    """Shared UTC-day quota backed by an atomic Redis Lua operation."""

    def __init__(
        self,
        *,
        limit: int,
        redis_url: str | None = None,
        key_prefix: str | None = None,
        client: Redis | None = None,
    ) -> None:
        if limit < 1:
            raise QuotaStoreConfigurationError("quota limit must be positive")

        self.limit = limit
        self.key_prefix = key_prefix or os.getenv("REDIS_KEY_PREFIX", "elrag:quota")
        self._client = client or Redis.from_url(
            redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
            health_check_interval=30,
        )

    @property
    def client(self) -> Redis:
        return self._client

    def _key(self, now: datetime | None = None) -> str:
        current = now or datetime.now(timezone.utc)
        date_value = current.astimezone(timezone.utc).date().isoformat()
        return f"{self.key_prefix}:{date_value}"

    def _ttl_seconds(self, now: datetime | None = None) -> int:
        current = now or datetime.now(timezone.utc)
        next_day = current.astimezone(timezone.utc).date() + timedelta(days=2)
        expiry = datetime.combine(next_day, datetime.min.time(), tzinfo=timezone.utc)
        return max(int((expiry - current).total_seconds()), 60)

    async def ping(self) -> bool:
        try:
            return bool(await self._client.ping())
        except RedisError as exc:
            raise QuotaStoreUnavailableError("quota store is unavailable") from exc

    async def snapshot(self, now: datetime | None = None) -> QuotaSnapshot:
        try:
            value = await self._client.get(self._key(now))
        except RedisError as exc:
            raise QuotaStoreUnavailableError("quota store is unavailable") from exc

        remaining = self.limit if value is None else max(int(value), 0)
        return QuotaSnapshot(
            limit=self.limit,
            remaining=remaining,
            allowed=remaining > 0,
        )

    async def consume(self, now: datetime | None = None) -> QuotaSnapshot:
        current = now or datetime.now(timezone.utc)
        try:
            allowed, remaining = await self._client.eval(
                _CONSUME_QUOTA_SCRIPT,
                1,
                self._key(current),
                str(self.limit),
                str(self._ttl_seconds(current)),
            )
        except RedisError as exc:
            raise QuotaStoreUnavailableError("quota store is unavailable") from exc

        return QuotaSnapshot(
            limit=self.limit,
            remaining=max(int(remaining), 0),
            allowed=bool(allowed),
        )

    async def close(self) -> None:
        await self._client.aclose()
