#!/usr/bin/env python3
"""
Model diagnostic: send the SAME rewrite prompt for conv-30 failed sessions
to multiple model configurations, capture raw evidence, and compare.

Per docs/handoff.md §Model Diagnostic Evidence Requirements:
  - 1 known-success session (e.g., session_1)
  - 3 failed sessions (6, 8, 17)
  - Same prompt, same parser, same schema checker
  - Compare DeepSeek current / json_object / 16384 / 32768 / Qwen3-235B / Gemini

Usage:
  DIAGNOSTIC_LOG=1 python diagnose_rewrite.py --sample 30 --sessions 1,6,8,17
"""

import os, sys, json, time, hashlib, copy, argparse, logging
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from llm.controller import LLM
from prompts.prompts import Prompts
from prompts import schema as json_scheme
from common import config

logger = logging.getLogger("diagnose")
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')

# --- Output dirs ---
DIAG_DIR = os.path.join("result", "diagnostics", "rewrite")
RAW_DIR = os.path.join(DIAG_DIR, "raw")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(os.path.join("result", "diagnostics", "raw_api_calls"), exist_ok=True)

RUN_ID = datetime.now().strftime("%Y%m%d-%H%M%S")

# --- Model configurations to test ---
DS_MODEL = os.getenv("DEEPSEEK_MODEL_ID", "deepseek-ai/DeepSeek-V4-Pro")
QW_MODEL = "Qwen/Qwen3.5-397B-A17B"
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.siliconflow.cn/v1")
API_KEY = os.getenv("OPENAI_API_KEY")

MODEL_CONFIGS = [
    # DeepSeek-V4-Pro: token budget sweep
    {"label": "ds_4096",     "model_id": DS_MODEL, "base_url": BASE_URL, "api_key": API_KEY,
     "max_tokens": 4096,  "temperature": 0.0, "extra": {}},
    {"label": "ds_16384",    "model_id": DS_MODEL, "base_url": BASE_URL, "api_key": API_KEY,
     "max_tokens": 16384, "temperature": 0.0, "extra": {}},
    {"label": "ds_32768",    "model_id": DS_MODEL, "base_url": BASE_URL, "api_key": API_KEY,
     "max_tokens": 32768, "temperature": 0.0, "extra": {}},
    # DeepSeek with response_format=json_object
    {"label": "ds_16384_json", "model_id": DS_MODEL, "base_url": BASE_URL, "api_key": API_KEY,
     "max_tokens": 16384, "temperature": 0.0,
     "extra": {"response_format": {"type": "json_object"}}},
    # Qwen3-397B: token budget sweep
    {"label": "qw_4096",     "model_id": QW_MODEL, "base_url": BASE_URL, "api_key": API_KEY,
     "max_tokens": 4096,  "temperature": 0.0, "extra": {}},
    {"label": "qw_16384",    "model_id": QW_MODEL, "base_url": BASE_URL, "api_key": API_KEY,
     "max_tokens": 16384, "temperature": 0.0, "extra": {}},
    # Qwen with json_object (if supported; record error if not)
    {"label": "qw_16384_json", "model_id": QW_MODEL, "base_url": BASE_URL, "api_key": API_KEY,
     "max_tokens": 16384, "temperature": 0.0,
     "extra": {"response_format": {"type": "json_object"}}},
]

def load_session(sample_id: str, session_num: int) -> tuple:
    """Load a single session's raw text from the dataset."""
    with open(config.datapath) as f:
        ds = json.load(f)
    for s in ds:
        if s.get("sample_id") == sample_id:
            conv = s["conversation"]
            sk = f"session_{session_num}"
            text = conv.get(sk)
            if text is None:
                return None, f"session {sk} not found in dataset"
            return text, None
    return None, f"sample {sample_id} not found"


def build_prompt(session_text: str) -> tuple:
    """Build the exact same rewrite prompt the pipeline uses."""
    system_prompt = Prompts.REWRITE_SYSTEM_PROMPT
    user_prompt = Prompts.extract_rewrite_prompt(json.dumps(session_text, ensure_ascii=False))
    return system_prompt, user_prompt


