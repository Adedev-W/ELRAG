from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from python.core.auth_be import AuthorizationServiceBE

auth_api = APIRouter()
auth_service = AuthorizationServiceBE()


@auth_api.get("/verify")
async def verify_client(
    client_id: str = Header(..., alias="client_id"),
) -> JSONResponse:
    client = auth_service.validate_client(client_id)
    if client is None:
        return JSONResponse(status_code=404, content={"message": "client not found"})

    quota_limit, quota_remaining = auth_service.quota_snapshot()
    return JSONResponse(
        status_code=200,
        content={
            "message": "client verified",
            "data": {
                "client_id": client_id,
                "client_name": client.client_name,
                "quota_limit": quota_limit,
                "quota_remaining": quota_remaining,
            },
        },
        headers=auth_service.build_quota_headers(),
    )

