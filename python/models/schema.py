from typing import Optional
from pydantic import BaseModel, Field


    


class Client(BaseModel):
    id: str = Field(..., description="Unique client identifier")
    client_name: Optional[str] = Field(None, description="Optional client display name")


class GCSUploadResponse(BaseModel):
    message: str = Field(..., description="Response message")
    vision_id: Optional[str] = Field(
        None, description="ID of the created vision record if upload is successful"
    )


#Vision Schema for API response 

class Vision(BaseModel):
    id: str = Field(..., description="Unique vision record identifier")
    gcs_uri: Optional[str] = Field(
        None, description="Google Cloud Storage URI for the image or document"
    )
    
    metadata: Optional[str] = Field(
        None, description="Optional metadata or extracted text summary"
    )
    content: Optional[str] = Field(None, description="Optional raw content or OCR text")

class VisionResponse(BaseModel):
    id: str = Field(..., description="Unique vision record identifier")
    metadata: Optional[str] = Field(
        None, description="Optional metadata or extracted text summary"
    )
    content: Optional[str] = Field(None, description="Optional raw content or OCR text")




