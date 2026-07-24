from fastapi import APIRouter
from dotenv import load_dotenv

from agno.agent import Agent
from agno.models.deepseek import DeepSeek
from agno.os import AgentOS
    
from fastapi import FastAPI

load_dotenv()

router = APIRouter()

agent = Agent(
    id="copilot",
    model=DeepSeek(id="deepseek-v4-flash"),
    add_history_to_context=True,
    enable_agentic_memory=True,
)

agent_os = AgentOS(
    agents=[agent],
)

router.routes.extend(agent_os.get_routes())
app = agent_os.get_app()



app = FastAPI(
    title="My FastAPI Application",
)

app.include_router(
    router,
    prefix="/copilot",
    tags=["Copilot"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}