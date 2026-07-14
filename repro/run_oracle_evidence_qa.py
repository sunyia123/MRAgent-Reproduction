#!/usr/bin/env python3
"""Oracle evidence QA baseline.

The model receives gold evidence rewrite sentences directly. This tests whether
errors come from retrieval/tool path or from answer synthesis/evaluation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import config
from data.get_data import get_data
from llm.controller import LLM
from repro.baseline_utils import answer_system_prompt, format_question, load_subset_manifest


SYSTEM_PROMPT = """Answer the question using ONLY the provided gold evidence context.
If the evidence is insufficient, answer "no information available".
Give a concise answer."""


def load_rewrite_sentences(rewrite_path: str) -> list[dict[str, Any]]:
    rows = []
    with open(rewrite_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            for _, data in obj.items():
                if not isinstance(data, dict):
                    continue
                for sent in data.get("sentence") or []:
                    rows.append(
                        {
                            "id": sent.get("id", ""),
                            "origin": sent.get("origin", ""),
                            "tag": sent.get("tag", ""),
                            "text": sent.get("text", ""),
                            "event_time": sent.get("time", ""),
                            "session_date": data.get("conversation_time", ""),
                        }
                    )
    return rows


def evidence_context(sentences: list[dict[str, Any]], evidence_ids: list[Any]) -> tuple[str, list[str]]:
    wanted = [str(e) for e in evidence_ids or []]
    matched = []
    seen = set()
    for ev in wanted:
        prefix = f"{ev}-"
        for sent in sentences:
            if sent["origin"] == ev or sent["id"] == ev or sent["id"].startswith(prefix):
                if sent["id"] not in seen:
                    matched.append(sent)
                    seen.add(sent["id"])
    lines = []
    for sent in matched:
        metadata = []
        if sent.get("event_time"):
            metadata.append(f"event_date={sent['event_time']}")
        if sent.get("session_date"):
            metadata.append(f"session_date={sent['session_date']}")
        date_text = f" ({'; '.join(metadata)})" if metadata else ""
        lines.append(f"[{sent['id']}]{date_text} [{sent['tag']}] origin={sent['origin']} text={sent['text']}")
    return "\n".join(lines), sorted({s["origin"] for s in matched})


def answer(llm: LLM, question: str, context: str, category: Any) -> str:
    result = llm.chat_plain_text(
        messages=[
            {"role": "system", "content": answer_system_prompt(SYSTEM_PROMPT, category)},
            {"role": "user", "content": f"Question: {question}\n\nGold evidence context:\n{context}\n\nAnswer:"},
        ],
        model=config.QA_MODEL,
        max_tokens=config.QA_MAX_TOKENS,
    )
    return str(result or "no information available")


def run_sample(args: argparse.Namespace, sample_id: str, qa_list: list[dict[str, Any]], q_indices: list[int] | None) -> None:
    rewrite_path = config.rewrite_template.format(dataset=args.data, sample_id=sample_id)
    if not os.path.exists(rewrite_path):
        raise FileNotFoundError(rewrite_path)
    sentences = load_rewrite_sentences(rewrite_path)
    result_path = config.result_template.format(dataset=args.data, sample_id=sample_id).replace(
        f"result_{config.ADDITIONAL_RE}", f"result_{args.model}_{args.file}"
    )
    os.makedirs(os.path.dirname(result_path), exist_ok=True)
    items = [(idx, qa_list[idx]) for idx in q_indices] if q_indices is not None else list(enumerate(qa_list))

    done = 0
    if os.path.exists(result_path):
        with open(result_path, encoding="utf-8") as f:
            done = sum(1 for line in f if line.strip())
    if done >= len(items):
        return

    llm = LLM()
    for seq, (orig_idx, qa) in enumerate(items):
        if seq < done:
            continue
        context, pred_ctx = evidence_context(sentences, qa.get("evidence") or [])
        started = time.time()
        try:
            prediction = answer(llm, format_question(qa, sample_id, orig_idx), context, qa.get("category"))
        except Exception as exc:
            prediction = "ERROR"
            print(f"{sample_id} q{orig_idx+1} failed: {exc}")
        runtime = round(time.time() - started, 2)
        row = {
            "answer": qa.get("answer"),
            "prediction": prediction,
            "category": qa.get("category"),
            "evidence": qa.get("evidence") or [],
            "question": qa.get("question"),
            "prediction_context": pred_ctx,
            "sample": sample_id,
            "question_index": orig_idx,
            "question_index_1based": orig_idx + 1,
            "_metrics": {
                "tool_calls": 0,
                "schema_retries": 0,
                "forced_accepts": 0,
                "runtime_sec": runtime,
                "oracle_evidence_count": len(pred_ctx),
                "qa_model": config.QA_MODEL,
            },
        }
        with open(result_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        print(f"{sample_id} {seq+1}/{len(items)} orig={orig_idx+1} cat={qa.get('category')} done")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run oracle evidence QA baseline.")
    parser.add_argument("--data", default="locomo")
    parser.add_argument("--model", default="deepseek")
    parser.add_argument("--file", default="oracle")
    parser.add_argument("--sample_ids", default=None)
    parser.add_argument("--subset_manifest", default=None)
    parser.add_argument("--qa_model", default=None, help="QA model; parsed by common.config before this runner starts")
    args = parser.parse_args()

    _, question_list, _, _ = get_data(args.data, f"data/dataset_{args.data}.json")
    subset = load_subset_manifest(args.subset_manifest)
    if args.sample_ids:
        sample_ids = [s.strip() if s.strip().startswith("conv-") else f"conv-{s.strip()}" for s in args.sample_ids.split(",") if s.strip()]
    elif subset:
        sample_ids = list(subset)
    else:
        sample_ids = list(question_list)

    for sample_id in sample_ids:
        q_indices = subset.get(sample_id) if subset else None
        run_sample(args, sample_id, question_list.get(sample_id, []), q_indices)


if __name__ == "__main__":
    main()
