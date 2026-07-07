from __future__ import annotations

from pathlib import Path

from python.sdk.resources import AuthSDK, DocsSDK, GCSSDK, UnitestSDK, VisionSDK
from python.sdk.transport import ElragTransport


class ElragSDK:
    def __init__(
        self,
        base_url: str | None = None,
        auth_file: str | Path | None = None,
        config_file: str | Path | None = None,
    ) -> None:
        self.transport = ElragTransport(base_url=base_url, auth_file=auth_file, config_file=config_file)
        self.auth = AuthSDK(self.transport)
        self.docs = DocsSDK(self.transport)
        self.gcs = GCSSDK(self.transport)
        self.vision = VisionSDK(self.transport)
        self.unitest = UnitestSDK(self.transport)

    async def close(self) -> None:
        await self.transport.close()
