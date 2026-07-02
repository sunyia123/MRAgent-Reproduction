import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root on path for standalone runs
import json
import argparse
import numbers
import time
import re
from pathlib import Path
from collections import defaultdict
from eval.evaluation import f1_score
from eval.judge import evaluate_llm_judge


def parse_args():
    p = argparse.ArgumentParser(description="F1 + LLM-judge evaluation (dataset-agnostic: locomo / LM).")
    p.add_argument("--data", type=str, default="locomo", help="Dataset name (locomo / LM)")
    p.add_argument("--model", type=str, default="gemini", help="Chat model short name")
    p.add_argument("--file", type=str, default="0", help="Run/experiment tag")
    p.add_argument("--allfile", action="store_true", help="Aggregate all result files for the run")
    p.add_argument("--sample", type=str, default=None, help="Single sample id (used when --allfile is not set)")
    p.add_argument("--f1_only", action="store_true", help="Skip LLM judge; only compute F1 scores")
    p.add_argument("--no_llm_judge", action="store_true", help="Alias for --f1_only")
    return p.parse_args()


def load_results(data, model, file, allfile, sample):
    """Read result jsonl into a flat list. Pattern matches both locomo (conv-*) and LM (hex) sample ids."""
    root = Path(f"result/{data}")
    if allfile:
        files = sorted(root.glob(f"*_result_{model}_{file}.jsonl"))
    else:
        files = [root / f"{sample}_result_{model}_{file}.jsonl"]
    rows = []
    for fp in files:
        if not fp.exists():
            continue
        with fp.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def is_adversarial(category):
    # locomo category 5 = adversarial: gold answer is "not mentioned"; scored by string match, not F1/LLM-judge
    return category == 5


def extract_metrics_from_result_rows(rows):
    """Extract per-question metrics from result rows (populated by instrumented run)."""
    metrics = {
        "tool_calls": [],
        "schema_retries": [],
        "forced_accepts": [],
        "runtime_sec": [],
        "total_runtime_sec": 0.0,
    }
    for r in rows:
        meta = r.get("_metrics", {})
        if meta:
            metrics["tool_calls"].append(meta.get("tool_calls", 0))
            metrics["schema_retries"].append(meta.get("schema_retries", 0))
            metrics["forced_accepts"].append(meta.get("forced_accepts", 0))
            metrics["runtime_sec"].append(meta.get("runtime_sec", 0.0))
    if metrics["runtime_sec"]:
        metrics["total_runtime_sec"] = sum(metrics["runtime_sec"])
    return metrics


def print_metrics_summary(rows, metrics):
    """Print a structured metrics summary."""
    samples = set(r.get("sample", "?") for r in rows)
    n_questions = len(rows)
    n_samples = len(samples)

    print("\n" + "=" * 60)
    print("METRICS SUMMARY")
    print("=" * 60)
    print(f"  samples            : {n_samples}")
    print(f"  total questions    : {n_questions}")

    # category breakdown
    cat_counts = defaultdict(int)
    for r in rows:
        cat_counts[r.get("category", "?")] += 1
    print(f"  category breakdown :")
    for cat in sorted(cat_counts, key=str):
        print(f"    cat {cat}: {cat_counts[cat]} questions")

    # tool calls
    tc = metrics["tool_calls"]
    if tc:
        print(f"  tool calls / q     : avg={sum(tc)/len(tc):.1f}  min={min(tc)}  max={max(tc)}")
    else:
        print(f"  tool calls / q     : (not instrumented)")

    # schema retries
    sr = metrics["schema_retries"]
    if sr:
        print(f"  schema retries / q : avg={sum(sr)/len(sr):.1f}  min={min(sr)}  max={max(sr)}  total={sum(sr)}")
    else:
        print(f"  schema retries / q : (not instrumented)")

    # forced accepts
    fa = metrics["forced_accepts"]
    if fa:
        print(f"  forced accepts / q : avg={sum(fa)/len(fa):.1f}  total={sum(fa)}")
    else:
        print(f"  forced accepts / q : (not instrumented)")

    # runtime
    rt = metrics["runtime_sec"]
    if rt:
        total_sec = metrics["total_runtime_sec"]
        print(f"  runtime / q        : avg={sum(rt)/len(rt):.1f}s  min={min(rt):.1f}s  max={max(rt):.1f}s")
        if total_sec >= 3600:
            print(f"  total runtime      : {total_sec/3600:.2f}h")
        elif total_sec >= 60:
            print(f"  total runtime      : {total_sec/60:.1f}min")
        else:
            print(f"  total runtime      : {total_sec:.1f}s")
    else:
        print(f"  runtime / q        : (not instrumented)")

    # errors
    errors = [r for r in rows if r.get("prediction") == "ERROR"]
    print(f"  errors             : {len(errors)}/{n_questions}")

    # F1 by category
    print("\n  F1 by category:")
    f1_by_cat = defaultdict(list)
    for r in rows:
        prediction, reference, category = r["prediction"], r["answer"], r["category"]
        if is_adversarial(category):
            f1_by_cat[category].append(1 if "Not mentioned" in str(prediction) else 0)
            continue
        if isinstance(prediction, numbers.Number):
            prediction = str(prediction)
        if isinstance(reference, numbers.Number):
            reference = str(reference)
        f1_by_cat[category].append(f1_score(prediction, reference))
    for cat in sorted(f1_by_cat, key=str):
        v = f1_by_cat[cat]
        print(f"    cat {cat}: n={len(v)}  F1={sum(v)/len(v):.4f}")

    # overall F1
    all_f1 = [x for v in f1_by_cat.values() for x in v]
    if all_f1:
        print(f"    OVERALL F1: {sum(all_f1)/len(all_f1):.4f}")

    # LLM judge scores
    judge_path = f"result_judge_{args.data}_{args.model}_{args.file}.jsonl"
    if Path(judge_path).exists():
        judge_by_cat = defaultdict(list)
        with open(judge_path, encoding="utf-8") as jf:
            for line in jf:
                line = line.strip()
                if line:
                    jr = json.loads(line)
                    judge_by_cat[jr.get("category", "?")].append(jr.get("llm_score", 0))
        print("\n  LLM-judge accuracy by category:")
        total_ok = total = 0
        for cat in sorted(judge_by_cat, key=str):
            v = judge_by_cat[cat]
            total_ok += sum(v)
            total += len(v)
            print(f"    cat {cat}: n={len(v)}  acc={sum(v)/len(v):.4f}")
        if total:
            print(f"    OVERALL ACC: {total_ok}/{total} = {total_ok/total:.4f}")
    else:
        print("\n  LLM-judge: (not run — use without --f1_only to generate)")

    print("=" * 60)

    return {
        "n_samples": n_samples,
        "n_questions": n_questions,
        "cat_counts": dict(cat_counts),
        "f1_by_cat": {str(k): sum(v)/len(v) for k, v in f1_by_cat.items()},
        "overall_f1": sum(all_f1)/len(all_f1) if all_f1 else None,
        "tool_calls_avg": sum(tc)/len(tc) if tc else None,
        "schema_retries_total": sum(sr) if sr else None,
        "forced_accepts_total": sum(fa) if fa else None,
        "total_runtime_sec": metrics["total_runtime_sec"] if metrics["total_runtime_sec"] else None,
        "errors": len(errors),
    }


