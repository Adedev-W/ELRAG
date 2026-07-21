from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from python.api.auth.auth import auth_api
from python.api.gcs import gcs_api
from python.api.docs import docs_api
from python.api.vision import vision_api
from python.api.unitest_api import unitest_api
from python.api.agent import agent_api
from python.core.auth_be import AuthorizationServiceBE
from python.mcp.server import mcp_app
from python.models.base import sync_all_tables
import python.models.model  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    sync_all_tables()
    yield


app = FastAPI(lifespan=lifespan)
auth_service = AuthorizationServiceBE()


@app.middleware("http")
async def enforce_client_authorization(request: Request, call_next):
    path = request.url.path
    excluded_prefixes = (
        "/unitest",
        "/auth",
        "/docs",
        "/redoc",
        "/openapi.json",
    )

    if path.startswith(excluded_prefixes):
        return await call_next(request)

    client_id = request.headers.get("client_id") or request.headers.get("x-client-id")
    if not client_id:
        headers = auth_service.build_quota_headers()
        return JSONResponse(
            status_code=400,
            content={"message": "client_id header is required"},
            headers=headers,
        )

    auth_result = auth_service.authorize_request(client_id)
    headers = auth_service.build_quota_headers()
    headers["X-Client-Id"] = auth_result.client_id or client_id

    if not auth_result.allowed:
        return JSONResponse(
            status_code=auth_result.status_code,
            content={"message": auth_result.message},
            headers=headers,
        )

    response: Response = await call_next(request)
    for key, value in headers.items():
        response.headers[key] = value
    return response


app.include_router(vision_api, prefix="/vision", tags=["Vision API"])
app.include_router(gcs_api, prefix="/gcs", tags=["GCS API"])
app.include_router(docs_api, prefix="/docs", tags=["Document AI API"])
app.include_router(unitest_api, prefix="/unitest", tags=["Unit Test API"])
app.include_router(auth_api, prefix="/auth", tags=["Auth API"])
app.include_router(agent_api)
app.mount("/mcp", mcp_app)


