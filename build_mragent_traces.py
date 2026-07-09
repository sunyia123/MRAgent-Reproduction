#!/usr/bin/env python3
"""Extract per-question MRAgent 100q traces from run logs and result files."""
import json, os, re, csv, gzip
from collections import defaultdict
from pathlib import Path
from eval.evaluation import f1_score

SAMPLES = [26, 30, 41, 42, 43, 44, 47, 48, 49, 50]
TRACE_DIR = Path("result/diagnostics/mragent_100q_traces")
LOG_SUFFIX = "_all10_mragent_100q_fix_20260708"

# Patterns for log parsing
RE_QUESTION = re.compile(r"---------------question(\d+)\s+\(cat (\d+)\)")
RE_QUESTION_RESULT = re.compile(r"---------------question(\d+)\s+\(orig (\d+)\)")
RE_API_LOG_ENTRY = re.compile(r"HTTP Request: (POST|GET)")
RE_ERROR = re.compile(r"\[ERROR\].*question(\d+).*failed:\s*(.*)")
RE_TOOL = re.compile(r"tool_call|query_|dispatch")
RE_INPUT = re.compile(r"---------- input \(round (\d+)\) ---------")
RE_COOLDOWN = re.compile(r"API cooldown")

SANITIZE_KEYS = {"authorization", "api_key", "api-key", "x-api-key", "openai_api_key",
                 "siliconflow_api_key", "openrouter_api_key", "llm_base_url"}

def sanitize(obj):
    """Recursively remove sensitive keys."""
    if isinstance(obj, dict):
        return {k: ("[REDACTED]" if k.lower().replace("-","_") in SANITIZE_KEYS else sanitize(v))
                for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize(v) for v in obj]
    elif isinstance(obj, str):
        # Redact bearer tokens
        for pattern in [r'Bearer\s+[\w\-\.]+', r'sk-[\w]+', r'api[_-]?key[=:]\s*\S+']:
            obj = re.sub(pattern, lambda m: m.group(0)[:10] + '...[REDACTED]', obj, flags=re.IGNORECASE)
        return obj
    return obj

def parse_run_log_errors():
    """Parse all10 run log for per-question error messages."""
    run_log = "log/locomo/runs/all10_mragent_100q_fix_20260708_deepseek_graphbuild_100q.log"
    if not os.path.exists(run_log):
        return {}
    errors = {}
    with open(run_log, encoding="utf-8") as f:
        for line in f:
            m = re.search(r"\[ERROR\].*question(\d+)\s*\(orig idx (\d+)\).*failed:\s*(.*)", line)
            if m:
                qnum = int(m.group(1))
                orig = int(m.group(2))
                msg = m.group(3).strip()
                if orig not in errors:
                    errors[orig] = []
                errors[orig].append(msg)
    return errors

def load_raw_api_calls():
    """Load raw API call records from the all10 run."""
    path = "result/diagnostics/raw_api_calls_all10_mragent_100q_fix_20260708.jsonl"
    if not os.path.exists(path):
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                records.append(json.loads(line))
            except: pass
    return records

def parse_per_sample_log(sid):
    """Parse per-sample log into per-question sections."""
    log_path = f"log/locomo/conv-{sid}_deepseek_graphbuild_100q{LOG_SUFFIX}.log"
    if not os.path.exists(log_path):
        return {}

    with open(log_path, encoding="utf-8") as f:
        lines = f.readlines()

    questions = {}  # qnum -> {"prompts": [], "responses": [], "errors": [], "log_lines": []}
    current_q = None

    for line in lines:
        m = RE_QUESTION.search(line)
        if m:
            current_q = int(m.group(1))
            questions.setdefault(current_q, {"prompts": [], "responses": [], "errors": [], "log_lines": []})
            questions[current_q]["cat"] = int(m.group(2))
            continue

        # Also detect question result lines
        m2 = RE_QUESTION_RESULT.search(line)
        if m2:
            current_q = int(m2.group(1))
            questions.setdefault(current_q, {"prompts": [], "responses": [], "errors": [], "log_lines": []})

        if current_q:
            questions[current_q]["log_lines"].append(line)
            # Capture error lines
            err_m = re.search(r"\[ERROR\].*failed:\s*(.*)", line)
            if err_m:
                questions[current_q]["errors"].append(err_m.group(1).strip())

    return questions

