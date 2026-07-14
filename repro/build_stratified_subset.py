#!/usr/bin/env python3
"""Build a fixed stratified LoCoMo subset manifest for core comparison runs."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def normalize_sample_id(value: str) -> str:
    value = str(value).strip()
    return value if value.startswith("conv-") else f"conv-{value}"


def select_for_sample(
    qa_list: list[dict[str, Any]],
    total: int,
    per_category: int,
    seed: int,
    allowed_categories: set[str] | None = None,
    included_indices: set[int] | None = None,
) -> list[int]:
    rng = random.Random(seed)
    by_cat: dict[str, list[int]] = defaultdict(list)
    for idx, qa in enumerate(qa_list):
        category = str(qa.get("category"))
        if allowed_categories is None or category in allowed_categories:
            by_cat[category].append(idx)

    eligible = {idx for indices in by_cat.values() for idx in indices}
    selected: dict[int, None] = {
        idx: None for idx in (included_indices or set()) if idx in eligible
    }
    if len(selected) > total:
        raise ValueError(f"included indices exceed per-sample total: {len(selected)} > {total}")
    for cat in sorted(by_cat, key=str):
        pool = [idx for idx in by_cat[cat] if idx not in selected]
        existing = sum(1 for idx in selected if idx in by_cat[cat])
        take = min(max(0, per_category - existing), len(pool), total - len(selected))
        for idx in rng.sample(pool, take):
            selected[idx] = None

    if len(selected) < total:
        remaining = [idx for idx in eligible if idx not in selected]
        rng.shuffle(remaining)
        for idx in remaining[: total - len(selected)]:
            selected[idx] = None

    return sorted(selected)


def load_included_indices(path: str | None) -> dict[str, set[int]]:
    if not path:
        return {}
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    result: dict[str, set[int]] = defaultdict(set)
    for record in manifest.get("records", []):
        sample_id = record.get("sample_id")
        question_index = record.get("question_index")
        if sample_id is not None and question_index is not None:
            result[str(sample_id)].add(int(question_index))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Build fixed stratified subset manifest.")
    parser.add_argument("--data_path", default="data/dataset_locomo.json")
    parser.add_argument("--sample_ids", default="26,30,41,42,43,44,47,48,49,50")
    parser.add_argument("--per_sample", type=int, default=10)
    parser.add_argument("--per_category", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--categories", default=None, help="Optional comma-separated LoCoMo categories, e.g. 1,2,3,4")
    parser.add_argument("--include_manifest", default=None, help="Existing manifest whose eligible questions must be retained")
    parser.add_argument("--output", default="data/subsets/locomo10_100q_seed42.json")
    args = parser.parse_args()

    data = json.loads(Path(args.data_path).read_text(encoding="utf-8"))
    wanted = [normalize_sample_id(s) for s in args.sample_ids.split(",") if s.strip()]
    by_sample = {sample.get("sample_id"): sample for sample in data}
    allowed_categories = {c.strip() for c in args.categories.split(",") if c.strip()} if args.categories else None
    included_indices = load_included_indices(args.include_manifest)

    records = []
    global_idx = 0
    for sample_id in wanted:
        if sample_id not in by_sample:
            raise KeyError(f"sample_id not found: {sample_id}")
        qa_list = by_sample[sample_id].get("qa") or []
        selected = select_for_sample(
            qa_list=qa_list,
            total=args.per_sample,
            per_category=args.per_category,
            seed=args.seed + sum(ord(c) for c in sample_id),
            allowed_categories=allowed_categories,
            included_indices=included_indices.get(sample_id),
        )
        if len(selected) != args.per_sample:
            raise ValueError(
                f"{sample_id}: only {len(selected)} eligible questions for requested per_sample={args.per_sample}"
            )
        for qidx in selected:
            qa = qa_list[qidx]
            global_idx += 1
            records.append(
                {
                    "global_index": global_idx,
                    "sample_id": sample_id,
                    "question_index": qidx,
                    "question_index_1based": qidx + 1,
                    "category": qa.get("category"),
                    "question": qa.get("question"),
                    "answer": qa.get("answer"),
                    "evidence": qa.get("evidence") or [],
                }
            )

    cat_counts = Counter(str(r["category"]) for r in records)
    sample_counts = Counter(r["sample_id"] for r in records)
    manifest = {
        "name": Path(args.output).stem,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "data_path": args.data_path,
        "sample_ids": wanted,
        "per_sample": args.per_sample,
        "per_category": args.per_category,
        "seed": args.seed,
        "categories": sorted(allowed_categories) if allowed_categories else "all",
        "include_manifest": args.include_manifest,
        "n_questions": len(records),
        "category_counts": dict(sorted(cat_counts.items())),
        "sample_counts": dict(sorted(sample_counts.items())),
        "records": records,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    print(json.dumps({"n_questions": len(records), "category_counts": manifest["category_counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
