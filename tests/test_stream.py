from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from agent import credentials as creds_mod
from agent.service import app

os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest-only")
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", "Z7vQ9X2mP5kA8rT1yU4wS6xL0cV3bN8nM7qR2tW5yZ8=")

client = TestClient(app)


@pytest.fixture(autouse=True)
def init_store(tmp_path):
    db_path = str(tmp_path / "test.db")
    creds_mod.credential_store = None
    creds_mod.init_credential_store(db_path)
    yield
    store = creds_mod.credential_store
    if store is not None:
        store.close()
    creds_mod.credential_store = None


@pytest.fixture
def account_id() -> str:
    store = creds_mod.credential_store
    assert store is not None
    return store.create_account("testuser", "testpass", "testkey")


def _auth_headers() -> dict[str, str]:
    resp = client.post(
        "/auth/login", json={"user_name": "testuser", "password": "testpass", "access_key": "testkey"}
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class _FakeGraph:
    def __init__(self, script: list):
        self._script = script

    def stream(self, inp, config=None, stream_mode=None, **kwargs):  # noqa: ANN001, ANN003
        assert stream_mode == ["messages", "updates"]
        yield from self._script


def test_chat_stream_requires_session(init_store, account_id: str) -> None:
    headers = _auth_headers()
    resp = client.post("/chat/stream", json={"thread_id": "missing", "message": "hi"}, headers=headers)
    assert resp.status_code == 404


def test_chat_stream_sse_sequence(init_store, account_id: str, monkeypatch) -> None:
    from agent import service as svc

    meta_reasoning = {"langgraph_node": "agent", "langgraph_step": 2}
    meta_answer = {"langgraph_node": "agent", "langgraph_step": 4}
    script = [
        ("messages", (AIMessageChunk(content="", additional_kwargs={"reasoning_content": "thi"}), meta_reasoning)),
        ("messages", (AIMessageChunk(content="", additional_kwargs={"reasoning_content": "nking"}), meta_reasoning)),
        ("messages", (AIMessageChunk(content="He"), meta_reasoning)),
        ("messages", (AIMessageChunk(content="llo"), meta_reasoning)),
        (
            "updates",
            {
                "agent": {
                    "messages": [
                        AIMessage(
                            content="",
                            additional_kwargs={"reasoning_content": "thinking"},
                            tool_calls=[
                                {"id": "t1", "name": "get_profile", "args": {}, "type": "tool_call"}
                            ],
                        )
                    ]
                }
            },
        ),
        ("updates", {"tools": {"messages": [ToolMessage(content="{}", tool_call_id="t1")]}}),
        ("messages", (AIMessageChunk(content="Final ans"), meta_answer)),
        ("messages", (AIMessageChunk(content="wer"), meta_answer)),
        ("updates", {"agent": {"messages": [AIMessage(content="Final answer")]}}),
    ]
    monkeypatch.setattr(svc, "build_graph", lambda path: _FakeGraph(script))

    headers = _auth_headers()
    resp = client.post("/sessions", json={"label": "s"}, headers=headers)
    assert resp.status_code == 200
    thread_id = resp.json()["thread_id"]

    with client.stream(
        "POST", "/chat/stream", json={"thread_id": thread_id, "message": "hi"}, headers=headers
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        events = []
        for line in resp.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

    types = [e["type"] for e in events]
    assert types == [
        "start",
        "reasoning_delta",
        "reasoning_delta",
        "text_delta",
        "text_delta",
        "tool_call",
        "tool_result",
        "text_delta",
        "text_delta",
        "done",
    ]
    done = events[-1]
    assert done["response"] == "Final answer"
    assert done["steps"] == [
        {"type": "reasoning", "text": "thinking"},
        {"type": "tool_call", "name": "get_profile", "args": {}, "tool_call_id": "t1"},
        {"type": "tool_result", "tool_call_id": "t1", "name": "get_profile", "result": "{}"},
    ]


def test_chat_stream_survives_graph_error(init_store, account_id: str, monkeypatch) -> None:
    from agent import service as svc

    class _BoomGraph:
        def stream(self, inp, config=None, stream_mode=None, **kwargs):  # noqa: ANN001, ANN003
            yield ("messages", (AIMessageChunk(content="par"), {"langgraph_node": "agent"}))
            raise RuntimeError("boom")

    monkeypatch.setattr(svc, "build_graph", lambda path: _BoomGraph())

    headers = _auth_headers()
    resp = client.post("/sessions", json={"label": "s"}, headers=headers)
    thread_id = resp.json()["thread_id"]

    with client.stream(
        "POST", "/chat/stream", json={"thread_id": thread_id, "message": "hi"}, headers=headers
    ) as resp:
        assert resp.status_code == 200
        events = []
        for line in resp.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

    assert events[-1]["type"] == "error"
