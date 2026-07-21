

import os

from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.deepseek import DeepSeek
from tavily import TavilyClient
from python.lib.gmaps import GoogleMapsService
from agno.os import AgentOS
import asyncio

load_dotenv()

def web_search(query: str) -> dict:
    """
    Perform a web search using the Tavily API.(Query must use same language as the user input)
    """
    client = TavilyClient()
    response = client.search(
        query=query,
        search_depth="advanced",
        max_results=20
    )
    return response


def search_places(
    query: str
) -> dict:
    """
    Search for multiple place candidates using a natural-language query.(Query must use same language as the user input)

    Use this tool for requests such as:
    - coffee shops near an airport
    - hospitals in Pontianak
    - restaurants suitable for meetings

    Do not use this tool when a specific Place ID is already available.
    Do not call this tool repeatedly after valid candidates are returned.
    """
    maps_service = GoogleMapsService()
    result = asyncio.run(maps_service.text_search(query, max_result_count=10))
    return result


class GmapsAgent:
    def __init__(self):
        self.gmaps_agent = Agent(
            name="Google Maps Service Agent",
            model=DeepSeek(
                id=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            ),
            tools=[
                web_search,
                search_places
            ],
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
        
    def run(self):
        self.agent_os = AgentOS(agents=[self.gmaps_agent])
        return self.agent_os.get_routes()
        
        

# if __name__ == "__main__":
#     gmaps_agent.print_response(
#         "",
#         stream=True
#     )
    