def call_rewrite_api(system_prompt: str, user_prompt: str, config_label: str,
                     model_id: str, base_url: str, api_key: str,
                     max_tokens: int, temperature: float, extra: dict) -> dict:
    """Make a single rewrite API call and capture ALL diagnostic evidence."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=600.0, max_retries=1)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    req = dict(
        model=model_id,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    req.update(extra)

    result = {
        "timestamp": datetime.now().isoformat(),
        "config_label": config_label,
        "model_id": model_id,
        "base_url": base_url,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "extra_params": {k: str(v) for k, v in extra.items()},
        "prompt": {
            "system_prompt_length": len(system_prompt),
            "user_prompt_length": len(user_prompt),
            "system_sha256": hashlib.sha256(system_prompt.encode()).hexdigest(),
            "user_sha256": hashlib.sha256(user_prompt.encode()).hexdigest(),
        },
        "response": {},
        "parse_result": {},
        "schema_result": {},
    }

    _t0 = time.time()
    try:
        resp = client.chat.completions.create(**req)
        latency = time.time() - _t0
        result["latency_s"] = round(latency, 3)

        choice = resp.choices[0]
        msg = choice.message

        # --- Raw response capture ---
        result["response"]["finish_reason"] = choice.finish_reason
        result["response"]["model"] = resp.model
        result["response"]["content"] = msg.content or ""
        result["response"]["content_length"] = len(msg.content) if msg.content else 0
        result["response"]["reasoning_content"] = getattr(msg, "reasoning_content", None) or ""
        result["response"]["reasoning_content_length"] = len(result["response"]["reasoning_content"])
        result["response"]["tool_calls"] = [
            {"id": tc.id, "function": tc.function.name, "arguments": tc.function.arguments}
            for tc in (msg.tool_calls or [])
        ] if hasattr(msg, "tool_calls") else []

        usage = resp.usage
        if usage:
            result["response"]["usage"] = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            }

        # Check for max_tokens truncation
        result["response"]["truncation_suspected"] = (
            choice.finish_reason == "length" or
            (usage and usage.completion_tokens >= max_tokens)
        )

    except Exception as e:
        result["error"] = repr(e)
        result["error_type"] = type(e).__name__
        result["latency_s"] = round(time.time() - _t0, 3)
        return result

    # --- Parse JSON ---
    raw_text = msg.content or ""
    parse_status = "unknown"
    parse_error = ""
    parsed_obj = None

    if not raw_text.strip():
        parse_status = "empty"
        parse_error = "content is empty or whitespace only"
    else:
        try:
            parsed_obj = json.loads(raw_text)
            parse_status = "ok"
        except json.JSONDecodeError as e:
            parse_error = str(e)[:500]
            # Try extract_json_from_content
            from common.utils import extract_json_from_content
            try:
                parsed_obj = extract_json_from_content(raw_text)
                parse_status = "recovered_via_extract"
            except Exception as e2:
                parse_status = "json_parse_error"
                parse_error += f" | extract also failed: {str(e2)[:200]}"

    result["parse_result"] = {
        "status": parse_status,
        "error": parse_error,
        "raw_text_preview": raw_text[:500],
        "raw_text_length": len(raw_text),
    }

    # --- Schema validation ---
    if parsed_obj is not None and parse_status in ("ok", "recovered_via_extract"):
        from agent.agent import Agent
        Agent._normalize_sentence_ids(parsed_obj)
        flag, err = json_scheme.check_rewrite_json(parsed_obj, "")
        result["schema_result"] = {
            "valid": flag,
            "error": str(err)[:500] if err else "",
        }
        # Check null fields
        if isinstance(parsed_obj, dict):
            result["schema_result"]["sentence_is_null"] = parsed_obj.get("sentence") is None
            result["schema_result"]["topics_is_null"] = parsed_obj.get("topics") is None
            result["schema_result"]["personal_sentences_is_null"] = parsed_obj.get("personal_sentences") is None
            s = parsed_obj.get("sentence")
            result["schema_result"]["sentence_count"] = len(s) if isinstance(s, list) else 0
            t = parsed_obj.get("topics")
            result["schema_result"]["topics_count"] = len(t) if isinstance(t, dict) else 0
            p = parsed_obj.get("personal_sentences")
            result["schema_result"]["personal_count"] = len(p) if isinstance(p, list) else 0
    else:
        result["schema_result"] = {"valid": False, "error": "no valid JSON to validate"}

    return result


def save_raw_evidence(session_num: int, config_label: str, result: dict, system_prompt: str, user_prompt: str):
    """Save raw prompt/response to disk for audit trail."""
    tag = f"session{session_num}_{config_label}_{RUN_ID}"
    evidence = {
        "run_id": RUN_ID,
        "session": session_num,
        "config": config_label,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "raw_response_content": result.get("response", {}).get("content", ""),
        "raw_response_reasoning": result.get("response", {}).get("reasoning_content", ""),
        "finish_reason": result.get("response", {}).get("finish_reason"),
        "usage": result.get("response", {}).get("usage", {}),
        "parse_status": result.get("parse_result", {}).get("status"),
        "parse_error": result.get("parse_result", {}).get("error"),
        "schema_valid": result.get("schema_result", {}).get("valid"),
        "schema_error": result.get("schema_result", {}).get("error"),
        "truncation_suspected": result.get("response", {}).get("truncation_suspected"),
        "error": result.get("error"),
    }
    path = os.path.join(RAW_DIR, f"{tag}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--diag_sample", type=str, default="conv-30")
    parser.add_argument("--diag_sessions", type=str, default="1,6,8,17",
                        help="Comma-separated session numbers (1=OK, 6,8,17=failed)")
    args, _ = parser.parse_known_args()

    session_numbers = [int(x.strip()) for x in args.diag_sessions.split(",")]
    logger.info(f"Diagnostic run {RUN_ID}: sessions={session_numbers}, configs={len(MODEL_CONFIGS)}")

    all_results = []
    manifest_entries = []

    for sn in session_numbers:
        session_text, err = load_session(args.diag_sample, sn)
        if err:
            logger.error(f"session_{sn}: {err}")
            continue

        system_prompt, user_prompt = build_prompt(session_text)
        logger.info(f"session_{sn}: loaded ({len(session_text)} chars text, "
                     f"prompt: sys={len(system_prompt)} user={len(user_prompt)})")

        for cfg in MODEL_CONFIGS:
            label = cfg["label"]
            logger.info(f"  → {label} (max_tokens={cfg['max_tokens']})")

            result = call_rewrite_api(
                system_prompt, user_prompt,
                config_label=label,
                model_id=cfg["model_id"],
                base_url=cfg["base_url"],
                api_key=cfg["api_key"],
                max_tokens=cfg["max_tokens"],
                temperature=cfg["temperature"],
                extra=cfg["extra"],
            )

            result["session"] = sn
            result["sample"] = args.diag_sample

            # Save raw evidence
            evidence_path = save_raw_evidence(sn, label, result, system_prompt, user_prompt)

            # Summary
            fs = result.get("response", {}).get("finish_reason", "N/A")
            ps = result.get("parse_result", {}).get("status", "N/A")
            sv = result.get("schema_result", {}).get("valid", "N/A")
            sc = result.get("schema_result", {}).get("sentence_count", "N/A")
            tok = result.get("response", {}).get("usage", {}).get("total_tokens", "N/A")
            trunc = "⚠ TRUNC" if result.get("response", {}).get("truncation_suspected") else ""
            err_flag = "❌ ERROR" if result.get("error") else ""
            null_flag = " NULL_SENT" if result.get("schema_result", {}).get("sentence_is_null") else ""

            logger.info(f"    finish={fs} parse={ps} schema_valid={sv} "
                         f"sentence_count={sc} tokens={tok} {trunc}{err_flag}{null_flag}")

            manifest_entries.append({
                "session": sn,
                "config": label,
                "model_id": cfg["model_id"],
                "max_tokens": cfg["max_tokens"],
                "finish_reason": fs,
                "parse_status": ps,
                "schema_valid": sv,
                "sentence_count": sc,
                "total_tokens": tok,
                "truncation_suspected": result.get("response", {}).get("truncation_suspected", False),
                "error": result.get("error"),
                "evidence_path": evidence_path,
            })

            all_results.append(result)

    # --- Write manifest ---
    manifest = {
        "run_id": RUN_ID,
        "sample": args.diag_sample,
        "sessions_tested": session_numbers,
        "model_configs": [
            {"label": c["label"], "model_id": c["model_id"], "max_tokens": c["max_tokens"]}
            for c in MODEL_CONFIGS
        ],
        "results": manifest_entries,
    }
    manifest_path = os.path.join(DIAG_DIR, f"diagnostic_manifest_{RUN_ID}.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # --- Print summary table ---
    print("\n" + "=" * 100)
    print(f"DIAGNOSTIC RESULTS — {RUN_ID}")
    print("=" * 100)
    header = f"{'Session':<8} {'Config':<20} {'Finish':<12} {'Parse':<25} {'Schema':<8} {'Sent':<6} {'Tokens':<8} {'Flags'}"
    print(header)
    print("-" * 100)
    for e in manifest_entries:
        flags = []
        if e.get("truncation_suspected"): flags.append("TRUNC")
        if e.get("error"): flags.append("ERROR")
        print(f"{e['session']:<8} {e['config']:<20} {str(e['finish_reason']):<12} "
              f"{str(e['parse_status']):<25} {str(e['schema_valid']):<8} "
              f"{str(e['sentence_count']):<6} {str(e['total_tokens']):<8} {' '.join(flags)}")
    print("=" * 100)
    print(f"\nManifest: {manifest_path}")
    print(f"Raw evidence: {RAW_DIR}/")
    print(f"Run log: result/diagnostics/raw_api_calls.jsonl (if DIAGNOSTIC_LOG=1)")


if __name__ == "__main__":
    main()
