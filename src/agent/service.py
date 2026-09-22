from __future__ import annotations

import ast
import json
import logging
import sqlite3
import time
import uuid
from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime
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
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import RunnableConfig
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
    steps: list[dict] = []
    model: str | None = None


# ==================== AUTH ====================


@app.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest) -> LoginResponse:
    store = _store()
    account_id = store.verify_login(req.user_name, req.password)
    if account_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return LoginResponse(
        access_token=create_access_token(account_id),
        account_id=str(account_id),
    )


@app.post("/auth/logout")
def logout(account_id: str = Depends(get_current_account)) -> dict[str, str]:
    return {"status": "logged_out", "account_id": account_id}


@app.get("/auth/me", response_model=AccountInfoResponse)
def get_me(account_id: str = Depends(get_current_account)) -> AccountInfoResponse:
    store = _store()
    account = store.get_account(account_id)
    return AccountInfoResponse(account_id=account_id, user_name=account["user_name"])


# ==================== SESSIONS ====================


@app.get("/sessions", response_model=SessionListResponse)
def list_sessions(account_id: str = Depends(get_current_account)) -> SessionListResponse:
    store = _store()
    sessions = store.get_sessions(account_id)
    return SessionListResponse(
        sessions=[
            SessionResponse(
                id=s["id"],
                thread_id=s["thread_id"],
                label=s["label"],
                created_at=s["created_at"],
                last_used_at=s["last_used_at"],
            )
            for s in sessions
        ]
    )


@app.post("/sessions", response_model=SessionResponse)
def create_session(
    req: SessionCreateRequest,
    account_id: str = Depends(get_current_account),
) -> SessionResponse:
    store = _store()
    thread_id = req.thread_id or uuid.uuid4().hex
    store.create_session(account_id, thread_id, req.label or "")
    session = store.get_session(thread_id)
    if session is None:
        raise HTTPException(status_code=500, detail="Failed to create session")
    return SessionResponse(
        id=session["id"],
        thread_id=session["thread_id"],
        label=session["label"],
        created_at=session["created_at"],
        last_used_at=session["last_used_at"],
    )


@app.delete("/sessions/{thread_id}")
def delete_session(
    thread_id: str,
    account_id: str = Depends(get_current_account),
) -> dict[str, str]:
    store = _store()
    session = store.get_session(thread_id)
    if session is None or str(session["account_id"]) != account_id:
        raise HTTPException(status_code=404, detail="Session not found")
    store.delete_session(thread_id)
    try:
        conn = sqlite3.connect(settings.checkpoint_db_path, check_same_thread=False)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            SqliteSaver(conn).delete_thread(thread_id)
        finally:
            conn.close()
    except Exception:  # noqa: BLE001
        pass
    return {"thread_id": thread_id, "status": "ended"}


# ==================== CHAT ====================


def _get_message_timestamp(msg: Any) -> str | int | float | None:
    timestamp = getattr(msg, "timestamp", None)
    if isinstance(timestamp, (int, float, str)):
        return timestamp
    metadata = getattr(msg, "response_metadata", None)
    if isinstance(metadata, dict):
        timestamp = metadata.get("timestamp")
        if isinstance(timestamp, (int, float, str)):
            return timestamp
    return None


def _set_message_timestamp(msg: Any, timestamp: str) -> None:
    if _get_message_timestamp(msg) is not None:
        return
    metadata = getattr(msg, "response_metadata", None)
    if isinstance(metadata, dict):
        metadata["timestamp"] = timestamp
    else:
        setattr(msg, "timestamp", timestamp)


def _message_timestamp_key(msg: Any, occurrence: int) -> tuple[str, str, int]:
    message_id = getattr(msg, "id", None)
    identity = str(message_id) if message_id else _message_text(msg)
    return type(msg).__name__, identity, occurrence


