#!/usr/bin/env python3
"""Build resumable raw-turn embedding caches for the native LoCoMo RAG baseline."""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.embeddings import EMBED_MODEL, get_openai_embedding
from repro.baseline_utils import raw_turns


def load_dataset(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(sample["sample_id"]): sample for sample in data}


def load_partial(path: Path, units: list[dict[str, str]]) -> list[list[float]]:
    if not path.exists():
        return []
    with path.open("rb") as f:
        cached = pickle.load(f)
    if cached.get("units") != units:
        raise ValueError(f"partial cache does not match current dataset: {path}")
    embeddings = cached.get("embeddings") or []
    if len(embeddings) > len(units):
        raise ValueError(f"partial cache has too many embeddings: {path}")
    return embeddings


def write_cache(path: Path, units: list[dict[str, str]], embeddings: list[list[float]]) -> None:
    with path.open("wb") as f:
        pickle.dump(
            {
                "format": "locomo_native_raw_turn_v1",
                "embedding_model": EMBED_MODEL,
                "units": units,
                "embeddings": embeddings,
            },
            f,
        )


def build_one(sample_id: str, sample: dict[str, Any], output_dir: Path, batch_size: int) -> None:
    units = raw_turns(sample["conversation"])
    output = output_dir / f"{sample_id}_raw_turn.pkl"
    temporary = output.with_suffix(output.suffix + ".tmp")
    if output.exists():
        with output.open("rb") as f:
            existing = pickle.load(f)
        if existing.get("units") == units and len(existing.get("embeddings") or []) == len(units):
            print(f"{sample_id}: cache complete ({len(units)} turns), skip")
            return
        raise ValueError(f"invalid completed cache: {output}")

    embeddings = load_partial(temporary, units)
    for start in range(len(embeddings), len(units), batch_size):
        batch = units[start : start + batch_size]
        vectors = get_openai_embedding([row["text"] for row in batch], batch_size=batch_size)
        embeddings.extend(vectors)
        write_cache(temporary, units, embeddings)
        print(f"{sample_id}: embedded {len(embeddings)}/{len(units)} raw turns")
    os.replace(temporary, output)
    print(f"{sample_id}: wrote {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build raw-turn RAG embedding caches.")
    parser.add_argument("--data_path", default="data/dataset_locomo.json")
    parser.add_argument("--sample_ids", required=True, help="Comma-separated ids, e.g. 26,30 or conv-26,conv-30")
    parser.add_argument("--output_dir", default="data/locomo/rag_native")
    parser.add_argument("--batch_size", type=int, default=64)
    args = parser.parse_args()

    samples = load_dataset(Path(args.data_path))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for value in args.sample_ids.split(","):
        sample_id = value.strip()
        if not sample_id:
            continue
        if not sample_id.startswith("conv-"):
            sample_id = f"conv-{sample_id}"
        if sample_id not in samples:
            raise KeyError(f"sample_id not found: {sample_id}")
        build_one(sample_id, samples[sample_id], output_dir, args.batch_size)


if __name__ == "__main__":
    main()
