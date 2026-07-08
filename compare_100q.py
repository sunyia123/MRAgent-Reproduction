#!/usr/bin/env python3
"""Per-question comparison: MRAgent vs Oracle vs RAG vs GraphRAG."""
import json, csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval.evaluation import f1_score

SAMPLES = [26, 30, 41, 42, 43, 44, 47, 48, 49, 50]
METHODS = {
    "mragent": "graphbuild_100q",
    "oracle": "oracle_plain_100q",
    "rag": "rag_plain_100q",
    "graphrag": "graphrag_plain_100q",
}

def load_by_sample(method_suffix):
    """Return dict[sample_id][question_text] = row (aligned by question text)."""
    data = {}
    for sid in SAMPLES:
        path = f"result/locomo/conv-{sid}_result_deepseek_{method_suffix}.jsonl"
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                r = json.loads(line)
                q = r.get("question", "").strip()
                data.setdefault(sid, {})[q] = r
    return data

def main():
    mra = load_by_sample(METHODS["mragent"])
    ora = load_by_sample(METHODS["oracle"])
    rag = load_by_sample(METHODS["rag"])
    gra = load_by_sample(METHODS["graphrag"])

    rows = []
    errors = []

    for sid in SAMPLES:
        mra_s = mra.get(sid, {})
        # Use MRAgent questions as the reference set (sorted by question text for stability)
        for qi_idx, q_text in enumerate(sorted(mra_s.keys()), 1):
            mr = mra_s[q_text]
            o_r = ora.get(sid, {}).get(q_text, {})
            r_r = rag.get(sid, {}).get(q_text, {})
            g_r = gra.get(sid, {}).get(q_text, {})

            gold = mr.get("answer")
            gold_ev = mr.get("evidence", [])
            cat = mr.get("category", "?")
            question = mr.get("question", "?")

            def get_f1(row, gold_val):
                pred = row.get("prediction", "")
                if pred == "ERROR": return 0.0, "ERROR"
                if gold_val is None:
                    neg_phrases = ["not mentioned", "no information", "cannot be determined",
                                  "not specified", "none", "not stated", "no evidence",
                                  "does not mention", "not provide", "unclear"]
                    pred_lower = str(pred).lower().strip()
                    return (1.0, pred) if any(ph in pred_lower for ph in neg_phrases) else (0.0, pred)
                return f1_score(str(pred), str(gold_val)), pred

            def get_ctx(row):
                ctx = row.get("prediction_context", [])
                if isinstance(ctx, list):
                    return "; ".join(str(c) for c in ctx[:5])
                return str(ctx)[:200]

            m_f1, m_pred = get_f1(mr, gold)
            o_f1, o_pred = get_f1(o_r, gold) if o_r else (0.0, "MISSING")
            r_f1, r_pred = get_f1(r_r, gold) if r_r else (0.0, "MISSING")
            g_f1, g_pred = get_f1(g_r, gold) if g_r else (0.0, "MISSING")

            o_ev_count = o_r.get("oracle_evidence_count", len(gold_ev)) if o_r else len(gold_ev)

            # Track ERRORs
            for label, pred_val in [("oracle", o_pred), ("rag", r_pred), ("graphrag", g_pred), ("mragent", m_pred)]:
                if pred_val == "ERROR":
                    errors.append({"sample": f"conv-{sid}", "question_index": qi_idx, "method": label,
                                   "question": str(question)[:100], "gold_answer": str(gold)[:100]})

            # Flags
            flags = []
            if o_ev_count == 0: flags.append("oracle_evidence_count==0")
            if o_f1 == 0 and o_pred != "ERROR" and o_pred != "MISSING": flags.append("oracle_hit_but_wrong")
            if m_f1 == 0 and m_pred != "ERROR": flags.append("mragent_hit_but_wrong")
            if m_f1 == 0 and o_f1 > 0: flags.append("mragent_miss_but_oracle_correct")
            if r_f1 > 0 and m_f1 == 0: flags.append("rag_correct_mragent_wrong")
            if m_f1 > 0 and r_f1 == 0: flags.append("mragent_correct_rag_wrong")
            if cat == 2: flags.append("temporal_question")
            if gold is None: flags.append("cat5_null_gold")

            rows.append({
                "sample": f"conv-{sid}", "question_index": qi_idx, "category": cat,
                "question": question, "gold_answer": gold, "gold_evidence": str(gold_ev),
                "mragent_prediction": m_pred, "mragent_context": get_ctx(mr), "mragent_f1": round(m_f1, 3),
                "oracle_prediction": o_pred, "oracle_context": get_ctx(o_r) if o_r else "", "oracle_f1": round(o_f1, 3),
                "rag_prediction": r_pred, "rag_context": get_ctx(r_r) if r_r else "", "rag_f1": round(r_f1, 3),
                "graphrag_prediction": g_pred, "graphrag_context": get_ctx(g_r) if g_r else "", "graphrag_f1": round(g_f1, 3),
                "flags": "; ".join(flags),
            })

    # Write CSV
    csv_path = "reports/core_validation_100q_per_question_compare_20260708.csv"
    fieldnames = ["sample", "question_index", "category", "question", "gold_answer", "gold_evidence",
                  "mragent_prediction", "mragent_context", "mragent_f1",
                  "oracle_prediction", "oracle_context", "oracle_f1",
                  "rag_prediction", "rag_context", "rag_f1",
                  "graphrag_prediction", "graphrag_context", "graphrag_f1", "flags"]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"CSV: {csv_path} ({len(rows)} rows)")

    # ---- Badcase pack ----
    lines = [
        "# Core Validation 100q — Badcase Pack",
        "Generated: 2026-07-08",
        "",
        f"Total questions: {len(rows)}",
        "",
    ]

    # Summary stats
    from collections import Counter
    flag_counts = Counter()
    for r in rows:
        for fl in r["flags"].split("; "):
            if fl: flag_counts[fl] += 1

    lines.extend(["## Flag Summary", "", "| Flag | Count |", "|---|---:|"])
    for flag, cnt in flag_counts.most_common():
        lines.append(f"| {flag} | {cnt} |")

    # Cat5 null-gold examples
    cat5_rows = [r for r in rows if "cat5_null_gold" in r["flags"]]
    lines.extend(["", "## Cat5 Adversarial (null gold)", f"Count: {len(cat5_rows)}", ""])
    lines.append("| sample | qi | question | mragent_pred | rag_pred | gold | flags |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in cat5_rows[:15]:
        lines.append(f"| {r['sample']} | {r['question_index']} | {str(r['question'])[:60]} | {str(r['mragent_prediction'])[:50]} | {str(r['rag_prediction'])[:50]} | {r['gold_answer']} | {r['flags']} |")

    # MRAgent correct, RAG wrong
    mc_rw = [r for r in rows if "mragent_correct_rag_wrong" in r["flags"]]
    lines.extend(["", f"## MRAgent Correct, RAG Wrong ({len(mc_rw)} cases)", ""])
    for r in mc_rw[:15]:
        lines.append(f"- **{r['sample']} Q{r['question_index']} (cat{r['category']})**: {str(r['question'])[:100]}")
        lines.append(f"  - Gold: {r['gold_answer']} | MRAgent: {str(r['mragent_prediction'])[:80]} | RAG: {str(r['rag_prediction'])[:80]}")

    # RAG correct, MRAgent wrong
    rc_mw = [r for r in rows if "rag_correct_mragent_wrong" in r["flags"]]
    lines.extend(["", f"## RAG Correct, MRAgent Wrong ({len(rc_mw)} cases)", ""])
    for r in rc_mw[:15]:
        lines.append(f"- **{r['sample']} Q{r['question_index']} (cat{r['category']})**: {str(r['question'])[:100]}")
        lines.append(f"  - Gold: {r['gold_answer']} | MRAgent: {str(r['mragent_prediction'])[:80]} | RAG: {str(r['rag_prediction'])[:80]}")

    # Temporal (cat2) failures
    tmp_fail = [r for r in rows if "temporal_question" in r["flags"] and r["mragent_f1"] == 0 and r["rag_f1"] == 0]
    lines.extend(["", f"## Temporal Questions — Both MRAgent & RAG Wrong ({len(tmp_fail)} cases)", ""])
    for r in tmp_fail[:10]:
        lines.append(f"- **{r['sample']} Q{r['question_index']}**: {str(r['question'])[:100]}")
        lines.append(f"  - Gold: {r['gold_answer']} | MRAgent: {str(r['mragent_prediction'])[:80]} | RAG: {str(r['rag_prediction'])[:80]}")

    # ERRORs
    lines.extend(["", f"## ERRORs ({len(errors)} total)", ""])
    lines.append("| sample | qi | method | question | gold_answer |")
    lines.append("|---|---|---|---|---|")
    for e in errors[:30]:
        lines.append(f"| {e['sample']} | {e['question_index']} | {e['method']} | {e['question'][:60]} | {e['gold_answer'][:50]} |")

    md_path = "reports/core_validation_100q_badcase_pack_20260708.md"
    with open(md_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Badcase: {md_path}")

if __name__ == "__main__":
    main()
