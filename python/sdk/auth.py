from __future__ import annotations

from python.sdk.client import ElragSDK


class AuthSDK:
    def __init__(self, client: ElragSDK) -> None:
        self.client = client

    async def verify_client(self) -> tuple[dict, dict[str, str]]:
        return await self.client.get_data("/auth/verify")

