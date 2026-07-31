from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from elrag.api.auth.auth import auth_api
from elrag.api.gcs import gcs_api
from elrag.api.telemetry import telemetry_api
from elrag.api.docs import docs_api
from elrag.api.vision import vision_api
from elrag.api.agent import agent_api
from elrag.core.auth_be import (
    AuthConfigurationError,
    AuthenticationError,
    AuthorizationError,
    AuthorizationServiceBE,
    QuotaExceededError,
)
from elrag.mcp.server import mcp_app
from elrag.models.base import sync_all_tables
from elrag.lib.telemetry import format_usage_event, usage_telemetry
import elrag.models.model  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    sync_all_tables()
    yield


app = FastAPI(lifespan=lifespan)
auth_service = AuthorizationServiceBE()
TELEMETRY_STREAM_PATH = "/telemetry/stream"
PUBLIC_PATHS = {
    "/auth/login",
    "/auth/callback",
    "/docs",
    "/redoc",
    "/openapi.json",
}


@app.middleware("http")
async def enforce_client_authorization(request: Request, call_next):
    path = request.url.path
    should_publish_usage = path != TELEMETRY_STREAM_PATH

    if path in PUBLIC_PATHS:
        response: Response = await call_next(request)
        if should_publish_usage:
            await usage_telemetry.publish(
                format_usage_event(request.method, path, response.status_code)
            )
        return response

    bearer_token = _extract_bearer_token(request)
    if bearer_token is None:
        headers = auth_service.build_quota_headers()
        response = JSONResponse(
            status_code=401,
            content={"message": "Authorization bearer token is required"},
            headers=headers,
        )
        if should_publish_usage:
            await usage_telemetry.publish(
                format_usage_event(
                    request.method,
                    path,
                    response.status_code,
                    headers["X-Global-Quota-Remaining"],
                )
            )
        return response

    try:
        request.state.user = auth_service.authenticate_bearer_token(bearer_token)
        if path == TELEMETRY_STREAM_PATH:
            headers = auth_service.build_quota_headers()
            quota_remaining = headers["X-Global-Quota-Remaining"]
        else:
            quota_limit, quota_remaining = auth_service.consume_quota()
            headers = {
                "X-Global-Quota-Limit": str(quota_limit),
                "X-Global-Quota-Remaining": str(quota_remaining),
            }
    except AuthConfigurationError as exc:
        response = JSONResponse(status_code=500, content={"message": str(exc)})
        if should_publish_usage:
            await usage_telemetry.publish(
                format_usage_event(request.method, path, response.status_code)
            )
        return response
    except AuthenticationError as exc:
        headers = auth_service.build_quota_headers()
        response = JSONResponse(
            status_code=401,
            content={"message": str(exc)},
            headers=headers,
        )
        if should_publish_usage:
            await usage_telemetry.publish(
                format_usage_event(
                    request.method,
                    path,
                    response.status_code,
                    headers["X-Global-Quota-Remaining"],
                )
            )
        return response
    except AuthorizationError as exc:
        headers = auth_service.build_quota_headers()
        response = JSONResponse(
            status_code=403,
            content={"message": str(exc)},
            headers=headers,
        )
        if should_publish_usage:
            await usage_telemetry.publish(
                format_usage_event(
                    request.method,
                    path,
                    response.status_code,
                    headers["X-Global-Quota-Remaining"],
                )
            )
        return response
    except QuotaExceededError as exc:
        headers = auth_service.build_quota_headers()
        response = JSONResponse(
            status_code=429,
            content={"message": str(exc)},
            headers=headers,
        )
        if should_publish_usage:
            await usage_telemetry.publish(
                format_usage_event(
                    request.method,
                    path,
                    response.status_code,
                    headers["X-Global-Quota-Remaining"],
                )
            )
        return response

    response: Response = await call_next(request)
    for key, value in headers.items():
        response.headers[key] = value
    if should_publish_usage:
        await usage_telemetry.publish(
            format_usage_event(
                request.method,
                path,
                response.status_code,
                quota_remaining,
            )
        )
    return response


def _extract_bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization")
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


app.include_router(vision_api, prefix="/vision", tags=["Vision API"])
app.include_router(gcs_api, prefix="/gcs", tags=["GCS API"])
app.include_router(docs_api, prefix="/docs", tags=["Document AI API"])
app.include_router(auth_api, prefix="/auth", tags=["Auth API"])
app.include_router(telemetry_api)
app.include_router(agent_api)
app.mount("/mcp", mcp_app)
