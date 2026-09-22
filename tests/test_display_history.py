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
        {"type": "text", "kind": "answer", "text": "Here is your profile."},
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


def test_collect_turn_events_tags_tool_calling_text_as_reasoning() -> None:
    """An AIMessage that emits a preface ("I'll first...") AND a tool_call
    must be tagged kind=reasoning so _finalize_turn never surfaces the
    preface as the user-visible answer."""
    import agent.service as svc

    raw = [
        AIMessage(
            content="I'll first retrieve the available payment modes.",
            tool_calls=[{"id": "tc1", "name": "get_payment_modes", "args": {"segment_type": "domestic_b2c"}, "type": "tool_call"}],
        ),
    ]
    events = svc._collect_turn_events(raw)
    text_events = [e for e in events if e["type"] == "text"]
    assert len(text_events) == 1
    assert text_events[0]["kind"] == "reasoning"
    assert text_events[0]["text"] == "I'll first retrieve the available payment modes."


def test_finalize_turn_picks_last_answer_not_last_reasoning() -> None:
    """The bug: model emits a preface before tool calls and then never
    produces answer content. _finalize_turn must return empty content
    instead of leaking the preface."""
    from agent.service import _collect_turn_events, _finalize_turn

    raw = [
        AIMessage(
            content="I'll first retrieve the available domestic B2C payment modes.",
            tool_calls=[{"id": "tc1", "name": "get_payment_modes", "args": {"segment_type": "domestic_b2c"}, "type": "tool_call"}],
        ),
        AIMessage(
            content="",
            tool_calls=[{"id": "tc2", "name": "get_risk_types", "args": {}, "type": "tool_call"}],
        ),
        AIMessage(
            content="",
            tool_calls=[{"id": "tc3", "name": "calculate_rate", "args": {}, "type": "tool_call"}],
        ),
        # Final answer AIMessage: empty content (truncated by reasoning).
        AIMessage(content="", response_metadata={"finish_reason": "length"}),
    ]
    turn_data = _finalize_turn(_collect_turn_events(raw))
    assert turn_data["content"] == ""
    # Reasoning text must be preserved as a step (so users still see what
    # the agent was thinking), not promoted to the answer.
    reasoning_steps = [s for s in turn_data["steps"] if s.get("type") == "reasoning"]
    assert len(reasoning_steps) == 1
    assert "I'll first retrieve" in reasoning_steps[0]["text"]


def test_answer_was_truncated_by_reasoning_detects_finish_reason_length() -> None:
    """The detection helper must fire when the final AIMessage has empty
    content and finish_reason=length (the failure mode)."""
    from agent.service import _answer_was_truncated_by_reasoning

    msgs = [
        HumanMessage(content="calc rate"),
        AIMessage(content="I'll first...", tool_calls=[{"id": "tc1", "name": "calculate_rate", "args": {}}]),
        AIMessage(content="", response_metadata={"finish_reason": "length"}),
    ]
    assert _answer_was_truncated_by_reasoning(msgs) is True


def test_answer_was_truncated_by_reasoning_returns_false_for_normal_turn() -> None:
    """A successful turn with a real answer must not trigger a retry."""
    from agent.service import _answer_was_truncated_by_reasoning

    msgs = [
        HumanMessage(content="hi"),
        AIMessage(content="Hello! How can I help?"),
    ]
    assert _answer_was_truncated_by_reasoning(msgs) is False


def test_answer_was_truncated_by_reasoning_returns_false_for_pending_tool_call() -> None:
    """A final AIMessage that emits a tool_call (no finish_reason yet) must
    not be classified as a reasoning-truncation failure."""
    from agent.service import _answer_was_truncated_by_reasoning

    msgs = [
        HumanMessage(content="calc"),
        AIMessage(
            content="",
            tool_calls=[{"id": "tc1", "name": "calculate_rate", "args": {}}],
            response_metadata={"finish_reason": "tool_calls"},
        ),
    ]
    assert _answer_was_truncated_by_reasoning(msgs) is False


def test_three_tool_calls_then_truncated_does_not_leak_preface() -> None:
    """End-to-end shape of the user-reported failure: get_payment_modes,
    get_risk_types, calculate_rate all succeed, then the final AIMessage
    is empty (truncated by reasoning). The chat response must NOT be the
    preface text."""
    from agent.service import _collect_turn_events, _finalize_turn

    raw = [
        AIMessage(
            content="I'll first retrieve the available domestic B2C payment modes and risk categories so I can select cash on delivery and the no-risk option, then I'll calculate the rate for the specified box.",
            tool_calls=[{"id": "tc1", "name": "get_payment_modes", "args": {"segment_type": "domestic_b2c"}, "type": "tool_call"}],
        ),
        AIMessage(content="{'status': True, 'data': [...]}", tool_calls=[]),
        AIMessage(
            content="",
            tool_calls=[{"id": "tc2", "name": "get_risk_types", "args": {}, "type": "tool_call"}],
        ),
        AIMessage(content="{'status': True, 'data': [...]}", tool_calls=[]),
        AIMessage(
            content="",
            tool_calls=[{"id": "tc3", "name": "calculate_rate", "args": {}, "type": "tool_call"}],
        ),
        AIMessage(content="{'status': True, 'data': {...rates...}}", tool_calls=[]),
        AIMessage(content="", response_metadata={"finish_reason": "length"}),
    ]
    turn_data = _finalize_turn(_collect_turn_events(raw))
    assert not turn_data["content"]
    assert "I'll first retrieve" not in turn_data["content"]


def test_successful_three_tool_call_turn_keeps_answer() -> None:
    """Regression guard: a normal successful turn with a real answer must
    continue to surface that answer, with reasoning kept as a step."""
    from agent.service import _collect_turn_events, _finalize_turn

    raw = [
        AIMessage(
            content="I'll first retrieve the payment modes.",
            tool_calls=[{"id": "tc1", "name": "get_payment_modes", "args": {"segment_type": "domestic_b2c"}, "type": "tool_call"}],
        ),
        AIMessage(
            content="",
            tool_calls=[{"id": "tc2", "name": "get_risk_types", "args": {}, "type": "tool_call"}],
        ),
        AIMessage(
            content="",
            tool_calls=[{"id": "tc3", "name": "calculate_rate", "args": {}, "type": "tool_call"}],
        ),
        AIMessage(content="Here are the shipping rates for your 15 kg package..."),
    ]
    turn_data = _finalize_turn(_collect_turn_events(raw))
    assert turn_data["content"] == "Here are the shipping rates for your 15 kg package..."
    reasoning_steps = [s for s in turn_data["steps"] if s.get("type") == "reasoning"]
    assert len(reasoning_steps) == 1
    assert "I'll first retrieve" in reasoning_steps[0]["text"]

