#!/usr/bin/env python3
"""Summarize medium-scale core validation results across methods."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def simple_f1_score(prediction: str, ground_truth: str) -> float:
    pred_tokens = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", " ", prediction.lower()).split()
    gold_tokens = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", " ", ground_truth.lower()).split()
    if not pred_tokens and not gold_tokens:
        return 1.0
    if not pred_tokens or not gold_tokens:
        return 0.0
    common = Counter(pred_tokens) & Counter(gold_tokens)
    same = sum(common.values())
    if same == 0:
        return 0.0
    precision = same / len(pred_tokens)
    recall = same / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def score(row: dict[str, Any]) -> float:
    if str(row.get("category")) == "5":
        return 1.0 if "not mentioned" in str(row.get("prediction", "")).lower() else 0.0
    return simple_f1_score(str(row.get("prediction", "")), str(row.get("answer", "")))


def evidence_hit(row: dict[str, Any]) -> bool:
    ctx = {str(x) for x in row.get("prediction_context") or []}
    for eid in row.get("evidence") or []:
        eid = str(eid)
        if eid in ctx:
            return True
        if any(c.startswith(f"{eid}-") for c in ctx):
            return True
    return False


def avg(values: list[float]) -> str:
    return "NA" if not values else f"{sum(values) / len(values):.4f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize fixed-subset core validation results.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--data", default="locomo")
    parser.add_argument(
        "--methods",
        default="mragent_100q,rag_100q,graphrag_100q,oracle_100q",
        help="Comma-separated result file tags.",
    )
    parser.add_argument("--model", default="deepseek")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    records = manifest.get("records", [])
    expected = {(r["sample_id"], int(r["question_index"])): r for r in records}
    methods = [m.strip() for m in args.methods.split(",") if m.strip()]

    method_rows: dict[str, dict[tuple[str, int], dict[str, Any]]] = {}
    for method in methods:
        rows_by_key = {}
        for sample_id in manifest.get("sample_ids", []):
            path = Path("result") / args.data / f"{sample_id}_result_{args.model}_{method}.jsonl"
            for row in load_jsonl(path):
                qidx = row.get("question_index")
                if qidx is None:
                    # fall back to question text later not supported in this strict summary
                    continue
                rows_by_key[(sample_id, int(qidx))] = row
        method_rows[method] = rows_by_key

    lines = [
        f"# Medium Core Validation Summary - {datetime.now().strftime('%Y-%m-%d')}",
        "",
        f"- manifest: `{args.manifest}`",
        f"- expected questions: {len(expected)}",
        f"- methods: {', '.join(methods)}",
        "",
        "## Method Summary",
        "",
        "| method | completed | overall score | evidence hit | cat1 | cat2 | cat3 | cat4 | cat5 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for method in methods:
        rows = method_rows[method]
        scores = []
        hits = []
        by_cat: dict[str, list[float]] = defaultdict(list)
        for key in expected:
            row = rows.get(key)
            if not row:
                continue
            s = score(row)
            scores.append(s)
            hits.append(1.0 if evidence_hit(row) else 0.0)
            by_cat[str(row.get("category"))].append(s)
        lines.append(
            f"| {method} | {len(rows)} / {len(expected)} | {avg(scores)} | {avg(hits)} | "
            f"{avg(by_cat.get('1', []))} | {avg(by_cat.get('2', []))} | {avg(by_cat.get('3', []))} | "
            f"{avg(by_cat.get('4', []))} | {avg(by_cat.get('5', []))} |"
        )

    lines.extend(
        [
            "",
            "## Missing Outputs",
            "",
            "| method | missing count | first missing keys |",
            "| --- | ---: | --- |",
        ]
    )
    for method in methods:
        missing = [key for key in expected if key not in method_rows[method]]
        preview = ", ".join(f"{s}:{i+1}" for s, i in missing[:10])
        lines.append(f"| {method} | {len(missing)} | {preview} |")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- If Oracle is high and retrieval methods are low, the bottleneck is retrieval/tool path.",
            "- If Oracle is also low, inspect rewrite quality, evidence expression, model synthesis, and metric mismatch.",
            "- If GraphRAG beats Standard RAG, graph expansion adds value.",
            "- If MRAgent loses to GraphRAG on evidence hit, the multi-round tool policy is suspect.",
        ]
    )

    output = Path(args.output) if args.output else Path("reports") / f"medium_core_validation_summary_{datetime.now().strftime('%Y%m%d')}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
