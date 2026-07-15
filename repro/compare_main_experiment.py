#!/usr/bin/env python3
"""Compare aligned LoCoMo methods and report conversation-clustered confidence intervals."""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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


def evidence_hit(row: dict[str, Any]) -> float:
    def origins(values: Any) -> set[str]:
        result = set()
        for value in values or []:
            for match in re.findall(r"D\d+:\d+(?:-\d+)?", str(value)):
                result.add(re.sub(r"-\d+$", "", match))
        return result

    gold = origins(row.get("evidence"))
    return float(bool(gold & origins(row.get("prediction_context")))) if gold else 0.0


def result_key(row: dict[str, Any]) -> tuple[str, int] | None:
    sample_id = row.get("sample", row.get("sample_id"))
    question_index = row.get("question_index")
    if sample_id is None or question_index is None:
        return None
    return str(sample_id), int(question_index)


def load_method_rows(
    data: str,
    model: str,
    tag: str,
    sample_ids: list[str],
    expected_by_question: dict[tuple[str, str], tuple[str, int]],
) -> dict[tuple[str, int], dict[str, Any]]:
    rows = {}
    for sample_id in sample_ids:
        path = Path("result") / data / f"{sample_id}_result_{model}_{tag}.jsonl"
        for row in load_jsonl(path):
            key = result_key(row)
            if key is None:
                key = expected_by_question.get((sample_id, str(row.get("question", ""))))
            if key is not None:
                rows[key] = row
    return rows


def load_judge(tag: str, data: str, model: str) -> tuple[dict[tuple[str, int], int], dict[tuple[str, str], int]]:
    rows = load_jsonl(Path(f"result_judge_{data}_{model}_{tag}.jsonl"))
    by_index, by_question = {}, {}
    for row in rows:
        if row.get("llm_score") is None:
            continue
        sample_id = str(row.get("sample", row.get("sample_id", "")))
        if row.get("question_index") is not None:
            by_index[(sample_id, int(row["question_index"]))] = int(row["llm_score"])
        if row.get("question") is not None:
            by_question[(sample_id, str(row["question"]))] = int(row["llm_score"])
    return by_index, by_question


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def fmt(value: float | None) -> str:
    return "NA" if value is None else f"{value:.4f}"


