from __future__ import annotations

from typing import Any

from python.sdk.client import ElragSDK


class UnitestSDK:
    def __init__(self, client: ElragSDK) -> None:
        self.client = client

    async def create_client(self, client_name: str, client_pinkey: str) -> tuple[Any, dict[str, str]]:
        return await self.client.post_data(
            "/unitest/client",
            {},
            needs_auth=False,
            params={"client_name": client_name, "client_pinkey": client_pinkey},
        )

    async def get_client(self, client_id: str) -> tuple[Any, dict[str, str]]:
        return await self.client.get_data(f"/unitest/client/{client_id}", needs_auth=False)

    async def get_clients(self) -> tuple[Any, dict[str, str]]:
        return await self.client.get_data("/unitest/clients", needs_auth=False)

    async def update_client(self, client_id: str, client_name: str, client_pinkey: str) -> tuple[Any, dict[str, str]]:
        return await self.client.put_data(
            f"/unitest/client/{client_id}",
            {},
            needs_auth=False,
            params={"client_name": client_name, "client_pinkey": client_pinkey},
        )

    async def delete_client(self, client_id: str) -> tuple[Any, dict[str, str]]:
        return await self.client.delete_data(f"/unitest/client/{client_id}", needs_auth=False)