def main():
    global args
    args = parse_args()
    data = load_results(args.data, args.model, args.file, args.allfile, args.sample)
    print(f"loaded {len(data)} results from result/{args.data}")
    if not data:
        return

    # Extract per-question metrics from result rows
    metrics = extract_metrics_from_result_rows(data)

    # ---- F1 by category (categories may be int (locomo) or str (LM)) ----
    f1_by_cat = defaultdict(list)
    for r in data:
        prediction, reference, category = r["prediction"], r["answer"], r["category"]
        if is_adversarial(category):
            f1_by_cat[category].append(1 if "Not mentioned" in str(prediction) else 0)
            continue
        if isinstance(prediction, numbers.Number):
            prediction = str(prediction)
        if isinstance(reference, numbers.Number):
            reference = str(reference)
        f1_by_cat[category].append(f1_score(prediction, reference))

    print("\n== F1 by category ==")
    for cat in sorted(f1_by_cat, key=str):
        v = f1_by_cat[cat]
        print(f"  {cat}: n={len(v)} F1={sum(v) / len(v):.4f}")

    # ---- LLM-judge by category (skip adversarial: scored by string match above) ----
    skip_judge = args.f1_only or args.no_llm_judge
    if skip_judge:
        print("\n== LLM-judge skipped (--f1_only / --no_llm_judge) ==")
    else:
        judge_by_cat = defaultdict(list)
        out_path = f"result_judge_{args.data}_{args.model}_{args.file}.jsonl"
        # Remove old judge file to prevent append pollution from previous runs
        if os.path.exists(out_path):
            os.remove(out_path)
        _t0 = time.time()
        with open(out_path, "w", encoding="utf-8") as of:
            for r in data:
                category = r["category"]
                if is_adversarial(category):
                    continue
                score = evaluate_llm_judge(r["question"], r["answer"], r["prediction"])
                judge_by_cat[category].append(score)
                of.write(json.dumps({
                    "llm_score": score, "question": r["question"], "prediction": r["prediction"],
                    "reference": r["answer"], "category": category, "sample": r.get("sample"),
                }, ensure_ascii=False, default=list) + "\n")

        print("\n== LLM-judge accuracy by category ==")
        total_ok = total = 0
        for cat in sorted(judge_by_cat, key=str):
            v = judge_by_cat[cat]
            total_ok += sum(v); total += len(v)
            print(f"  {cat}: n={len(v)} acc={sum(v) / len(v):.4f}")
        if total:
            print(f"  OVERALL: {total_ok}/{total} = {total_ok / total:.4f}")

    # ---- Metrics summary ----
    summary = print_metrics_summary(data, metrics)

    # Save metrics summary as JSON
    summary_path = f"result/{args.data}/metrics_summary_{args.model}_{args.file}.json"
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as sf:
        json.dump(summary, sf, ensure_ascii=False, indent=2)
    print(f"\nMetrics summary saved to {summary_path}")


if __name__ == "__main__":
    main()
