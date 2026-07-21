from fastapi import APIRouter
from python.lib.agents import GmapsAgent

agent_api = APIRouter(prefix="/agent", tags=["Agent"])

gmaps_agent = GmapsAgent()

agent_api.routes.extend(gmaps_agent.run())