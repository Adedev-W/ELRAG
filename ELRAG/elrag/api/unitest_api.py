from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException

from elrag.models.base import get_session

unitest_api = APIRouter()

KEYSPACE = "production"
TABLE = f"{KEYSPACE}.client"


def _row_to_dict(row) -> dict:
    return {
        "id": str(row["id"]),
        "client_name": row["client_name"],
        "client_pinkey": row["client_pinkey"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


@unitest_api.post("/client")
def create_client(client_name: str, client_pinkey: str) -> dict:
    session = get_session()
    client_id = uuid4()
    created_at = datetime.now(timezone.utc)

    session.execute(
        f"""
        INSERT INTO {TABLE} (id, client_name, client_pinkey, created_at)
        VALUES (%s, %s, %s, %s)
        """,
        (client_id, client_name, client_pinkey, created_at),
    )

    return {
        "message": "client created",
        "data": {
            "id": str(client_id),
            "client_name": client_name,
            "client_pinkey": client_pinkey,
            "created_at": created_at.isoformat(),
        },
    }


@unitest_api.get("/client/{client_id}")
def get_client(client_id: UUID) -> dict:
    session = get_session()

    rows = session.execute(
        f"""
        SELECT id, client_name, client_pinkey, created_at
        FROM {TABLE}
        WHERE id = %s
        """,
        (client_id,),
    )
    row = rows.one()
    if row is None:
        raise HTTPException(status_code=404, detail="client not found")

    return {"message": "client found", "data": _row_to_dict(row)}


@unitest_api.get("/clients")
def get_clients() -> dict:
    session = get_session()

    rows = session.execute(
        f"""
        SELECT id, client_name, client_pinkey, created_at
        FROM {TABLE}
        LIMIT 100
        """
    )

    data = [_row_to_dict(row) for row in rows]
    return {"message": "clients found", "count": len(data), "data": data}


@unitest_api.put("/client/{client_id}")
def update_client(client_id: UUID, client_name: str, client_pinkey: str) -> dict:
    session = get_session()

    session.execute(
        f"""
        UPDATE {TABLE}
        SET client_name = %s, client_pinkey = %s
        WHERE id = %s
        """,
        (client_name, client_pinkey, client_id),
    )

    return {
        "message": "client updated",
        "data": {
            "id": str(client_id),
            "client_name": client_name,
            "client_pinkey": client_pinkey,
        },
    }


@unitest_api.delete("/client/{client_id}")
def delete_client(client_id: UUID) -> dict:
    session = get_session()

    session.execute(
        f"DELETE FROM {TABLE} WHERE id = %s",
        (client_id,),
    )

    return {"message": "client deleted", "id": str(client_id)}
