#!/usr/bin/env python3
"""Write a reproducible directory manifest for server-side experiment handoff.

Default target:
  /data/nishome/cuiwenjia/MRAgent-Reproduction

The manifest is intended to be committed before pushing server experiment
reports, so local/remote reviewers can see which cache, graph, result, report,
and log files exist on the server.

Includes per-sample cache summary: rewrite sessions, keyword, embedding,
result rows, graph snapshots, and run logs.
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


# ---------------------------------------------------------------------------
# Per-sample cache summary
# ---------------------------------------------------------------------------

def _count_jsonl_lines(root: Path, rel_path: str) -> int | None:
    """Return number of non-empty lines in a JSONL file, or None if missing."""
    p = root / rel_path
    if not p.is_file():
        return None
    try:
        return sum(1 for line in p.read_text(encoding="utf-8").splitlines() if line.strip())
    except Exception:
        return None


def _parse_rewrite_tmp_detail(root: Path, rel_path: str) -> dict | None:
    """Parse a rewrite .tmp file and return detail dict, or None if missing."""
    p = root / rel_path
    if not p.is_file():
        return None
    try:
        valid = 0
        skip = 0
        other_invalid = 0
        session_ids = []
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                other_invalid += 1
                continue
            if not isinstance(obj, dict) or len(obj) != 1:
                other_invalid += 1
                continue
            sid, data = next(iter(obj.items()))
            session_ids.append(sid)
            ct = str(data.get("conversation_time", ""))
            if ct.startswith("skipped"):
                skip += 1
            elif isinstance(data.get("sentence"), list) and len(data.get("sentence")) > 0:
                valid += 1
            else:
                other_invalid += 1
        return {
            "total_lines": valid + skip + other_invalid,
            "valid_sessions": valid,
            "skip_markers": skip,
            "other_invalid": other_invalid,
            "session_ids": session_ids,
        }
    except Exception:
        return None


def _count_result_rows(root: Path, rel_path: str) -> int | None:
    """Return number of non-empty JSONL result rows, or None if missing."""
    return _count_jsonl_lines(root, rel_path)


def _cache_summary_for_sample(root: Path, sample_id: str) -> dict:
    """Build a cache-status summary dict for one sample."""
    summary: dict = {
        "sample_id": sample_id,
        "rewrite": {},
        "keyword": {},
        "embedding": {},
        "result": {},
        "graph_snapshot": {},
        "logs": {},
    }

    # --- rewrite ---
    # Look for rewrite_<model>/<sample>_rewrite.json and .tmp
    rewrite_dir = root / "data" / "locomo"
    if rewrite_dir.exists():
        for sub in sorted(rewrite_dir.iterdir()):
            if not sub.is_dir() or not sub.name.startswith("rewrite"):
                continue
            model_tag = sub.name.replace("rewrite", "").lstrip("_")
            main_file = sub / f"{sample_id}_rewrite.json"
            tmp_file = sub / f"{sample_id}_rewrite.json.tmp"
            main_info = None
            tmp_info = None
            if main_file.is_file():
                n = _count_jsonl_lines(root, str(main_file.relative_to(root)))
                main_info = {"lines": n, "has_tmp": False}
            if tmp_file.is_file():
                detail = _parse_rewrite_tmp_detail(root, str(tmp_file.relative_to(root)))
                tmp_info = detail
            if main_info or tmp_info:
                summary["rewrite"][model_tag] = {
                    "main": main_info,
                    "tmp": tmp_info,
                }

    # --- keyword ---
    kw_dir = root / "data" / "locomo"
    if kw_dir.exists():
        for sub in sorted(kw_dir.iterdir()):
            if not sub.is_dir() or not sub.name.startswith("keyword"):
                continue
            model_tag = sub.name.replace("keyword", "").lstrip("_")
            kw_file = sub / f"{sample_id}_keyword.json"
            if kw_file.is_file():
                n = _count_jsonl_lines(root, str(kw_file.relative_to(root)))
                summary["keyword"][model_tag] = {"lines": n}

    # --- embedding ---
    emb_dir = root / "data" / "locomo" / "embedding"
    if emb_dir.exists():
        for sub in sorted(emb_dir.iterdir()):
            if not sub.is_dir():
                continue
            emb_file = sub / f"{sample_id}_embedding.pkl"
            if emb_file.is_file():
                size_kb = emb_file.stat().st_size / 1024
                summary["embedding"][sub.name] = {"size_kb": round(size_kb, 1)}

    # --- result ---
    result_dir = root / "result" / "locomo"
    if result_dir.exists():
        for f in sorted(result_dir.iterdir()):
            if not f.is_file():
                continue
            if sample_id in f.name and f.suffix == ".jsonl":
                n = _count_result_rows(root, str(f.relative_to(root)))
                summary["result"][f.name] = {"rows": n}
            elif sample_id in f.name:
                summary["result"][f.name] = {"size_bytes": f.stat().st_size}

    # --- graph snapshot ---
    gs_dir = root / "result" / "graph_snapshot"
    if gs_dir.exists():
        for f in sorted(gs_dir.iterdir()):
            if sample_id in f.name and f.is_file():
                summary["graph_snapshot"][f.name] = {"size_bytes": f.stat().st_size}

    # --- run logs ---
    log_dir = root / "log" / "locomo" / "runs"
    if log_dir.exists():
        for f in sorted(log_dir.iterdir()):
            if sample_id in f.name and f.is_file():
                summary["logs"][f.name] = {"size_bytes": f.stat().st_size}

    return summary


def _bool_icon(flag: bool) -> str:
    return "✅" if flag else "❌"


def _cache_summary_markdown(root: Path) -> str:
    """Produce a per-sample cache summary markdown table."""
    conv_path = root / "data" / "conversation_list_locomo.json"
    if not conv_path.is_file():
        return "\n## Cache Summary\n\n*(conversation list not found)*\n"

    try:
        convs = json.loads(conv_path.read_text(encoding="utf-8"))
    except Exception:
        return "\n## Cache Summary\n\n*(failed to parse conversation list)*\n"

    sample_ids = sorted(convs.keys(), key=lambda x: int(x.split("-")[1]))

    lines = [
        "",
        "## Per-Sample Cache Summary",
        "",
        "| sample | sessions | rewrite | keyword | embedding | results | graph | logs |",
        "|---|---|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    for sid in sample_ids:
        n_sessions = len(convs[sid])
        cs = _cache_summary_for_sample(root, sid)

        # rewrite status
        rewrite_parts = []
        for model, info in sorted(cs["rewrite"].items()):
            if info["main"]:
                rewrite_parts.append(f"{model}: {info['main']['lines']}/{n_sessions}")
            if info["tmp"]:
                d = info["tmp"]
                parts = []
                if d["valid_sessions"]:
                    parts.append(f"valid={d['valid_sessions']}")
                if d["skip_markers"]:
                    parts.append(f"skip={d['skip_markers']}")
                if d["other_invalid"]:
                    parts.append(f"bad={d['other_invalid']}")
                rewrite_parts.append(f"{model}.tmp({', '.join(parts)})")
        rewrite_str = "<br>".join(rewrite_parts) if rewrite_parts else "❌"

        # keyword status
        kw_parts = []
        for model, info in sorted(cs["keyword"].items()):
            kw_parts.append(f"{model}: {info['lines']} lines")
        kw_str = "<br>".join(kw_parts) if kw_parts else "❌"

        # embedding status
        emb_parts = []
        for name, info in sorted(cs["embedding"].items()):
            emb_parts.append(f"{name}: {info['size_kb']:.0f} KB")
        emb_str = "<br>".join(emb_parts) if emb_parts else "❌"

        # result status
        res_parts = []
        for name, info in sorted(cs["result"].items()):
            if "rows" in info:
                res_parts.append(f"{info['rows']} rows")
            else:
                res_parts.append(f"{info.get('size_bytes', 0)} B")
        # deduplicate: show count of result files
        if res_parts:
            res_str = f"{len(cs['result'])} files"
        else:
            res_str = "❌"

        # graph status
        gs_count = len(cs["graph_snapshot"])
        gs_str = f"{gs_count} files" if gs_count else "❌"

        # log status
        log_count = len(cs["logs"])
        log_str = f"{log_count} files" if log_count else "❌"

        lines.append(
            f"| {sid} | {n_sessions} | {rewrite_str} | {kw_str} | {emb_str} | {res_str} | {gs_str} | {log_str} |"
        )

    # Summary of which samples have any cache
    lines.append("")
    lines.append("### Cache Completeness")
    lines.append("")
    lines.append("| sample | rewrite ready | keyword ready | embedding ready | overall |")
    lines.append("|---|---:|---:|---:|---:|")

    for sid in sample_ids:
        cs = _cache_summary_for_sample(root, sid)
        has_rewrite = any(
            info.get("main") and info["main"]["lines"] and info["main"]["lines"] > 0
            for info in cs["rewrite"].values()
        )
        has_keyword = len(cs["keyword"]) > 0
        has_embedding = len(cs["embedding"]) > 0
        overall = "✅" if (has_rewrite and has_keyword and has_embedding) else "❌"
        lines.append(
            f"| {sid} | {_bool_icon(has_rewrite)} | {_bool_icon(has_keyword)} | {_bool_icon(has_embedding)} | {overall} |"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report writers
# ---------------------------------------------------------------------------

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

    # Per-sample cache summary
    lines.append(_cache_summary_markdown(root))

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
