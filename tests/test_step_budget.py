"""Regression tests for the agent step budget and the empty-answer fallback.

The production incident: a rate-quote request needed 4 sequential tool calls
(get_payment_modes, get_package_types, get_risk_types, calculate_rate) but
recursion_limit was max_tool_calls + 2 = 12. Each tool round costs 3 graph
tasks (agent, tools, pre_model_hook) plus an initial hook and the final
answer task, so the 4th round hit langgraph's "Sorry, need more steps" guard
and the user saw no answer at all.
"""
from __future__ import annotations

import os
from typing import Any

import pytest

os.environ.setdefault("LLM_MODEL", "test-model")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest-only")
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", "Z7vQ9X2mP5kA8rT1yU4wS6xL0cV3bN8nM7qR2tW5yZ8=")

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from agent import credentials as creds_mod
from agent import graph as graph_mod
from agent import service as svc


@pytest.fixture(autouse=True)
def init_store(tmp_path):
    db_path = str(tmp_path / "creds.db")
    creds_mod.credential_store = None
    creds_mod.init_credential_store(db_path)
    yield
    store = creds_mod.credential_store
    if store is not None:
        store.close()
    creds_mod.credential_store = None


class _MainFake(BaseChatModel):
    responses: list

    def bind_tools(self, tools: Any, **kwargs: Any) -> "_MainFake":
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        if not self.responses:
            raise AssertionError("fake LLM ran out of responses")
        return ChatResult(generations=[ChatGeneration(message=self.responses.pop(0))])

    @property
    def _llm_type(self) -> str:
        return "fake-main"


class _ClassifierFake(BaseChatModel):
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="ON_TOPIC"))])

    @property
    def _llm_type(self) -> str:
        return "fake-classifier"


def _install_fake_llm(monkeypatch: Any, n_rounds: int) -> None:
    responses = [
        AIMessage(
            content="",
            tool_calls=[{"name": f"tool_{i}", "args": {}, "id": f"tc{i}", "type": "tool_call"}],
        )
        for i in range(n_rounds)
    ]
    responses.append(AIMessage(content="Here are your rates."))

    def factory(**kwargs: Any) -> BaseChatModel:
        if "extra_body" not in kwargs:
            return _ClassifierFake()
        return _MainFake(responses=list(responses))

    monkeypatch.setattr(graph_mod, "ChatOpenAI", factory)


def _invoke_with_service_budget(monkeypatch: Any, n_rounds: int, tmp_path: Any) -> str:
    _install_fake_llm(monkeypatch, n_rounds)
    agent = graph_mod.build_graph(str(tmp_path / "cp.db"))
    result = agent.invoke(
        {"messages": [HumanMessage(content="calculate shipping rates")]},
        config={
            "configurable": {"thread_id": f"t-{n_rounds}"},
            "recursion_limit": svc._recursion_limit(),
        },
    )
    return str(result["messages"][-1].content)


def test_recursion_limit_fits_four_sequential_tool_rounds(
    monkeypatch: Any, tmp_path: Any
) -> None:
    # The exact shape of the reported failure: 4 sequential tool calls.
    content = _invoke_with_service_budget(monkeypatch, 4, tmp_path)
    assert content == "Here are your rates."


def test_recursion_limit_fits_max_tool_rounds(monkeypatch: Any, tmp_path: Any) -> None:
    content = _invoke_with_service_budget(monkeypatch, 10, tmp_path)
    assert content == "Here are your rates."


def test_over_budget_rounds_degrade_gracefully(monkeypatch: Any, tmp_path: Any) -> None:
    # One round over max_tool_calls must not crash with GraphRecursionError;
    # langgraph's guard replaces the response with its step message.
    content = _invoke_with_service_budget(monkeypatch, 11, tmp_path)
    assert content == "Sorry, need more steps to process this request."


def test_recursion_limit_formula() -> None:
    assert svc._recursion_limit() == svc.settings.max_tool_calls * 3 + 3


