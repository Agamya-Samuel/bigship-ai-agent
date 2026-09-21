from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.service import _get_display_history, _strip_orphaned_tool_calls


class _FakeStore:
    pass


def _run(raw: list, *, thread_id: str = "t1", db_path: str = ":memory:") -> list[dict]:
    import agent.service as svc

    orig = svc._get_history
    svc._get_history = lambda *a, **kw: raw
    try:
        return _get_display_history(thread_id, db_path, _FakeStore())
    finally:
        svc._get_history = orig


def test_intermediate_echo_becomes_trace_with_tool_call() -> None:
    raw = [
        HumanMessage(content="my balance"),
        AIMessage(
            content="",
            tool_calls=[{"id": "tc1", "name": "get_profile", "args": {}}],
        ),
        AIMessage(content="{'status': True, 'message': 'User profile fetched successfully.', 'data': {...}}"),
        AIMessage(content="Your current wallet balance is ₹0."),
    ]
    out = _run(raw)
    assert len(out) == 2
    assert out[0]["role"] == "user"
    assert out[0]["content"] == "my balance"
    assert out[1]["role"] == "assistant"
    assert out[1]["content"] == "Your current wallet balance is ₹0."
    assert out[1]["steps"] == [
        {"type": "tool_call", "name": "get_profile", "args": {}, "tool_call_id": "tc1"},
    ]


def test_multi_round_tool_calls_keep_chronological_order() -> None:
    raw = [
        HumanMessage(content="b2c"),
        AIMessage(
            content="I'll first look up the payment modes.",
            tool_calls=[{"id": "tc1", "name": "get_payment_modes", "args": {"segment_type": "domestic_b2c"}}],
        ),
        AIMessage(content="{'status': True, 'message': 'Payment mode retrieved successfully.', 'data': [...]}"),
        AIMessage(
            content="",
            tool_calls=[{"id": "tc2", "name": "get_risk_types", "args": {}}],
        ),
        AIMessage(content="{'status': True, 'message': 'Risk Types Retrieved Successfully!', 'data': [...]}"),
        AIMessage(content="Here are the available payment methods for domestic B2C shipments..."),
    ]
    out = _run(raw)
    assert len(out) == 2
    assert out[1]["role"] == "assistant"
    assert out[1]["content"] == "Here are the available payment methods for domestic B2C shipments..."
    assert out[1]["steps"] == [
        {"type": "reasoning", "text": "I'll first look up the payment modes."},
        {"type": "tool_call", "name": "get_payment_modes", "args": {"segment_type": "domestic_b2c"}, "tool_call_id": "tc1"},
        {"type": "tool_call", "name": "get_risk_types", "args": {}, "tool_call_id": "tc2"},
    ]


def test_pure_text_assistant_message_has_no_steps() -> None:
    raw = [
        HumanMessage(content="hi"),
        AIMessage(content="Hello!"),
    ]
    out = _run(raw)
    assert len(out) == 2
    assert out[1]["content"] == "Hello!"
    assert out[1]["steps"] == []


def test_error_echo_is_filtered_and_retry_kept() -> None:
    raw = [
        HumanMessage(content="calculate rate"),
        AIMessage(
            content="",
            tool_calls=[{"id": "tc1", "name": "calculate_rate", "args": {"a": 1}}],
        ),
        AIMessage(content="Error: COD amount is required for COD payments."),
        AIMessage(content=""),
        AIMessage(
            content="",
            tool_calls=[{"id": "tc2", "name": "calculate_rate", "args": {"a": 2}}],
        ),
        AIMessage(content="{'status': True, 'message': 'All Charges Retrieved Successfully!', 'data': [...]}"),
        AIMessage(content="Here are the shipping rates for your 1 kg box..."),
    ]
    out = _run(raw)
    assert len(out) == 2
    assert out[1]["content"] == "Here are the shipping rates for your 1 kg box..."
    assert out[1]["steps"] == [
        {"type": "tool_call", "name": "calculate_rate", "args": {"a": 1}, "tool_call_id": "tc1"},
        {"type": "tool_call", "name": "calculate_rate", "args": {"a": 2}, "tool_call_id": "tc2"},
    ]


