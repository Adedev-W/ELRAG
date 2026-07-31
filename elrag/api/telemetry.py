from __future__ import annotations

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from elrag.lib.telemetry import usage_telemetry

telemetry_api = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@telemetry_api.get("/stream")
async def stream_usage(_: Request) -> EventSourceResponse:
    queue = await usage_telemetry.subscribe()

    async def event_generator():
        try:
            while True:
                message = await queue.get()
                yield {"event": "usage", "data": message}
        finally:
            await usage_telemetry.unsubscribe(queue)

    return EventSourceResponse(event_generator(), ping=15)
