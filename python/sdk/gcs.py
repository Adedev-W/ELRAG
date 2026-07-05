from __future__ import annotations

from typing import Any

from python.sdk.client import ElragSDK, SDKResponseError


class GCSSDK:
    def __init__(self, client: ElragSDK) -> None:
        self.client = client

    async def upload_file(self, file_path: str) -> tuple[Any, dict[str, str]]:
        with open(file_path, "rb") as file_handle:
            response = await self.client.client.post(
                "/gcs/upload",
                files={"file": (file_path.split("/")[-1], file_handle)},
                headers=self.client._request_headers(True),
            )
        if response.status_code >= 400:
            raise SDKResponseError(response)
        return response.json(), dict(response.headers)

    async def list_files(self) -> tuple[Any, dict[str, str]]:
        return await self.client.get_data("/gcs/files")

    async def info_file(self, blob_name: str) -> tuple[Any, dict[str, str]]:
        return await self.client.get_data("/gcs/files/info", params={"blob_name": blob_name})

    async def download_file(self, blob_name: str) -> tuple[Any, dict[str, str]]:
        return await self.client.get_data("/gcs/files/download", params={"blob_name": blob_name})
