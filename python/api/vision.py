from turtle import mode
from typing import Optional

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from python.lib.vision import VisionService
from python.models.schema import Vision, VisionResponse
from python.models.base import get_session
session = get_session()

vision_api = APIRouter()

@vision_api.get("/vision/{vision_id}", response_model=VisionResponse)
async def get_vision_data(vision_id: str) -> JSONResponse:
    query = session.query(Vision).filter(Vision.id == vision_id)
    get_vision = query.first()
    if not get_vision:
        return JSONResponse(status_code=404, content={"message": "Vision not found"})
    return JSONResponse(status_code=200, content=get_vision.dict())

@vision_api.post("/vision", response_model=list[VisionResponse])
async def extract_features(files: UploadFile = File(...)) -> JSONResponse:
    extractor = VisionService()
    data = await files.read()
    output = extractor.detect_text(data)
    return JSONResponse(status_code=200, content={"message": "Features extracted successfully", "data": output})


@vision_api.post("/vision-gcs", response_model=list[VisionResponse])
async def extract_features(gcs_uri: str) -> JSONResponse:
    extractor = VisionService()
    output = extractor.detect_text_forgcs(gcs_uri)
    return JSONResponse(status_code=200, content={"message": "Features extracted successfully", "data": output})
