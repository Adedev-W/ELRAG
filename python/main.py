from fastapi import FastAPI
from python.api.gcs import gcs_api
from python.api.vision import vision_api
from python.models.base import sync_all_tables
sync_all_tables()  # Ensure all tables are synchronized with the database


app = FastAPI()
app.include_router(vision_api, prefix="/vision", tags=["Vision API"])
app.include_router(gcs_api, prefix="/gcs", tags=["GCS API"])

