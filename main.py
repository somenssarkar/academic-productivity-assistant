import os
from dotenv import load_dotenv

load_dotenv("eduflow_agents/.env")

from google.adk.cli.fast_api import get_fast_api_app
from google.adk.sessions import DatabaseSessionService

# ---------------------------------------------------------------------------
# Session service (AlloyDB via asyncpg)
# ---------------------------------------------------------------------------

SESSION_DB_URI = os.environ["SESSION_DB_URI"]

session_service = DatabaseSessionService(db_url=SESSION_DB_URI)

# ---------------------------------------------------------------------------
# FastAPI app (ADK-managed routes: /run, /run_sse, /apps, etc.)
# ---------------------------------------------------------------------------

app = get_fast_api_app(
    agent_dir="eduflow_agents",
    session_service=session_service,
    allow_origins=["*"],  # Tighten for production
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
