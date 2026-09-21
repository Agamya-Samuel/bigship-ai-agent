from __future__ import annotations

import ast
import json
import logging
import sqlite3
import uuid
from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any

from bigship_sdk import BigshipClient
from bigship_sdk.errors import BigshipAuthError, BigshipError, BigshipNetworkError
from bigship_sdk.models import (
    RateCalculatorRequest,
    SaveWarehouseRequest,
    UpdateWarehouseRequest,
    WarehouseListRequest,
)
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from pydantic import BaseModel

from agent.auth import create_access_token, get_current_account
from agent.config import settings
from agent.credentials import (
    EncryptedCredentialStore,
    get_credential_store,
    init_credential_store,
)
from agent.graph import build_graph

logger = logging.getLogger(__name__)

DOCUMENT_TYPES = ["invoice", "label", "ewaybill", "manifest"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_credential_store(settings.checkpoint_db_path)
    yield


app = FastAPI(title="Bigship AI Agent", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _store() -> EncryptedCredentialStore:
    return get_credential_store()


def _default_thread_id(store: EncryptedCredentialStore, account_id: str) -> str:
    sessions = store.get_sessions(account_id)
    if sessions:
        return str(sessions[0]["thread_id"])
    thread_id = uuid.uuid4().hex
    store.create_session(account_id, thread_id, "Default")
    return thread_id


@contextmanager
def _account_client(account_id: str) -> Generator[BigshipClient, None, None]:
    store = _store()
    thread_id = _default_thread_id(store, account_id)
    yield store.get_or_create_client(thread_id)


def _call(client: BigshipClient, method: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
    try:
        resp = getattr(client, method)(*args, **kwargs)
    except BigshipAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Bigship authentication failed: {exc.message}",
        ) from exc
    except BigshipNetworkError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Bigship network error: {exc.message}",
        ) from exc
    except BigshipError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Bigship API error: {exc.message}",
        ) from exc
    return _format_result(resp)


def _format_result(resp: Any) -> dict[str, Any]:
    data: Any = getattr(resp, "data", None)
    message: Any = getattr(resp, "message", None)
    if data is not None and hasattr(data, "model_dump"):
        data = data.model_dump(mode="json", exclude_none=True)
    if not getattr(resp, "status", True):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(message or "Bigship API returned an error"),
        )
    return {"data": data, "message": message}


# ==================== MODELS ====================


class LoginRequest(BaseModel):
    user_name: str
    password: str
    access_key: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    account_id: str


class AccountInfoResponse(BaseModel):
    account_id: str
    user_name: str


class SessionCreateRequest(BaseModel):
    thread_id: str | None = None
    label: str | None = None


class SessionResponse(BaseModel):
    id: str
    thread_id: str
    label: str
    created_at: str
    last_used_at: str


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]


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
