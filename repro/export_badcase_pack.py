#!/usr/bin/env python3
"""Export a compact, GitHub-friendly badcase report from MRAgent result JSONL.

The report is meant for fast iteration: it records question, gold answer,
prediction, category, gold evidence ids, retrieved context ids, tool-call count,
runtime, and a lightweight failure label. Large logs stay on the server; this
small Markdown pack can be committed to GitHub.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def normalize(text: str) -> list[str]:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text)
    return [tok for tok in text.split() if tok]


def token_f1(gold: str, pred: str) -> float:
    gold_toks = normalize(gold)
    pred_toks = normalize(pred)
    if not gold_toks and not pred_toks:
        return 1.0
    if not gold_toks or not pred_toks:
        return 0.0
    common = Counter(gold_toks) & Counter(pred_toks)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0
    precision = num_same / len(pred_toks)
    recall = num_same / len(gold_toks)
    return 2 * precision * recall / (precision + recall)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception as exc:
                rows.append({"_parse_error": repr(exc), "_line_no": line_no, "_raw": line[:500]})
                continue
            row["_line_no"] = line_no
            rows.append(row)
    return rows


def classify(row: dict[str, Any], f1: float, no_info_patterns: tuple[str, ...]) -> str:
    pred = (row.get("prediction") or "").lower()
    evidence = set(row.get("evidence") or [])
    ctx = set(row.get("prediction_context") or [])
    cat = str(row.get("category"))
    if row.get("_parse_error"):
        return "parse_error"
    if cat == "5" and any(p in pred for p in no_info_patterns):
        return "adversarial_correct_or_needs_check"
    if any(p in pred for p in no_info_patterns):
        return "no_information_answer"
    if cat == "5":
        return "adversarial_wrong_or_needs_check"
    if evidence and not (evidence & ctx):
        return "retrieval_miss_or_context_mismatch"
    if f1 < 0.2:
        return "low_f1_possible_paraphrase_or_wrong_answer"
    return "ok_or_needs_manual_review"


def truncate(text: Any, limit: int) -> str:
    text = str(text or "").replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def result_path_from_args(args: argparse.Namespace) -> Path:
    if args.result:
        return Path(args.result)
    if args.sample:
        sample = args.sample if str(args.sample).startswith("conv-") else f"conv-{args.sample}"
        return Path("result") / args.data / f"{sample}_result_{args.model}_{args.file}.jsonl"
    raise SystemExit("Either --result or --sample is required")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a badcase process report from result JSONL.")
    parser.add_argument("--data", default="locomo")
    parser.add_argument("--model", default="deepseek")
    parser.add_argument("--file", default="stratified")
    parser.add_argument("--sample", default=None, help="Sample id, e.g. 30 or conv-30")
    parser.add_argument("--result", default=None, help="Explicit result JSONL path")
    parser.add_argument("--output", default=None, help="Markdown output path")
    parser.add_argument("--max_cases", type=int, default=30)
    parser.add_argument("--f1_threshold", type=float, default=0.2)
    args = parser.parse_args()

    result_path = result_path_from_args(args)
    if not result_path.exists():
        raise FileNotFoundError(result_path)

    rows = load_jsonl(result_path)
    no_info_patterns = ("no information", "not mentioned", "not available", "cannot determine")

    enriched = []
    for row in rows:
        f1 = token_f1(row.get("answer", ""), row.get("prediction", ""))
        failure_type = classify(row, f1, no_info_patterns)
        metrics = row.get("_metrics") or {}
        display_f1 = f1
        if str(row.get("category")) == "5" and "not mentioned" in (row.get("prediction") or "").lower():
            display_f1 = 1.0
        enriched.append(
            {
                "line": row.get("_line_no"),
                "sample": row.get("sample") or row.get("sample_id") or args.sample or "",
                "category": row.get("category"),
                "question": row.get("question", ""),
                "gold": row.get("answer", ""),
                "prediction": row.get("prediction", ""),
                "f1": display_f1,
                "token_f1": f1,
                "failure_type": failure_type,
                "gold_evidence": row.get("evidence") or [],
                "prediction_context": row.get("prediction_context") or [],
                "tool_calls": metrics.get("tool_calls"),
                "runtime_sec": metrics.get("runtime_sec"),
                "raw": row,
            }
        )

    badcases = [
        r
        for r in enriched
        if (
            r["failure_type"] not in {"ok_or_needs_manual_review", "adversarial_correct_or_needs_check"}
            or r["f1"] < args.f1_threshold
        )
    ]
    badcases.sort(key=lambda r: (r["failure_type"].startswith("adversarial"), r["f1"], -(r.get("tool_calls") or 0)))
    badcases = badcases[: args.max_cases]

    by_cat = defaultdict(list)
    for r in enriched:
        by_cat[str(r["category"])].append(r["f1"])

    stamp = datetime.now().strftime("%Y%m%d")
    output = (
        Path(args.output)
        if args.output
        else Path("reports") / f"badcase_pack_{args.data}_{args.model}_{args.file}_{stamp}.md"
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Badcase Process Pack - {stamp}",
        "",
        "## Source",
        "",
        f"- result: `{result_path}`",
        f"- rows: {len(rows)}",
        f"- selected badcases: {len(badcases)}",
        f"- f1_threshold: {args.f1_threshold}",
        "",
        "## Category Summary",
        "",
        "| category | count | avg report score |",
        "| --- | ---: | ---: |",
    ]
    for cat in sorted(by_cat, key=lambda x: str(x)):
        vals = by_cat[cat]
        avg = sum(vals) / len(vals) if vals else 0.0
        lines.append(f"| {cat} | {len(vals)} | {avg:.4f} |")

    lines.extend(
        [
            "",
            "## Badcase Table",
            "",
            "| # | cat | f1 | type | tools | question | gold | prediction | gold evidence | retrieved context |",
            "| ---: | --- | ---: | --- | ---: | --- | --- | --- | --- | --- |",
        ]
    )
    for idx, r in enumerate(badcases, start=1):
        lines.append(
            "| {idx} | {cat} | {f1:.4f} | {typ} | {tools} | {q} | {gold} | {pred} | {ev} | {ctx} |".format(
                idx=idx,
                cat=r["category"],
                f1=r["f1"],
                typ=r["failure_type"],
                tools=r.get("tool_calls") if r.get("tool_calls") is not None else "",
                q=truncate(r["question"], 120).replace("|", "\\|"),
                gold=truncate(r["gold"], 120).replace("|", "\\|"),
                pred=truncate(r["prediction"], 160).replace("|", "\\|"),
                ev=", ".join(map(str, r["gold_evidence"])),
                ctx=", ".join(map(str, r["prediction_context"])),
            )
        )

    lines.extend(
        [
            "",
            "## Manual Review Checklist",
            "",
            "For each important badcase, add:",
            "",
            "- original conversation snippets for gold evidence ids;",
            "- rewrite sentences and keyword records for those ids;",
            "- full tool-call path from log files;",
            "- whether the error is retrieval miss, graph traversal issue, rewrite loss, image evidence loss, temporal calculation, model synthesis, or metric mismatch;",
            "- concrete code/prompt change to test next.",
            "",
            "This report is intentionally small enough to commit to GitHub. Large logs should be referenced by manifest path, size, and checksum.",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
