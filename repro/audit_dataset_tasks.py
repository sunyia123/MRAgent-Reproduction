#!/usr/bin/env python3
"""Audit dataset/task structure before running expensive MRAgent experiments."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def session_keys(conversation: dict[str, Any]) -> list[str]:
    keys = []
    for key, value in conversation.items():
        if key.startswith("session_") and key[len("session_") :].isdigit() and isinstance(value, list):
            keys.append(key)
    return sorted(keys, key=lambda x: int(x.split("_")[1]))


def has_image(turn: dict[str, Any]) -> bool:
    url = turn.get("img_url")
    if isinstance(url, str):
        return bool(url)
    return bool(url)


def audit_dataset(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected list dataset, got {type(data)}")

    samples = []
    category_counts = Counter()
    total_questions = 0
    total_sessions = 0
    total_turns = 0
    total_image_turns = 0

    for sample in data:
        sample_id = sample.get("sample_id")
        conversation = sample.get("conversation") or {}
        qa = sample.get("qa") or []
        cats = Counter(str(q.get("category")) for q in qa)
        category_counts.update(cats)
        sessions = session_keys(conversation)
        turns = 0
        image_turns = 0
        speakers = Counter()
        for sk in sessions:
            for turn in conversation.get(sk, []):
                if not isinstance(turn, dict):
                    continue
                turns += 1
                speakers.update([turn.get("speaker") or "UNKNOWN"])
                if has_image(turn):
                    image_turns += 1

        total_questions += len(qa)
        total_sessions += len(sessions)
        total_turns += turns
        total_image_turns += image_turns
        samples.append(
            {
                "sample_id": sample_id,
                "sessions": len(sessions),
                "turns": turns,
                "image_turns": image_turns,
                "questions": len(qa),
                "categories": dict(sorted(cats.items())),
                "speakers": dict(speakers.most_common()),
            }
        )

    return {
        "path": str(path),
        "samples": samples,
        "n_samples": len(samples),
        "total_questions": total_questions,
        "total_sessions": total_sessions,
        "total_turns": total_turns,
        "total_image_turns": total_image_turns,
        "category_counts": dict(sorted(category_counts.items())),
    }


def write_report(audit: dict[str, Any], output: Path) -> None:
    lines = [
        f"# Dataset And Task Audit - {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "## Summary",
        "",
        f"- dataset path: `{audit['path']}`",
        f"- samples: {audit['n_samples']}",
        f"- questions: {audit['total_questions']}",
        f"- sessions: {audit['total_sessions']}",
        f"- turns: {audit['total_turns']}",
        f"- image turns: {audit['total_image_turns']}",
        "",
        "## Category Distribution",
        "",
        "| category | count |",
        "| --- | ---: |",
    ]
    for cat, count in audit["category_counts"].items():
        lines.append(f"| {cat} | {count} |")

    lines.extend(
        [
            "",
            "## Per-Sample Tasks",
            "",
            "| sample | sessions | turns | image turns | questions | categories | speakers |",
            "| --- | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for sample in audit["samples"]:
        cats = ", ".join(f"{k}:{v}" for k, v in sample["categories"].items())
        speakers = ", ".join(f"{k}:{v}" for k, v in sample["speakers"].items())
        lines.append(
            f"| `{sample['sample_id']}` | {sample['sessions']} | {sample['turns']} | "
            f"{sample['image_turns']} | {sample['questions']} | {cats} | {speakers} |"
        )

    lines.extend(
        [
            "",
            "## How To Use This Audit",
            "",
            "- Use small, stratified subsets before full runs.",
            "- Include image-heavy samples only when the image access path is validated.",
            "- Keep category counts fixed across MRAgent, Standard RAG, GraphRAG, Oracle, and CBR ablations.",
            "- Do not interpret a diagnostic subset as a paper-level benchmark.",
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit dataset/task composition.")
    parser.add_argument("--data_path", default="data/dataset_locomo.json")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    path = Path(args.data_path)
    audit = audit_dataset(path)
    output = Path(args.output) if args.output else Path("reports") / f"dataset_task_audit_{path.stem}_{datetime.now().strftime('%Y%m%d')}.md"
    write_report(audit, output)
    print(output)


if __name__ == "__main__":
    main()