def clustered_delta_ci(
    full: dict[tuple[str, int], float],
    other: dict[tuple[str, int], float],
    sample_ids: list[str],
    seed: int = 42,
    iterations: int = 5000,
) -> tuple[float | None, float | None, float | None, int]:
    common = set(full) & set(other)
    clusters = {
        sample_id: [key for key in common if key[0] == sample_id]
        for sample_id in sample_ids
    }
    clusters = {sample_id: keys for sample_id, keys in clusters.items() if keys}
    if not clusters:
        return None, None, None, 0
    observed = mean([full[key] - other[key] for key in common])
    rng = random.Random(seed)
    cluster_names = list(clusters)
    boot = []
    for _ in range(iterations):
        sampled = [rng.choice(cluster_names) for _ in cluster_names]
        values = [
            full[key] - other[key]
            for sample_id in sampled for key in clusters[sample_id]
        ]
        boot.append(sum(values) / len(values))
    boot.sort()
    low = boot[int(0.025 * (iterations - 1))]
    high = boot[int(0.975 * (iterations - 1))]
    return observed, low, high, len(common)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--methods", required=True, help="Comma-separated label=tag pairs; first is Full MRAgent")
    parser.add_argument("--data", default="locomo")
    parser.add_argument("--model", default="deepseek")
    parser.add_argument("--output_prefix", required=True)
    parser.add_argument("--bootstrap_iterations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    expected = {
        (str(row["sample_id"]), int(row["question_index"])): row
        for row in manifest.get("records", [])
    }
    expected_by_question = {
        (key[0], str(record.get("question", ""))): key for key, record in expected.items()
    }
    methods = []
    for item in args.methods.split(","):
        label, separator, tag = item.strip().partition("=")
        if not separator:
            raise ValueError(f"method must use label=tag: {item}")
        methods.append((label, tag))
    sample_ids = [str(value) for value in manifest.get("sample_ids", [])]

    rows_by_method = {}
    judges_by_method = {}
    aligned_rows = []
    scores_by_method: dict[str, dict[tuple[str, int], float]] = defaultdict(dict)
    judges_for_ci: dict[str, dict[tuple[str, int], float]] = defaultdict(dict)
    summary = {}

    for label, tag in methods:
        rows = load_method_rows(args.data, args.model, tag, sample_ids, expected_by_question)
        judge_by_index, judge_by_question = load_judge(tag, args.data, args.model)
        rows_by_method[label] = rows
        judges_by_method[label] = (judge_by_index, judge_by_question)
        f1_values, judge_values, cat5_values = [], [], []
        hits, tools, rounds, runtimes, contexts = [], [], [], [], []
        category_f1: dict[int, list[float]] = defaultdict(list)
        category_judge: dict[int, list[float]] = defaultdict(list)
        category_hits: dict[int, list[float]] = defaultdict(list)
        errors = 0
        for key, record in expected.items():
            row = rows.get(key)
            if row is None:
                continue
            prediction = str(row.get("prediction", ""))
            if prediction.upper() == "ERROR" or not prediction:
                errors += 1
            category = int(row.get("category", record.get("category")))
            score = (1.0 if "not mentioned" in prediction.lower() else 0.0) if category == 5 else lexical_f1(prediction, row.get("answer"))
            if category == 5:
                cat5_values.append(score)
                category_f1[category].append(score)
            else:
                f1_values.append(score)
                category_f1[category].append(score)
                scores_by_method[label][key] = score
                judge = judge_by_index.get(key, judge_by_question.get((key[0], str(row.get("question", "")))))
                if judge is not None:
                    judge_values.append(float(judge))
                    category_judge[category].append(float(judge))
                    judges_for_ci[label][key] = float(judge)
            metrics = row.get("_metrics") or {}
            hit = evidence_hit(row)
            hits.append(hit)
            category_hits[category].append(hit)
            tools.append(float(metrics.get("tool_calls", 0) or 0))
            rounds.append(float(metrics.get("reasoning_rounds", 0) or 0))
            if metrics.get("runtime_sec") is not None:
                runtimes.append(float(metrics["runtime_sec"]))
            contexts.append(float(len(row.get("prediction_context") or [])))
            aligned_rows.append({
                "sample_id": key[0], "question_index": key[1], "category": category,
                "method": label, "tag": tag, "f1_or_cat5": round(score, 6),
                "judge": judges_for_ci[label].get(key), "evidence_hit": evidence_hit(row),
                "prediction": prediction, "answer": row.get("answer"),
            })
        completed = sum(1 for key in expected if key in rows)
        summary[label] = {
            "tag": tag, "completed": completed, "expected": len(expected),
            "extra_rows": len(set(rows) - set(expected)), "errors": errors,
            "ordinary_f1": mean(f1_values), "ordinary_judge": mean(judge_values),
            "cat5_accuracy": mean(cat5_values), "evidence_hit": mean(hits),
            "avg_tool_calls": mean(tools), "avg_reasoning_rounds": mean(rounds),
            "avg_runtime_sec": mean(runtimes),
            "avg_context_items": mean(contexts), "judge_count": len(judge_values),
            "category_f1": {str(category): mean(values) for category, values in sorted(category_f1.items())},
            "category_judge": {str(category): mean(values) for category, values in sorted(category_judge.items())},
            "category_evidence_hit": {str(category): mean(values) for category, values in sorted(category_hits.items())},
        }

    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    with prefix.with_suffix(".csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(aligned_rows[0]) if aligned_rows else ["method"])
        writer.writeheader()
        writer.writerows(aligned_rows)

    full_label = methods[0][0]
    lines = [
        "# LoCoMo 500 题主实验对比",
        "",
        f"- Manifest: `{args.manifest}`",
        f"- 主参照方法: `{full_label}`",
        f"- Conversation-clustered bootstrap: {args.bootstrap_iterations} 次",
        "",
        "## 总表",
        "",
        "| 方法 | 完成 | 额外行 | ERROR | 普通题 F1 | 普通题 Judge | Cat5 | Evidence hit | Tools | Rounds | Runtime(s) | Context |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, _ in methods:
        item = summary[label]
        lines.append(
            f"| {label} | {item['completed']}/{item['expected']} | {item['extra_rows']} | {item['errors']} | "
            f"{fmt(item['ordinary_f1'])} | {fmt(item['ordinary_judge'])} ({item['judge_count']}) | "
            f"{fmt(item['cat5_accuracy'])} | {fmt(item['evidence_hit'])} | "
            f"{fmt(item['avg_tool_calls'])} | {fmt(item['avg_reasoning_rounds'])} | "
            f"{fmt(item['avg_runtime_sec'])} | {fmt(item['avg_context_items'])} |")

    lines.extend([
        "", "## 分类别结果", "",
        "| 方法 | 类别 | F1/Accuracy | Judge | Evidence hit |",
        "|---|---:|---:|---:|---:|",
    ])
    for label, _ in methods:
        item = summary[label]
        for category in range(1, 6):
            key = str(category)
            lines.append(
                f"| {label} | {category} | {fmt(item['category_f1'].get(key))} | "
                f"{fmt(item['category_judge'].get(key))} | {fmt(item['category_evidence_hit'].get(key))} |")

    lines.extend(["", "## 相对 Full MRAgent 的配对差值", "", "正值表示 Full MRAgent 更好。", "",
                  "| 对比 | 指标 | 配对题数 | 差值 | 95% CI |", "|---|---|---:|---:|---:|"])
    for label, _ in methods[1:]:
        for metric, values in (("F1", scores_by_method), ("Judge", judges_for_ci)):
            delta, low, high, count = clustered_delta_ci(
                values[full_label], values[label], sample_ids, args.seed, args.bootstrap_iterations)
            lines.append(f"| {full_label} - {label} | {metric} | {count} | {fmt(delta)} | [{fmt(low)}, {fmt(high)}] |")

    lines.extend([
        "", "## 判定规则", "",
        "- 只有同题、同模型、完整输出的配对结果进入差值；缺题和 ERROR 必须单独报告，不能静默删除。",
        "- 95% CI 不跨 0 才视为当前 10 个 conversation 上的稳定差异；这仍不是论文 50 conversation 的完整复现。",
        "- 普通题统计 cat1-4；cat5 单列，不与论文排除 adversarial 的主表混算。",
    ])
    prefix.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    prefix.with_suffix(".json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(prefix.with_suffix(".md"))


if __name__ == "__main__":
    main()
