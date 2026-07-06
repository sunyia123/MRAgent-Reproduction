#!/usr/bin/env python3
"""
Convert HuggingFace longmemeval_s_cleaned.json to MRAgent data/dataset_LM.json.

Source: https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned
Download: curl -L -o data/external/longmemeval_s_cleaned.json \
  https://hf-mirror.com/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_s_cleaned.json

Conversion:
  - haystack_sessions[i] → session_{i+1}: [{"role","content"}] → [{"speaker","dia_id","text"}]
  - Keep only user turns (LM mode requires user-only filtering in get_data)
  - haystack_dates[i] → session_{i+1}_date_time
  - question_type → category (MRAgent LM category mapping)
  - question, answer, question_date → qa list
  - answer_session_ids → evidence field in qa
  - question_id → sample_id

Usage:
  python repro/convert_longmemeval_to_mragent.py \
    --input data/external/longmemeval_s_cleaned.json \
    --output data/dataset_LM.json
"""

import json, argparse, hashlib, os, sys
from pathlib import Path
from collections import defaultdict

# MRAgent LM category mapping (from run.py category_dict["LM"])
QUESTION_TYPE_TO_CATEGORY = {
    "multi-session": 0,
    "single-session-user": 1,
    "temporal-reasoning": 2,
    "single-session-preference": 3,
    "knowledge-update": 4,
    "single-session-assistant": 5,
}


def convert_sample(hf_item: dict) -> dict:
    """Convert one HF sample to MRAgent LM format."""
    question_id = hf_item["question_id"]
    question_type = hf_item["question_type"]
    category = QUESTION_TYPE_TO_CATEGORY.get(question_type)
    if category is None:
        raise ValueError(f"Unknown question_type: {question_type} (id={question_id})")

    # Build conversation dict with session_1, session_1_date_time, etc.
    conversation = {}
    haystack = hf_item.get("haystack_sessions", [])
    dates = hf_item.get("haystack_dates", [])

    for i, session_turns in enumerate(haystack):
        sn = i + 1
        session_key = f"session_{sn}"
        date_key = f"session_{sn}_date_time"

        if i < len(dates):
            conversation[date_key] = dates[i]

        # Convert [{"role":"user","content":"..."}, {"role":"assistant","content":"..."}]
        # to [{"speaker":"user","dia_id":"D{sn}:{turn_i}","text":"..."}]
        turns = []
        for j, turn in enumerate(session_turns):
            if not isinstance(turn, dict):
                continue
            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            # Skip empty turns
            if not content or not content.strip():
                continue
            dia_id = f"D{sn}:{j + 1}"
            turns.append({
                "speaker": role,
                "dia_id": dia_id,
                "text": content.strip(),
            })
        conversation[session_key] = turns

    # Build qa list (MRAgent expects a list, even if one question per sample)
    qa = [{
        "question": hf_item["question"],
        "answer": hf_item["answer"],
        "category": category,
        "evidence": hf_item.get("answer_session_ids", []),
    }]

    # Build metadata with question_date (used by temporal reasoning)
    metadata = {"question_date": hf_item.get("question_date", "")}

    return {
        "sample_id": question_id,
        "conversation": conversation,
        "qa": qa,
        "metadata": metadata,
    }


def main():
    parser = argparse.ArgumentParser(description="Convert HF LongMemEval to MRAgent dataset_LM.json")
    parser.add_argument("--input", required=True, help="Path to longmemeval_s_cleaned.json")
    parser.add_argument("--output", default="data/dataset_LM.json", help="Output path")
    args = parser.parse_args()

    # Load source
    src_path = Path(args.input)
    if not src_path.exists():
        print(f"ERROR: {src_path} not found")
        sys.exit(1)

    raw = json.loads(src_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(raw)} items from {src_path}")

    # Convert
    converted = []
    stats = defaultdict(int)
    skipped = 0

    for item in raw:
        try:
            sample = convert_sample(item)
            converted.append(sample)
            qtype = item["question_type"]
            stats["total"] += 1
            stats[f"type_{qtype}"] += 1
            stats[f"cat_{sample['qa'][0]['category']}"] += 1
        except Exception as e:
            print(f"  SKIP {item.get('question_id', '?')}: {e}")
            skipped += 1

    # Write output
    out_path = Path(args.output)
    out_path.write_text(json.dumps(converted, ensure_ascii=False, indent=2), encoding="utf-8")
    out_size = out_path.stat().st_size
    out_sha = hashlib.sha256(out_path.read_bytes()).hexdigest()

    print(f"\nConverted: {len(converted)} samples ({skipped} skipped)")
    print(f"Output: {out_path} ({out_size:,} bytes, sha256={out_sha[:16]}...)")
    print(f"\nCategory distribution:")
    for cat_id in sorted(stats):
        if cat_id.startswith("cat_"):
            cat_num = cat_id.replace("cat_", "")
            cat_name = {v: k for k, v in QUESTION_TYPE_TO_CATEGORY.items()}.get(int(cat_num), "?")
            print(f"  cat {cat_num} ({cat_name}): {stats[cat_id]}")

    # Verify questions
    total_qa = sum(len(s["qa"]) for s in converted)
    print(f"Total questions: {total_qa}")


if __name__ == "__main__":
    main()
