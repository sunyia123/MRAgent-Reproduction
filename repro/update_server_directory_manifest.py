#!/usr/bin/env python3
"""Write a reproducible directory manifest for server-side experiment handoff.

Default target:
  /data/nishome/cuiwenjia/MRAgent-Reproduction

The manifest is intended to be committed before pushing server experiment
reports, so local/remote reviewers can see which cache, graph, result, report,
and log files exist on the server.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable


DEFAULT_ROOT = Path("/data/nishome/cuiwenjia/MRAgent-Reproduction")
DEFAULT_REPORT = Path("reports/server_directory_manifest.md")
DEFAULT_JSONL = Path("reports/server_directory_manifest.jsonl")
DEFAULT_SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate server directory manifest.")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="Repository root to scan.")
    parser.add_argument("--output", default=str(DEFAULT_REPORT), help="Markdown manifest path.")
    parser.add_argument("--jsonl", default=str(DEFAULT_JSONL), help="Machine-readable JSONL manifest path.")
    parser.add_argument("--include_venv", action="store_true", help="Include .venv files. Usually too large for committed manifests.")
    parser.add_argument("--max_md_rows", type=int, default=20000, help="Maximum file rows to print in Markdown.")
    return parser.parse_args()


def iter_files(root: Path, skip_dirs: set[str]) -> Iterable[Path]:
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in skip_dirs)
        for name in sorted(files):
            yield Path(current) / name


def file_record(root: Path, path: Path) -> dict:
    st = path.stat()
    rel = path.relative_to(root).as_posix()
    return {
        "path": rel,
        "size_bytes": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
        "suffix": path.suffix,
    }


def summarize(records: list[dict]) -> dict:
    by_top = {}
    by_suffix = {}
    for rec in records:
        top = rec["path"].split("/", 1)[0]
        by_top[top] = by_top.get(top, 0) + 1
        suffix = rec["suffix"] or "[no suffix]"
        by_suffix[suffix] = by_suffix.get(suffix, 0) + 1
    return {
        "file_count": len(records),
        "by_top_dir": dict(sorted(by_top.items())),
        "by_suffix": dict(sorted(by_suffix.items(), key=lambda item: (-item[1], item[0]))[:30]),
    }


def write_markdown(root: Path, output: Path, records: list[dict], summary: dict, skipped: set[str], max_rows: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().isoformat(timespec="seconds")
    lines = [
        "# Server Directory Manifest",
        "",
        f"Generated: `{now}`",
        f"Root: `{root}`",
        "",
        "## Scan Policy",
        "",
        f"- Skipped directories: `{', '.join(sorted(skipped))}`",
        "- Use `repro/update_server_directory_manifest.py --include_venv` only for local debugging; do not commit huge virtualenv manifests.",
        "",
        "## Summary",
        "",
        f"- Files listed: `{summary['file_count']}`",
        "",
        "### Top-Level Counts",
        "",
        "| top-level path | files |",
        "|---|---:|",
    ]
    for name, count in summary["by_top_dir"].items():
        lines.append(f"| `{name}` | {count} |")
    lines.extend(["", "### Suffix Counts", "", "| suffix | files |", "|---|---:|"])
    for suffix, count in summary["by_suffix"].items():
        lines.append(f"| `{suffix}` | {count} |")

    lines.extend([
        "",
        "## Files",
        "",
        "| path | size bytes | modified |",
        "|---|---:|---|",
    ])
    shown = records[:max_rows]
    for rec in shown:
        lines.append(f"| `{rec['path']}` | {rec['size_bytes']} | `{rec['mtime']}` |")
    if len(records) > max_rows:
        lines.extend([
            "",
            f"Only first `{max_rows}` rows shown in Markdown. See JSONL for all `{len(records)}` rows.",
        ])
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    if not root.exists():
        raise SystemExit(f"Root does not exist: {root}")
    skip_dirs = set(DEFAULT_SKIP_DIRS)
    if args.include_venv:
        skip_dirs.discard(".venv")
    records = [file_record(root, path) for path in iter_files(root, skip_dirs)]
    records.sort(key=lambda rec: rec["path"])
    summary = summarize(records)
    write_markdown(root, Path(args.output), records, summary, skip_dirs, args.max_md_rows)
    write_jsonl(Path(args.jsonl), records)
    print(json.dumps({
        "root": str(root),
        "output": args.output,
        "jsonl": args.jsonl,
        "file_count": len(records),
        "skipped_dirs": sorted(skip_dirs),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
