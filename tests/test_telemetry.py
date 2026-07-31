from __future__ import annotations

import json
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from elrag.api.telemetry import stream_usage
from elrag.core.auth_be import AuthenticatedUser
from elrag.lib.telemetry import usage_telemetry


class FakeRequest:
    def __init__(self, path: str, headers: dict[str, str] | None = None) -> None:
        self.method = "GET"
        self.url = SimpleNamespace(path=path)
        self.headers = headers or {}
        self.state = SimpleNamespace()


class TelemetryStreamTest(unittest.IsolatedAsyncioTestCase):
    async def test_usage_hub_broadcasts_messages(self) -> None:
        queue = await usage_telemetry.subscribe()
        try:
            await usage_telemetry.publish("GET /docs 200")
            self.assertEqual(
                "GET /docs 200",
                await asyncio.wait_for(queue.get(), timeout=1),
            )
        finally:
            await usage_telemetry.unsubscribe(queue)

    async def test_stream_route_returns_sse_response(self) -> None:
        response = await stream_usage(FakeRequest("/telemetry/stream"))

        self.assertIsInstance(response, EventSourceResponse)

    async def test_middleware_publishes_usage_without_extra_metadata(self) -> None:
        from elrag import main as main_module

        user = AuthenticatedUser(
            google_sub="google-sub-1",
            email="user@example.com",
            name="User Example",
            picture=None,
            role="user",
        )

        class FakeAuthService:
            def __init__(self) -> None:
                self.consume_calls = 0

            def build_quota_headers(self):
                return {
                    "X-Global-Quota-Limit": "1000",
                    "X-Global-Quota-Remaining": "1000",
                }

            def authenticate_bearer_token(self, raw_token: str):
                return user

            def consume_quota(self):
                self.consume_calls += 1
                return 1000, 999

        async def call_next(_: FakeRequest) -> JSONResponse:
            return JSONResponse(status_code=200, content={"ok": True})

        fake_auth_service = FakeAuthService()
        publish_mock = AsyncMock()

        with patch.object(main_module, "auth_service", fake_auth_service), patch.object(
            main_module.usage_telemetry,
            "publish",
            publish_mock,
        ):
            public_response = await main_module.enforce_client_authorization(
                FakeRequest("/docs"),
                call_next,
            )
            self.assertEqual(200, public_response.status_code)

            protected_response = await main_module.enforce_client_authorization(
                FakeRequest("/auth/me", {"authorization": "Bearer valid-token"}),
                call_next,
            )
            self.assertEqual(200, protected_response.status_code)

            telemetry_response = await main_module.enforce_client_authorization(
                FakeRequest("/telemetry/stream", {"authorization": "Bearer valid-token"}),
                call_next,
            )
            self.assertEqual(200, telemetry_response.status_code)

        self.assertEqual(1, fake_auth_service.consume_calls)
        self.assertEqual(
            ["GET /docs 200", "GET /auth/me 200 quota=999"],
            [call.args[0] for call in publish_mock.await_args_list],
        )

    async def test_stream_requires_bearer_token(self) -> None:
        from elrag import main as main_module

        async def call_next(_: FakeRequest) -> JSONResponse:
            return JSONResponse(status_code=200, content={"ok": True})

        response = await main_module.enforce_client_authorization(
            FakeRequest("/telemetry/stream"),
            call_next,
        )

        self.assertEqual(401, response.status_code)
        self.assertEqual(
            {"message": "Authorization bearer token is required"},
            json.loads(response.body),
        )


if __name__ == "__main__":
    unittest.main()
