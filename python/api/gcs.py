import uuid

from fastapi import FastAPI, UploadFile, File, APIRouter
from fastapi.responses import JSONResponse
from python.lib.storage_rest import GCSService
from uuid import uuid4
from python.models.schema import Vision, Client

gcs_api = APIRouter()

@gcs_api.post("/upload")
async def upload_file_to_gcs(file: UploadFile = File(...)) -> JSONResponse:
    """
    Endpoint untuk mengupload file ke GCS dan mengekstrak fitur.
    """
    try:
        # Simpan file sementara di server
        temp_file_path = f"/tmp/{file.filename}"
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(await file.read())

        # Upload file ke GCS
        gcs_service = GCSService(bucket_name="your-bucket-name")
        destination_blob_name = f"uploads/{file.filename}"
        upload_success = gcs_service.upload_file(temp_file_path, destination_blob_name)

        if not upload_success:
            return JSONResponse(status_code=500, content={"message": "Gagal mengupload file ke GCS."})

        # Simpan metadata ke database (misalnya menggunakan Cassandra)
        vision_record = Vision(
            id=str(uuid4()),
            gcs_uri=f"gs://your-bucket-name/{destination_blob_name}",
            metadata="Metadata tambahan jika ada",
            content="Konten tambahan jika ada"
        )
        # Simpan vision_record ke database (implementasi terserah Anda)

        return JSONResponse(status_code=200, content={"message": "File berhasil diupload dan fitur diekstrak.", "vision_id": vision_record.id})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Terjadi kesalahan: {e}"})
    
