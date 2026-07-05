from __future__ import annotations

import asyncio
import json
from uuid import UUID, uuid4

from python.lib.vision import VisionService
from python.models.model import Vision as VisionModel
from python.models.schema import VisionResponse


class VisionServiceBE:
    async def save_vision_response(self, response: VisionModel) -> VisionModel:
        await asyncio.to_thread(response.save)
        return response

    async def get_vision_response(self, vision_id: str) -> VisionModel | None:
        def _get() -> VisionModel | None:
            return VisionModel.objects(id=UUID(vision_id)).first()

        return await asyncio.to_thread(_get)

    @staticmethod
    def serialize_vision_response(response: VisionModel) -> dict:
        return {
            "id": str(response.id),
            "metadata": response.metadata,
            "content": response.content,
        }

    async def process_vision_bytes(self, file_bytes: bytes) -> VisionResponse:
        vision_service = VisionService()
        output = await asyncio.to_thread(vision_service.detect_text, file_bytes)

        response = VisionResponse(
            id=str(uuid4()),
            metadata=None,
            content=output,
        )
        await self._persist_vision_response(
            response_id=response.id,
            gcs_uri=None,
            metadata=response.metadata,
            content=response.content,
        )
        return response

    async def process_vision_gcs(self, gcs_uri: str) -> VisionResponse:
        vision_service = VisionService()
        output = await asyncio.to_thread(vision_service.detect_text_forgcs, gcs_uri)

        response = VisionResponse(
            id=str(uuid4()),
            metadata=None,
            content=output,
        )
        await self._persist_vision_response(
            response_id=response.id,
            gcs_uri=gcs_uri,
            metadata=response.metadata,
            content=response.content,
        )
        return response

    async def _persist_vision_response(
        self,
        *,
        response_id: str,
        gcs_uri: str | None,
        metadata: dict | str | None,
        content: str | None,
    ) -> None:
        if isinstance(metadata, dict):
            metadata_value = json.dumps(metadata)
        else:
            metadata_value = metadata

        record = VisionModel(
            id=UUID(response_id),
            gcs_uri=gcs_uri,
            metadata=metadata_value,
            content=content,
        )
        await self.save_vision_response(record)
