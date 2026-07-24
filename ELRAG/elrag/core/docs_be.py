from __future__ import annotations

import asyncio
import json
import os
from uuid import UUID, uuid4

from google.protobuf.json_format import MessageToDict

from elrag.lib.documentai import DocumentAIService
from elrag.lib.storage_rest import GCSService
from elrag.models.model import DocumentAI
from elrag.models.schema import DocumentAIResponseBytes, DocumentAIResponseGCS


class DocsServiceBE:
    def __init__(self) -> None:
        self.bucket_name = os.environ.get("GCS_BUCKET")

    async def save_documentai_response(self, response: DocumentAI) -> DocumentAI:
        await asyncio.to_thread(response.save)
        return response

    async def get_documentai_response(self, response_id: str) -> DocumentAI | None:
        def _get() -> DocumentAI | None:
            return DocumentAI.objects(id=UUID(response_id)).first()

        return await asyncio.to_thread(_get)

    @staticmethod
    def serialize_documentai_response(response: DocumentAI) -> dict:
        return {
            "id": str(response.id),
            "gcs_uri": response.gcs_uri,
            "filename": response.filename,
            "metadata": response.metadata,
            "content": response.content,
        }

    async def process_documents_gcs(self, gcs_uri: str) -> DocumentAIResponseGCS:
        gcs_service = GCSService(self.bucket_name)
        gcs_info = await asyncio.to_thread(gcs_service.info_files, gcs_uri)
        if not gcs_info:
            raise ValueError("GCS file not found")

        document_service = DocumentAIService("us")
        document = await asyncio.to_thread(
            document_service.process_document_gcs,
            project_id="adesapt",
            location="us",
            processor_id="2ff00dc23a9dd3f8",
            gcs_input_uri=gcs_info["name"],
            mime_type=gcs_info["content_type"],
        )

        response = DocumentAIResponseGCS(
            id=str(uuid4()),
            gcs_uri=gcs_info["name"],
            metadata=MessageToDict(document._pb),
            content=document.text,
        )
        await self._persist_documentai_response(
            response_id=response.id,
            gcs_uri=response.gcs_uri,
            filename=None,
            metadata=response.metadata,
            content=response.content,
        )
        return response

    async def process_documents_bytes(
        self,
        file_bytes: bytes,
        filename: str | None,
        mime_type: str | None,
    ) -> DocumentAIResponseBytes:
        document_service = DocumentAIService("us")
        document = await asyncio.to_thread(
            document_service.process_document,
            project_id="adsapt",
            location="us",
            processor_id="2ff00dc23a9dd3f8",
            files=file_bytes,
            mime_type=mime_type,
        )

        response = DocumentAIResponseBytes(
            id=str(uuid4()),
            filename=filename,
            metadata=MessageToDict(document._pb),
            content=document.text,
        )
        await self._persist_documentai_response(
            response_id=response.id,
            gcs_uri=None,
            filename=response.filename,
            metadata=response.metadata,
            content=response.content,
        )
        return response

    async def _persist_documentai_response(
        self,
        *,
        response_id: str,
        gcs_uri: str | None,
        filename: str | None,
        metadata: dict | None,
        content: str | None,
    ) -> None:
        record = DocumentAI(
            id=UUID(response_id),
            gcs_uri=gcs_uri,
            filename=filename,
            metadata="" if metadata is None else json.dumps(metadata),
            content=content,
        )
        await self.save_documentai_response(record)

