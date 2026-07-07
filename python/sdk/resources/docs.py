from __future__ import annotations

from typing import Any

from python.sdk.exceptions import SDKResponseError
from python.sdk.transport import ElragTransport


class DocsSDK:
    def __init__(self, client: ElragTransport) -> None:
        self.client = client

    async def process_documents_gcs(self, gcs_uri: str) -> tuple[Any, dict[str, str]]:
        return await self.client.post_data("/docs/documentai/gcs", {}, params={"gcs_uri": gcs_uri})

    async def process_documents_bytes(
        self,
        file_path: str,
    ) -> tuple[Any, dict[str, str]]:
        with open(file_path, "rb") as file_handle:
            files = {"file": (file_path.split("/")[-1], file_handle)}
            response = await self.client.client.post(
                "/docs/documentai/bytes",
                files=files,
                headers=self.client._request_headers(True),
            )
        if response.status_code >= 400:
            raise SDKResponseError(response)
        return response.json(), dict(response.headers)

    async def get_documentai_response(self, response_id: str) -> tuple[Any, dict[str, str]]:
        return await self.client.get_data(f"/docs/documentai/{response_id}")
