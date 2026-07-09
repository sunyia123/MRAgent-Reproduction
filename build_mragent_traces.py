#!/usr/bin/env python3
"""Build real MRAgent 100q per-question traces from raw API logs and per-sample logs."""
import json, os, re, sys
from collections import defaultdict
from pathlib import Path
from datetime import datetime

SAMPLES = [26, 30, 41, 42, 43, 44, 47, 48, 49, 50]
RAW_API_PATH = "result/diagnostics/raw_api_calls_all10_mragent_100q_fix_20260708.jsonl"
TRACE_DIR = Path("result/diagnostics/mragent_100q_traces")
LOG_SUFFIX = "_all10_mragent_100q_fix_20260708"

SANITIZE_PATTERNS = [
    (re.compile(r'Bearer\s+[\w\-\.]+', re.IGNORECASE), 'Bearer [REDACTED]'),
    (re.compile(r'sk-[\w]{20,}', re.IGNORECASE), 'sk-[REDACTED]'),
    (re.compile(r'api[_-]?key[=:]\s*\S+', re.IGNORECASE), 'api_key=[REDACTED]'),
]

def sanitize_text(text):
    if not isinstance(text, str):
        return text
    for pattern, replacement in SANITIZE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text

def sanitize_obj(obj):
    if isinstance(obj, dict):
        return {k: sanitize_obj(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_obj(v) for v in obj]
    elif isinstance(obj, str):
        return sanitize_text(obj)
    return obj

def _ids(value):
    text = " ".join(map(str, value)) if isinstance(value, list) else str(value)
    return re.findall(r'\bD\d+:\d+(?:-\d+)?\b', text)

def evidence_hit_ratio(gold_evidence, prediction_context):
    gold_ids = _ids(gold_evidence)
    if not gold_ids:
        return 1.0
    context_ids = _ids(prediction_context)
    hit = 0
    for gold_id in gold_ids:
        if any(ctx_id == gold_id or ctx_id.startswith(gold_id + "-") for ctx_id in context_ids):
            hit += 1
    return hit / len(gold_ids)

def load_raw_api_calls():
    """Load all raw API calls indexed by request_id for matching started/success/error."""
    calls = defaultdict(dict)  # request_id -> {started: {...}, success: {...}, error: {...}}
    all_calls = []
    with open(RAW_API_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                r = json.loads(line)
            except: continue
            rid = r.get("request_id", "")
            status = r.get("status", "unknown")
            calls[rid][status] = r
            all_calls.append(r)
    return dict(calls), all_calls

def parse_per_sample_questions(sid):
    """Parse per-sample log to get question timing windows and error info."""
    log_path = f"log/locomo/conv-{sid}_deepseek_graphbuild_100q{LOG_SUFFIX}.log"
    if not os.path.exists(log_path):
        return [], {}, []

    questions = []
    current_q = None
    q_start_ts = None
    q_lines = []
    error_msgs = []

    with open(log_path, encoding="utf-8") as f:
        for line in f:
            # Question start marker: "---------------questionN (cat X)"
            m_start = re.search(r"---------------question(\d+)\s+\(cat (\d+)\)", line)
            if m_start:
                if current_q is not None:
                    questions.append({
                        "qnum": current_q, "cat": q_cat, "start_ts": q_start_ts,
                        "end_ts": None, "lines": q_lines, "errors": list(error_msgs),
                    })
                current_q = int(m_start.group(1))
                q_cat = int(m_start.group(2))
                q_start_ts = extract_ts(line)
                q_lines = [line]
                error_msgs = []
                continue

            # Question done marker: "---------------questionN (orig idx M)"
            m_done = re.search(r"---------------question(\d+)\s+\(orig (\d+)\)", line)
            if m_done:
                q_lines.append(line)
                if current_q is not None:
                    questions.append({
                        "qnum": current_q, "cat": q_cat, "start_ts": q_start_ts,
                        "end_ts": extract_ts(line), "lines": q_lines,
                        "errors": list(error_msgs),
                        "orig_idx": int(m_done.group(2)),
                    })
                current_q = None
                q_lines = []
                error_msgs = []
                continue

            if current_q is not None:
                q_lines.append(line)
                # Capture errors
                if "[ERROR]" in line:
                    m_err = re.search(r"failed:\s*(.*)", line)
                    if m_err:
                        error_msgs.append(m_err.group(1).strip())

    # Don't forget last question
    if current_q is not None:
        questions.append({
            "qnum": current_q, "cat": q_cat, "start_ts": q_start_ts,
            "end_ts": None, "lines": q_lines, "errors": list(error_msgs),
        })

    return questions, {}, error_msgs

def extract_ts(line):
    """Extract timestamp from log line like [2026-07-08 21:57:20]"""
    m = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", line)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        except: pass
    return None

def extract_ts_from_api(api_entry):
    """Extract timestamp from API call entry."""
    ts_str = api_entry.get("ts", "")
    try:
        return datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S")
    except: pass
    return None

def match_raw_calls_to_questions(questions, raw_calls_idx, all_raw_calls, result_rows):
    """Match raw API calls to each question by question text in request messages."""
    # Build list of (ts, rid, status, entry) for all calls
    timed_calls = []
    for rid, entries in raw_calls_idx.items():
        for status, entry in entries.items():
            ts = extract_ts_from_api(entry)
            if ts:
                timed_calls.append((ts, rid, status, entry))
    timed_calls.sort(key=lambda x: x[0])

    for qi, q in enumerate(questions):
        qi_1based = qi + 1
        result_row = result_rows[qi] if qi < len(result_rows) else {}
        q_text = result_row.get("question", "").strip()

        q_calls = []
        for ts, rid, status, entry in timed_calls:
            # Try to match by question text in messages
            req = entry.get("request", {})
            if isinstance(req, dict):
                msgs = req.get("messages", [])
                matched = False
                for msg in msgs:
                    if isinstance(msg, dict):
                        content = str(msg.get("content", ""))
                        # Check if this message mentions the question text or keywords
                        if q_text and len(q_text) > 20 and q_text[:30] in content:
                            matched = True
                            break
                        # For shorter questions, check partial match
                        if q_text and len(q_text) <= 20 and q_text in content:
                            matched = True
                            break
                if matched:
                    q_calls.append((rid, status, entry))

        # Fallback: if no question-text match, use timestamp window
        if not q_calls:
            q_start = q.get("start_ts")
            q_end = q.get("end_ts")
            for ts, rid, status, entry in timed_calls:
                if q_start and ts < q_start:
                    continue
                if q_end and ts > q_end:
                    if (ts - q_end).total_seconds() > 60:
                        break
                q_calls.append((rid, status, entry))

        questions[qi]["raw_call_ids"] = list(set(rid for rid, _, _ in q_calls))
        questions[qi]["raw_calls"] = q_calls

    return questions

def main():
    TRACE_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading raw API calls...")
    raw_calls_idx, all_raw_calls = load_raw_api_calls()
    print(f"  {len(raw_calls_idx)} unique request_ids, {len(all_raw_calls)} total entries")

    # Parse run log for global errors
    run_log = "log/locomo/runs/all10_mragent_100q_fix_20260708_deepseek_graphbuild_100q.log"
    run_errors = {}  # (sample, question_number_in_sample) -> [error messages]
    if os.path.exists(run_log):
        with open(run_log, encoding="utf-8") as f:
            for line in f:
                m = re.search(r"\[ERROR\].*question(\d+)\s*\(orig idx (\d+)\).*failed:\s*(.*)", line)
                if m:
                    qnum = int(m.group(1))
                    orig = int(m.group(2))
                    msg = m.group(3).strip()
                    run_errors.setdefault((None, qnum, orig), []).append(msg)
        print(f"  {len(run_errors)} run-level errors found")

    manifest_rows = []
    total_prompts = 0
    total_responses = 0
    total_tools = 0
    total_retries = 0

    for sid in SAMPLES:
        print(f"\nProcessing conv-{sid}...")
        questions, _, _ = parse_per_sample_questions(sid)
        print(f"  {len(questions)} questions found in log")

        # Load result file for ground truth
        result_path = f"result/locomo/conv-{sid}_result_deepseek_graphbuild_100q.jsonl"
        results = []
        if os.path.exists(result_path):
            with open(result_path) as f:
                for line in f:
                    if line.strip():
                        results.append(json.loads(line.strip()))

        # Match raw API calls to questions by question text
        questions = match_raw_calls_to_questions(questions, raw_calls_idx, all_raw_calls, results)

        sample_dir = TRACE_DIR / f"conv-{sid}"
        sample_dir.mkdir(parents=True, exist_ok=True)

        for qi, q in enumerate(questions):
            qi_1based = qi + 1
            qname = f"q{qi_1based:03d}"
            result_row = results[qi] if qi < len(results) else {}

            # Collect raw API calls for this question
            q_raw_calls = q.get("raw_calls", [])
            q_call_ids = q.get("raw_call_ids", [])

            # Build real prompt/response files from raw API calls
            prompt_entries = []
            response_entries = []
            tool_entries = []
            retry_entries = []

            seen_rids = set()
            for rid, status, entry in q_raw_calls:
                if rid not in seen_rids:
                    seen_rids.add(rid)
                req = entry.get("request", {})
                if status == "started" and isinstance(req, dict):
                    msgs = req.get("messages", [])
                    sanitized = sanitize_obj({"model": entry.get("model"), "messages": msgs,
                                              "max_tokens": entry.get("max_tokens"),
                                              "extra_body": req.get("extra_body", {})})
                    prompt_entries.append({"request_id": rid, "ts": entry.get("ts"),
                                           "attempt": entry.get("attempt"), **sanitized})
                elif status == "success":
                    resp = entry.get("response", {})
                    sanitized = sanitize_obj({"finish_reason": resp.get("finish_reason"),
                                              "usage": resp.get("usage"),
                                              "message": resp.get("message", {}),
                                              "latency_s": entry.get("latency_s")})
                    response_entries.append({"request_id": rid, "ts": entry.get("ts"),
                                             "attempt": entry.get("attempt"), **sanitized})
                    # Extract tool calls from response message
                    msg = resp.get("message", {})
                    tool_calls = msg.get("tool_calls") or []
                    if isinstance(tool_calls, list):
                        for tc in tool_calls:
                            fn = tc.get("function", {}) if isinstance(tc, dict) else {}
                            tool_entries.append({
                                "request_id": rid,
                                "tool_call_id": tc.get("id", "") if isinstance(tc, dict) else "",
                                "function_name": fn.get("name", ""),
                                "arguments": sanitize_text(str(fn.get("arguments", ""))[:500]),
                            })
                elif status == "error":
                    retry_entries.append({"request_id": rid, "ts": entry.get("ts"),
                                          "attempt": entry.get("attempt"),
                                          "error": str(entry.get("error", ""))[:500]})

            # Collect errors from run log for this question
            q_errors = list(q.get("errors", []))
            for (err_sid, err_qnum, err_orig), msgs in run_errors.items():
                if err_sid == sid and err_qnum == qi_1based:
                    q_errors.extend(msgs)

            evidence_hit = evidence_hit_ratio(
                result_row.get("evidence", []),
                result_row.get("prediction_context", []),
            )

            # Write real trace files
            with open(sample_dir / f"{qname}_raw_prompts.jsonl", "w") as f:
                for pe in prompt_entries:
                    f.write(json.dumps(pe, ensure_ascii=False) + "\n")
                if not prompt_entries:
                    f.write(json.dumps({"note": "no prompt data in raw API log for this question"}, ensure_ascii=False) + "\n")

            with open(sample_dir / f"{qname}_raw_responses.jsonl", "w") as f:
                for re_ in response_entries:
                    f.write(json.dumps(re_, ensure_ascii=False) + "\n")
                if not response_entries:
                    f.write(json.dumps({"note": "no response data in raw API log for this question"}, ensure_ascii=False) + "\n")

            with open(sample_dir / f"{qname}_retry_log.jsonl", "w") as f:
                wrote = False
                for re_ in retry_entries:
                    f.write(json.dumps(re_, ensure_ascii=False) + "\n"); wrote = True
                for err_msg in q_errors:
                    f.write(json.dumps({"error": err_msg}, ensure_ascii=False) + "\n"); wrote = True
                if not wrote:
                    f.write(json.dumps({"note": "no retries or errors for this question"}, ensure_ascii=False) + "\n")

            # Update trace JSON with real info
            trace = {
                "sample": f"conv-{sid}", "question_index": qi_1based, "category": q.get("cat", "?"),
                "question": result_row.get("question", "?"),
                "gold_answer": str(result_row.get("answer", "")),
                "gold_evidence": result_row.get("evidence", []),
                "prediction": str(result_row.get("prediction", "")),
                "prediction_context": result_row.get("prediction_context", []),
                "evidence_hit": round(evidence_hit, 3),
                "prompt_count": len(prompt_entries),
                "response_count": len(response_entries),
                "tool_call_count": len(tool_entries),
                "tool_call_sequence": tool_entries[:20],
                "error_count": len(retry_entries) + len(q_errors),
                "error_details": [str(e)[:300] for e in (retry_entries + [{"error": e} for e in q_errors])],
                "metrics": result_row.get("_metrics", {}),
                "raw_call_ids": q_call_ids[:30],
            }
            with open(sample_dir / f"{qname}_trace.json", "w") as f:
                json.dump(trace, f, ensure_ascii=False, indent=2)

            # Manifest
            from eval.evaluation import f1_score as f1_scorer
            pred = str(result_row.get("prediction", ""))
            gold = result_row.get("answer")
            f1_val = 0.0
            if pred == "ERROR": f1_val = 0.0
            elif gold is None:
                neg = ["not mentioned","no information","cannot be determined","not specified","none","not stated","no evidence","does not mention","not provide","unclear"]
                f1_val = 1.0 if any(ph in pred.lower() for ph in neg) else 0.0
            else:
                f1_val = f1_scorer(pred, str(gold))

            error_type = ""
            if pred == "ERROR":
                all_err_text = " ".join(str(e) for e in q_errors + [r.get("error","") for r in retry_entries])
                if "timed out" in all_err_text.lower() or "timeout" in all_err_text.lower():
                    error_type = "api_timeout"
                elif "json parse" in all_err_text.lower():
                    error_type = "json_parse_failure"
                elif all_err_text:
                    error_type = "other"
                else:
                    error_type = "unknown"

            manifest_rows.append({
                "sample": f"conv-{sid}", "question_index": qi_1based, "category": q.get("cat", "?"),
                "question": result_row.get("question", "?"),
                "gold_answer": str(gold), "gold_evidence": str(result_row.get("evidence", [])),
                "prediction": pred, "prediction_context": str(result_row.get("prediction_context", []))[:500],
                "f1": round(f1_val, 3), "evidence_hit": round(evidence_hit, 3),
                "trace_file": f"result/diagnostics/mragent_100q_traces/conv-{sid}/{qname}_trace.json",
                "raw_prompt_file": f"result/diagnostics/mragent_100q_traces/conv-{sid}/{qname}_raw_prompts.jsonl",
                "raw_response_file": f"result/diagnostics/mragent_100q_traces/conv-{sid}/{qname}_raw_responses.jsonl",
                "retry_log_file": f"result/diagnostics/mragent_100q_traces/conv-{sid}/{qname}_retry_log.jsonl",
                "error_type": error_type,
                "error_message": " | ".join(str(e)[:200] for e in (q_errors + [r.get("error","") for r in retry_entries]))[:300],
                "runtime_sec": result_row.get("_metrics", {}).get("runtime_sec", 0),
                "tool_calls": len(tool_entries),
                "prompt_entries": len(prompt_entries),
                "response_entries": len(response_entries),
            })

            if prompt_entries: total_prompts += 1
            if response_entries: total_responses += 1
            if tool_entries: total_tools += 1
            if retry_entries or q_errors: total_retries += 1

    # Write manifest
    with open("reports/mragent_100q_trace_manifest_20260709.jsonl", "w") as f:
        for mr in manifest_rows:
            f.write(json.dumps(mr, ensure_ascii=False) + "\n")

    # Summary
    total_qs = len(manifest_rows)
    errors_in_manifest = sum(1 for m in manifest_rows if m["prediction"] == "ERROR")
    print(f"\n=== Final Summary ===")
    print(f"Total questions: {total_qs}")
    print(f"Real prompt coverage: {total_prompts}/{total_qs}")
    print(f"Real response coverage: {total_responses}/{total_qs}")
    print(f"Tool call sequence coverage: {total_tools}/{total_qs}")
    print(f"Retry/error coverage: {total_retries}/{total_qs}")
    print(f"ERRORs: {errors_in_manifest}")

    for m in manifest_rows:
        if m["prediction"] == "ERROR":
            print(f"\nERROR: {m['sample']} Q{m['question_index']}")
            print(f"  Question: {m['question'][:100]}")
            print(f"  Type: {m['error_type']}")
            print(f"  Message: {m['error_message'][:300]}")
            print(f"  Prompt entries: {m['prompt_entries']}, Response entries: {m['response_entries']}")
            print(f"  Tool calls: {m['tool_calls']}, Runtime: {m['runtime_sec']}s")

if __name__ == "__main__":
    main()
