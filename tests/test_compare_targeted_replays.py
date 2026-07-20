from repro.compare_targeted_replays import (
    content_tool_error_count,
    context_fields_complete,
    lexical_f1,
    replay_score,
)


def test_replay_contract_metrics():
    row = {
        "_metrics": {
            "initial_context_ids": [],
            "tool_context_ids": ["D1:1"],
            "final_context_ids": ["D1:1"],
            "tool_trace": [
                {"tool": "query_topic_events", "error": "bad topic"},
                {"tool": "query_event_context", "error": "unrelated"},
            ],
        }
    }
    assert context_fields_complete(row)
    assert content_tool_error_count(row) == 1
    assert lexical_f1("a vintage camera", "A vintage camera") == 1.0
    assert replay_score("Not mentioned in the conversation", None, 5) == 1.0
