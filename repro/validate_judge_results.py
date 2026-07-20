#!/usr/bin/env python3
"""Validate Judge coverage, alignment, and provenance before comparison."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def row_key(row: dict[str, Any]) -> tuple[str, int] | None:
    sample_id = row.get("sample", row.get("sample_id"))
    question_index = row.get("question_index")
    if sample_id is None or question_index is None:
        return None
    return str(sample_id), int(question_index)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--judge_path", required=True)
    parser.add_argument("--expected_count", type=int, default=None)
    parser.add_argument("--expected_model", default=None)
    parser.add_argument("--expected_prompt_version", default=None)
    parser.add_argument("--expected_thinking", choices=("true", "false"), default=None)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    expected = {
        (str(row["sample_id"]), int(row["question_index"]))
        for row in manifest.get("records", [])
        if int(row["category"]) != 5
    }
    rows = load_jsonl(Path(args.judge_path))
    keys = [row_key(row) for row in rows]
    missing_keys = [index for index, key in enumerate(keys, start=1) if key is None]
    valid_keys = [key for key in keys if key is not None]
    duplicates = sorted(key for key, count in Counter(valid_keys).items() if count > 1)
    extra = sorted(set(valid_keys) - expected)

    errors = []
    if missing_keys:
        errors.append(f"rows missing sample/question_index: {missing_keys[:10]}")
    if duplicates:
        errors.append(f"duplicate question keys: {duplicates[:10]}")
    if extra:
        errors.append(f"question keys outside manifest: {extra[:10]}")
    if args.expected_count is not None and len(rows) != args.expected_count:
        errors.append(f"row count is {len(rows)}, expected {args.expected_count}")
    if len(rows) == len(expected) and set(valid_keys) != expected:
        errors.append(f"full run key mismatch: missing={len(expected - set(valid_keys))}")

    required = {
        "llm_score", "judge_label", "judge_model", "judge_prompt_version",
        "judge_enable_thinking", "judge_prompt", "judge_raw_response",
        "judge_finish_reason", "judge_usage", "judge_attempts", "judge_retries",
    }
    for index, row in enumerate(rows, start=1):
        absent = sorted(field for field in required if row.get(field) is None)
        if absent:
            errors.append(f"row {index} missing provenance: {absent}")
        label = row.get("judge_label")
        score = row.get("llm_score")
        if label not in {"CORRECT", "WRONG"} or score != (1 if label == "CORRECT" else 0):
            errors.append(f"row {index} has inconsistent label/score: {label!r}/{score!r}")

    models = sorted({str(row.get("judge_model")) for row in rows})
    prompts = sorted({str(row.get("judge_prompt_version")) for row in rows})
    thinking = sorted({str(bool(row.get("judge_enable_thinking"))).lower() for row in rows})
    if len(models) > 1:
        errors.append(f"mixed judge models: {models}")
    if len(prompts) > 1:
        errors.append(f"mixed prompt versions: {prompts}")
    if len(thinking) > 1:
        errors.append(f"mixed thinking settings: {thinking}")
    if args.expected_model and models != [args.expected_model]:
        errors.append(f"judge model is {models}, expected {[args.expected_model]}")
    if args.expected_prompt_version and prompts != [args.expected_prompt_version]:
        errors.append(
            f"prompt version is {prompts}, expected {[args.expected_prompt_version]}")
    if args.expected_thinking and thinking != [args.expected_thinking]:
        errors.append(f"thinking is {thinking}, expected {[args.expected_thinking]}")

    summary = {
        "rows": len(rows),
        "manifest_ordinary_questions": len(expected),
        "unique_question_keys": len(set(valid_keys)),
        "models": models,
        "prompt_versions": prompts,
        "thinking": thinking,
        "errors": errors,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