def test_multiple_turns_do_not_leak_steps() -> None:
    raw = [
        HumanMessage(content="one"),
        AIMessage(
            content="",
            tool_calls=[{"id": "tc1", "name": "get_profile", "args": {}}],
        ),
        AIMessage(content="{'status': True, 'data': 1}"),
        AIMessage(content="Answer one."),
        HumanMessage(content="two"),
        AIMessage(content="Answer two."),
    ]
    out = _run(raw)
    assert len(out) == 4
    assert out[1]["content"] == "Answer one."
    assert out[1]["steps"] == [{"type": "tool_call", "name": "get_profile", "args": {}, "tool_call_id": "tc1"}]
    assert out[2] == {"role": "user", "content": "two"}
    assert out[3]["content"] == "Answer two."
    assert out[3]["steps"] == []


def test_intermediate_reasoning_only_turn() -> None:
    raw = [
        HumanMessage(content="plan something"),
        AIMessage(content="Let me think about this..."),
        AIMessage(content="Here is my plan."),
    ]
    out = _run(raw)
    assert len(out) == 2
    assert out[1]["content"] == "Here is my plan."
    assert out[1]["steps"] == [{"type": "reasoning", "text": "Let me think about this..."}]


def test_tool_calls_with_results_are_not_orphaned() -> None:
    class _NoDeleteSaver:
        def delete_thread(self, thread_id: str) -> None:
            raise AssertionError("healthy thread must not be deleted")

    msgs = [
        HumanMessage(content="q"),
        AIMessage(content="", tool_calls=[{"id": "tc1", "name": "get_profile", "args": {}}]),
        ToolMessage(content="{'status': True}", tool_call_id="tc1"),
        AIMessage(content="answer"),
    ]
    out = _strip_orphaned_tool_calls(msgs, _NoDeleteSaver(), "t1")
    assert out == msgs


def test_collect_turn_events_includes_tool_results() -> None:
    import agent.service as svc

    raw = [
        AIMessage(
            content="",
            tool_calls=[{"id": "tc1", "name": "get_profile", "args": {}, "type": "tool_call"}],
        ),
        ToolMessage(content="{'status': True}", tool_call_id="tc1"),
        AIMessage(content="Here is your profile."),
    ]
    events = svc._collect_turn_events(raw)
    assert events == [
        {"type": "tool_call", "tool_call_id": "tc1", "name": "get_profile", "args": {}},
        {"type": "tool_result", "tool_call_id": "tc1", "name": "get_profile", "result": '{\n  "status": true\n}'},
        {"type": "text", "text": "Here is your profile."},
    ]


def test_display_history_includes_tool_results() -> None:
    raw = [
        HumanMessage(content="my balance"),
        AIMessage(
            content="",
            tool_calls=[{"id": "tc1", "name": "get_profile", "args": {}, "type": "tool_call"}],
        ),
        ToolMessage(content="{'status': True, 'data': {'balance': 0}}", tool_call_id="tc1"),
        AIMessage(content="Your current wallet balance is ₹0."),
    ]
    out = _run(raw)
    assert len(out) == 2
    assert out[1]["role"] == "assistant"
    assert out[1]["content"] == "Your current wallet balance is ₹0."
    assert out[1]["steps"] == [
        {"type": "tool_call", "name": "get_profile", "args": {}, "tool_call_id": "tc1"},
        {"type": "tool_result", "tool_call_id": "tc1", "name": "get_profile", "result": '{\n  "status": true,\n  "data": {\n    "balance": 0\n  }\n}'},
    ]


def test_genuinely_orphaned_tool_call_is_dropped() -> None:
    deleted: list[str] = []

    class _FakeSaver:
        def delete_thread(self, thread_id: str) -> None:
            deleted.append(thread_id)

    msgs = [
        HumanMessage(content="q"),
        AIMessage(content="", tool_calls=[{"id": "tc1", "name": "get_profile", "args": {}}]),
        AIMessage(content="never reached"),
    ]
    out = _strip_orphaned_tool_calls(msgs, _FakeSaver(), "t1")
    assert out == msgs[:1]
    assert deleted == ["t1"]

