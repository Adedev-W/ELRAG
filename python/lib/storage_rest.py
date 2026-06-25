import os
from google.cloud import storage

class GCSService:
    def __init__(self, bucket_name: str):
        # SDK otomatis membaca Environment Variable GOOGLE_APPLICATION_CREDENTIALS
        self.client = storage.Client(project="adsapt")
        self.bucket = self.client.bucket(bucket_name)

    def upload_file(self, local_file_path: str, destination_blob_name: str):
        """Mengupload file dari lokal ke GCS Bucket"""
        try:
            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_filename(local_file_path)
            print(f"File {local_file_path} berhasil diupload ke {destination_blob_name}.")
            return True
        except Exception as e:
            print(f"Gagal upload ke GCS: {e}")
            return False
        
    def list_files(self):
        """Mendapatkan daftar file di GCS Bucket"""
        try:
            blobs = self.bucket.list_blobs()
            file_list = [blob.name for blob in blobs]
            print(f"Daftar file di bucket {self.bucket.name}: {file_list}")
            return file_list
        except Exception as e:
            print(f"Gagal mendapatkan daftar file: {e}")
            return []
        
    def download_file(self, source_blob_name: str, destination_file_path: str = None):
        """Mendownload file dari GCS Bucket ke lokal"""
        try:
            blob = self.bucket.blob(source_blob_name)
            files = blob.download_as_text()
            print(f"Isi file {source_blob_name}:\n{files}")
            return True
        except Exception as e:
            print(f"Gagal download dari GCS: {e}")
            return False