def _attach_checkpoint_timestamps(
    messages: list[Any],
    saver: SqliteSaver,
    thread_id: str,
) -> None:
    config: RunnableConfig = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
    try:
        checkpoints = list(saver.list(config))
    except Exception:  # noqa: BLE001
        return
    checkpoints.sort(key=lambda item: str(item.checkpoint.get("ts", "")))
    timestamps: dict[tuple[str, str, int], str] = {}
    for checkpoint_tuple in checkpoints:
        checkpoint_messages = checkpoint_tuple.checkpoint.get("channel_values", {}).get(
            "messages", []
        )
        occurrences: dict[tuple[str, str], int] = {}
        for message in checkpoint_messages:
            base_key = (
                type(message).__name__,
                str(getattr(message, "id", None)) or _message_text(message),
            )
            occurrence = occurrences.get(base_key, 0)
            occurrences[base_key] = occurrence + 1
            key = _message_timestamp_key(message, occurrence)
            checkpoint_ts = checkpoint_tuple.checkpoint.get("ts")
            if checkpoint_ts:
                timestamps.setdefault(key, str(checkpoint_ts))
    latest_occurrences: dict[tuple[str, str], int] = {}
    for message in messages:
        base_key = (
            type(message).__name__,
            str(getattr(message, "id", None)) or _message_text(message),
        )
        occurrence = latest_occurrences.get(base_key, 0)
        latest_occurrences[base_key] = occurrence + 1
        timestamp = timestamps.get(_message_timestamp_key(message, occurrence))
        if timestamp:
            _set_message_timestamp(message, timestamp)


def _get_history(thread_id: str, db_path: str, store: EncryptedCredentialStore) -> list[Any]:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        saver = SqliteSaver(conn)
        config: RunnableConfig = {
            "configurable": {"thread_id": thread_id, "checkpoint_ns": ""}
        }
        try:
            checkpoint = saver.get(config)
        except Exception:  # noqa: BLE001
            return []
        if not (checkpoint and isinstance(checkpoint.get("channel_values"), dict)):
            return []
        raw = checkpoint["channel_values"].get("messages", [])
        # Orphan detection must run on the full message list (ToolMessages included),
        # otherwise every tool call looks orphaned and the thread gets wiped.
        cleaned = _strip_orphaned_tool_calls(raw, saver, thread_id)
        return [m for m in cleaned if isinstance(m, (AIMessage, HumanMessage, ToolMessage))]
    finally:
        conn.close()


def _get_history_with_timestamps(
    thread_id: str,
    db_path: str,
    store: EncryptedCredentialStore,
) -> list[Any]:
    messages = _get_history(thread_id, db_path, store)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        _attach_checkpoint_timestamps(messages, SqliteSaver(conn), thread_id)
    except Exception:  # noqa: BLE001
        pass
    finally:
        conn.close()
    return messages


def _strip_orphaned_tool_calls(messages: list, saver: SqliteSaver, thread_id: str) -> list:
    tool_call_ids: set[str] = set()
    for msg in messages:
        if isinstance(msg, AIMessage):
            for tc in msg.tool_calls:
                tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                if tc_id:
                    tool_call_ids.add(tc_id)
    tool_result_ids: set[str] = set()
    for msg in messages:
        if isinstance(msg, ToolMessage):
            tool_result_ids.add(msg.tool_call_id)
    orphaned = tool_call_ids - tool_result_ids
    if not orphaned:
        return messages
    drop_index = -1
    for i, msg in enumerate(messages):
        if isinstance(msg, AIMessage):
            for tc in msg.tool_calls:
                tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                if tc_id in orphaned:
                    drop_index = i
                    break
        if drop_index != -1:
            break
    if drop_index == -1:
        return messages
    cleaned = messages[:drop_index]
    # The checkpoint has orphaned tool_calls from a crashed execution.
    # Delete the thread from the checkpointer so langgraph starts fresh
    # with the cleaned history (the credential store session is preserved).
    try:
        saver.delete_thread(thread_id)
    except Exception:  # noqa: BLE001
        logger.warning("Could not delete corrupted thread_id=%s", thread_id)
    return cleaned


def _serialize_tool_calls(msg: AIMessage) -> list[dict]:
    return [
        {
            "tool_call_id": tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", ""),
            "name": tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", ""),
            "args": tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {}),
        }
        for tc in getattr(msg, "tool_calls", [])
    ]


