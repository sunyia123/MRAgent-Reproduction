#!/usr/bin/env python3
"""Build the fixed LoCoMo manifests used by the 500-question main run and ablation."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


DEFAULT_SAMPLES = "26,30,41,42,43,44,47,48,49,50"


def normalize_sample_id(value: str) -> str:
    value = str(value).strip()
    return value if value.startswith("conv-") else f"conv-{value}"


def build_pools(
    samples: dict[str, dict[str, Any]],
    sample_ids: list[str],
    categories: Iterable[int],
    seed: int,
    allowed: set[tuple[str, int]] | None = None,
) -> dict[int, dict[str, list[int]]]:
    pools: dict[int, dict[str, list[int]]] = defaultdict(dict)
    for sample_pos, sample_id in enumerate(sample_ids):
        qa_list = samples[sample_id].get("qa") or []
        for category in categories:
            indices = [
                index for index, qa in enumerate(qa_list)
                if int(qa.get("category")) == category
                and (allowed is None or (sample_id, index) in allowed)
            ]
            random.Random(seed + sample_pos * 1009 + category * 9176).shuffle(indices)
            pools[category][sample_id] = indices
    return pools


def select_balanced(
    pools: dict[int, dict[str, list[int]]],
    quotas: dict[int, int],
    sample_ids: list[str],
    initial_sample_counts: Counter[str] | None = None,
) -> list[tuple[str, int, int]]:
    """Select exact category quotas while balancing each category across conversations."""
    selected: list[tuple[str, int, int]] = []
    sample_counts = Counter(initial_sample_counts or {})
    sample_category_counts: Counter[tuple[str, int]] = Counter()

    for category in sorted(quotas):
        available = sum(len(pools[category][sample_id]) for sample_id in sample_ids)
        if available < quotas[category]:
            raise ValueError(
                f"category {category}: requested {quotas[category]}, only {available} available")
        for _ in range(quotas[category]):
            candidates = [sample_id for sample_id in sample_ids if pools[category][sample_id]]
            sample_id = min(
                candidates,
                key=lambda value: (
                    sample_category_counts[(value, category)],
                    sample_counts[value],
                    sample_ids.index(value),
                ),
            )
            question_index = pools[category][sample_id].pop()
            selected.append((sample_id, question_index, category))
            sample_category_counts[(sample_id, category)] += 1
            sample_counts[sample_id] += 1
    return selected


def balanced_ordinary_quotas(capacities: dict[int, int], total: int) -> dict[int, int]:
    """Water-fill category quotas, redistributing shortages without hiding them."""
    quotas = {category: 0 for category in sorted(capacities)}
    for _ in range(total):
        candidates = [category for category in quotas if quotas[category] < capacities[category]]
        if not candidates:
            raise ValueError(f"only {sum(capacities.values())} ordinary questions are available")
        category = min(candidates, key=lambda value: (quotas[value], value))
        quotas[category] += 1
    return quotas


def make_records(
    selected: Iterable[tuple[str, int, int]],
    samples: dict[str, dict[str, Any]],
    sample_ids: list[str],
) -> list[dict[str, Any]]:
    order = {sample_id: index for index, sample_id in enumerate(sample_ids)}
    rows = sorted(selected, key=lambda row: (order[row[0]], row[1]))
    records = []
    for global_index, (sample_id, question_index, category) in enumerate(rows, start=1):
        qa = samples[sample_id]["qa"][question_index]
        records.append({
            "global_index": global_index,
            "sample_id": sample_id,
            "question_index": question_index,
            "question_index_1based": question_index + 1,
            "category": category,
            "question": qa.get("question"),
            "answer": qa.get("answer"),
            "evidence": qa.get("evidence") or [],
        })
    return records


def make_manifest(
    name: str,
    records: list[dict[str, Any]],
    sample_ids: list[str],
    data_path: str,
    seed: int,
    purpose: str,
) -> dict[str, Any]:
    keys = [(row["sample_id"], row["question_index"]) for row in records]
    if len(keys) != len(set(keys)):
        raise ValueError(f"{name}: duplicate question keys")
    return {
        "name": name,
        "purpose": purpose,
        "generated_by": "repro/build_main_experiment_manifests.py",
        "data_path": data_path,
        "seed": seed,
        "sample_ids": sample_ids,
        "n_questions": len(records),
        "category_counts": dict(sorted(Counter(str(row["category"]) for row in records).items())),
        "sample_counts": dict(sorted(Counter(row["sample_id"] for row in records).items())),
        "records": records,
    }


def build_manifests(
    data: list[dict[str, Any]], sample_ids: list[str], seed: int, data_path: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    samples = {str(sample.get("sample_id")): sample for sample in data}
    missing = [sample_id for sample_id in sample_ids if sample_id not in samples]
    if missing:
        raise KeyError(f"sample ids not found: {missing}")

    ordinary_categories = (1, 2, 3, 4)
    ordinary_pools = build_pools(samples, sample_ids, ordinary_categories, seed)
    capacities = {
        category: sum(len(ordinary_pools[category][sample_id]) for sample_id in sample_ids)
        for category in ordinary_categories
    }
    ordinary_quotas = balanced_ordinary_quotas(capacities, 400)
    ordinary = select_balanced(ordinary_pools, ordinary_quotas, sample_ids)

    ordinary_sample_counts = Counter(sample_id for sample_id, _, _ in ordinary)
    adversarial_pools = build_pools(samples, sample_ids, (5,), seed + 50000)
    adversarial = select_balanced(
        adversarial_pools, {5: 100}, sample_ids, ordinary_sample_counts)
    main_records = make_records(ordinary + adversarial, samples, sample_ids)
    main_manifest = make_manifest(
        f"locomo10_500q_main_seed{seed}",
        main_records,
        sample_ids,
        data_path,
        seed,
        "Five-method main comparison: 400 ordinary questions plus 100 adversarial questions.",
    )

    main_keys = {(row["sample_id"], row["question_index"]) for row in main_records}
    ablation_pools = build_pools(samples, sample_ids, (1, 2), seed + 90000, main_keys)
    ablation = select_balanced(ablation_pools, {1: 100, 2: 100}, sample_ids)
    ablation_records = make_records(ablation, samples, sample_ids)
    ablation_manifest = make_manifest(
        f"locomo10_200q_ablation_seed{seed}",
        ablation_records,
        sample_ids,
        data_path,
        seed,
        "Strict graph-view and active-vs-passive retrieval ablation on multi-hop and temporal questions.",
    )

    if len(main_records) != 500 or len(ablation_records) != 200:
        raise AssertionError("manifest size invariant failed")
    if not {(row["sample_id"], row["question_index"]) for row in ablation_records} <= main_keys:
        raise AssertionError("ablation manifest must be a subset of the main manifest")
    return main_manifest, ablation_manifest


def write_manifest(path: str, manifest: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{output}: {manifest['n_questions']} questions, {manifest['category_counts']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data_path", default="data/dataset_locomo.json")
    parser.add_argument("--sample_ids", default=DEFAULT_SAMPLES)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--main_output", default="data/subsets/locomo10_500q_main_seed42.json")
    parser.add_argument("--ablation_output", default="data/subsets/locomo10_200q_ablation_seed42.json")
    args = parser.parse_args()

    data = json.loads(Path(args.data_path).read_text(encoding="utf-8"))
    sample_ids = [normalize_sample_id(value) for value in args.sample_ids.split(",") if value.strip()]
    main_manifest, ablation_manifest = build_manifests(data, sample_ids, args.seed, args.data_path)
    write_manifest(args.main_output, main_manifest)
    write_manifest(args.ablation_output, ablation_manifest)


if __name__ == "__main__":
    main()
