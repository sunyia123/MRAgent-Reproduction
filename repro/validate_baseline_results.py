#!/usr/bin/env python3
"""Validate that an external baseline result is comparable to a fixed manifest."""

from __future__ import annotations

import argparse
import glob
import json
from collections import Counter
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate external baseline outputs against a fixed manifest.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--result_glob", required=True, help="Quoted glob, e.g. 'result/external/amem/*.jsonl'")
    parser.add_argument("--method", required=True)
    parser.add_argument("--provenance", required=True, help="Markdown/JSON file recording repo URL, commit, model and settings")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    expected = {(r["sample_id"], int(r["question_index"])): r for r in manifest.get("records", [])}
    paths = [Path(value) for value in sorted(glob.glob(args.result_glob))]
    rows = [row for path in paths for row in load_jsonl(path)]
    seen: Counter[tuple[str, int]] = Counter()
    invalid_rows = []
    for row in rows:
        if row.get("sample") is None or row.get("question_index") is None:
            invalid_rows.append("missing sample or question_index")
            continue
        key = (str(row["sample"]), int(row["question_index"]))
        seen[key] += 1
        if key not in expected:
            invalid_rows.append(f"not in manifest: {key[0]}:{key[1] + 1}")
        if "prediction" not in row:
            invalid_rows.append(f"missing prediction: {key[0]}:{key[1] + 1}")

    missing = sorted(set(expected) - set(seen))
    duplicate = sorted(key for key, count in seen.items() if count > 1)
    provenance = Path(args.provenance)
    valid = bool(paths) and provenance.exists() and not missing and not duplicate and not invalid_rows
    lines = [
        "# External Baseline Comparability Check",
        "",
        f"- method: `{args.method}`",
        f"- manifest: `{args.manifest}` ({len(expected)} questions)",
        f"- result files: {len(paths)}",
        f"- provenance: `{args.provenance}` ({'present' if provenance.exists() else 'MISSING'})",
        f"- status: {'PASS' if valid else 'FAIL'}",
        "",
        "## Coverage",
        "",
        f"- rows: {len(rows)}",
        f"- unique manifest keys: {len(seen)} / {len(expected)}",
        f"- missing: {len(missing)}",
        f"- duplicates: {len(duplicate)}",
        f"- invalid rows: {len(invalid_rows)}",
    ]
    if missing:
        lines.append("- first missing: " + ", ".join(f"{s}:{i + 1}" for s, i in missing[:20]))
    if duplicate:
        lines.append("- duplicates: " + ", ".join(f"{s}:{i + 1}" for s, i in duplicate[:20]))
    if invalid_rows:
        lines.append("- invalid examples: " + "; ".join(invalid_rows[:20]))
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.output)
    if not valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