def load_result(sid):
    """Load MRAgent result for a sample."""
    path = f"result/locomo/conv-{sid}_result_deepseek_graphbuild_100q.jsonl"
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line.strip()) for line in f if line.strip()]

def compute_f1(pred, gold):
    if pred == "ERROR": return 0.0
    if gold is None:
        neg_phrases = ["not mentioned", "no information", "cannot be determined",
                      "not specified", "none", "not stated", "no evidence",
                      "does not mention", "not provide", "unclear"]
        return 1.0 if any(ph in str(pred).lower() for ph in neg_phrases) else 0.0
    return f1_score(str(pred), str(gold))

def compute_evidence_hit(ctx_list, evidence_list):
    if not evidence_list: return 1.0  # no gold evidence → trivially "hit"
    ev_set = set(evidence_list)
    ctx_set = set()
    for item in (ctx_list or []):
        if isinstance(item, dict):
            ctx_set.add(item.get("turn") or item.get("origin") or str(item))
        else:
            ctx_set.add(str(item))
    hits = len(ev_set & ctx_set)
    return hits / len(ev_set)

def main():
    TRACE_DIR.mkdir(parents=True, exist_ok=True)

    all_rows = []
    manifest_rows = []
    run_errors = parse_run_log_errors()
    raw_calls = load_raw_api_calls()

    # Index raw calls by question for each sample (approximate: by timestamp)
    # We'll extract relevant calls for each sample's QA phase

    for sid in SAMPLES:
        print(f"Processing conv-{sid}...")
        results = load_result(sid)
        log_qs = parse_per_sample_log(sid)

        sample_dir = TRACE_DIR / f"conv-{sid}"
        sample_dir.mkdir(parents=True, exist_ok=True)

        for qi, row in enumerate(results, 1):
            gold = row.get("answer")
            gold_ev = row.get("evidence", [])
            pred_val = row.get("prediction", "")
            cat = row.get("category", "?")
            question = row.get("question", "?")
            ctx = row.get("prediction_context", [])
            metrics = row.get("_metrics", {})
            f1 = compute_f1(pred_val, gold)
            ev_hit = compute_evidence_hit(ctx, gold_ev)

            # Get log traces
            log_data = log_qs.get(qi, {})
            log_lines = log_data.get("log_lines", [])
            errors = log_data.get("errors", [])

            # Extract prompts, responses, tool calls from log lines
            prompts = []
            responses = []
            tool_lines = []
            retry_lines = []
            error_lines = []

            in_input = False
            current_prompt_section = []
            for ll in log_lines:
                if RE_INPUT.search(ll):
                    in_input = True
                    continue
                if in_input:
                    if RE_API_LOG_ENTRY.search(ll) or RE_ERROR.search(ll) or RE_COOLDOWN.search(ll):
                        prompts.append("".join(current_prompt_section[-20:]))  # keep last 20 lines of input
                        current_prompt_section = []
                        in_input = False
                    else:
                        current_prompt_section.append(ll)

                if RE_TOOL.search(ll.lower() if isinstance(ll, str) else ""):
                    tool_lines.append(ll)
                if "retry" in ll.lower() or "attempt" in ll.lower():
                    retry_lines.append(ll)
                if "[ERROR]" in ll or "[WARNING]" in ll and ("failed" in ll.lower() or "error" in ll.lower()):
                    error_lines.append(ll)
                if RE_API_LOG_ENTRY.search(ll):
                    responses.append(ll)

            # Save trace files
            qname = f"q{qi:03d}"

            # Trace JSON
            trace = {
                "sample": f"conv-{sid}", "question_index": qi, "category": cat,
                "question": question, "gold_answer": gold, "gold_evidence": gold_ev,
                "prediction": pred_val, "prediction_context": ctx, "f1": round(f1, 3),
                "evidence_hit": round(ev_hit, 3),
                "errors": errors, "metrics": metrics,
                "prompt_sections": len(prompts), "response_lines": len(responses),
                "tool_call_lines": len(tool_lines), "retry_lines": len(retry_lines),
            }
            with open(sample_dir / f"{qname}_trace.json", "w") as f:
                json.dump(trace, f, ensure_ascii=False, indent=2)

            # Raw prompts (sanitized)
            with open(sample_dir / f"{qname}_raw_prompts.jsonl", "w") as f:
                for p in prompts:
                    f.write(json.dumps(sanitize({"prompt_section": p}), ensure_ascii=False) + "\n")
            if not prompts:
                with open(sample_dir / f"{qname}_raw_prompts.jsonl", "w") as f:
                    f.write(json.dumps({"note": "prompts not extractable from log — log only contains HTTP-level traces"}, ensure_ascii=False) + "\n")

            # Raw responses (sanitized)
            with open(sample_dir / f"{qname}_raw_responses.jsonl", "w") as f:
                for r in responses:
                    f.write(json.dumps(sanitize({"response_log": r.strip()}), ensure_ascii=False) + "\n")
            if not responses:
                with open(sample_dir / f"{qname}_raw_responses.jsonl", "w") as f:
                    f.write(json.dumps({"note": "responses not extractable from log"}, ensure_ascii=False) + "\n")

            # Retry/error log
            with open(sample_dir / f"{qname}_retry_log.jsonl", "w") as f:
                for rl in retry_lines + error_lines + errors:
                    f.write(json.dumps({"log": rl.strip() if isinstance(rl, str) else str(rl)}, ensure_ascii=False) + "\n")
                if not (retry_lines or error_lines or errors):
                    f.write(json.dumps({"note": "no retries or errors"}, ensure_ascii=False) + "\n")

            # Error classification
            error_type = ""
            error_message = ""
            if pred_val == "ERROR":
                # Check run_errors by iterating all entries for matching question text
                all_errs = list(errors)
                for orig_idx, err_msgs in run_errors.items():
                    # Check if this error is for our question by matching sample context
                    all_errs.extend(err_msgs)
                combined = "; ".join(all_errs[:5])
                if any("timed out" in e.lower() or "timeout" in e.lower() for e in all_errs):
                    error_type = "api_timeout"
                    error_message = combined[:300]
                elif any("json parse" in e.lower() or "json" in e.lower() for e in all_errs):
                    error_type = "json_parse_failure"
                    error_message = combined[:300]
                elif all_errs:
                    error_type = "other"
                    error_message = combined[:300]
                else:
                    error_type = "unknown"
                    error_message = "no error message found in run or sample log"

            manifest_rows.append({
                "sample": f"conv-{sid}", "question_index": qi, "category": cat,
                "question": question, "gold_answer": str(gold), "gold_evidence": str(gold_ev),
                "prediction": str(pred_val), "prediction_context": str(ctx)[:500],
                "f1": round(f1, 3), "evidence_hit": round(ev_hit, 3),
                "trace_file": f"{sample_dir}/{qname}_trace.json",
                "raw_prompt_file": f"{sample_dir}/{qname}_raw_prompts.jsonl",
                "raw_response_file": f"{sample_dir}/{qname}_raw_responses.jsonl",
                "retry_log_file": f"{sample_dir}/{qname}_retry_log.jsonl",
                "error_type": error_type, "error_message": error_message[:300],
                "runtime_sec": metrics.get("runtime_sec", 0),
                "tool_calls": metrics.get("tool_calls", 0),
            })
            all_rows.append((sid, qi, row, f1, ev_hit, cat, errors, metrics))

    # Write manifest
    manifest_path = "reports/mragent_100q_trace_manifest_20260709.jsonl"
    with open(manifest_path, "w") as f:
        for mr in manifest_rows:
            f.write(json.dumps(mr, ensure_ascii=False) + "\n")

    # ---- Badcase pack ----
    lines = [
        "# MRAgent 100q Badcase Pack",
        "Generated: 2026-07-09",
        "",
        "## Summary",
        f"Total questions: {len(all_rows)}",
    ]

    # Overall stats
    total = len(all_rows)
    errs = sum(1 for _, _, r, _, _, _, _, _ in all_rows if r["prediction"] == "ERROR")
    f1s = [f1 for _, _, _, f1, _, _, _, _ in all_rows]
    overall_f1 = sum(f1s) / len(f1s)
    lines.extend([f"- Overall F1: {overall_f1:.3f}", f"- ERRORs: {errs}", ""])

    # Classification
    f1_lt_03 = [(s, q, r, f1) for s, q, r, f1, _, _, _, _ in all_rows if f1 < 0.3 and r["prediction"] != "ERROR"]
    ev_hit_wrong = [(s, q, r, f1, eh) for s, q, r, f1, eh, _, _, _ in all_rows
                    if eh >= 1.0 and f1 < 0.5 and r["prediction"] != "ERROR"]
    miss_ev = [(s, q, r, f1, eh) for s, q, r, f1, eh, _, _, _ in all_rows if eh == 0.0 and r["prediction"] != "ERROR"]
    errors_list = [(s, q, r, errs_list) for s, q, r, _, _, _, errs_list, _ in all_rows if r["prediction"] == "ERROR"]
    cat5_overanswer = [(s, q, r) for s, q, r, _, _, cat, _, _ in all_rows
                       if cat == 5 and r.get("answer") is None and r["prediction"] != "ERROR"
                       and not any(ph in str(r["prediction"]).lower() for ph in
                                  ["not mentioned", "no information", "cannot be determined", "not specified"])]
    temporal_wrong = [(s, q, r, f1) for s, q, r, f1, _, cat, _, _ in all_rows if cat == 2 and f1 < 0.3]
    cat3_fail = [(s, q, r, f1) for s, q, r, f1, _, cat, _, _ in all_rows if cat == 3 and f1 < 0.3]
    singlehop_low = [(s, q, r, f1) for s, q, r, f1, _, cat, _, _ in all_rows if cat == 4 and f1 < 0.3]

    def write_section(title, items, count_label="cases"):
        lines.extend(["", f"## {title} ({len(items)} {count_label})", ""])
        for item in items[:15]:
            if len(item) == 3:
                s, q, r = item; f1_val = compute_f1(r["prediction"], r.get("answer"))
            elif len(item) == 4:
                if isinstance(item[3], float):
                    s, q, r, f1_val = item
                else:
                    s, q, r, errs_list = item; f1_val = 0
            else:
                s, q, r, f1_val, _ = item
            pred = str(r.get("prediction", ""))[:80]
            gold = str(r.get("answer", ""))[:80]
            lines.append(f"- **conv-{s} Q{q} (cat{r.get('category','?')})**: {str(r.get('question','?'))[:100]}")
            lines.append(f"  - Pred: {pred} | Gold: {gold}")
            if isinstance(item, tuple) and len(item) >= 5:
                lines.append(f"  - F1={f1_val:.3f}, ev_hit={item[4]:.2f}")

    write_section("F1 < 0.3", f1_lt_03)
    write_section("Evidence Hit but Wrong", ev_hit_wrong)
    write_section("Miss Gold Evidence (ev_hit=0)", miss_ev)
    write_section("ERRORs", errors_list)
    write_section("Cat5 Null-Gold Over-Answer", cat5_overanswer)
    write_section("Temporal Wrong (cat2, F1<0.3)", temporal_wrong)
    write_section("Category 3 Reasoning Fail (F1<0.3)", cat3_fail)
    write_section("Single-Hop Low F1 (cat4, F1<0.3)", singlehop_low)

    badcase_path = "reports/mragent_100q_badcase_pack_20260709.md"
    with open(badcase_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    # Summary
    print(f"Total questions: {total}")
    print(f"ERRORs: {errs}")
    print(f"Overall F1: {overall_f1:.3f}")
    print(f"F1<0.3: {len(f1_lt_03)}, ev_hit_wrong: {len(ev_hit_wrong)}, miss_ev: {len(miss_ev)}")
    print(f"cat5_overanswer: {len(cat5_overanswer)}, temporal_wrong: {len(temporal_wrong)}")
    print(f"cat3_fail: {len(cat3_fail)}, singlehop_low: {len(singlehop_low)}")
    print(f"Trace dir: {TRACE_DIR}")
    print(f"Manifest: {manifest_path}")
    print(f"Badcase: {badcase_path}")

    # Two ERROR details
    for s, q, r, errs_list in errors_list:
        print(f"\nERROR conv-{s} Q{q}: {r['question'][:100]}")
        print(f"  Error type: {[mr['error_type'] for mr in manifest_rows if mr['sample']==f'conv-{s}' and mr['question_index']==q]}")
        print(f"  Errors: {errs_list}")

if __name__ == "__main__":
    main()
