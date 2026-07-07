#!/usr/bin/env python3
"""Print the effective runtime config for a command.

Run this with the same argv as the experiment runner, for example:
  python repro/audit_runtime_config.py --sample_ids 26 --model deepseek --re_model v4flash

It imports common.config after argparse sees those flags, so the printed values
match what run_stratified.py/run.py would use.
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import config


def _effective_embed_model():
    if os.getenv("EMBED_MODEL"):
        return os.getenv("EMBED_MODEL")
    return "Qwen/Qwen3-Embedding-4B" if "siliconflow.cn" in config.EMBED_BASE_URL else "text-embedding-3-large"


def _redact(value):
    if not value:
        return False
    text = str(value)
    if len(text) <= 8:
        return "***"
    return f"{text[:4]}...{text[-4:]}"


def main():
    payload = {
        "args_model": config.args.model,
        "args_re_model": config.args.re_model,
        "MODEL": config.MODEL,
        "RE_MODEL": config.RE_MODEL,
        "MODEL_NAME": config.MODEL_NAME,
        "LLM_BASE_URL": config.LLM_BASE_URL,
        "EMBED_BASE_URL": config.EMBED_BASE_URL,
        "EMBED_MODEL": _effective_embed_model(),
        "EMBED_MODEL_FROM_ENV": bool(os.getenv("EMBED_MODEL")),
        "API_KEY_SET": bool(config.API_KEY),
        "API_KEY_HEAD_TAIL": _redact(config.API_KEY),
        "DEEPSEEK_MODEL_ID": os.getenv("DEEPSEEK_MODEL_ID"),
        "QWEN_MODEL_ID": os.getenv("QWEN_MODEL_ID"),
        "SAMPLE_IDS": config.SAMPLE_IDS,
        "SUBSET_MANIFEST": config.SUBSET_MANIFEST,
        "STRATIFIED_TOTAL": config.STRATIFIED_TOTAL,
        "STRATIFIED_PER_CATEGORY": config.STRATIFIED_PER_CATEGORY,
        "ADDITIONAL_TK": config.ADDITIONAL_TK,
        "ADDITIONAL_RE": config.ADDITIONAL_RE,
        "rewrite_template": config.rewrite_template,
        "keyword_template": config.keyword_template,
        "embedding_template": config.embedding_template,
        "result_template": config.result_template,
        "REWRITE_MAX_TOKENS": config.REWRITE_MAX_TOKENS,
        "KEYWORD_MAX_TOKENS": config.KEYWORD_MAX_TOKENS,
        "QA_MAX_TOKENS": config.QA_MAX_TOKENS,
        "API_TIMEOUT_SECONDS": config.API_TIMEOUT_SECONDS,
        "API_CLIENT_MAX_RETRIES": config.API_CLIENT_MAX_RETRIES,
        "API_CALL_MAX_RETRIES": config.API_CALL_MAX_RETRIES,
        "CHAT_TEXT_PARSE_MAX_ATTEMPTS": config.CHAT_TEXT_PARSE_MAX_ATTEMPTS,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
