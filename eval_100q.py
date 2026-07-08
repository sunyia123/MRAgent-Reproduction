#!/usr/bin/env python3
"""Core validation 100q evaluation across MRAgent, RAG, GraphRAG, Oracle."""
import json, sys, os
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval.evaluation import f1_score

SAMPLES = [26, 30, 41, 42, 43, 44, 47, 48, 49, 50]
METHODS = {
    "MRAgent": "graphbuild_100q",
    "RAG": "rag_graphbuild_100q",
    "GraphRAG": "graphrag_graphbuild_100q",
    "Oracle": "oracle_graphbuild_100q",
}

def load_results(method_suffix):
    all_rows = []
    for sid in SAMPLES:
        path = f"result/locomo/conv-{sid}_result_deepseek_{method_suffix}.jsonl"
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    all_rows.append(json.loads(line))
                except: pass
    return all_rows

def eval_method(name, suffix):
    rows = load_results(suffix)
    total = len(rows)
    errors = sum(1 for r in rows if r.get("prediction") == "ERROR")

    cat_f1 = defaultdict(list)
    cat_ev = defaultdict(list)
    evidence_hits = 0
    evidence_total = 0

    for r in rows:
        pred = str(r.get("prediction", ""))
        gold_raw = r.get("answer")
        cat = r.get("category", "?")
        evidence = r.get("evidence", [])

        if pred == "ERROR":
            score = 0
        elif gold_raw is None:
            # adversarial (cat5): gold is null → question is unanswerable
            neg_phrases = ["not mentioned", "no information", "cannot be determined",
                          "not specified", "none", "not stated", "no evidence",
                          "does not mention", "not provide", "unclear"]
            pred_lower = pred.lower().strip()
            score = 1.0 if any(ph in pred_lower for ph in neg_phrases) else 0.0
        else:
            score = f1_score(pred, str(gold_raw))
        cat_f1[cat].append(score)

        # evidence hit rate from prediction_context
        ctx = r.get("prediction_context", [])
        if isinstance(ctx, list) and isinstance(evidence, list):
            ev_set = set(evidence)
            ctx_turns = set()
            for item in ctx:
                if isinstance(item, dict):
                    turn = item.get("turn") or item.get("origin") or ""
                else:
                    turn = str(item)
                ctx_turns.add(turn)
            if ev_set:
                hits = len(ev_set & ctx_turns) if ctx_turns else 0
                cat_ev[cat].append(hits / len(ev_set) if ev_set else 0)

    cat_summary = {}
    for cat in sorted(cat_f1.keys(), key=str):
        scores = cat_f1[cat]
        evs = cat_ev.get(cat, [])
        cat_summary[cat] = {
            "n": len(scores),
            "f1_mean": sum(scores)/len(scores) if scores else 0,
            "ev_hit_rate": sum(evs)/len(evs) if evs else 0,
        }

    overall_f1 = sum(sum(v) for v in cat_f1.values()) / sum(len(v) for v in cat_f1.values()) if total else 0
    all_ev = [v for ev_list in cat_ev.values() for v in ev_list]
    overall_ev = sum(all_ev)/len(all_ev) if all_ev else 0

    return {
        "name": name, "total": total, "errors": errors,
        "overall_f1": overall_f1, "overall_ev_hit": overall_ev,
        "categories": cat_summary,
        "rows": rows,
    }

def main():
    results = {}

    for name, suffix in METHODS.items():
        results[name] = eval_method(name, suffix)
        r = results[name]
        print(f"{name}: {r['total']} rows, {r['errors']} ERRORs, F1={r['overall_f1']:.3f}, ev_hit={r['overall_ev_hit']:.3f}")

    # ---- Build markdown report ----
    lines = [
        "# Core Validation 100q — Evaluation Report",
        f"Generated: 2026-07-08",
        "",
        "## Methods",
        "",
        "| Method | Rows | ERRORs | Overall F1 | Evidence Hit Rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in ["MRAgent", "RAG", "GraphRAG", "Oracle"]:
        r = results[name]
        lines.append(f"| {name} | {r['total']} | {r['errors']} | {r['overall_f1']:.3f} | {r['overall_ev_hit']:.3f} |")

    # Per-category
    lines.extend(["", "## Per-Category F1", ""])
    all_cats = sorted(set(c for r in results.values() for c in r["categories"]), key=str)

    lines.append("| Category | " + " | ".join(f"{name} F1" for name in METHODS) + " |")
    lines.append("|---|" + "|".join("---:|" for _ in METHODS))
    for cat in all_cats:
        row = f"| {cat} "
        for name in METHODS:
            c = results[name]["categories"].get(cat, {})
            row += f"| {c.get('f1_mean', 0):.3f} (n={c.get('n',0)}) "
        row += "|"
        lines.append(row)

    # Evidence hit rate
    lines.extend(["", "## Evidence Hit Rate", ""])
    lines.append("| Category | " + " | ".join(f"{name}" for name in METHODS) + " |")
    lines.append("|---|" + "|".join("---:|" for _ in METHODS))
    for cat in all_cats:
        row = f"| {cat} "
        for name in METHODS:
            c = results[name]["categories"].get(cat, {})
            row += f"| {c.get('ev_hit_rate', 0):.2%} "
        row += "|"
        lines.append(row)

    # Oracle error examples
    oracle = results["Oracle"]
    oracle_errors = [r for r in oracle["rows"] if r.get("prediction") == "ERROR"]
    lines.extend([
        "", "## Oracle ERROR Examples",
        f"Total Oracle ERRORs: {len(oracle_errors)}/{oracle['total']}",
        "",
    ])
    for i, r in enumerate(oracle_errors[:10]):
        lines.append(f"### Oracle Error #{i+1}")
        lines.append(f"- **Question**: {r.get('question', '?')}")
        lines.append(f"- **Gold Answer**: {r.get('answer', '?')}")
        lines.append(f"- **Category**: {r.get('category', '?')}")
        lines.append(f"- **Evidence**: {r.get('evidence', [])}")
        lines.append(f"- **Sample**: {r.get('sample', '?')}")
        lines.append("")

    # Key findings
    lines.extend([
        "", "## Key Findings", "",
    ])
    # Temporal (cat 2) RAG check
    for name in ["RAG", "GraphRAG"]:
        cat2 = results[name]["categories"].get(2, {})
        lines.append(f"- **{name} cat2 (temporal) F1**: {cat2.get('f1_mean', 0):.3f} — {'STILL FAILING' if cat2.get('f1_mean', 0) < 0.1 else 'improved'}")

    # Cat4 single-hop
    for name in METHODS:
        cat4 = results[name]["categories"].get(4, {})
        lines.append(f"- **{name} cat4 (single-hop) F1**: {cat4.get('f1_mean', 0):.3f}")

    report_path = "reports/core_validation_100q_20260708.md"
    with open(report_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nReport written to {report_path}")

if __name__ == "__main__":
    main()
