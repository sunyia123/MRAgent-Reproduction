#!/usr/bin/env python3
"""Create auditable, mutually exclusive bad-case attributions from result JSONLs."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


RELATIVE_TIME = re.compile(
    r"\b(yesterday|tomorrow|last (week|month|year|friday|monday|tuesday|wednesday|thursday|saturday|sunday)|next (week|month|year|friday|monday|tuesday|wednesday|thursday|saturday|sunday)|ago)\b",
    re.IGNORECASE,
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_judge_scores(path: str | None) -> dict[tuple[str, str], int]:
    if not path:
        return {}
    return {
        (str(row.get("sample", row.get("sample_id", ""))), str(row.get("question", ""))): int(row["llm_score"])
        for row in load_jsonl(Path(path))
        if row.get("llm_score") is not None
    }


def load_manual_reviews(path: str | None) -> dict[tuple[str, int], dict[str, Any]]:
    if not path:
        return {}
    review_path = Path(path)
    if review_path.suffix.lower() == ".csv":
        with review_path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
    else:
        rows = load_jsonl(review_path)
    return {
        (str(row.get("sample_id", row.get("sample", ""))), int(row["question_index"])): row
        for row in rows
        if row.get("question_index") not in (None, "")
    }


def is_true(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def tokens(text: Any) -> list[str]:
    return re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", " ", str(text or "").lower()).split()


def lexical_f1(row: dict[str, Any]) -> float:
    if str(row.get("category")) == "5":
        return 1.0 if "not mentioned" in str(row.get("prediction", "")).lower() else 0.0
    prediction, answer = tokens(row.get("prediction")), tokens(row.get("answer"))
    if not prediction or not answer:
        return 0.0
    counts = Counter(prediction)
    overlap = 0
    for token in answer:
        if counts[token]:
            counts[token] -= 1
            overlap += 1
    return 0.0 if not overlap else 2 * overlap / (len(prediction) + len(answer))


def evidence_hit(row: dict[str, Any]) -> bool:
    contexts = [str(value) for value in row.get("prediction_context") or []]
    evidence = [str(value) for value in row.get("evidence") or []]
    return bool(evidence) and any(
        context == item or context.startswith(item + "-")
        for item in evidence for context in contexts
    )


def is_likely_format_mismatch(row: dict[str, Any]) -> bool:
    prediction, answer = set(tokens(row.get("prediction"))), set(tokens(row.get("answer")))
    return bool(prediction and answer) and (answer <= prediction or prediction <= answer)


def primary_cause(
    row: dict[str, Any],
    score: float,
    hit: bool,
    badcase_f1: float,
    judge_score: int | None,
    manual_semantic_correct: bool,
) -> str:
    prediction = str(row.get("prediction", ""))
    category = str(row.get("category"))
    evidence = row.get("evidence") or []
    if prediction == "ERROR":
        return "execution_error"
    if manual_semantic_correct and judge_score == 0:
        return "semantic_correct_judge_false_negative"
    if score < badcase_f1 and (manual_semantic_correct or judge_score == 1):
        return "semantic_correct_lexical_false_negative"
    if category == "5" and "not mentioned" not in prediction.lower():
        return "adversarial_overanswer"
    if not evidence:
        return "no_annotated_evidence"
    if not hit:
        return "retrieval_miss"
    if category == "2" and RELATIVE_TIME.search(prediction):
        return "temporal_normalization_failure"
    if "no information available" in prediction.lower():
        return "evidence_utilization_failure"
    if is_likely_format_mismatch(row):
        return "likely_metric_or_format_mismatch"
    return "answer_synthesis_or_semantic_error"


def trace_status(row: dict[str, Any], trace_root: Path) -> tuple[bool, int]:
    trace = row.get("_metrics", {}).get("tool_trace") or []
    if trace:
        return True, len(trace)
    sample = row.get("sample")
    index = row.get("question_index")
    if sample is not None and index is not None:
        legacy = trace_root / str(sample) / f"q{int(index) + 1:03d}_trace.json"
        if legacy.exists():
            return True, int(row.get("_metrics", {}).get("tool_calls", 0))
    return False, int(row.get("_metrics", {}).get("tool_calls", 0))


def main() -> None:
    parser = argparse.ArgumentParser(description="Attribute MRAgent bad cases using observable evidence.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--result_tag", required=True, help="Result suffix, e.g. graphbuild_100q")
    parser.add_argument("--model", default="deepseek")
    parser.add_argument("--data", default="locomo")
    parser.add_argument("--badcase_f1", type=float, default=0.8)
    parser.add_argument("--judge_results", default=None, help="Optional judge JSONL with sample, question and llm_score.")
    parser.add_argument(
        "--manual_review",
        default=None,
        help="Optional CSV/JSONL with sample_id, question_index and semantic_correct.",
    )
    parser.add_argument("--trace_dir", default="result/diagnostics/mragent_100q_traces")
    parser.add_argument("--output_prefix", required=True)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    expected = {
        (record["sample_id"], int(record["question_index"])): record
        for record in manifest.get("records", [])
    }
    rows_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    judge_scores = load_judge_scores(args.judge_results)
    manual_reviews = load_manual_reviews(args.manual_review)
    for sample_id in manifest.get("sample_ids", []):
        path = Path("result") / args.data / f"{sample_id}_result_{args.model}_{args.result_tag}.jsonl"
        for row in load_jsonl(path):
            if row.get("question_index") is not None:
                rows_by_key[(sample_id, int(row["question_index"]))] = row

    cases = []
    trace_root = Path(args.trace_dir)
    for key, record in expected.items():
        row = rows_by_key.get(key)
        if row is None:
            row = {
                **record,
                "prediction": "ERROR",
                "prediction_context": [],
                "_metrics": {"tool_calls": 0},
            }
        score = lexical_f1(row)
        judge_score = judge_scores.get((key[0], str(row.get("question", record.get("question", "")))))
        manual_review = manual_reviews.get(key, {})
        manual_semantic_correct = is_true(manual_review.get("semantic_correct"))
        judge_false_negative = manual_semantic_correct and judge_score == 0
        if score >= args.badcase_f1 and row.get("prediction") != "ERROR" and not judge_false_negative:
            continue
        hit = evidence_hit(row)
        trace_found, trace_calls = trace_status(row, trace_root)
        cause = primary_cause(row, score, hit, args.badcase_f1, judge_score, manual_semantic_correct)
        cases.append(
            {
                "sample_id": row.get("sample", key[0]),
                "question_index": row.get("question_index", key[1]),
                "category": row.get("category"),
                "primary_cause": cause,
                "lexical_f1": round(score, 4),
                "llm_judge_score": judge_score,
                "manual_semantic_correct": manual_semantic_correct,
                "manual_review_note": manual_review.get("note", ""),
                "evidence_hit": hit,
                "tool_calls": row.get("_metrics", {}).get("tool_calls", 0),
                "tool_trace_calls": trace_calls,
                "trace_found": trace_found,
                "question": row.get("question", record.get("question")),
                "answer": row.get("answer", record.get("answer")),
                "prediction": row.get("prediction"),
                "evidence": json.dumps(row.get("evidence") or [], ensure_ascii=False),
                "prediction_context": json.dumps(row.get("prediction_context") or [], ensure_ascii=False),
                "manual_review_needed": cause in {
                    "answer_synthesis_or_semantic_error",
                    "likely_metric_or_format_mismatch",
                    "no_annotated_evidence",
                    "semantic_correct_judge_false_negative",
                },
            }
        )

    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    csv_path = prefix.with_suffix(".csv")
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(cases[0]) if cases else ["primary_cause"])
        writer.writeheader()
        writer.writerows(cases)

    by_cause = Counter(case["primary_cause"] for case in cases)
    by_category: dict[str, Counter[str]] = defaultdict(Counter)
    for case in cases:
        by_category[str(case["category"])][case["primary_cause"]] += 1
    total = len(cases)
    report = [
        "# Bad-case Attribution",
        "",
        f"- manifest: `{args.manifest}`",
        f"- result tag: `{args.result_tag}`",
        f"- completed rows: {len(rows_by_key)} / {len(expected)}",
        f"- bad-case threshold: lexical F1 < {args.badcase_f1}",
        f"- bad cases: {total}",
        "",
        "## Primary Attribution",
        "",
        "| cause | count | share of bad cases |",
        "| --- | ---: | ---: |",
    ]
    for cause, count in by_cause.most_common():
        report.append(f"| {cause} | {count} | {count / total:.1%} |")
    report.extend(["", "## By Question Category", ""])
    for category in sorted(by_category, key=str):
        parts = ", ".join(f"{cause}={count}" for cause, count in by_category[category].most_common())
        report.append(f"- cat{category}: {parts}")
    report.extend(
        [
            "",
            "## Interpretation Rules",
            "",
            "- `retrieval_miss` means annotated evidence was not present in prediction_context; it is an observable retrieval failure.",
            "- `temporal_normalization_failure` means evidence was retrieved but the prediction retained a relative date; it is a synthesis/context-metadata failure.",
            "- `likely_metric_or_format_mismatch` and `answer_synthesis_or_semantic_error` require human or LLM-judge review before being claimed as final semantic causes.",
            "- `semantic_correct_lexical_false_negative` means lexical F1 is below the threshold but the LLM judge or human review accepts the answer.",
            "- `semantic_correct_judge_false_negative` requires `manual_review` evidence that the answer is semantically correct while the judge rejects it.",
            "- The CSV keeps raw question, answer, prediction, evidence and trace availability for that review.",
        ]
    )
    md_path = prefix.with_suffix(".md")
    md_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(csv_path)
    print(md_path)


if __name__ == "__main__":
    main()
