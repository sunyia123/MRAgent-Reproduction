"""Shared, auditable plumbing for external LoCoMo baseline adapters."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Iterable

from common import config
from data.get_data import get_data
from llm.controller import LLM
from repro.baseline_utils import answer_system_prompt, format_question, load_subset_manifest, raw_turns


ANSWER_SYSTEM_PROMPT = """Answer the question based ONLY on the provided conversation context.
If the context does not contain enough information, answer "no information available".
Give a concise answer - just the key fact, entity, date, or phrase asked for."""


def normalize_sample_ids(value: str | None) -> set[str] | None:
    if not value:
        return None
    return {
        item if item.startswith("conv-") else f"conv-{item}"
        for item in (part.strip() for part in value.split(","))
        if item
    }


def load_locomo_run(
    dataset_path: str,
    manifest_path: str,
    sample_ids: str | None,
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]], dict[str, list[int]]]:
    _, questions, raw_conversations, _ = get_data("locomo", dataset_path)
    subset = load_subset_manifest(manifest_path)
    if subset is None:
        raise ValueError("--subset_manifest is required for an external baseline run")
    requested = normalize_sample_ids(sample_ids)
    selected = {
        sample_id: indices
        for sample_id, indices in subset.items()
        if (requested is None or sample_id in requested)
    }
    if not selected:
        raise ValueError("manifest and --sample_ids select no LoCoMo samples")
    missing = [sample_id for sample_id in selected if sample_id not in raw_conversations]
    if missing:
        raise KeyError(f"samples missing from dataset: {missing}")
    return raw_conversations, questions, selected


def question_items(
    sample_id: str,
    qa_list: list[dict[str, Any]],
    indices: Iterable[int],
) -> list[tuple[int, dict[str, Any], str]]:
    items = []
    for index in indices:
        if not 0 <= index < len(qa_list):
            raise IndexError(f"{sample_id} question index out of range: {index}")
        qa = qa_list[index]
        items.append((index, qa, format_question(qa, sample_id, index)))
    return items


def conversation_units(raw_conversation: dict[str, Any]) -> list[dict[str, str]]:
    units = raw_turns(raw_conversation)
    speaker_a = str(raw_conversation.get("speaker_a") or "")
    for unit in units:
        if not unit.get("origin"):
            raise ValueError("LoCoMo turn is missing dia_id; provenance would be ambiguous")
        unit["role"] = "user" if unit.get("speaker") == speaker_a else "assistant"
    return units


def memory_input_text(unit: dict[str, str]) -> str:
    date = unit.get("session_date") or "unknown"
    source = unit.get("origin") or unit.get("sentence_id") or "unknown"
    speaker = unit.get("speaker") or "UNKNOWN"
    return f"[source={source}; session_date={date}] Speaker {speaker} says: {unit['text']}"


def build_context(rows: list[dict[str, Any]]) -> str:
    lines = []
    for row in rows:
        source = row.get("source_id") or row.get("id") or "unknown"
        date = row.get("session_date") or row.get("timestamp") or ""
        date_text = f" (session_date={date})" if date else ""
        lines.append(f"[{source}]{date_text} {row.get('text') or row.get('memory') or ''}")
    return "\n".join(lines)


def answer_question(llm: LLM, question: str, context: str, category: Any) -> str:
    llm._current_stage = "external_baseline_qa"
    result = llm.chat_plain_text(
        messages=[
            {"role": "system", "content": answer_system_prompt(ANSWER_SYSTEM_PROMPT, category)},
            {
                "role": "user",
                "content": f"Question: {question}\n\nContext:\n{context}\n\nAnswer:",
            },
        ],
        model=config.QA_MODEL,
        max_tokens=config.QA_MAX_TOKENS,
    )
    return str(result or "no information available")


def result_path(sample_id: str, model_name: str, file_tag: str) -> Path:
    path = Path("result/locomo") / f"{sample_id}_result_{model_name}_{file_tag}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def completed_question_indices(path: Path) -> set[int]:
    done: set[int] = set()
    if not path.exists():
        return done
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            done.add(int(row["question_index"]))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid resumable result at {path}:{line_number}: {exc}") from exc
    return done


def append_result(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def trace_path(method: str, sample_id: str, question_index: int) -> Path:
    path = (
        Path("result/diagnostics/external_baselines")
        / method
        / sample_id
        / f"q{question_index + 1:03d}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_trace(method: str, sample_id: str, question_index: int, payload: dict[str, Any]) -> None:
    trace_path(method, sample_id, question_index).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def source_ids_from_text(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"\bD\d+:\d+\b", text or "")))


def repo_commit(repo_path: str) -> str:
    return subprocess.check_output(
        ["git", "-C", repo_path, "rev-parse", "HEAD"], text=True
    ).strip()


def require_repo_commit(repo_path: str, expected_commit: str, label: str) -> str:
    path = Path(repo_path)
    if not path.exists():
        raise FileNotFoundError(f"{label} repository not found: {path}")
    actual = repo_commit(str(path))
    if actual != expected_commit:
        raise RuntimeError(
            f"{label} commit mismatch: expected {expected_commit}, got {actual}. "
            "Do not run an unpinned external baseline."
        )
    return actual


def file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_provenance(method: str, file_tag: str, values: dict[str, Any]) -> Path:
    stem = file_tag if file_tag.startswith(f"{method}_") else f"{method}_{file_tag}"
    path = Path("reports/external_baselines") / f"{stem}_provenance.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {method} provenance: {file_tag}", ""]
    for key, value in values.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
