import json

from agent.tools import ToolBridge


class _Memory:
    topic_dict = {"D3:t1": object()}
    persona_list = {"Caroline": object()}


class _Controller:
    memory = _Memory()

    def __init__(self):
        self.topic = None

    def query_topic_events(self, topic):
        self.topic = topic
        return json.dumps(["D3:1-1:text"]), ["D3:1"]

    def query_personal_information(self, person):
        return {"person": person, "aspects": []}


def _call(name, arguments):
    return [{
        "id": "call-1",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }]


def test_topic_argument_is_normalized_and_traced():
    controller = _Controller()
    bridge = ToolBridge(controller)
    bridge.call(_call("query_topic_events", {"topic": "D3:t1:Caroline school talk"}))

    assert controller.topic == "D3:t1"
    assert bridge.trace[0]["arguments"] == {"topic": "D3:t1"}
    assert bridge.trace[0]["decoded_arguments"] == {"topic": "D3:t1:Caroline school talk"}
    assert bridge.trace[0]["error"] is None


def test_unknown_topic_and_person_are_structured_tool_errors():
    bridge = ToolBridge(_Controller())
    results = bridge.call(
        _call("query_topic_events", {"topic": "not-a-topic"})
        + _call("query_personal_information", {"person": "John"})
    )

    assert len(results) == 2
    assert bridge.trace[0]["error_type"] == "ValueError"
    assert "invalid topic id" in bridge.trace[0]["error"]
    assert bridge.trace[1]["error_type"] == "ValueError"
    assert "unknown person" in bridge.trace[1]["error"]


def test_person_argument_uses_case_insensitive_exact_canonical_name():
    bridge = ToolBridge(_Controller())
    bridge.call(_call("query_personal_information", {"person": "caroline"}))

    assert bridge.trace[0]["arguments"] == {"person": "Caroline"}
    assert bridge.trace[0]["error"] is None


def test_disabled_tool_does_not_run_argument_validation():
    bridge = ToolBridge(_Controller(), disabled_tools={"query_topic_events"})
    result = bridge.call(_call("query_topic_events", {"topic": "bad-topic"}))

    assert "tool disabled" in result[0]["content"]
    assert bridge.trace[0]["arguments"] == {"topic": "bad-topic"}
    assert bridge.trace[0]["error"] is None
