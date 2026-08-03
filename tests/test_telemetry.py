from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.responses import JSONResponse

from elrag.core.auth_be import AuthenticatedUser
from elrag.core.quota import QuotaStoreUnavailableError


class FakeRequest:
    def __init__(self, path: str, headers: dict[str, str] | None = None) -> None:
        self.method = "GET"
        self.url = SimpleNamespace(path=path)
        self.headers = headers or {}
        self.state = SimpleNamespace()
        self.scope = {}


class MainMiddlewareTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        from elrag import main as main_module

        self.main_module = main_module

    async def test_request_without_bearer_is_recorded_as_401(self) -> None:
        class FakeAuthService:
            async def build_quota_headers(self):
                return {"X-Global-Quota-Limit": "1000", "X-Global-Quota-Remaining": "1000"}

        with patch.object(self.main_module, "auth_service", FakeAuthService()), patch.object(
            self.main_module, "record_request"
        ) as record:
            response = await self.main_module.enforce_client_authorization(
                FakeRequest("/auth/me"),
                self._success_handler,
            )

        self.assertEqual(401, response.status_code)
        record.assert_called_once()
        self.assertEqual(401, record.call_args.kwargs["status_code"])
        self.assertFalse(record.call_args.kwargs["authenticated"])

    async def test_successful_request_consumes_quota_and_records_once(self) -> None:
        user = AuthenticatedUser(
            google_sub="google-sub-1",
            email="user@example.com",
            name="User Example",
            picture=None,
            role="user",
        )

        class FakeAuthService:
            def authenticate_bearer_token(self, raw_token: str):
                return user

            async def consume_quota(self):
                return 1000, 999

        with patch.object(self.main_module, "auth_service", FakeAuthService()), patch.object(
            self.main_module, "record_request"
        ) as record:
            response = await self.main_module.enforce_client_authorization(
                FakeRequest("/auth/me", {"authorization": "Bearer valid-token"}),
                self._success_handler,
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("999", response.headers["X-Global-Quota-Remaining"])
        record.assert_called_once()
        self.assertEqual(200, record.call_args.kwargs["status_code"])
        self.assertTrue(record.call_args.kwargs["authenticated"])
        self.assertTrue(record.call_args.kwargs["quota_consumed"])

    async def test_downstream_exception_is_recorded_as_500(self) -> None:
        user = AuthenticatedUser(
            google_sub="google-sub-1",
            email="user@example.com",
            name="User Example",
            picture=None,
            role="user",
        )

        class FakeAuthService:
            def authenticate_bearer_token(self, raw_token: str):
                return user

            async def consume_quota(self):
                return 1000, 998

        async def failing_handler(_: FakeRequest) -> JSONResponse:
            raise RuntimeError("handler failed")

        with patch.object(self.main_module, "auth_service", FakeAuthService()), patch.object(
            self.main_module, "record_request"
        ) as record:
            with self.assertRaisesRegex(RuntimeError, "handler failed"):
                await self.main_module.enforce_client_authorization(
                    FakeRequest("/auth/me", {"authorization": "Bearer valid-token"}),
                    failing_handler,
                )

        record.assert_called_once()
        self.assertEqual(500, record.call_args.kwargs["status_code"])
        self.assertTrue(record.call_args.kwargs["quota_consumed"])

    async def test_quota_store_unavailable_returns_503_and_is_recorded(self) -> None:
        user = AuthenticatedUser(
            google_sub="google-sub-1",
            email="user@example.com",
            name="User Example",
            picture=None,
            role="user",
        )

        class FakeAuthService:
            def authenticate_bearer_token(self, raw_token: str):
                return user

            async def consume_quota(self):
                raise QuotaStoreUnavailableError("quota store is unavailable")

        with patch.object(self.main_module, "auth_service", FakeAuthService()), patch.object(
            self.main_module, "record_request"
        ) as record:
            response = await self.main_module.enforce_client_authorization(
                FakeRequest("/auth/me", {"authorization": "Bearer valid-token"}),
                self._success_handler,
            )

        self.assertEqual(503, response.status_code)
        self.assertEqual(503, record.call_args.kwargs["status_code"])
        self.assertTrue(record.call_args.kwargs["authenticated"])
        self.assertFalse(record.call_args.kwargs["quota_consumed"])

    async def test_documentation_is_not_business_usage(self) -> None:
        with patch.object(self.main_module, "record_request") as record:
            response = await self.main_module.enforce_client_authorization(
                FakeRequest("/docs"),
                self._success_handler,
            )

        self.assertEqual(200, response.status_code)
        record.assert_not_called()

    async def test_lifespan_closes_resources_when_startup_fails(self) -> None:
        fake_auth_service = SimpleNamespace(
            check_quota_store=AsyncMock(side_effect=RuntimeError("redis unavailable")),
            close=AsyncMock(),
        )

        with patch.object(
            self.main_module, "auth_service", fake_auth_service
        ), patch.object(
            self.main_module, "validate_observability"
        ), patch.object(
            self.main_module, "sync_all_tables"
        ) as sync_all_tables, patch.object(
            self.main_module, "shutdown_observability"
        ) as shutdown:
            with self.assertRaisesRegex(RuntimeError, "redis unavailable"):
                async with self.main_module.lifespan(self.main_module.app):
                    pass

        fake_auth_service.close.assert_awaited_once()
        sync_all_tables.assert_not_called()
        shutdown.assert_called_once()

    async def test_legacy_telemetry_stream_route_is_not_exposed(self) -> None:
        routes = self.main_module.app.openapi()["paths"]

        self.assertNotIn("/telemetry/stream", routes)
        self.assertIn("/agent/run", routes)

    async def _success_handler(self, _: FakeRequest) -> JSONResponse:
        return JSONResponse(status_code=200, content={"ok": True})


if __name__ == "__main__":
    unittest.main()
