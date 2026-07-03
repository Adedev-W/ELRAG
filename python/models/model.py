from __future__ import annotations

from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model
from .base import register_model


@register_model
class CloudStorage(Model):
    __table_name__ = "cloud_storage"
    id = columns.UUID(primary_key=True)
    name = columns.Text()
    description = columns.Text()
    bucket_name = columns.Text()
    file_path = columns.Text()
    file_type = columns.Text()
    created_at = columns.DateTime()

@register_model
class ControllerServices(Model):
    __table_name__ = "controller_services"
    id = columns.UUID(primary_key=True)
    cs_id = columns.UUID()
    vision_limit = columns.Integer()
    gcs_limit = columns.Integer()
    documentai_limit = columns.Integer()
    created_at = columns.DateTime()

@register_model
class DocumentAI(Model):
    __table_name__ = "document_ai"
    id = columns.UUID(primary_key=True)
    metadata = columns.Text()

@register_model
class Vision(Model):
    __table_name__ = "vision"
    id = columns.UUID(primary_key=True)
    description = columns.Text()
    metadata = columns.Text()
    content = columns.Text()
    
@register_model
class Client(Model):
    __table_name__ = "client"
    id = columns.UUID(primary_key=True)
    client_name = columns.Text()
    client_pinkey = columns.Text()
    created_at = columns.DateTime()
