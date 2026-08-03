import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response
from opentelemetry import trace

from elrag.api.auth.auth import auth_api
from elrag.api.gcs import gcs_api
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
from elrag.core.quota import QuotaStoreUnavailableError
from elrag.mcp.server import mcp_app
from elrag.models.base import sync_all_tables
from elrag.lib.observability import (
    configure_observability,
    monotonic,
    record_request,
    shutdown_observability,
    validate_observability,
)
import elrag.models.model  # noqa: F401

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        validate_observability()
        await auth_service.check_quota_store()
        sync_all_tables()
        yield
    finally:
        try:
            await auth_service.close()
        finally:
            shutdown_observability()


app = FastAPI(lifespan=lifespan)
auth_service = AuthorizationServiceBE()
PUBLIC_PATHS = {
    "/auth/login",
    "/auth/callback",
    "/docs",
    "/redoc",
    "/openapi.json",
}
NON_USAGE_PATHS = {"/docs", "/redoc", "/openapi.json"}


@app.middleware("http")
async def enforce_client_authorization(request: Request, call_next):
    path = request.url.path
    should_record_usage = path not in NON_USAGE_PATHS
    started_at = monotonic()
    status_code = 500
    authenticated = False
    quota_consumed = False

    try:
        if path in PUBLIC_PATHS:
            response: Response = await call_next(request)
            status_code = response.status_code
            return response

        bearer_token = _extract_bearer_token(request)
        if bearer_token is None:
            response = JSONResponse(
                status_code=401,
                content={"message": "Authorization bearer token is required"},
                headers=await _best_effort_quota_headers(),
            )
            status_code = response.status_code
            return response

        try:
            request.state.user = auth_service.authenticate_bearer_token(bearer_token)
            authenticated = True
            quota_limit, quota_remaining = await auth_service.consume_quota()
            quota_consumed = True
            headers = {
                "X-Global-Quota-Limit": str(quota_limit),
                "X-Global-Quota-Remaining": str(quota_remaining),
            }
        except AuthConfigurationError as exc:
            response = JSONResponse(status_code=500, content={"message": str(exc)})
            status_code = response.status_code
            return response
        except AuthenticationError as exc:
            response = JSONResponse(
                status_code=401,
                content={"message": str(exc)},
                headers=await _best_effort_quota_headers(),
            )
            status_code = response.status_code
            return response
        except AuthorizationError as exc:
            response = JSONResponse(
                status_code=403,
                content={"message": str(exc)},
                headers=await _best_effort_quota_headers(),
            )
            status_code = response.status_code
            return response
        except QuotaExceededError as exc:
            response = JSONResponse(
                status_code=429,
                content={"message": str(exc)},
                headers=await _best_effort_quota_headers(),
            )
            status_code = response.status_code
            return response
        except QuotaStoreUnavailableError:
            response = JSONResponse(
                status_code=503,
                content={"message": "quota service unavailable"},
            )
            status_code = response.status_code
            return response

        response = await call_next(request)
        status_code = response.status_code
        for key, value in headers.items():
            response.headers[key] = value
        return response
    except Exception as exc:
        status_code = 500
        span = trace.get_current_span()
        if span.is_recording():
            span.record_exception(exc)
        raise
    finally:
        if should_record_usage:
            scope = getattr(request, "scope", {})
            route = getattr(scope.get("route"), "path", path)
            try:
                record_request(
                    method=request.method,
                    route=route,
                    status_code=status_code,
                    duration_seconds=monotonic() - started_at,
                    authenticated=authenticated,
                    quota_consumed=quota_consumed,
                )
            except Exception:
                logger.exception("Failed to record request observability metrics")


async def _best_effort_quota_headers() -> dict[str, str]:
    try:
        return await auth_service.build_quota_headers()
    except QuotaStoreUnavailableError:
        return {}


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
app.include_router(agent_api)
app.mount("/mcp", mcp_app)
configure_observability(app)
