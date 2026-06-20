from __future__ import annotations

from contextlib import ExitStack

from langchain.agents.middleware.summarization import SummarizationMiddleware
from langgraph.checkpoint.sqlite import SqliteSaver

from app.agents.chef.models import chat_model
from app.config import CHECKPOINT_DB_PATH

_checkpoint_stack = ExitStack()
CHECKPOINT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
checkpointer = _checkpoint_stack.enter_context(
    SqliteSaver.from_conn_string(str(CHECKPOINT_DB_PATH))
)
checkpointer.setup()

summarization_middleware = SummarizationMiddleware(
    model=chat_model,
    trigger=("messages", 10),
    keep=("tokens", 3000),
)
