from __future__ import annotations

from pathlib import Path

from python.sdk.auth import AuthSDK
from python.sdk.client import ElragSDK
from python.sdk.docs import DocsSDK
from python.sdk.gcs import GCSSDK
from python.sdk.unitest import UnitestSDK
from python.sdk.vision import VisionSDK


class ElragAPIClient:
    def __init__(
        self,
        base_url: str | None = None,
        auth_file: str | Path | None = None,
        config_file: str | Path | None = None,
    ) -> None:
        self.transport = ElragSDK(base_url=base_url, auth_file=auth_file, config_file=config_file)
        self.auth = AuthSDK(self.transport)
        self.docs = DocsSDK(self.transport)
        self.gcs = GCSSDK(self.transport)
        self.vision = VisionSDK(self.transport)
        self.unitest = UnitestSDK(self.transport)

    async def close(self) -> None:
        await self.transport.close()

