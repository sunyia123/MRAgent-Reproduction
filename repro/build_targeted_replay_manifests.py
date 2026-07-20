#!/usr/bin/env python3
"""Build fixed manifests for replaying only observed MRAgent failures."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable


CONTENT_TOOLS = {
    "query_topic_events",
    "query_personal_information",
    "query_personal_aspect",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def is_execution_error(row: dict[str, Any]) -> bool:
    prediction = str(row.get("prediction", "")).strip()
    return not prediction or prediction.upper() == "ERROR"


def has_content_tool_error(row: dict[str, Any]) -> bool:
    trace = (row.get("_metrics") or {}).get("tool_trace") or []
    return any(
        item.get("tool") in CONTENT_TOOLS and item.get("error")
        for item in trace
    )


def collect_reasons(
    result_root: Path,
    sample_ids: list[str],
    model: str,
    tag: str,
    predicates: list[tuple[str, Callable[[dict[str, Any]], bool]]],
) -> dict[tuple[str, int], list[str]]:
    reasons: dict[tuple[str, int], list[str]] = defaultdict(list)
    for sample_id in sample_ids:
        path = result_root / f"{sample_id}_result_{model}_{tag}.jsonl"
        for row in load_jsonl(path):
            if row.get("question_index") is None:
                continue
            key = (str(row.get("sample", sample_id)), int(row["question_index"]))
            for reason, predicate in predicates:
                if predicate(row):
                    reasons[key].append(reason)
    return dict(reasons)


def make_manifest(
    name: str,
    purpose: str,
    source_manifest: Path,
    source_tag: str,
    reasons: dict[tuple[str, int], list[str]],
) -> dict[str, Any]:
    base = json.loads(source_manifest.read_text(encoding="utf-8"))
    records_by_key = {
        (str(row["sample_id"]), int(row["question_index"])): row
        for row in base.get("records", [])
    }
    missing = sorted(set(reasons) - set(records_by_key))
    if missing:
        raise ValueError(f"replay keys missing from source manifest: {missing}")

    records = []
    for key in sorted(reasons):
        record = dict(records_by_key[key])
        record["replay_reasons"] = sorted(set(reasons[key]))
        records.append(record)

    return {
        "name": name,
        "purpose": purpose,
        "generated_by": "repro/build_targeted_replay_manifests.py",
        "source_manifest": source_manifest.as_posix(),
        "source_result_tag": source_tag,
        "n_questions": len(records),
        "sample_ids": sorted({row["sample_id"] for row in records}),
        "sample_counts": dict(Counter(row["sample_id"] for row in records)),
        "category_counts": {
            str(key): value
            for key, value in sorted(Counter(int(row["category"]) for row in records).items())
        },
        "records": records,
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main_manifest", default="data/subsets/locomo10_500q_main_seed42.json")
    parser.add_argument("--result_root", default="result/locomo")
    parser.add_argument("--model", default="deepseek")
    parser.add_argument("--output_dir", default="data/subsets")
    args = parser.parse_args()

    source_manifest = Path(args.main_manifest)
    base = json.loads(source_manifest.read_text(encoding="utf-8"))
    sample_ids = [str(value) for value in base.get("sample_ids", [])]
    result_root = Path(args.result_root)
    output_dir = Path(args.output_dir)

    specs = [
        (
            "locomo_replay_mragent_main_errors_20260720",
            "Replay the five execution errors from the 500-question Full MRAgent run.",
            "mragent_500q_main",
            [("execution_error", is_execution_error)],
        ),
        (
            "locomo_replay_cte_active_errors_20260720",
            "Replay execution errors from the 200-question CTE-active ablation.",
            "ablation_200q_cte_active",
            [("execution_error", is_execution_error)],
        ),
        (
            "locomo_replay_ctc_active_repairs_20260720",
            "Replay CTC-active execution errors and observed content-tool contract failures.",
            "ablation_200q_ctc_active",
            [
                ("execution_error", is_execution_error),
                ("content_tool_error", has_content_tool_error),
            ],
        ),
    ]

    for name, purpose, tag, predicates in specs:
        reasons = collect_reasons(result_root, sample_ids, args.model, tag, predicates)
        manifest = make_manifest(name, purpose, source_manifest, tag, reasons)
        path = output_dir / f"{name}.json"
        write_manifest(path, manifest)
        print(f"{path}: {manifest['n_questions']} questions")


if __name__ == "__main__":
    main()
