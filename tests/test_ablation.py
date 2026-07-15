from agent.ablation import disabled_tools_for_view, support_ids_from_payload, uses_content, uses_tags


def test_memory_view_tool_filters_are_nested():
    ce = disabled_tools_for_view("ce")
    cte = disabled_tools_for_view("cte")
    ctc = disabled_tools_for_view("ctc")

    assert "edges_by_tag" in ce
    assert "query_topic_events" in ce
    assert "edges_by_tag" not in cte
    assert "query_topic_events" in cte
    assert "query_topic_events" not in ctc
    assert uses_tags("ce") is False
    assert uses_tags("cte") is True
    assert uses_content("ctc") is True


def test_explicitly_disabled_tools_are_preserved():
    disabled = disabled_tools_for_view("ctc", {"query_event_context"})
    assert disabled == frozenset({"query_event_context"})


def test_support_ids_are_deduplicated_and_normalized():
    payload = {"events": ["D1:2-1:text", "D1:2-2:text", "D3:7:text"]}
    assert support_ids_from_payload(payload) == ["D1:2", "D3:7"]

