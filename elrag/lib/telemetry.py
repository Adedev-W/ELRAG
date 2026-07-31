from __future__ import annotations

import asyncio


class UsageTelemetryHub:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        async with self._lock:
            self._subscribers.discard(queue)

    async def publish(self, message: str) -> None:
        async with self._lock:
            subscribers = tuple(self._subscribers)
        for queue in subscribers:
            queue.put_nowait(message)


def format_usage_event(
    method: str,
    path: str,
    status_code: int,
    quota_remaining: str | int | None = None,
) -> str:
    message = f"{method} {path} {status_code}"
    if quota_remaining is not None:
        message = f"{message} quota={quota_remaining}"
    return message


usage_telemetry = UsageTelemetryHub()
