#!/usr/bin/env python3
"""Summarize actual API models used by stage from api_call_log.jsonl."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", default="result/diagnostics/api_call_log.jsonl")
    parser.add_argument("--last", type=int, default=200)
    args = parser.parse_args()

    path = Path(args.log)
    if not path.exists():
        raise SystemExit(f"log not found: {path}")

    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if args.last:
        rows = rows[-args.last :]

    by_stage = defaultdict(Counter)
    errors = []
    for row in rows:
        stage = row.get("stage") or "unknown"
        model = row.get("model") or "unknown"
        by_stage[stage][model] += 1
        if row.get("error"):
            errors.append(row)

    print("# API model audit")
    print()
    print(f"log: `{path}`")
    print(f"records inspected: {len(rows)}")
    print()
    print("## Models by stage")
    print()
    for stage in sorted(by_stage):
        print(f"- {stage}")
        for model, count in by_stage[stage].most_common():
            print(f"  - {model}: {count}")
    print()
    print("## Recent errors")
    print()
    for row in errors[-20:]:
        print(
            "- "
            + json.dumps(
                {
                    "ts": row.get("ts"),
                    "stage": row.get("stage"),
                    "model": row.get("model"),
                    "attempt": row.get("attempt"),
                    "latency_s": row.get("latency_s"),
                    "error": row.get("error"),
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
