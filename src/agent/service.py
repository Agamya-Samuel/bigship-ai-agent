from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from agent.config import settings
from agent.credentials import (
    SessionNotFoundError,
    get_credential_store,
    init_credential_store,
)
from agent.graph import build_graph

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_credential_store(settings.checkpoint_db_path)
    store = get_credential_store()
    store.cleanup_stale_clients()
    task = asyncio.create_task(_periodic_cleanup(store))
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def _periodic_cleanup(store: Any, interval_seconds: int = 300) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        store.cleanup_stale_clients()


app = FastAPI(title="Bigship AI Agent", version="0.1.0", lifespan=lifespan)

API_KEY_HEADER = APIKeyHeader(name="X-Service-Api-Key", auto_error=False)


def verify_service_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    expected = getattr(settings, "agent_service_api_key", None)
    if expected is not None and api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid service API key")
    return api_key


class AccountSessionCreateRequest(BaseModel):
    thread_id: str
    user_name: str
    password: str
    access_key: str


class SessionEndRequest(BaseModel):
    thread_id: str


class ChatRequest(BaseModel):
    thread_id: str
    message: str


class ChatResponse(BaseModel):
    response: str


@app.post("/account/session")
def create_account_session(
    req: AccountSessionCreateRequest,
    _: str = Depends(verify_service_key),
) -> dict[str, str]:
    store = get_credential_store()
    store.create_session(req.thread_id, req.user_name, req.password, req.access_key)
    return {"thread_id": req.thread_id, "status": "created"}


@app.post("/session/end")
def end_session(
    req: SessionEndRequest,
    _: str = Depends(verify_service_key),
) -> dict[str, str]:
    store = get_credential_store()
    store.delete_session(req.thread_id)
    return {"thread_id": req.thread_id, "status": "ended"}


@app.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    _: str = Depends(verify_service_key),
) -> ChatResponse:
    store = get_credential_store()
    try:
        store.get_or_create_client(req.thread_id)
    except SessionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No active session for thread_id: {req.thread_id}",
        )

    graph = build_graph(settings.checkpoint_db_path)

    config = {
        "thread_id": req.thread_id,
        "metadata": {"thread_id": req.thread_id},
        "recursion_limit": settings.max_tool_calls + 2,
    }

    try:
        result = graph.invoke(
            {"messages": [HumanMessage(content=req.message)]},
            config=config,
        )
    except Exception as exc:
        logger.exception("Agent execution failed for thread_id=%s", req.thread_id)
        raise HTTPException(status_code=500, detail="Agent execution failed") from exc

    last_message = result["messages"][-1]
    response_text = getattr(last_message, "content", str(last_message))
    return ChatResponse(response=response_text)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
