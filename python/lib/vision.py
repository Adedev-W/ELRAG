from google.cloud import vision

class VisionService:
    def __init__(self):
        self.client = vision.ImageAnnotatorClient()

    def detect_text(self, gs_image_path: str):
        """Mendeteksi teks dalam gambar menggunakan Google Cloud Vision API"""
        try:
        
            image = vision.Image(source=vision.ImageSource(gcs_image_uri=gs_image_path))
            response = self.client.text_detection(image=image)
            texts = response.text_annotations
            if texts:
                detected_text = texts[0].description
                print(f"Teks terdeteksi dalam {gs_image_path}:\n{detected_text}")
                return detected_text
            else:
                print(f"Tidak ada teks yang terdeteksi dalam {gs_image_path}.")
                return ""
        except Exception as e:
            print(f"Gagal mendeteksi teks: {e}")
            return ""
        
# scan = VisionService()
# scan.detect_text("gs://document-001/sample-2944.png")