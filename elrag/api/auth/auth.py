from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from elrag.core.auth_be import (
    AuthConfigurationError,
    AuthenticationError,
    AuthorizationError,
    AuthorizationServiceBE,
    OAUTH_STATE_COOKIE,
)

auth_api = APIRouter()
auth_service = AuthorizationServiceBE()


@auth_api.get("/login")
async def login(request: Request) -> RedirectResponse:
    try:
        state = auth_service.create_state()
        redirect_uri = auth_service.get_redirect_uri(
            str(request.url_for("google_oauth_callback"))
        )
        authorization_url = auth_service.build_authorization_url(state, redirect_uri)
    except AuthConfigurationError as exc:
        return JSONResponse(status_code=500, content={"message": str(exc)})

    response = RedirectResponse(authorization_url, status_code=307)
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response


@auth_api.get("/callback", name="google_oauth_callback")
async def callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> JSONResponse:
    if error:
        return _state_clearing_response(
            status_code=400,
            content={"message": "Google OAuth returned an error"},
        )

    expected_state = request.cookies.get(OAUTH_STATE_COOKIE)
    if not code or not state or not expected_state or state != expected_state:
        return _state_clearing_response(
            status_code=400,
            content={"message": "invalid OAuth state"},
        )

    redirect_uri = auth_service.get_redirect_uri(
        str(request.url_for("google_oauth_callback"))
    )

    try:
        token_response = await auth_service.exchange_authorization_code(
            code,
            redirect_uri,
        )
        claims = auth_service.verify_google_id_token(token_response["id_token"])
        user = auth_service.get_or_create_user(claims)
        auth_user = auth_service.require_active_user(user)
        auth_service.record_login(user)
        access_token = auth_service.create_access_token(user)
    except AuthConfigurationError as exc:
        return _state_clearing_response(
            status_code=500,
            content={"message": str(exc)},
        )
    except AuthenticationError as exc:
        return _state_clearing_response(
            status_code=401,
            content={"message": str(exc)},
        )
    except AuthorizationError as exc:
        return _state_clearing_response(
            status_code=403,
            content={"message": str(exc)},
        )

    return _state_clearing_response(
        status_code=200,
        content={
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": auth_service.settings.token_ttl_seconds,
            "user": asdict(auth_user),
        },
    )


@auth_api.get("/me")
async def me(request: Request) -> JSONResponse:
    user = getattr(request.state, "user", None)
    if user is None:
        return JSONResponse(status_code=401, content={"message": "not authenticated"})
    return JSONResponse(status_code=200, content={"user": asdict(user)})


def _state_clearing_response(status_code: int, content: dict) -> JSONResponse:
    response = JSONResponse(status_code=status_code, content=content)
    response.delete_cookie(OAUTH_STATE_COOKIE)
    return response