def test_chat_never_returns_empty_response(
    monkeypatch: Any, tmp_path: Any
) -> None:
    """Even when both the first attempt and the retry produce no answer text
    (reasoning-truncated model), /chat must return the fallback message."""
    monkeypatch.setattr(svc.settings, "checkpoint_db_path", str(tmp_path / "cp.db"))
    empty_truncated = AIMessage(
        content="",
        additional_kwargs={"reasoning_content": "thinking..."},
        response_metadata={"finish_reason": "length"},
    )
    empty_retry = AIMessage(content="", response_metadata={"finish_reason": "stop"})
    graphs = iter([
        type("G", (), {"invoke": lambda self, inp, config=None: {
            "messages": inp["messages"] + [empty_truncated]
        }})(),
        type("G", (), {"invoke": lambda self, inp, config=None: {
            "messages": inp["messages"] + [empty_retry]
        }})(),
    ])
    monkeypatch.setattr(svc, "build_graph", lambda path, **kw: next(graphs))

    store = svc._store()
    account_id = store.create_account("budgetuser", "pw", "key")
    store.create_session(str(account_id), "t-fallback", "")
    from agent.auth import create_access_token
    from fastapi.testclient import TestClient

    client = TestClient(svc.app)
    resp = client.post(
        "/chat",
        json={"thread_id": "t-fallback", "message": "rates"},
        headers={"Authorization": f"Bearer {create_access_token(str(account_id))}"},
    )
    assert resp.status_code == 200
    assert resp.json()["response"] == svc.NO_ANSWER_FALLBACK


def test_chat_stream_never_ends_with_empty_response(
    monkeypatch: Any, tmp_path: Any
) -> None:
    """Streaming variant: first attempt truncated, retry also empty -> the
    done event must carry the fallback text, never an empty string."""
    monkeypatch.setattr(svc.settings, "checkpoint_db_path", str(tmp_path / "cp.db"))
    from fastapi.testclient import TestClient
    from langchain_core.messages import AIMessageChunk, ToolMessage

    meta = {"langgraph_node": "agent", "langgraph_step": 2}
    first_script = [
        (
            "updates",
            {
                "agent": {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {"id": "t1", "name": "calculate_rate", "args": {}, "type": "tool_call"}
                            ],
                        )
                    ]
                }
            },
        ),
        ("updates", {"tools": {"messages": [ToolMessage(content="{}", tool_call_id="t1")]}}),
        # Final answer attempt: empty content, reasoning burned the budget.
        (
            "updates",
            {
                "agent": {
                    "messages": [
                        AIMessage(
                            content="",
                            additional_kwargs={"reasoning_content": "thinking..."},
                            response_metadata={"finish_reason": "length"},
                        )
                    ]
                }
            },
        ),
    ]
    retry_script = [
        ("messages", (AIMessageChunk(content="", additional_kwargs={"reasoning_content": "hmm"}), meta)),
        ("updates", {"agent": {"messages": [AIMessage(content="")]}}),
    ]
    graphs = iter([_ScriptedGraph(first_script), _ScriptedGraph(retry_script)])
    monkeypatch.setattr(svc, "build_graph", lambda path, **kw: next(graphs))

    store = svc._store()
    account_id = store.create_account("streamuser", "pw", "key")
    store.create_session(str(account_id), "t-stream-fallback", "")
    from agent.auth import create_access_token

    client = TestClient(svc.app)
    with client.stream(
        "POST",
        "/chat/stream",
        json={"thread_id": "t-stream-fallback", "message": "rates"},
        headers={"Authorization": f"Bearer {create_access_token(str(account_id))}"},
    ) as resp:
        import json

        events = []
        for line in resp.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

    done = events[-1]
    assert done["type"] == "done"
    assert done["response"] == svc.NO_ANSWER_FALLBACK


class _ScriptedGraph:
    def __init__(self, script: list):
        self._script = script

    def stream(self, inp, config=None, stream_mode=None, **kwargs):  # noqa: ANN001, ANN003
        yield from self._script
