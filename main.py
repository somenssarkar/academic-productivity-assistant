import os
from dotenv import load_dotenv

load_dotenv("eduflow_agents/.env")

from google.adk.cli.fast_api import get_fast_api_app

# SESSION_DB_URI is optional — if unset, ADK uses in-memory session storage
SESSION_DB_URI = os.environ.get("SESSION_DB_URI")

app = get_fast_api_app(
    agents_dir=".",
    session_service_uri=SESSION_DB_URI,  # None → InMemorySessionService
    allow_origins=["*"],                 # Tighten for production
    web=True,                            # Required: enables /run_sse and /apps/* routes
    auto_create_session=True,            # Auto-create session if not found (avoids 404 on first message)
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
