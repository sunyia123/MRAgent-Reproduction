#!/usr/bin/env python3
"""Compare full Standard RAG output against a smaller MRAgent subset.

Use case:
- MRAgent stratified result has 15 selected questions.
- Standard RAG smoke may run all 105 conv-30 questions.
- This script matches by exact question text, extracts the same subset from
  RAG, and writes a fair per-question comparison report.

No API calls are made.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval.evaluation import f1_score


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            row["_line_no"] = line_no
            rows.append(row)
    return rows


def score_row(row: dict[str, Any]) -> float:
    if str(row.get("category")) == "5":
        return 1.0 if "not mentioned" in str(row.get("prediction", "")).lower() else 0.0
    return f1_score(str(row.get("prediction", "")), str(row.get("answer", "")))


def evidence_hit(evidence: list[Any], context: list[Any]) -> bool:
    ctx = {str(x) for x in context or []}
    for eid in evidence or []:
        eid = str(eid)
        if eid in ctx:
            return True
        prefix = f"{eid}-"
        if any(c.startswith(prefix) for c in ctx):
            return True
    return False


def avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def fmt(value: float | None) -> str:
    return "NA" if value is None else f"{value:.4f}"


def truncate(text: Any, limit: int = 120) -> str:
    text = str(text or "").replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare RAG full output to MRAgent subset by question text.")
    parser.add_argument("--mragent_result", required=True)
    parser.add_argument("--rag_result", required=True)
    parser.add_argument("--output", default=None)
    parser.add_argument("--subset_output", default=None)
    args = parser.parse_args()

    mragent_path = Path(args.mragent_result)
    rag_path = Path(args.rag_result)
    mr_rows = load_jsonl(mragent_path)
    rag_rows = load_jsonl(rag_path)

    rag_by_question: dict[str, dict[str, Any]] = {}
    duplicates = []
    for row in rag_rows:
        q = str(row.get("question", "")).strip()
        if q in rag_by_question:
            duplicates.append(q)
        rag_by_question[q] = row

    pairs = []
    missing = []
    for idx, mr in enumerate(mr_rows, start=1):
        q = str(mr.get("question", "")).strip()
        rag = rag_by_question.get(q)
        if rag is None:
            missing.append({"idx": idx, "question": q})
            continue
        mr_score = score_row(mr)
        rag_score = score_row(rag)
        pairs.append(
            {
                "idx": idx,
                "question": q,
                "category": mr.get("category"),
                "gold": mr.get("answer"),
                "mragent_prediction": mr.get("prediction"),
                "rag_prediction": rag.get("prediction"),
                "mragent_score": mr_score,
                "rag_score": rag_score,
                "score_delta_rag_minus_mragent": rag_score - mr_score,
                "mragent_context": mr.get("prediction_context") or [],
                "rag_context": rag.get("prediction_context") or [],
                "evidence": mr.get("evidence") or [],
                "mragent_evidence_hit": evidence_hit(mr.get("evidence") or [], mr.get("prediction_context") or []),
                "rag_evidence_hit": evidence_hit(rag.get("evidence") or [], rag.get("prediction_context") or []),
                "mragent_tool_calls": (mr.get("_metrics") or {}).get("tool_calls"),
                "rag_top_k": (rag.get("_metrics") or {}).get("rag_top_k"),
                "rag_line_no": rag.get("_line_no"),
                "mragent_line_no": mr.get("_line_no"),
            }
        )

    if args.subset_output:
        subset_path = Path(args.subset_output)
        subset_path.parent.mkdir(parents=True, exist_ok=True)
        with subset_path.open("w", encoding="utf-8") as f:
            for pair in pairs:
                row = rag_by_question[pair["question"]]
                f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    by_cat_mr: dict[str, list[float]] = defaultdict(list)
    by_cat_rag: dict[str, list[float]] = defaultdict(list)
    hit_by_cat_mr: dict[str, list[float]] = defaultdict(list)
    hit_by_cat_rag: dict[str, list[float]] = defaultdict(list)
    for pair in pairs:
        cat = str(pair["category"])
        by_cat_mr[cat].append(pair["mragent_score"])
        by_cat_rag[cat].append(pair["rag_score"])
        hit_by_cat_mr[cat].append(1.0 if pair["mragent_evidence_hit"] else 0.0)
        hit_by_cat_rag[cat].append(1.0 if pair["rag_evidence_hit"] else 0.0)

    output = Path(args.output) if args.output else Path("reports") / f"rag_vs_mragent_subset_{datetime.now().strftime('%Y%m%d')}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# RAG vs MRAgent Subset Comparison - {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "## Source",
        "",
        f"- MRAgent subset: `{mragent_path}` ({len(mr_rows)} rows)",
        f"- RAG full result: `{rag_path}` ({len(rag_rows)} rows)",
        f"- matched questions: {len(pairs)} / {len(mr_rows)}",
        f"- missing questions: {len(missing)}",
        f"- duplicate RAG questions: {len(duplicates)}",
        "",
        "## Score Summary",
        "",
        "| category | n | MRAgent score | RAG score | RAG - MRAgent | MRAgent evidence hit | RAG evidence hit |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for cat in sorted(set(by_cat_mr) | set(by_cat_rag), key=str):
        mr_avg = avg(by_cat_mr.get(cat, []))
        rag_avg = avg(by_cat_rag.get(cat, []))
        delta = None if mr_avg is None or rag_avg is None else rag_avg - mr_avg
        lines.append(
            f"| {cat} | {len(by_cat_mr.get(cat, []))} | {fmt(mr_avg)} | {fmt(rag_avg)} | "
            f"{fmt(delta)} | {fmt(avg(hit_by_cat_mr.get(cat, [])))} | {fmt(avg(hit_by_cat_rag.get(cat, [])))} |"
        )
    mr_all = [p["mragent_score"] for p in pairs]
    rag_all = [p["rag_score"] for p in pairs]
    lines.append(
        f"| OVERALL | {len(pairs)} | {fmt(avg(mr_all))} | {fmt(avg(rag_all))} | "
        f"{fmt((avg(rag_all) or 0) - (avg(mr_all) or 0))} | "
        f"{fmt(avg([1.0 if p['mragent_evidence_hit'] else 0.0 for p in pairs]))} | "
        f"{fmt(avg([1.0 if p['rag_evidence_hit'] else 0.0 for p in pairs]))} |"
    )

    lines.extend(
        [
            "",
            "## Per-Question Comparison",
            "",
            "| # | cat | MR score | RAG score | MR hit | RAG hit | question | gold | MRAgent prediction | RAG prediction |",
            "| ---: | --- | ---: | ---: | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for pair in pairs:
        lines.append(
            "| {idx} | {cat} | {mr:.4f} | {rag:.4f} | {mrhit} | {raghit} | {q} | {gold} | {mrpred} | {ragpred} |".format(
                idx=pair["idx"],
                cat=pair["category"],
                mr=pair["mragent_score"],
                rag=pair["rag_score"],
                mrhit="Y" if pair["mragent_evidence_hit"] else "N",
                raghit="Y" if pair["rag_evidence_hit"] else "N",
                q=truncate(pair["question"]).replace("|", "\\|"),
                gold=truncate(pair["gold"]).replace("|", "\\|"),
                mrpred=truncate(pair["mragent_prediction"]).replace("|", "\\|"),
                ragpred=truncate(pair["rag_prediction"]).replace("|", "\\|"),
            )
        )

    if missing:
        lines.extend(["", "## Missing Questions", ""])
        for item in missing:
            lines.append(f"- #{item['idx']}: {item['question']}")

    lines.extend(
        [
            "",
            "## Interpretation Rules",
            "",
            "- If RAG hits evidence and MRAgent misses it, diagnose tool-path or graph traversal.",
            "- If both hit evidence but answer differs, diagnose answer synthesis or evaluation.",
            "- If both miss evidence, diagnose rewrite/embedding/query formulation or image missingness.",
            "- This comparison is fair only for matched questions; do not compare 105-question RAG aggregate to 15-question MRAgent aggregate directly.",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
