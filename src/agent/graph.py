import sqlite3

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode, create_react_agent

from agent.config import settings
from agent.tools import ALL_TOOLS


def build_graph(checkpoint_db_path: str):  # type: ignore[no-untyped-def]
    if not settings.llm_model:
        raise RuntimeError(
            "LLM_MODEL is not set. Provide it via the LLM_MODEL env var."
        )

    llm = ChatOpenAI(
        model=settings.llm_model,
        openai_api_base="https://openrouter.ai/api/v1",  # type: ignore
        openai_api_key=settings.openrouter_api_key,
        temperature=0,
        extra_body={"reasoning": {"enabled": True}},  # type: ignore
    )

    tools = ALL_TOOLS
    tool_node = ToolNode(tools, handle_tool_errors=True)
    agent = create_react_agent(llm, tool_node)

    conn = sqlite3.connect(checkpoint_db_path, check_same_thread=False)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    except Exception:  # noqa: BLE001
        pass
    checkpointer = SqliteSaver(conn)
    agent.checkpointer = checkpointer

    return agent
