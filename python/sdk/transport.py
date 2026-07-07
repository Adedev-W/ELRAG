from __future__ import annotations

from pathlib import Path
from typing import Any

from httpx import AsyncClient, Response

from python.sdk.config_loader import load_auth_file, load_sdk_conf
from python.sdk.exceptions import SDKResponseError


class ElragTransport:
    def __init__(
        self,
        base_url: str | None = None,
        auth_file: str | Path | None = None,
        config_file: str | Path | None = None,
    ) -> None:
        config_path = (
            Path(config_file)
            if config_file is not None
            else Path(__file__).with_name("config").joinpath(".conf")
        )
        config = load_sdk_conf(config_path)
        self.base_url = base_url or config.get("BASE_URL", "http://127.0.0.1:8000")

        auth_file_value = (
            Path(auth_file)
            if auth_file is not None
            else Path(config.get("BASE_AUTH_FILE", ".elrag_secret"))
        )
        auth_file_path = auth_file_value if auth_file_value.is_absolute() else config_path.parent / auth_file_value
        self.auth = load_auth_file(auth_file_path)
        self.client = AsyncClient(base_url=self.base_url)

    def _default_headers(self) -> dict[str, str]:
        return {"client_id": self.auth["client_id"]}

    def _request_headers(self, needs_auth: bool = True) -> dict[str, str]:
        return self._default_headers() if needs_auth else {}

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        needs_auth: bool = True,
        **kwargs: Any,
    ) -> tuple[Any, dict[str, str]]:
        response = await self.client.request(
            method,
            endpoint,
            headers=self._request_headers(needs_auth),
            **kwargs,
        )
        if response.status_code >= 400:
            raise SDKResponseError(response)
        return self._parse_json(response), dict(response.headers)

    @staticmethod
    def _parse_json(response: Response) -> Any:
        try:
            return response.json()
        except Exception:
            return response.text

    async def get_data(
        self,
        endpoint: str,
        *,
        needs_auth: bool = True,
        params: dict[str, Any] | None = None,
    ) -> tuple[Any, dict[str, str]]:
        return await self._request("GET", endpoint, params=params, needs_auth=needs_auth)

    async def post_data(
        self,
        endpoint: str,
        data: dict,
        *,
        needs_auth: bool = True,
        params: dict[str, Any] | None = None,
    ) -> tuple[Any, dict[str, str]]:
        return await self._request("POST", endpoint, json=data, params=params, needs_auth=needs_auth)

    async def put_data(
        self,
        endpoint: str,
        data: dict,
        *,
        needs_auth: bool = True,
        params: dict[str, Any] | None = None,
    ) -> tuple[Any, dict[str, str]]:
        return await self._request("PUT", endpoint, json=data, params=params, needs_auth=needs_auth)

    async def delete_data(
        self,
        endpoint: str,
        *,
        needs_auth: bool = True,
        params: dict[str, Any] | None = None,
    ) -> tuple[Any, dict[str, str]]:
        return await self._request("DELETE", endpoint, params=params, needs_auth=needs_auth)

    async def close(self) -> None:
        await self.client.aclose()
