import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # add repo root to path for standalone runs
import argparse
import hashlib
import json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import openai
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()  # read API key from .env

# Judge LLM configuration — env-variable driven, provider-agnostic
JUDGE_API_KEY = os.getenv("JUDGE_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
JUDGE_BASE_URL = os.getenv("JUDGE_BASE_URL", os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1"))
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "deepseek-ai/DeepSeek-V4-Flash")
JUDGE_ENABLE_THINKING = os.getenv("JUDGE_ENABLE_THINKING", "0") == "1"
JUDGE_MAX_TOKENS = int(os.getenv("JUDGE_MAX_TOKENS", "256"))
JUDGE_TIMEOUT_SECONDS = float(os.getenv("JUDGE_TIMEOUT_SECONDS", "120"))
JUDGE_CLIENT_MAX_RETRIES = int(os.getenv("JUDGE_CLIENT_MAX_RETRIES", "0"))
JUDGE_CALL_MAX_ATTEMPTS = int(os.getenv("JUDGE_CALL_MAX_ATTEMPTS", "2"))
_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=JUDGE_API_KEY,
            base_url=JUDGE_BASE_URL,
            timeout=JUDGE_TIMEOUT_SECONDS,
            max_retries=JUDGE_CLIENT_MAX_RETRIES,
        )
    return _client

ACCURACY_PROMPT = """
Your task is to label an answer to a question as ’CORRECT’ or ’WRONG’. You will be given the following data:
    (1) a question (posed by one user to another user), 
    (2) a ’gold’ (ground truth) answer, 
    (3) a generated answer
which you will score as CORRECT/WRONG.

The point of the question is to ask about something one user should know about the other user based on their prior conversations.
The gold answer will usually be a concise and short answer that includes the referenced topic, for example:
Question: Do you remember what I got the last time I went to Hawaii?
Gold answer: A shell necklace
The generated answer might be much longer, but you should be generous with your grading - as long as it touches on the same topic as the gold answer, it should be counted as CORRECT. 

For time related questions, the gold answer will be a specific date, month, year, etc. The generated answer might be much longer or use relative time references (like "last Tuesday" or "next month"), but you should be generous with your grading - as long as it refers to the same date or time period as the gold answer, it should be counted as CORRECT. Even if the format differs (e.g., "May 7th" vs "7 May"), consider it CORRECT if it's the same date.

Now it’s time for the real question:
Question: {question}
Gold answer: {gold_answer}
Generated answer: {generated_answer}

Return exactly one JSON object using one of these two forms:
{{"label":"CORRECT"}}
{{"label":"WRONG"}}
Do not include an explanation, Markdown, or any additional keys.
"""
JUDGE_PROMPT_VERSION = hashlib.sha256(ACCURACY_PROMPT.encode("utf-8")).hexdigest()[:12]


def build_judge_prompt(question, gold_answer, generated_answer):
    return ACCURACY_PROMPT.format(
        question=question,
        gold_answer=gold_answer,
        generated_answer=generated_answer,
    )


def _usage_dict(usage):
    if usage is None:
        return None
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    return {
        key: getattr(usage, key, None)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }


def parse_judge_label(raw_content):
    parsed = json.loads(raw_content)
    if not isinstance(parsed, dict):
        raise ValueError(f"judge response must be a JSON object, got {type(parsed).__name__}")
    label = str(parsed.get("label", "")).strip().upper()
    if label not in {"CORRECT", "WRONG"}:
        raise ValueError(f"judge response has invalid label {label!r}: {raw_content[:500]!r}")
    return label


class JudgeResponseError(ValueError):
    def __init__(self, message, audit):
        super().__init__(message)
        self.audit = audit


def judge_done_sets(rows):
    by_index = set()
    by_question = set()
    for row in rows:
        sample_id = str(row.get("sample", row.get("sample_id", "")))
        if row.get("question_index") is not None:
            by_index.add((sample_id, int(row["question_index"])))
        if row.get("question") is not None:
            by_question.add((sample_id, str(row["question"])))
    return by_index, by_question


def order_rows_by_manifest(rows, manifest_path):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    ordered_keys = [
        (str(record["sample_id"]), int(record["question_index"]))
        for record in manifest.get("records", [])
    ]
    rows_by_key = {}
    for row in rows:
        sample_id = row.get("sample", row.get("sample_id"))
        question_index = row.get("question_index")
        if sample_id is None or question_index is None:
            continue
        rows_by_key[(str(sample_id), int(question_index))] = row
    missing = [key for key in ordered_keys if key not in rows_by_key]
    if missing:
        raise ValueError(f"Judge manifest rows missing from results: {missing[:10]}")
    return [rows_by_key[key] for key in ordered_keys]


