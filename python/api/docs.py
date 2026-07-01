from typing import Optional

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from python.lib.documentai import DocumentAIService
from python.lib.storage_rest import GCSService
from python.models.schema import DocumentAIRequestGCS, DocumentAIRequestBytes, DocumentAIResponseGCS, DocumentAIResponseBytes
from python.models.base import get_session
import os
from uuid import uuid4
from google.protobuf.json_format import MessageToDict

docs_api = APIRouter()

@docs_api.post("/documentai/gcs", response_model=DocumentAIResponseGCS)
async def process_documents_gcs(gcs_uri: str) -> JSONResponse:
    """Extracts text and structured data from a document stored in Google Cloud Storage using Document AI."""
    gcs_info = GCSService(os.environ.get("GCS_BUCKET"))
    gcs_output = gcs_info.info_files(gcs_uri)
    service = DocumentAIService("us")
    
    response = service.process_document_gcs(project_id="adesapt", location="us", processor_id="2ff00dc23a9dd3f8", gcs_input_uri=gcs_output["name"], mime_type=gcs_output["content_type"])
    final_response = DocumentAIResponseGCS(id=str(uuid4()), gcs_uri=gcs_output["name"], metadata=response.metadata, content=response.content).model_dump_json()
    return JSONResponse(content=final_response)

@docs_api.post("/documentai/bytes", response_model=DocumentAIResponseBytes)
async def process_documents_bytes(file: UploadFile = File(...)) -> JSONResponse:
    """Extracts text and structured data from a document uploaded as bytes using Document AI."""
    file_bytes = await file.read()
    service = DocumentAIService("us")
    response = service.process_document(project_id="adesapt", location="us", processor_id="2ff00dc23a9dd3f8", files=file_bytes, mime_type=file.content_type)
    final_response = DocumentAIResponseBytes(id=str(uuid4()), filename=file.filename, metadata=MessageToDict(response._pb), content=response.text).model_dump_json()
    return JSONResponse(content=final_response)