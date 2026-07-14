import json
from memory.controller import MemoryController

TOOLS= [
  {
  "type": "function",
  "function":{
    "name": "edges_by_tag",
    "description": "Follow memory graph edges filtered by a {tag, key} pair to retrieve related events under a topic. Do NOT repeat the same key–tag combination.",
    "parameters": {
      "type": "object",
      "properties": {
        "tag": {
          "type": "string",
          "description": "Select a tag aligned with the related keyword. When exploring, choose at least one tag from each related keyword."
        },
        "key": {
          "type": "string",
          "description": "A key from keys_candidates (e.g., a person/entity/topic)."
        },
        "note": {
        "type": "string",
        "minLength": 8,
        "maxLength": 80,
        "description": "Short, verifiable decision note for next round. No step-by-step reasoning."
        }
      },
      "required": ["tag", "key", "note"],
    }
  }
  },
  {
  "type": "function",
  "function":{
    "name": "query_conversation_time",
    "description": "Return WHEN the conversation containing the event occurred (conversation time). This is not the exact real-world event time.",
    "parameters": {
      "type": "object",
      "properties": {
        "event_id": {
          "type": "string",
          "description": "Target event ID (e.g., D1:1)."
        }
      },
      "required": ["event_id"],
    }
  }},
  {
"type": "function",
  "function":{
    "name": "query_event_keywords",
    "description": "Return salient keywords for an event (entities, topics, times). Use when the event is related but vague. Often followed by query_event_context.",
    "parameters": {
      "type": "object",
      "properties": {
        "event_id": {
          "type": "string",
          "description": "Event suspected to be relevant but lacking clarity (e.g., D3:2)."
        }
      },
      "required": ["event_id"],
    }
  }},
  {
"type": "function",
  "function":{
    "name": "query_event_context",
    "description": "Return surrounding conversational context of an event (before/after turns) when evidence is related but incomplete.",
    "parameters": {
      "type": "object",
      "properties": {
        "event_id": {
          "type": "string",
          "description": "Event whose context is needed (e.g., D3:2)."
        }
      },
      "required": ["event_id"],
    }
  }},
  {
    "type": "function",
    "function": {
      "name": "query_personal_information",
      "description": "List available aspects for a given person (e.g., hobbies, achievement, preference).",
      "parameters": {
        "type": "object",
        "properties": {
          "person": {
            "type": "string",
            "description": "Name of the person."
          }
        },
        "required": ["person"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "query_personal_aspect",
      "description": "Return detailed personal information for one selected aspect of the person.",
      "parameters": {
        "type": "object",
        "properties": {
          "person": {
            "type": "string",
            "description": "Name of the person."
          },
          "aspect": {
            "type": "string",
            "description": "One aspect returned by query_personal_information."
          }
        },
        "required": ["person", "aspect"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "query_topic_events",
      "description": "Return detailed events under queried topic.",
      "parameters": {
        "type": "object",
        "properties": {
          "topic": {
            "type": "string",
            "description": "topic id (e.g. D1:t2)."
          },
        },
        "required": ["topic"]
      }
    }
  }
  # {
  #   "type": "function",
  #   "function": {
  #     "name": "score_event_relevance",
  #     "description": "Score every existing event for its usefulness to answer the question. Return a score for every event id in [0.0, 1.0].",
  #     "parameters": {
  #       "type": "object",
  #       "properties": {
  #         "question": {"type": "string"},
  #         "scores": {
  #           "type": "object",
  #           "description": "scores of each event, e.g., {\"D1:1\":0.0-1.0,\"D1:2\":0.0-1.0}",
  #           # "additionalProperties": {"type": "string"}
  #         }
  #       },
  #       "required": ["question", "scores"]
  #     }
  #   }
  # }

]


class ToolBridge:
    def __init__(self, memory_controller: MemoryController, disabled_tools=None):
        self.memory_controller = memory_controller
        self.disabled_tools = set(disabled_tools or [])
        self.trace = []

    def reset_trace(self):
        self.trace = []

    @staticmethod
    def _preview(value, limit=1000):
        text = str(value)
        return text if len(text) <= limit else text[:limit] + "...<truncated>"

    def call(self, tool_call: list) -> list:
        tool_results = []
        for item in tool_call:
            op = item["function"].get("name")
            raw_arguments = item["function"].get("arguments")
            a = None
            error = None
            try:
                a = json.loads(raw_arguments)
                if op in self.disabled_tools:
                    out = {"error": f"tool disabled for this ablation: {op}"}
                elif op == "edges_by_tag":
                    out, _, _ = self.memory_controller.event_by_tag(**a)
                elif op == "query_conversation_time":
                    out = self.memory_controller.query_conversation_time(**a)
                elif op == "query_event_keywords":
                    out = self.memory_controller.query_event_keywords(**a)
                elif op == "query_event_context":
                    out, _ = self.memory_controller.query_event_context(**a)
                elif op == "query_personal_information":
                    out = self.memory_controller.query_personal_information(**a)
                elif op == "query_personal_aspect":
                    out, _ = self.memory_controller.query_personal_aspect(**a)
                elif op == "query_topic_events":
                    out, _ = self.memory_controller.query_topic_events(**a)
                else:
                    out = {"error": f"unknown op {op}"}
            except Exception as e:
                error = str(e)
                out = {"error": error}
            self.trace.append({
                "tool": op,
                "arguments": a if a is not None else raw_arguments,
                "result_preview": self._preview(out),
                "error": error,
            })
            tool_results.append({
                "role": "tool",
                "tool_call_id": item.get('id'),  # pair with the call
                "content": str(out),
            })
        return tool_results

