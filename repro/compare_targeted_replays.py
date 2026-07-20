#!/usr/bin/env python3
"""Compare a targeted replay with the original result rows it repairs."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


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


def result_key(row: dict[str, Any]) -> tuple[str, int] | None:
    sample_id = row.get("sample", row.get("sample_id"))
    question_index = row.get("question_index")
    if sample_id is None or question_index is None:
        return None
    return str(sample_id), int(question_index)


def load_result_map(root: Path, data: str, model: str, tag: str, samples: list[str]):
    rows = {}
    for sample_id in samples:
        path = root / data / f"{sample_id}_result_{model}_{tag}.jsonl"
        for row in load_jsonl(path):
            key = result_key(row)
            if key is not None:
                rows[key] = row
    return rows


def is_execution_error(row: dict[str, Any] | None) -> bool:
    if row is None:
        return True
    prediction = str(row.get("prediction", "")).strip()
    return not prediction or prediction.upper() == "ERROR"


def content_tool_error_count(row: dict[str, Any] | None) -> int:
    if row is None:
        return 0
    trace = (row.get("_metrics") or {}).get("tool_trace") or []
    return sum(
        1 for item in trace
        if item.get("tool") in CONTENT_TOOLS and item.get("error")
    )


def context_fields_complete(row: dict[str, Any] | None) -> bool:
    metrics = (row or {}).get("_metrics") or {}
    return all(isinstance(metrics.get(field), list) for field in (
        "initial_context_ids", "tool_context_ids", "final_context_ids"))


def lexical_f1(prediction: Any, answer: Any) -> float:
    def tokens(value: Any) -> list[str]:
        return re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", " ", str(value or "").lower()).split()

    pred, gold = tokens(prediction), tokens(answer)
    if not pred and not gold:
        return 1.0
    if not pred or not gold:
        return 0.0
    overlap = sum((Counter(pred) & Counter(gold)).values())
    return 0.0 if not overlap else 2 * overlap / (len(pred) + len(gold))


def replay_score(prediction: Any, answer: Any, category: Any) -> float:
    if int(category) == 5:
        return float("not mentioned" in str(prediction or "").lower())
    return lexical_f1(prediction, answer)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--after_tag", required=True)
    parser.add_argument("--before_tag", default=None)
    parser.add_argument("--result_root", default="result")
    parser.add_argument("--data", default="locomo")
    parser.add_argument("--model", default="deepseek")
    parser.add_argument("--output_prefix", required=True)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    records = manifest.get("records", [])
    expected = {
        (str(row["sample_id"]), int(row["question_index"])): row
        for row in records
    }
    samples = sorted({key[0] for key in expected})
    before_tag = args.before_tag or manifest.get("source_result_tag")
    if not before_tag:
        raise ValueError("before tag is absent; pass --before_tag or use a generated replay manifest")

    result_root = Path(args.result_root)
    before = load_result_map(result_root, args.data, args.model, before_tag, samples)
    after = load_result_map(result_root, args.data, args.model, args.after_tag, samples)

    detail = []
    for key, record in expected.items():
        old, new = before.get(key), after.get(key)
        answer = (new or old or record).get("answer")
        category = record.get("category")
        old_f1 = replay_score((old or {}).get("prediction"), answer, category) if old else None
        new_f1 = replay_score((new or {}).get("prediction"), answer, category) if new else None
        detail.append({
            "sample_id": key[0],
            "question_index": key[1],
            "category": category,
            "replay_reasons": record.get("replay_reasons", []),
            "before_present": old is not None,
            "after_present": new is not None,
            "before_error": is_execution_error(old),
            "after_error": is_execution_error(new),
            "before_content_tool_errors": content_tool_error_count(old),
            "after_content_tool_errors": content_tool_error_count(new),
            "after_context_fields_complete": context_fields_complete(new),
            "before_f1": old_f1,
            "after_f1": new_f1,
            "f1_delta": None if old_f1 is None or new_f1 is None else new_f1 - old_f1,
            "before_prediction": (old or {}).get("prediction"),
            "after_prediction": (new or {}).get("prediction"),
        })

    summary = {
        "manifest": args.manifest,
        "before_tag": before_tag,
        "after_tag": args.after_tag,
        "expected": len(expected),
        "before_present": sum(item["before_present"] for item in detail),
        "after_present": sum(item["after_present"] for item in detail),
        "before_execution_errors": sum(item["before_error"] for item in detail),
        "after_execution_errors": sum(item["after_error"] for item in detail),
        "before_content_tool_error_calls": sum(item["before_content_tool_errors"] for item in detail),
        "after_content_tool_error_calls": sum(item["after_content_tool_errors"] for item in detail),
        "after_context_fields_complete": sum(item["after_context_fields_complete"] for item in detail),
    }
    requires_content_repair = any(
        "content_tool_error" in item["replay_reasons"] for item in detail)
    failures = []
    if summary["after_present"] != summary["expected"]:
        failures.append("replay rows are incomplete")
    if summary["after_execution_errors"]:
        failures.append("execution ERROR remains after replay")
    if requires_content_repair and summary["after_content_tool_error_calls"]:
        failures.append("content-tool errors remain after replay")
    if summary["after_context_fields_complete"] != summary["expected"]:
        failures.append("active context id fields are incomplete")
    summary["failures"] = failures

    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    prefix.with_suffix(".json").write_text(
        json.dumps({"summary": summary, "questions": detail}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# 定向重跑前后对照",
        "",
        f"- Manifest: `{args.manifest}`",
        f"- 修复前 tag: `{before_tag}`",
        f"- 修复后 tag: `{args.after_tag}`",
        f"- 完成: {summary['after_present']}/{summary['expected']}",
        f"- 执行 ERROR: {summary['before_execution_errors']} -> {summary['after_execution_errors']}",
        f"- 内容工具错误调用: {summary['before_content_tool_error_calls']} -> {summary['after_content_tool_error_calls']}",
        f"- 新上下文字段完整: {summary['after_context_fields_complete']}/{summary['expected']}",
        "",
        "| Sample | Q | 原因 | Before ERROR | After ERROR | 工具错误 | F1 变化 |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for item in detail:
        delta = "NA" if item["f1_delta"] is None else f"{item['f1_delta']:+.4f}"
        lines.append(
            f"| {item['sample_id']} | {item['question_index']} | "
            f"{', '.join(item['replay_reasons'])} | {int(item['before_error'])} | "
            f"{int(item['after_error'])} | {item['after_content_tool_errors']} | {delta} |"
        )
    prefix.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
