from __future__ import annotations

import asyncio
import os
import threading
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from elrag.core.auth_be import AuthorizationServiceBE, OAuthSettings, QuotaExceededError
from elrag.core.quota import RedisQuotaStore


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.lock = threading.Lock()

    async def get(self, key: str):
        with self.lock:
            value = self.values.get(key)
            return None if value is None else str(value)

    async def eval(self, _script: str, _key_count: int, key: str, limit: str, _ttl: str):
        with self.lock:
            if key not in self.values:
                self.values[key] = int(limit)
            if self.values[key] <= 0:
                return [0, 0]
            self.values[key] -= 1
            return [1, self.values[key]]

    async def ping(self):
        return True

    async def aclose(self):
        return None


def _settings() -> OAuthSettings:
    return OAuthSettings(
        google_client_id="google-client-id",
        google_client_secret="google-client-secret",
        jwt_secret="jwt-secret-with-at-least-32-bytes",
        redirect_uri=None,
        token_ttl_seconds=3600,
    )


class RedisQuotaTest(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_consumers_cannot_exceed_limit(self) -> None:
        fake_redis = FakeRedis()
        store = RedisQuotaStore(limit=3, client=fake_redis)
        service = AuthorizationServiceBE(settings=_settings())
        service.quota_store = store

        results = await asyncio.gather(
            *(service.consume_quota() for _ in range(8)),
            return_exceptions=True,
        )

        successful = [result for result in results if not isinstance(result, Exception)]
        rejected = [result for result in results if isinstance(result, QuotaExceededError)]
        self.assertEqual(3, len(successful))
        self.assertEqual(5, len(rejected))

    def test_env_quota_limit_is_passed_to_store(self) -> None:
        with patch.dict("os.environ", {"GLOBAL_API_QUOTA_LIMIT": "7"}), patch(
            "elrag.core.auth_be.RedisQuotaStore"
        ) as store:
            AuthorizationServiceBE(settings=_settings())

        store.assert_called_once_with(limit=7)

    def test_key_uses_utc_date(self) -> None:
        store = RedisQuotaStore(limit=3, client=FakeRedis())
        now = datetime(2026, 8, 2, 23, 30, tzinfo=timezone.utc)

        self.assertEqual("elrag:quota:2026-08-02", store._key(now))


@unittest.skipUnless(
    os.getenv("RUN_REDIS_INTEGRATION_TESTS") == "1",
    "set RUN_REDIS_INTEGRATION_TESTS=1 to run against a local Redis instance",
)
class RedisQuotaIntegrationTest(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_consumers_use_real_redis_atomicity(self) -> None:
        store = RedisQuotaStore(
            limit=3,
            key_prefix=f"elrag:test:quota:{uuid4().hex}",
        )
        try:
            await store.ping()
            results = await asyncio.gather(*(store.consume() for _ in range(8)))

            allowed = [snapshot for snapshot in results if snapshot.allowed]
            rejected = [snapshot for snapshot in results if not snapshot.allowed]
            self.assertEqual(3, len(allowed))
            self.assertEqual(5, len(rejected))
            self.assertEqual(0, min(snapshot.remaining for snapshot in allowed))
            self.assertGreater(await store.client.ttl(store._key()), 0)
        finally:
            await store.close()


if __name__ == "__main__":
    unittest.main()
