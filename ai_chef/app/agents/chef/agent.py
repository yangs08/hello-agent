from __future__ import annotations

from langchain.agents import create_agent

from app.agents.chef.memory import checkpointer, summarization_middleware
from app.agents.chef.models import chat_model
from app.agents.chef.prompts import CHEF_SYSTEM_PROMPT
from app.agents.chef.tools import analyze_image, web_search

chef_agent = create_agent(
    model=chat_model,
    tools=[web_search,analyze_image],
    system_prompt=CHEF_SYSTEM_PROMPT,
    # middleware=[summarization_middleware],
    # checkpointer=checkpointer,
)