def evaluate_llm_judge_detailed(question, gold_answer, generated_answer):
    """Return the score together with enough response metadata for an audit."""
    prompt = build_judge_prompt(question, gold_answer, generated_answer)
    kwargs = {
        "model": JUDGE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
        "max_tokens": JUDGE_MAX_TOKENS,
    }
    if "siliconflow" in JUDGE_BASE_URL.lower():
        kwargs["extra_body"] = {"enable_thinking": JUDGE_ENABLE_THINKING}

    audit = {
        "judge_model": JUDGE_MODEL,
        "judge_base_url": JUDGE_BASE_URL,
        "judge_prompt_version": JUDGE_PROMPT_VERSION,
        "judge_enable_thinking": JUDGE_ENABLE_THINKING,
        "judge_max_tokens": JUDGE_MAX_TOKENS,
        "judge_call_max_attempts": JUDGE_CALL_MAX_ATTEMPTS,
        "judge_prompt": prompt,
        "judge_attempts": [],
    }
    last_error = None
    for attempt in range(1, max(1, JUDGE_CALL_MAX_ATTEMPTS) + 1):
        started = time.monotonic()
        try:
            response = _get_client().chat.completions.create(**kwargs)
            choice = response.choices[0]
            message = choice.message
            raw_content = message.content or ""
            response_audit = {
                "attempt": attempt,
                "status": "response",
                "latency_s": round(time.monotonic() - started, 3),
                "raw_response": raw_content,
                "reasoning_content": getattr(message, "reasoning_content", None),
                "finish_reason": getattr(choice, "finish_reason", None),
                "usage": _usage_dict(getattr(response, "usage", None)),
                "response_id": getattr(response, "id", None),
            }
            audit["judge_attempts"].append(response_audit)
            try:
                label = parse_judge_label(raw_content)
            except (json.JSONDecodeError, ValueError) as exc:
                response_audit["status"] = "parse_error"
                response_audit["error_type"] = type(exc).__name__
                response_audit["error"] = repr(exc)
                last_error = exc
                continue

            return {
                "llm_score": 1 if label == "CORRECT" else 0,
                "judge_label": label,
                **audit,
                "judge_raw_response": raw_content,
                "judge_reasoning_content": response_audit["reasoning_content"],
                "judge_finish_reason": response_audit["finish_reason"],
                "judge_usage": response_audit["usage"],
                "judge_response_id": response_audit["response_id"],
                "judge_retries": attempt - 1,
            }
        except Exception as exc:
            if isinstance(exc, JudgeResponseError):
                raise
            audit["judge_attempts"].append({
                "attempt": attempt,
                "status": "api_error",
                "latency_s": round(time.monotonic() - started, 3),
                "error_type": type(exc).__name__,
                "error": repr(exc),
            })
            last_error = exc

    raise JudgeResponseError(
        f"judge failed after {len(audit['judge_attempts'])} attempts: {last_error}", audit
    ) from last_error


def evaluate_llm_judge(question, gold_answer, generated_answer):
    """Evaluate the generated answer against the gold answer using an LLM judge."""
    return evaluate_llm_judge_detailed(question, gold_answer, generated_answer)["llm_score"]


# def main():
#     """Main function to evaluate RAG results using LLM judge."""
#     parser.add_argument(
#         "--input_file",
#     )


#     output_path = f"results/llm_judge_{dataset_path.split('/')[-1]}"

#     with open(dataset_path, "r") as f:


#             question = x["question"]
#             gold_answer = x["answer"]
#             generated_answer = x["response"]
#             category = x["category"]

#             # Skip category 5

#             # Evaluate the answer
#             LLM_JUDGE[category].append(label)

#             # Store the results
#             RESULTS[index].append(
#                 {
#                     "question": question,
#                     "gt_answer": gold_answer,
#                     "response": generated_answer,
#                     "category": category,
#                     "llm_label": label,
#                 }
#             )

#             # Save intermediate results
#             with open(output_path, "w") as f:

#             # Print current accuracy for all categories
#         index += 1

#     # Save final results
#     with open(output_path, "w") as f:

#     # Print final summary


