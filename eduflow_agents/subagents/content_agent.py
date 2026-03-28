from google.adk.agents import LlmAgent

from ..prompts.content_agent_prompt import CONTENT_AGENT_INSTRUCTION
from ..tools.youtube_search import youtube_search

MODEL = "gemini-2.5-flash"

content_agent = LlmAgent(
    name="content_agent",
    model=MODEL,
    instruction=CONTENT_AGENT_INSTRUCTION,
    tools=[youtube_search],
    description=(
        "Finds YouTube educational videos for each study session topic "
        "and generates session summaries."
    ),
    output_key="session_video_url",
)