def _collapse_repeated_string(value: str) -> str:
    # Chunk merging concatenates repeated string fields (e.g. OpenRouter sends
    # `model` in every stream chunk, so merged metadata becomes "modelmodel").
    n = len(value)
    for size in range(1, n // 2 + 1):
        if n % size == 0 and value[:size] * (n // size) == value:
            return value[:size]
    return value


def _get_model_from_message(msg: Any) -> str | None:
    metadata = getattr(msg, "response_metadata", None)
    if isinstance(metadata, dict):
        model = metadata.get("model_name") or metadata.get("model_id") or metadata.get("model")
        if isinstance(model, str) and model:
            return _collapse_repeated_string(model)
    return None


def _is_rate_limit_error(exc: Exception) -> bool:
    return getattr(exc, "status_code", None) == 429


def _rate_limit_retry_after(exc: Exception) -> int | None:
    """Best-effort seconds until the OpenRouter rate limit resets.

    Checks the Retry-After header, then x-ratelimit-reset (epoch ms in the
    JSON body metadata or seconds in headers).
    """
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    candidates: list[str] = []
    if headers is not None:
        retry_after = headers.get("retry-after")
        if retry_after:
            try:
                return max(1, int(float(retry_after)))
            except (TypeError, ValueError):
                pass
        reset = headers.get("x-ratelimit-reset")
        if reset:
            candidates.append(str(reset))
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error")
        metadata = error.get("metadata") if isinstance(error, dict) else None
        if isinstance(metadata, dict) and metadata.get("x-ratelimit-reset"):
            candidates.append(str(metadata["x-ratelimit-reset"]))
    for candidate in candidates:
        try:
            value = float(candidate)
        except (TypeError, ValueError):
            continue
        if value > 1e11:  # epoch milliseconds
            seconds = value / 1000 - time.time()
        elif value > 1e9:  # epoch seconds
            seconds = value - time.time()
        else:  # relative seconds
            seconds = value
        if seconds > 0:
            return min(int(seconds) + 1, 86400)
    return None


def _get_turn_metadata(messages: list) -> dict[str, Any]:
    last_ai = None
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            last_ai = msg
            break
    if not last_ai:
        return {}
    metadata = getattr(last_ai, "response_metadata", None)
    result: dict[str, Any] = {}
    if isinstance(metadata, dict):
        model = metadata.get("model_name") or metadata.get("model_id") or metadata.get("model")
        if isinstance(model, str) and model:
            result["model"] = _collapse_repeated_string(model)
        usage = getattr(last_ai, "usage_metadata", None)
        if isinstance(usage, dict):
            tokens = usage.get("output_tokens")
            if isinstance(tokens, int) and tokens > 0:
                result["tokens"] = tokens
        if "tokens" not in result:
            usage = metadata.get("usage")
            if isinstance(usage, dict):
                tokens = usage.get("output_tokens") or usage.get("total_tokens")
                if isinstance(tokens, int) and tokens > 0:
                    result["tokens"] = tokens
    ts = _get_message_timestamp(last_ai)
    if ts is not None:
        result["timestamp"] = ts
    return result


def _is_tool_echo(text: str) -> bool:
    s = text.strip()
    return (
        s.startswith("{'status'")
        or s.startswith('{"status"')
        or s.startswith("Error: ")
    )


def _message_text(msg: Any) -> str:
    content = getattr(msg, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text", "")))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content or "")


def _normalize_tool_result(text: str) -> str:
    if not text or not (text.startswith("{") or text.startswith("[")):
        return text
    try:
        parsed = ast.literal_eval(text)
        return json.dumps(parsed, indent=2)
    except Exception:
        return text


def _reasoning_delta_from_chunk(chunk: Any) -> str:
    extra = getattr(chunk, "additional_kwargs", {}) or {}
    if isinstance(extra, dict):
        rc = extra.get("reasoning_content")
        if isinstance(rc, str) and rc:
            return rc
    content = getattr(chunk, "content", "")
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "reasoning":
                text = block.get("reasoning") or block.get("text") or ""
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""


def _finish_reason(msg: Any) -> str | None:
    metadata = getattr(msg, "response_metadata", None)
    if isinstance(metadata, dict):
        reason = metadata.get("finish_reason")
        if isinstance(reason, str) and reason:
            return reason
    return None


def _answer_was_truncated_by_reasoning(messages: list) -> bool:
    """True if the final AIMessage had no answer text and was cut off mid-run.

    A reasoning model that emits reasoning chunks and then runs out of
    output tokens before producing any answer content ends with
    finish_reason="length" and an empty answer. In that case the service
    layer should retry with reasoning disabled rather than surface a
    truncated or reasoning-leaked response.
    """
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            if getattr(msg, "tool_calls", None):
                return False
            text = _message_text(msg).strip()
            if text:
                return False
            extra = getattr(msg, "additional_kwargs", {}) or {}
            reasoning = extra.get("reasoning_content") if isinstance(extra, dict) else None
            return bool(reasoning) or _finish_reason(msg) == "length"
    return False


def _collect_turn_events(messages: list) -> list[dict]:
    events: list[dict] = []
    tool_call_map: dict[str, str] = {}
    for msg in messages:
        if isinstance(msg, AIMessage):
            extra = getattr(msg, "additional_kwargs", {}) or {}
            reasoning = extra.get("reasoning_content") if isinstance(extra, dict) else None
            if isinstance(reasoning, str) and reasoning.strip():
                events.append({"type": "text", "kind": "reasoning", "text": reasoning.strip()})
            text = _message_text(msg).strip()
            if text and not _is_tool_echo(text):
                # An AIMessage that issues tool_calls but also has a "I'll first..."
                # preface in its content is a reasoning message, not an answer.
                kind = "reasoning" if getattr(msg, "tool_calls", None) else "answer"
                events.append({"type": "text", "kind": kind, "text": text})
            for tc in _serialize_tool_calls(msg):
                tool_call_map[tc["tool_call_id"]] = tc["name"]
                events.append({"type": "tool_call", **tc})
        elif isinstance(msg, ToolMessage):
            tc_id = getattr(msg, "tool_call_id", "")
            name = tool_call_map.get(tc_id, "")
            result_event = {
                "type": "tool_result",
                "tool_call_id": tc_id,
                "name": name,
                "result": _normalize_tool_result(_message_text(msg)),
            }
            insert_idx = len(events)
            for i in range(len(events) - 1, -1, -1):
                if (
                    events[i].get("type") == "tool_call"
                    and events[i].get("tool_call_id") == tc_id
                ):
                    insert_idx = i + 1
                    break
            events.insert(insert_idx, result_event)
    return events


def _finalize_turn(events: list[dict]) -> dict[str, Any]:
    # Pick the LAST answer text as the user-visible content. Reasoning text is
    # always demoted to a step trace, never shown as the final answer, so a
    # reasoning model that emits a "I'll first..." preface before its tool
    # calls (or whose reasoning budget consumes the output limit and leaves
    # no answer) cannot leak that preface into the user-visible response.
    answer_idx = -1
    for i, ev in enumerate(events):
        if ev["type"] == "text" and ev.get("kind") == "answer":
            answer_idx = i
    content = events[answer_idx]["text"] if answer_idx != -1 else ""
    steps: list[dict] = []
    for i, ev in enumerate(events):
        if i == answer_idx:
            continue
        if ev["type"] == "text":
            steps.append({"type": "reasoning", "text": ev["text"]})
        else:
            steps.append(ev)
    return {"content": content, "steps": steps}


def _get_display_history(
    thread_id: str, db_path: str, store: EncryptedCredentialStore
) -> list[dict]:
    raw_messages = _get_history_with_timestamps(thread_id, db_path, store)
    session_model = None
    session_metrics: dict[str, Any] = {}
    try:
        session = store.get_session(thread_id)
        if isinstance(session, dict):
            session_model = session.get("model")
            session_metrics = {
                "tokens": session.get("last_tokens"),
                "tps": session.get("last_tps"),
                "timestamp": session.get("last_timestamp"),
            }
    except Exception:  # noqa: BLE001
        session_model = None

    merged: list[dict] = []
    turn: list = []
    for msg in raw_messages:
        if isinstance(msg, HumanMessage):
            turn_data = _finalize_turn(_collect_turn_events(turn))
            if turn_data["content"] or turn_data["steps"]:
                metadata = _get_turn_metadata(turn)
                merged.append({
                    "role": "assistant",
                    **turn_data,
                    "model": metadata.get("model") or session_model,
                    "tokens": metadata.get("tokens"),
                    "tps": metadata.get("tps"),
                    "timestamp": metadata.get("timestamp"),
                })
            user_timestamp = _get_message_timestamp(msg)
            user_message = {"role": "user", "content": getattr(msg, "content", "") or ""}
            if user_timestamp is not None:
                user_message["timestamp"] = user_timestamp
            merged.append(user_message)
            turn = []
        else:
            turn.append(msg)
    turn_data = _finalize_turn(_collect_turn_events(turn))
    if turn_data["content"] or turn_data["steps"]:
        metadata = _get_turn_metadata(turn)
        merged.append({
            "role": "assistant",
            **turn_data,
            "model": metadata.get("model") or session_model,
            "tokens": metadata.get("tokens") or session_metrics.get("tokens"),
            "tps": metadata.get("tps") or session_metrics.get("tps"),
            "timestamp": metadata.get("timestamp") or session_metrics.get("timestamp"),
        })
    return merged


def _reset_thread_state(thread_id: str, db_path: str) -> None:
    """Drop all langgraph checkpoints for `thread_id` so the next invoke sees
    a fresh state. Used before a retry-with-no-reasoning attempt so the
    retry doesn't replay the partial reasoning-only run as if it were real
    history."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        SqliteSaver(conn).delete_thread(thread_id)
    except Exception:  # noqa: BLE001
        logger.warning("Could not reset thread state for retry thread_id=%s", thread_id)
    finally:
        conn.close()


def _run_agent(  # type: ignore[no-untyped-def]
    graph,
    *,
    config: dict[str, Any],
    history: list,
    user_message: str,
    thread_id: str,
    checkpoint_db_path: str,
):
    """Invoke the agent once; if the final AIMessage has no answer content
    (typically because a reasoning model exhausted its output budget on
    thinking), retry once with reasoning disabled and a reset thread state
    so the user gets a real answer instead of a truncated reasoning leak."""
    try:
        result = graph.invoke(
            {"messages": history + [HumanMessage(content=user_message)]},
            config=config,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent execution failed for thread_id=%s", thread_id)
        if _is_rate_limit_error(exc):
            retry_after = _rate_limit_retry_after(exc)
            headers = {"Retry-After": str(retry_after)} if retry_after else None
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please retry shortly.",
                headers=headers,
            ) from exc
        raise HTTPException(status_code=500, detail="Agent execution failed") from exc

    if not _answer_was_truncated_by_reasoning(result["messages"]):
        return result, history

    logger.info(
        "Retrying agent thread_id=%s with reasoning disabled "
        "(final AIMessage had no answer content)",
        thread_id,
    )
    _reset_thread_state(thread_id, checkpoint_db_path)
    history = []  # the retry should see a clean thread
    retry_graph = build_graph(checkpoint_db_path, disable_reasoning=True)
    try:
        result = retry_graph.invoke(
            {"messages": [HumanMessage(content=user_message)]},
            config=config,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent retry failed for thread_id=%s", thread_id)
        if _is_rate_limit_error(exc):
            retry_after = _rate_limit_retry_after(exc)
            headers = {"Retry-After": str(retry_after)} if retry_after else None
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please retry shortly.",
                headers=headers,
            ) from exc
        raise HTTPException(status_code=500, detail="Agent execution failed") from exc
    return result, history


@app.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    account_id: str = Depends(get_current_account),
) -> ChatResponse:
    store = _store()
    session = store.get_session(req.thread_id)
    if session is None or str(session["account_id"]) != account_id:
        raise HTTPException(
            status_code=404,
            detail=f"No active session for thread_id: {req.thread_id}",
        )
    store.get_or_create_client(req.thread_id)

    history = _get_history(req.thread_id, settings.checkpoint_db_path, store)
    config: dict[str, Any] = {
        "configurable": {"thread_id": req.thread_id, "account_id": account_id},
        "metadata": {"account_id": account_id, "thread_id": req.thread_id},
        "recursion_limit": settings.max_tool_calls + 2,
    }
    graph = build_graph(settings.checkpoint_db_path)
    result, history = _run_agent(
        graph,
        config=config,
        history=history,
        user_message=req.message,
        thread_id=req.thread_id,
        checkpoint_db_path=settings.checkpoint_db_path,
    )

    last_message = result["messages"][-1]
    input_length = len(history) + 1
    turn_data = _finalize_turn(_collect_turn_events(result["messages"][input_length:]))
    # Only fall back to the last AIMessage's raw content if it's a genuine
    # final answer (no tool_calls). Otherwise we'd surface reasoning content
    # as the response when the model's reasoning budget consumed the output
    # limit and no answer text was produced.
    if not turn_data["content"]:
        if isinstance(last_message, AIMessage) and not getattr(last_message, "tool_calls", None):
            turn_data["content"] = _message_text(last_message).strip()
    store._touch_session(req.thread_id)
    response_model = _get_model_from_message(last_message) or settings.llm_model
    try:
        store.update_session_model(req.thread_id, response_model)
    except Exception:  # noqa: BLE001
        pass
    usage = getattr(last_message, "usage_metadata", None)
    tokens = None
    if isinstance(usage, dict):
        output_tokens = usage.get("output_tokens")
        if isinstance(output_tokens, int) and output_tokens > 0:
            tokens = output_tokens
    try:
        store.update_session_metrics(
            req.thread_id,
            tokens=tokens,
            tps=None,
            timestamp=datetime.now(UTC).isoformat(),
        )
    except Exception:  # noqa: BLE001
        pass
    return ChatResponse(response=turn_data["content"], steps=turn_data["steps"], model=response_model)


@app.post("/chat/stream")
def chat_stream(
    req: ChatRequest,
    account_id: str = Depends(get_current_account),
) -> StreamingResponse:
    store = _store()
    session = store.get_session(req.thread_id)
    if session is None or str(session["account_id"]) != account_id:
        raise HTTPException(
            status_code=404,
            detail=f"No active session for thread_id: {req.thread_id}",
        )
    store.get_or_create_client(req.thread_id)
    history = _get_history(req.thread_id, settings.checkpoint_db_path, store)
    graph = build_graph(settings.checkpoint_db_path)
    config: dict[str, Any] = {
        "configurable": {"thread_id": req.thread_id, "account_id": account_id},
        "metadata": {"account_id": account_id, "thread_id": req.thread_id},
        "recursion_limit": settings.max_tool_calls + 2,
    }

    def _sse(event: dict[str, Any]) -> str:
        return f"data: {json.dumps(event)}\n\n"

    def _stream_attempt(  # type: ignore[no-untyped-def]
        attempt_graph, attempt_history
    ) -> Generator[tuple[str, list[AIMessage], int, str | None, list[dict]], None, None]:
        """Run one graph.stream pass; yield (sse_chunk, collected_ais, total_output_tokens, response_model, turn_events) for the outer generator to forward.

        The outer generator can decide whether to retry based on
        collected_ais / total_output_tokens once the inner pass completes.
        """
        turn_events: list[dict] = []
        tool_call_map: dict[str, str] = {}
        collected_ais: list[AIMessage] = []
        total_output_tokens = 0
        response_model: str | None = None
        for mode, payload in attempt_graph.stream(
            {"messages": attempt_history + [HumanMessage(content=req.message)]},
            config=config,
            stream_mode=["messages", "updates"],
        ):
            if mode == "messages":
                chunk, meta = payload
                if not isinstance(chunk, AIMessageChunk):
                    continue
                if not isinstance(meta, dict) or meta.get("langgraph_node") != "agent":
                    continue
                if response_model is None:
                    response_model = _get_model_from_message(chunk)
                usage = getattr(chunk, "usage_metadata", None)
                if isinstance(usage, dict):
                    output_tokens = usage.get("output_tokens")
                    if isinstance(output_tokens, int) and output_tokens > 0:
                        total_output_tokens = output_tokens
                reasoning_delta = _reasoning_delta_from_chunk(chunk)
                if reasoning_delta:
                    turn_events.append(
                        {"type": "text", "kind": "reasoning", "text": reasoning_delta}
                    )
                    yield _sse({"type": "reasoning_delta", "text": reasoning_delta}), collected_ais, total_output_tokens, response_model, turn_events
                text_delta = _message_text(chunk)
                if text_delta:
                    turn_events.append(
                        {"type": "text", "kind": "reasoning", "text": text_delta}
                    )
                    yield _sse({"type": "text_delta", "text": text_delta}), collected_ais, total_output_tokens, response_model, turn_events
            elif mode == "updates":
                if not isinstance(payload, dict):
                    continue
                update = payload.get("agent")
                if isinstance(update, dict):
                    for m in update.get("messages", []):
                        if not isinstance(m, AIMessage):
                            continue
                        collected_ais.append(m)
                        if not m.tool_calls:
                            continue
                        text = _message_text(m).strip()
                        if text and not _is_tool_echo(text):
                            turn_events.append(
                                {"type": "text", "kind": "reasoning", "text": text}
                            )
                            yield _sse({"type": "reasoning", "text": text}), collected_ais, total_output_tokens, response_model, turn_events
                        for tc in _serialize_tool_calls(m):
                            tool_call_map[tc["tool_call_id"]] = tc["name"]
                            turn_events.append({"type": "tool_call", **tc})
                            yield _sse({"type": "tool_call", **tc}), collected_ais, total_output_tokens, response_model, turn_events
                update = payload.get("tools")
                if isinstance(update, dict):
                    for m in update.get("messages", []):
                        if not isinstance(m, ToolMessage):
                            continue
                        collected_ais.append(m)
                        tc_id = getattr(m, "tool_call_id", "")
                        name = tool_call_map.get(tc_id, "")
                        result = _normalize_tool_result(_message_text(m))
                        result_event = {
                            "type": "tool_result",
                            "tool_call_id": tc_id,
                            "name": name,
                            "result": result,
                        }
                        insert_idx = len(turn_events)
                        for i in range(len(turn_events) - 1, -1, -1):
                            if (
                                turn_events[i].get("type") == "tool_call"
                                and turn_events[i].get("tool_call_id") == tc_id
                            ):
                                insert_idx = i + 1
                                break
                        turn_events.insert(insert_idx, result_event)
                        yield _sse(result_event), collected_ais, total_output_tokens, response_model, turn_events
        return

    def generate() -> Generator[str, None, None]:
        start_time = __import__("time").monotonic()
        total_output_tokens = 0
        response_model: str | None = None
        try:
            yield _sse({"type": "start"})
            attempt_graph = graph
            attempt_history = history
            for sse_chunk, collected_ais, attempt_tokens, attempt_model, _ in _stream_attempt(
                attempt_graph, attempt_history
            ):
                total_output_tokens = attempt_tokens or total_output_tokens
                if response_model is None and attempt_model:
                    response_model = attempt_model
                yield sse_chunk

            # First attempt complete. If the run produced no answer content
            # (a reasoning model spent its output budget on thinking), retry
            # once with reasoning disabled.
            truncated = _answer_was_truncated_by_reasoning(collected_ais)
            if truncated:
                logger.info(
                    "Streaming retry thread_id=%s: first attempt had no answer "
                    "content, retrying with reasoning disabled",
                    req.thread_id,
                )
                yield _sse(
                    {
                        "type": "reasoning_truncated",
                        "detail": "Reasoning consumed the output budget; retrying without reasoning.",
                    }
                )
                _reset_thread_state(req.thread_id, settings.checkpoint_db_path)
                retry_graph = build_graph(settings.checkpoint_db_path, disable_reasoning=True)
                total_output_tokens = 0
                response_model = None
                yield _sse({"type": "retry_start"})
                for sse_chunk, collected_ais, attempt_tokens, attempt_model, _ in _stream_attempt(
                    retry_graph, []
                ):
                    total_output_tokens = attempt_tokens or total_output_tokens
                    if response_model is None and attempt_model:
                        response_model = attempt_model
                    yield sse_chunk

            turn_data = _finalize_turn(_collect_turn_events(collected_ais))
            if not turn_data["content"] and collected_ais:
                last = collected_ais[-1]
                if isinstance(last, AIMessage) and not getattr(last, "tool_calls", None):
                    fallback = _message_text(last).strip()
                    if fallback and not _is_tool_echo(fallback):
                        turn_data["content"] = fallback
            store._touch_session(req.thread_id)
            elapsed = max(__import__("time").monotonic() - start_time, 0.001)
            tps = round(total_output_tokens / elapsed, 2) if total_output_tokens > 0 else None
            if response_model:
                try:
                    store.update_session_model(req.thread_id, response_model)
                except Exception:  # noqa: BLE001
                    pass
            try:
                store.update_session_metrics(
                    req.thread_id,
                    tokens=total_output_tokens or None,
                    tps=tps,
                    timestamp=__import__("datetime").datetime.now(UTC).isoformat(),
                )
            except Exception:  # noqa: BLE001
                pass
            yield _sse(
                {
                    "type": "done",
                    "response": turn_data["content"],
                    "steps": turn_data["steps"],
                    "tokens": total_output_tokens or None,
                    "tps": tps,
                    "model": response_model,
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Streaming chat failed for thread_id=%s", req.thread_id)
            if _is_rate_limit_error(exc):
                yield _sse(
                    {
                        "type": "error",
                        "detail": "Rate limit exceeded",
                        "error_type": "rate_limited",
                        "retry_after": _rate_limit_retry_after(exc),
                    }
                )
            else:
                yield _sse({"type": "error", "detail": "Agent execution failed"})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/chat/history/{thread_id}")
def chat_history(
    thread_id: str,
    account_id: str = Depends(get_current_account),
) -> dict[str, Any]:
    store = _store()
    session = store.get_session(thread_id)
    if session is None or str(session["account_id"]) != account_id:
        raise HTTPException(
            status_code=404,
            detail=f"No active session for thread_id: {thread_id}",
        )

    try:
        messages = _get_display_history(thread_id, settings.checkpoint_db_path, store)
        return {"messages": messages}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to load chat history for thread_id=%s", thread_id)
        raise HTTPException(status_code=500, detail="Failed to load chat history") from exc


# ==================== DASHBOARD API ====================


@app.get("/api/profile")
def api_profile(account_id: str = Depends(get_current_account)) -> dict[str, Any]:
    with _account_client(account_id) as client:
        return _call(client, "get_profile")


@app.get("/api/warehouses")
def api_warehouses(
    page: str = "1",
    per_page: str = "20",
    segment_type: str = "hyperlocal",
    status: str | None = None,
    account_id: str = Depends(get_current_account),
) -> dict[str, Any]:
    params = WarehouseListRequest(
        page=page,
        perPage=per_page,
        segment_type=segment_type,
        status=status,
    )
    with _account_client(account_id) as client:
        return _call(client, "get_warehouse_list", params)


@app.post("/api/warehouses")
def api_create_warehouse(
    payload: SaveWarehouseRequest,
    account_id: str = Depends(get_current_account),
) -> dict[str, Any]:
    with _account_client(account_id) as client:
        return _call(client, "save_warehouse", payload)


@app.put("/api/warehouses/{warehouse_id}")
def api_update_warehouse(
    warehouse_id: str,
    payload: dict[str, Any],
    account_id: str = Depends(get_current_account),
) -> dict[str, Any]:
    model = UpdateWarehouseRequest(**{"warehouseId": warehouse_id, **payload})
    with _account_client(account_id) as client:
        return _call(client, "update_warehouse", model)


@app.get("/api/orders")
def api_orders(
    page: str = "1",
    per_page: str = "20",
    from_date: str | None = None,
    to_date: str | None = None,
    status: str | None = None,
    account_id: str = Depends(get_current_account),
) -> dict[str, Any]:
    raise HTTPException(
        status_code=501,
        detail="Order listing is not supported by the Bigship SDK",
    )


@app.get("/api/orders/{order_id}")
def api_order_detail(
    order_id: str,
    account_id: str = Depends(get_current_account),
) -> dict[str, Any]:
    with _account_client(account_id) as client:
        return _call(client, "get_order_detail", order_id)


@app.post("/api/orders/{order_id}/cancel")
def api_cancel_order(
    order_id: str,
    account_id: str = Depends(get_current_account),
) -> dict[str, Any]:
    with _account_client(account_id) as client:
        return _call(client, "cancel_order", order_id)


@app.get("/api/orders/{order_id}/track")
def api_track_order(
    order_id: str,
    account_id: str = Depends(get_current_account),
) -> dict[str, Any]:
    with _account_client(account_id) as client:
        return _call(client, "track_order", order_id)


@app.get("/api/orders/{order_id}/documents")
def api_list_documents(
    order_id: str,
    account_id: str = Depends(get_current_account),
) -> dict[str, Any]:
    return {"order_id": order_id, "document_types": DOCUMENT_TYPES}


@app.get("/api/orders/{order_id}/documents/{doc_type}")
def api_download_document(
    order_id: str,
    doc_type: str,
    account_id: str = Depends(get_current_account),
) -> dict[str, Any]:
    if doc_type not in DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"document_type must be one of {DOCUMENT_TYPES}",
        )
    with _account_client(account_id) as client:
        return _call(client, "download_document", order_id, doc_type)


@app.get("/api/rate-calculator/payment-modes")
def api_payment_modes(
    segment_type: str,
    account_id: str = Depends(get_current_account),
) -> dict[str, Any]:
    with _account_client(account_id) as client:
        return _call(client, "get_payment_modes", segment_type)


@app.get("/api/rate-calculator/package-types")
def api_package_types(
    account_id: str = Depends(get_current_account),
) -> dict[str, Any]:
    with _account_client(account_id) as client:
        return _call(client, "get_package_types")


@app.post("/api/rate-calculator/calculate")
def api_calculate_rate(
    payload: RateCalculatorRequest,
    account_id: str = Depends(get_current_account),
) -> dict[str, Any]:
    with _account_client(account_id) as client:
        return _call(client, "calculate_rate", payload)


@app.get("/api/serviceable-couriers/{order_id}")
def api_serviceable_couriers(
    order_id: str,
    account_id: str = Depends(get_current_account),
) -> dict[str, Any]:
    with _account_client(account_id) as client:
        return _call(client, "get_serviceable_couriers", order_id)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@app.exception_handler(404)
def not_found(request: Request, exc: Exception):
    if _frontend_dist.is_dir() and request.method == "GET":
        return FileResponse(str(_frontend_dist / "index.html"))
    return JSONResponse(status_code=404, content={"detail": "Not found"})


if _frontend_dist.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=str(_frontend_dist), html=True),
        name="static",
    )
