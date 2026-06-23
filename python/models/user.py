from __future__ import annotations

from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model
from .base import register_model


@register_model
class UserModel(Model):
    __keyspace__ = "demo"
    __table_name__ = "users"
    id = columns.UUID(primary_key=True)
    name = columns.Text()
    email = columns.Text()

@register_model
class MessagesModel(Model):
    __keyspace__ = "demo"
    __table_name__ = "messages"
    id = columns.UUID(primary_key=True)
    user_id = columns.UUID()
    content = columns.Text()
    

