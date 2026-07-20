"""Validation helpers for small structured QA-stage model outputs."""

from __future__ import annotations

import math
from typing import Any


def _unwrap_single_object(value: Any) -> Any:
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
        return value[0]
    return value


def normalize_question_keys(value: Any) -> dict[str, Any] | None:
    value = _unwrap_single_object(value)
    if not isinstance(value, dict) or not isinstance(value.get("keywords"), list):
        return None

    keywords = []
    for item in value["keywords"]:
        if not isinstance(item, dict):
            return None
        key = str(item.get("id", "")).strip()
        if not key:
            return None
        alternatives = item.get("alternatives", [])
        if not isinstance(alternatives, list):
            return None
        keywords.append({
            "id": key,
            "alternatives": [str(part).strip() for part in alternatives if str(part).strip()],
        })

    question_time = value.get("question_time", "")
    if question_time is None:
        question_time = ""
    if not isinstance(question_time, str):
        return None
    return {"question_time": question_time.strip(), "keywords": keywords}


def normalize_tag_scores(value: Any, allowed_tags: list[str]) -> dict[str, float] | None:
    value = _unwrap_single_object(value)
    if not isinstance(value, dict) or not isinstance(value.get("tag_scores"), dict):
        return None

    allowed = set(allowed_tags)
    scores = {}
    for tag, score in value["tag_scores"].items():
        if tag not in allowed or isinstance(score, bool) or not isinstance(score, (int, float)):
            continue
        numeric = float(score)
        if math.isfinite(numeric):
            scores[tag] = min(1.0, max(0.0, numeric))
    return scores or None
