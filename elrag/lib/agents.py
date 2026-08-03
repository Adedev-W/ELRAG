from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

from agno.agent import Agent
from agno.models.deepseek import DeepSeek
from dotenv import load_dotenv
from tavily import TavilyClient

from elrag.lib.gmaps import GoogleMapsService

load_dotenv()


def web_search(query: str) -> dict:
    """Perform a web search using Tavily."""
    client = TavilyClient()
    return client.search(query=query, search_depth="advanced", max_results=20)


def search_places(query: str) -> dict:
    """Search for place candidates using Google Maps."""
    maps_service = GoogleMapsService()
    return asyncio.run(maps_service.text_search(query, max_result_count=10))


def _next_stream_item(iterator: Iterator[Any]) -> tuple[bool, Any]:
    try:
        return True, next(iterator)
    except StopIteration:
        return False, None


class GmapsAgent:
    def __init__(self) -> None:
        self.agent = Agent(
            name="Google Maps Service Agent",
            model=DeepSeek(
                id=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            ),
            tools=[web_search, search_places],
            tool_call_limit=2,
            add_datetime_to_context=True,
            instructions=[
                "You are a location decision agent specialized in Google Maps.",
                "Answer in the same language used by the user.",
                "Use web search first only for broad discovery or subjective requests.",
                "Examples of broad requests include best places, popular places, "
                "family-friendly places, or places suitable for working.",
                "After web discovery, verify no more than five candidates using "
                "the Google Maps service.",
                "Use Google Maps directly for autocomplete, nearby searches, "
                "addresses, opening status, coordinates, routes, distance, and ETA.",
                "Do not call autocomplete and text search for the same task unless "
                "autocomplete fails to identify the place.",
                "Only request place details after a place has been selected or when "
                "details are required to compare candidates.",
                "Only calculate routes for the final three candidates.",
                "Never invent addresses, ratings, opening hours, distances, or Place IDs.",
                "Clearly state when a result cannot be verified.",
                "Return concise recommendations with the reason each place matches.",
            ],
            markdown=True,
        )

    async def run(
        self,
        message: str,
        *,
        user_id: str,
        session_id: str | None = None,
    ) -> Any:
        return await asyncio.to_thread(
            self.agent.run,
            message,
            user_id=user_id,
            session_id=session_id,
            stream=False,
        )

    async def stream(
        self,
        message: str,
        *,
        user_id: str,
        session_id: str | None = None,
    ) -> AsyncIterator[Any]:
        iterator = await asyncio.to_thread(
            self.agent.run,
            message,
            user_id=user_id,
            session_id=session_id,
            stream=True,
        )

        while True:
            has_item, item = await asyncio.to_thread(_next_stream_item, iterator)
            if not has_item:
                return
            yield item
