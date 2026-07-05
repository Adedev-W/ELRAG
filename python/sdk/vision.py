from __future__ import annotations

from typing import Any

from python.sdk.client import ElragSDK


class VisionSDK:
    def __init__(self, client: ElragSDK) -> None:
        self.client = client

    async def get_vision(self, vision_id: str) -> tuple[Any, dict[str, str]]:
        return await self.client.get_data(f"/vision/vision/{vision_id}")

    async def process_vision_bytes(self, file_path: str) -> tuple[Any, dict[str, str]]:
        with open(file_path, "rb") as file_handle:
            response = await self.client.client.post(
                "/vision/vision",
                files={"files": (file_path.split("/")[-1], file_handle)},
                headers=self.client._request_headers(True),
            )
        if response.status_code >= 400:
            from python.sdk.client import SDKResponseError

            raise SDKResponseError(response)
        return response.json(), dict(response.headers)

    async def process_vision_gcs(self, gcs_uri: str) -> tuple[Any, dict[str, str]]:
        return await self.client.post_data("/vision/vision-gcs", {}, params={"gcs_uri": gcs_uri})
