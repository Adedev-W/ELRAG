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

    def process_document(
        self,
        project_id: str,
        location: str,
        processor_id: str,
        gcs_input_uri: str,
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
                    mime_type="application/pdf",
                ),
            )

            result = self.client.process_document(
                request=request
            )

            return result.document

        except Exception as e:
            print(f"Gagal memproses dokumen: {e}")
            return None


document_ai_service = DocumentAIService(
    location="us"
)

document = document_ai_service.process_document(
    project_id="xxxx",
    location="us",
    processor_id="xxxx",
    gcs_input_uri="gs://xxxxf",
)

if document:
    print("=== HASIL OCR ===")
    print(document.text)