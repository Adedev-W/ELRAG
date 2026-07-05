from google.cloud import documentai
from google.api_core.client_options import ClientOptions

class DocumentAIService:
    def __init__(self, location: str):
        opts = ClientOptions(
            api_endpoint=f"{location}-documentai.googleapis.com"
        )

        self.client = documentai.DocumentProcessorServiceClient(
            client_options=opts
        )
        

    def process_document_gcs(
        self,
        project_id: str,
        location: str,
        processor_id: str,
        gcs_input_uri: str,
        mime_type: str
    ):
        try:
            name = self.client.processor_path(
                project_id,
                location,
                processor_id,
            )
            request = documentai.ProcessRequest(
                name=name,
                gcs_document=documentai.GcsDocument(
                    gcs_uri=gcs_input_uri,
                    mime_type=mime_type,
                ),
            )

            result = self.client.process_document(
                request=request
            )

            return result.document

        except Exception as e:
            print(f"Gagal memproses dokumen: {e}")
            return None
        
    def process_document(
        self,
        project_id: str,
        location: str,
        processor_id: str,
        files: bytes,
        mime_type: str
    ):
        try:
            name = self.client.processor_path(
                project_id,
                location,
                processor_id,
            )
            
    

            request = documentai.ProcessRequest(
                name=name,
                raw_document=documentai.RawDocument(
                    content=files,
                    mime_type=mime_type
                ),
            )

            result = self.client.process_document(
                request=request
            )

            return result.document

        except Exception as e:
            print(f"Gagal memproses dokumen: {e}")
            return None


# document_ai_service = DocumentAIService(
#     location="us"
    
# )
# files = open("/home/As.Dev-ai/rust-project/rust-me/SAMPLE_OCR.pdf", "rb")

# document = document_ai_service.process_document(
#     project_id="adsapt",
#     location="us",
#     processor_id="2ff00dc23a9dd3f8",
#     files=files.read(),
#     mime_type="application/pdf"  
# )


# print(document.text)

