from __future__ import annotations

import os
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from agent import graph as graph_mod

os.environ.setdefault("LLM_MODEL", "test-model")

MODEL_CALLS: list[list[BaseMessage]] = []


class _MainFake(BaseChatModel):
    responses: list

    def bind_tools(self, tools: Any, **kwargs: Any) -> _MainFake:
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        MODEL_CALLS.append(list(messages))
        response = self.responses.pop(0)
        return ChatResult(generations=[ChatGeneration(message=response)])

    @property
    def _llm_type(self) -> str:
        return "fake-main"


class _ClassifierFake(BaseChatModel):
    verdicts: list[str]
    fail: bool = False

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self.fail:
            raise RuntimeError("classifier unavailable")
        verdict = self.verdicts.pop(0) if len(self.verdicts) > 1 else self.verdicts[0]
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=verdict))])

    @property
    def _llm_type(self) -> str:
        return "fake-classifier"


def _make_factory(
    monkeypatch: Any,
    responses: list[AIMessage],
    *,
    verdicts: list[str] | None = None,
    fail: bool = False,
) -> dict[str, int]:
    MODEL_CALLS.clear()
    calls = {"classifier": 0}

    def factory(**kwargs: Any) -> BaseChatModel:
        if "extra_body" not in kwargs:
            calls["classifier"] += 1
            return _ClassifierFake(verdicts=list(verdicts or ["ON_TOPIC"]), fail=fail)
        return _MainFake(responses=list(responses))

    monkeypatch.setattr(graph_mod, "ChatOpenAI", factory)
    return calls


def _invoke(agent: Any, message: str, thread_id: str) -> dict[str, Any]:
    return agent.invoke(
        {"messages": [HumanMessage(content=message)]},
        config={"configurable": {"thread_id": thread_id}},
    )


def test_off_topic_replaced_with_guardrail(monkeypatch: Any, tmp_path: Any) -> None:
    _make_factory(monkeypatch, [AIMessage(content="declined")], verdicts=["OFF_TOPIC"])
    agent = graph_mod.build_graph(str(tmp_path / "cp.db"))

    result = _invoke(agent, "2+5", "t-off")

    assert len(MODEL_CALLS) == 1
    joined = " ".join(str(m.content) for m in MODEL_CALLS[0])
    assert "Scope guardrail" in joined
    assert "2+5" not in joined
    assert result["messages"][0].content == "2+5"
    assert result["messages"][-1].content == "declined"


def test_on_topic_passes_through(monkeypatch: Any, tmp_path: Any) -> None:
    _make_factory(monkeypatch, [AIMessage(content="ok")], verdicts=["ON_TOPIC"])
    agent = graph_mod.build_graph(str(tmp_path / "cp.db"))

    _invoke(agent, "track my order", "t-on")

    assert len(MODEL_CALLS) == 1
    assert MODEL_CALLS[0][-1].content == "track my order"
    assert all("Scope guardrail" not in str(m.content) for m in MODEL_CALLS[0])


def test_tool_loop_skips_classifier(monkeypatch: Any, tmp_path: Any) -> None:
    tool_call = {"name": "no_such_tool", "args": {}, "id": "t1", "type": "tool_call"}
    responses = [AIMessage(content="", tool_calls=[tool_call]), AIMessage(content="done")]
    calls = _make_factory(monkeypatch, responses, verdicts=["ON_TOPIC"])
    agent = graph_mod.build_graph(str(tmp_path / "cp.db"))

    _invoke(agent, "where is my order", "t-loop")

    assert calls["classifier"] == 1
    assert len(MODEL_CALLS) == 2
    assert isinstance(MODEL_CALLS[1][-1], ToolMessage)


def test_classifier_failure_fails_open(monkeypatch: Any, tmp_path: Any) -> None:
    _make_factory(
        monkeypatch, [AIMessage(content="ok")], verdicts=["OFF_TOPIC"], fail=True
    )
    agent = graph_mod.build_graph(str(tmp_path / "cp.db"))

    _invoke(agent, "2+5", "t-fail")

    assert len(MODEL_CALLS) == 1
    assert MODEL_CALLS[0][-1].content == "2+5"


def test_second_turn_after_off_topic_sees_real_conversation(
    monkeypatch: Any, tmp_path: Any
) -> None:
    MODEL_CALLS.clear()
    calls = {"classifier": 0}
    responses = [
        AIMessage(content="declined"),
        AIMessage(
            content="",
            tool_calls=[{"name": "no_such_tool", "args": {}, "id": "t1", "type": "tool_call"}],
        ),
        AIMessage(content="order answer"),
    ]

    def factory(**kwargs: Any) -> BaseChatModel:
        if "extra_body" not in kwargs:
            calls["classifier"] += 1
            return _ClassifierFake(verdicts=["OFF_TOPIC", "ON_TOPIC"])
        return _MainFake(responses=list(responses))

    monkeypatch.setattr(graph_mod, "ChatOpenAI", factory)
    agent = graph_mod.build_graph(str(tmp_path / "cp.db"))
    cfg: dict[str, Any] = {"configurable": {"thread_id": "t-multi"}}

    agent.invoke({"messages": [HumanMessage(content="2+5")]}, config=cfg)
    agent.invoke({"messages": [HumanMessage(content="track my order")]}, config=cfg)

    turn2_first = " ".join(str(m.content) for m in MODEL_CALLS[1])
    assert "track my order" in turn2_first
    turn2_second = MODEL_CALLS[2]
    assert isinstance(turn2_second[-1], ToolMessage)
