from contextlib import asynccontextmanager

from fastapi import FastAPI
from python.api.gcs import gcs_api
from python.api.vision import vision_api
from python.api.docs import docs_api
from python.api.unitest_api import unitest_api
from python.models.base import sync_all_tables
import python.models.model  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    sync_all_tables()
    yield


app = FastAPI(lifespan=lifespan)


app.include_router(vision_api, prefix="/vision", tags=["Vision API"])
app.include_router(gcs_api, prefix="/gcs", tags=["GCS API"])
app.include_router(docs_api, prefix="/docs", tags=["Document AI API"])
app.include_router(unitest_api, prefix="/unitest", tags=["Unit Test API"])