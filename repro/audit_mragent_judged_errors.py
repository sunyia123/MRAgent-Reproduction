#!/usr/bin/env python3
"""Audit every MRAgent judge-wrong answer or execution failure with trace references."""

from __future__ import annotations

import argparse
import csv
import glob
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


RELATIVE_TIME = re.compile(
    r"\b(yesterday|tomorrow|ago|last|next|before|after|week|month|year|monday|tuesday|"
    r"wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)
NO_INFORMATION = re.compile(r"no information|not available|not mentioned|cannot determine", re.IGNORECASE)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc
    return rows


def load_rows(pattern: str) -> list[dict[str, Any]]:
    paths = [Path(value) for value in sorted(glob.glob(pattern))]
    if not paths:
        raise FileNotFoundError(f"no files matched: {pattern}")
    rows = []
    for path in paths:
        for row in load_jsonl(path):
            row.setdefault("_source_file", str(path))
            rows.append(row)
    return rows


def load_manual_reviews(path: str | None) -> dict[tuple[str, int], dict[str, Any]]:
    if not path:
        return {}
    review_path = Path(path)
    if review_path.suffix.lower() == ".csv":
        with review_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    else:
        rows = load_jsonl(review_path)
    return {
        (str(row.get("sample_id", row.get("sample", ""))), int(row["question_index"])): row
        for row in rows
        if row.get("question_index") not in (None, "")
    }


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def normalized_origins(values: Any) -> set[str]:
    origins = set()
    for value in values or []:
        for match in re.findall(r"D\d+:\d+(?:-\d+)?", str(value)):
            origins.add(re.sub(r"-\d+$", "", match))
    return origins


def evidence_status(row: dict[str, Any]) -> tuple[bool, int, int]:
    gold = normalized_origins(row.get("evidence"))
    retrieved = normalized_origins(row.get("prediction_context"))
    return bool(gold & retrieved), len(gold), len(retrieved)


def result_key(row: dict[str, Any]) -> tuple[str, int] | None:
    sample_id = row.get("sample", row.get("sample_id"))
    question_index = row.get("question_index")
    if sample_id is None or question_index is None:
        return None
    return str(sample_id), int(question_index)


def judge_maps(rows: list[dict[str, Any]]) -> tuple[dict[tuple[str, int], int], dict[tuple[str, str], int]]:
    by_index: dict[tuple[str, int], int] = {}
    by_question: dict[tuple[str, str], int] = {}
    for row in rows:
        if row.get("llm_score") is None:
            continue
        sample_id = str(row.get("sample", row.get("sample_id", "")))
        score = int(row["llm_score"])
        if row.get("question_index") is not None:
            by_index[(sample_id, int(row["question_index"]))] = score
        if row.get("question") is not None:
            by_question[(sample_id, str(row["question"]))] = score
    return by_index, by_question


def is_execution_error(row: dict[str, Any] | None) -> bool:
    if row is None:
        return True
    prediction = str(row.get("prediction", "")).strip().lower()
    metrics = row.get("_metrics") or {}
    return prediction in {"", "error"} or bool(metrics.get("error"))


def adversarial_correct(row: dict[str, Any]) -> bool:
    return "not mentioned" in str(row.get("prediction", "")).lower()


def trace_inventory(trace_root: Path, sample_id: str, question_index: int, global_index: int) -> list[str]:
    sample_root = trace_root / sample_id
    if not sample_root.exists():
        return []
    prefixes = {f"q{question_index + 1:03d}_", f"q{global_index:03d}_"}
    return sorted(
        str(path) for path in sample_root.iterdir()
        if path.is_file() and any(path.name.startswith(prefix) for prefix in prefixes)
    )


def automatic_cause(
    row: dict[str, Any] | None,
    category: int,
    hit: bool,
    gold_count: int,
    trace_found: bool,
    manual: dict[str, Any],
) -> tuple[str, list[str], bool]:
    override = str(manual.get("primary_cause", "")).strip()
    if override:
        tags = [value.strip() for value in str(manual.get("secondary_tags", "")).split(";") if value.strip()]
        return override, tags, False
    if truthy(manual.get("semantic_correct")):
        return "judge_false_negative", ["semantic_answer_accepted_by_human"], False
    if is_execution_error(row):
        return "execution_or_schema_failure", [], False
    if str(manual.get("graph_evidence_present", "")).strip().lower() in {"0", "false", "no", "n"}:
        return "graph_construction_missing", [], False
    if truthy(manual.get("visual_evidence_missing")):
        return "visual_evidence_missing", [], False
    if gold_count == 0:
        return "gold_or_evidence_annotation_issue", [], True

    prediction = str((row or {}).get("prediction", ""))
    tool_calls = int(((row or {}).get("_metrics") or {}).get("tool_calls", 0) or 0)
    secondary = []
    if not trace_found:
        secondary.append("trace_missing")
    if not hit:
        if tool_calls == 0:
            return "initial_key_extraction_failure", secondary, True
        return "tool_selection_or_path_failure", secondary, True
    if NO_INFORMATION.search(prediction):
        return "evidence_retrieved_but_not_used", secondary, True
    if category == 2:
        if RELATIVE_TIME.search(prediction):
            secondary.append("relative_time_left_unresolved")
        return "temporal_reasoning_failure", secondary, True
    if category == 1:
        return "multi_hop_composition_failure", secondary, True
    return "answer_synthesis_failure", secondary, True


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else ["sample_id", "question_index"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--result_glob", required=True)
    parser.add_argument("--judge_glob", default=None)
    parser.add_argument("--trace_dir", required=True)
    parser.add_argument("--manual_review", default=None)
    parser.add_argument("--output_prefix", required=True)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    expected = {
        (str(row["sample_id"]), int(row["question_index"])): row
        for row in manifest.get("records", [])
    }
    result_rows = load_rows(args.result_glob)
    expected_by_question = {
        (key[0], str(record.get("question", ""))): key for key, record in expected.items()
    }
    results = {}
    for row in result_rows:
        key = result_key(row)
        if key is None:
            sample_id = str(row.get("sample", row.get("sample_id", "")))
            key = expected_by_question.get((sample_id, str(row.get("question", ""))))
        if key is not None:
            results[key] = row
    judge_rows = load_rows(args.judge_glob) if args.judge_glob else []
    judge_by_index, judge_by_question = judge_maps(judge_rows)
    manual_reviews = load_manual_reviews(args.manual_review)
    trace_root = Path(args.trace_dir)

    cases = []
    missing_judge = 0
    for key, record in expected.items():
        row = results.get(key)
        question = str((row or record).get("question", ""))
        judge_score = judge_by_index.get(key, judge_by_question.get((key[0], question)))
        category = int((row or record).get("category"))
        execution_error = is_execution_error(row)
        judged_wrong = category == 5 and row is not None and not adversarial_correct(row)
        if category != 5:
            if judge_score is None and not execution_error:
                missing_judge += 1
            judged_wrong = judge_score == 0
        if not (execution_error or judged_wrong):
            continue

        effective_row = row or {**record, "prediction": "ERROR", "prediction_context": [], "_metrics": {}}
        hit, gold_count, retrieved_count = evidence_status(effective_row)
        trace_files = trace_inventory(
            trace_root, key[0], key[1], int(record.get("global_index", key[1] + 1)))
        manual = manual_reviews.get(key, {})
        metrics = effective_row.get("_metrics") or {}
        inline_trace = metrics.get("tool_trace") or []
        primary, secondary, manual_needed = automatic_cause(
            effective_row, category, hit, gold_count, bool(trace_files or inline_trace), manual)
        cases.append({
            "sample_id": key[0],
            "question_index": key[1],
            "question_index_1based": key[1] + 1,
            "global_index": record.get("global_index"),
            "category": category,
            "primary_cause": primary,
            "secondary_tags": ";".join(secondary),
            "manual_review_needed": manual_needed,
            "judge_score": judge_score,
            "execution_error": execution_error,
            "evidence_hit": hit,
            "gold_evidence_count": gold_count,
            "retrieved_context_count": retrieved_count,
            "tool_calls": metrics.get("tool_calls", 0),
            "runtime_sec": metrics.get("runtime_sec"),
            "question": question,
            "answer": effective_row.get("answer", record.get("answer")),
            "prediction": effective_row.get("prediction"),
            "evidence": json.dumps(effective_row.get("evidence", record.get("evidence", [])), ensure_ascii=False),
            "prediction_context": json.dumps(effective_row.get("prediction_context", []), ensure_ascii=False),
            "result_file": effective_row.get("_source_file", "missing result row"),
            "trace_files": json.dumps(trace_files, ensure_ascii=False),
            "inline_tool_trace": json.dumps(inline_trace, ensure_ascii=False),
            "manual_note": manual.get("note", ""),
        })

    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    jsonl_path = prefix.with_suffix(".jsonl")
    jsonl_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in cases), encoding="utf-8")
    write_csv(prefix.with_suffix(".csv"), cases)

    review_rows = [{
        "sample_id": row["sample_id"],
        "question_index": row["question_index"],
        "semantic_correct": "",
        "graph_evidence_present": "",
        "visual_evidence_missing": "",
        "primary_cause": row["primary_cause"],
        "secondary_tags": row["secondary_tags"],
        "note": "",
    } for row in cases]
    write_csv(prefix.parent / f"{prefix.name}_manual_review.csv", review_rows)

    counts = Counter(row["primary_cause"] for row in cases)
    by_category: dict[int, Counter[str]] = defaultdict(Counter)
    for row in cases:
        by_category[int(row["category"])][row["primary_cause"]] += 1
    total = len(expected)
    lines = [
        "# MRAgent 全量判错归因",
        "",
        f"- 题目总数：{total}",
        f"- Judge 判错或执行失败：{len(cases)}",
        f"- 非错误但缺少 Judge 结果：{missing_judge}",
        f"- Trace 目录：`{args.trace_dir}`",
        "",
        "## 主因分布",
        "",
        "| 主因 | 错例数 | 占全部错例 | 占全部题目 |",
        "|---|---:|---:|---:|",
    ]
    for cause, count in counts.most_common():
        lines.append(
            f"| {cause} | {count} | {count / max(1, len(cases)):.1%} | {count / max(1, total):.1%} |")
    lines.extend(["", "## 分类别主因", ""])
    for category in sorted(by_category):
        summary = ", ".join(f"{cause}={count}" for cause, count in by_category[category].most_common())
        lines.append(f"- Category {category}: {summary}")
    lines.extend([
        "",
        "## 解释边界",
        "",
        "- 自动归因只使用可观察证据；`manual_review_needed=true` 的主因不是最终因果结论。",
        "- `judge_false_negative` 只有在人工复核标记 `semantic_correct=true` 后才能成立。",
        "- 图构建缺失、视觉证据缺失和路径过早停止不能凭 F1 猜测，必须查看图快照与完整 trace。",
    ])
    prefix.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "total": total,
        "cases": len(cases),
        "missing_judge": missing_judge,
        "cause_counts": dict(counts),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
