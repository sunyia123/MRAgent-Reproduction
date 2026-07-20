"""Small, testable helpers for MRAgent structure/retrieval ablations."""

from __future__ import annotations

import re
from collections.abc import Iterable


_CONTENT_TOOLS = {
    "query_personal_information",
    "query_personal_aspect",
    "query_topic_events",
}


def disabled_tools_for_view(memory_view: str, explicitly_disabled: Iterable[str] = ()) -> frozenset[str]:
    disabled = set(explicitly_disabled)
    if memory_view == "ce":
        disabled.add("edges_by_tag")
        disabled.update(_CONTENT_TOOLS)
    elif memory_view == "cte":
        disabled.update(_CONTENT_TOOLS)
    elif memory_view != "ctc":
        raise ValueError(f"unknown memory view: {memory_view}")
    return frozenset(disabled)


def uses_tags(memory_view: str) -> bool:
    return memory_view in {"cte", "ctc"}


def uses_content(memory_view: str) -> bool:
    return memory_view == "ctc"


def support_ids_from_payload(payload: object) -> list[str]:
    """Extract stable LoCoMo turn ids from one-shot context payloads."""
    seen: set[str] = set()
    result: list[str] = []
    for value in re.findall(r"D\d+:\d+(?:-\d+)?", str(payload)):
        origin = re.sub(r"-\d+$", "", value)
        if origin not in seen:
            seen.add(origin)
            result.append(origin)
    return result


def merge_support_ids(*groups: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for group in groups:
        for value in group:
            if value not in seen:
                seen.add(value)
                merged.append(value)
    return merged
