from turtle import mode
from typing import Optional

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from python.lib.documentai import DocumentAIService
from python.models.schema import Vision, VisionResponse
from python.models.base import get_session