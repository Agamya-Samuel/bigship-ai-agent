import logging
import sqlite3

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent

from agent.config import settings
from agent.tools import ALL_TOOLS

logger = logging.getLogger(__name__)


def _init_sqlite_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


_graph = None


def build_graph(checkpoint_db_path: str):  # type: ignore[no-untyped-def]
    global _graph
    if _graph is not None:
        return _graph

    llm = ChatOpenAI(
        model=settings.llm_model,
        openai_api_base="https://openrouter.ai/api/v1",  # type: ignore
        openai_api_key=settings.openrouter_api_key,
        temperature=0,
    )

    tools = ALL_TOOLS
    agent = create_react_agent(llm, tools)

    conn = _init_sqlite_conn(checkpoint_db_path)
    checkpointer = SqliteSaver(conn)
    agent.checkpointer = checkpointer

    _graph = agent
    logger.info("Agent graph initialized with checkpoint db: %s", checkpoint_db_path)
    return _graph
