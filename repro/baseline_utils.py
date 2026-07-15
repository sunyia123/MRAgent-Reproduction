"""Shared helpers for LoCoMo passive-retrieval baselines."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def load_subset_manifest(path: str | None) -> dict[str, list[int]] | None:
    if not path:
        return None
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    by_sample: dict[str, list[int]] = {}
    for record in obj.get("records", []):
        sample_id = record.get("sample_id")
        question_index = record.get("question_index")
        if sample_id is not None and question_index is not None:
            by_sample.setdefault(str(sample_id), []).append(int(question_index))
    return {sample_id: sorted(set(indices)) for sample_id, indices in by_sample.items()}


def format_question(qa: dict[str, Any], sample_id: str, question_index: int) -> str:
    """Mirror MRAgent's LoCoMo question formatting without run-to-run randomness."""
    question = str(qa.get("question", ""))
    if qa.get("category") != 5:
        return question

    adversarial_answer = str(qa.get("adversarial_answer", ""))
    digest = hashlib.sha256(f"{sample_id}:{question_index}".encode("utf-8")).digest()[0]
    choices = ("Not mentioned in the conversation", adversarial_answer)
    if digest % 2:
        choices = tuple(reversed(choices))
    return question + " Select the correct answer: {} or {}.".format(*choices)


def temporal_instruction(category: Any) -> str:
    if str(category) != "2":
        return ""
    return (
        " For temporal questions, use each context line's event_date or session_date "
        "to resolve relative expressions such as 'yesterday', 'last Friday', and "
        "'last week'. Return the absolute date, month, year, or duration requested; "
        "do not return an unresolved relative expression."
    )


def answer_system_prompt(prefix: str, category: Any) -> str:
    return prefix + temporal_instruction(category)


def raw_turns(raw_conversation: dict[str, Any]) -> list[dict[str, str]]:
    """Flatten a LoCoMo conversation into date-preserving raw turn units."""
    rows: list[dict[str, str]] = []
    for session_number in range(1, 1000):
        session_key = f"session_{session_number}"
        turns = raw_conversation.get(session_key)
        if turns is None:
            if session_number > 1:
                break
            continue
        session_date = str(raw_conversation.get(f"{session_key}_date_time", ""))
        for turn in turns:
            if not isinstance(turn, dict):
                continue
            caption = str(turn.get("blip_caption") or "")
            text = str(turn.get("text") or "")
            if not text and not caption:
                continue
            if caption:
                text = f"{text} [image caption: {caption}]".strip()
            rows.append(
                {
                    "sentence_id": str(turn.get("dia_id", "")),
                    "origin": str(turn.get("dia_id", "")),
                    "text": text,
                    "speaker": str(turn.get("speaker", "")),
                    "session_date": session_date,
                    "event_time": "",
                    "tag": "raw_turn",
                }
            )
    return rows
