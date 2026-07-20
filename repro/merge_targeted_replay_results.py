#!/usr/bin/env python3
"""Replace repaired rows in a complete result set without mutating the original files."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def row_key(row: dict[str, Any]) -> tuple[str, int] | None:
    sample_id = row.get("sample", row.get("sample_id"))
    question_index = row.get("question_index")
    if sample_id is None or question_index is None:
        return None
    return str(sample_id), int(question_index)


def row_sha256(row: dict[str, Any]) -> str:
    payload = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_execution_error(row: dict[str, Any]) -> bool:
    prediction = str(row.get("prediction", "")).strip()
    return not prediction or prediction.upper() == "ERROR"


def index_rows(rows: list[dict[str, Any]], label: str) -> dict[tuple[str, int], dict[str, Any]]:
    indexed = {}
    for row in rows:
        key = row_key(row)
        if key is None:
            raise ValueError(f"{label} row lacks sample/question_index")
        if key in indexed:
            raise ValueError(f"duplicate {label} row: {key}")
        indexed[key] = row
    return indexed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--replay_tag", required=True)
    parser.add_argument("--output_tag", required=True)
    parser.add_argument("--source_tag", default=None)
    parser.add_argument("--result_root", default="result/locomo")
    parser.add_argument("--model", default="deepseek")
    parser.add_argument("--report_prefix", required=True)
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_tag = args.source_tag or manifest.get("source_result_tag")
    if not source_tag:
        raise ValueError("source tag is absent; pass --source_tag or use a generated replay manifest")
    if args.output_tag in {source_tag, args.replay_tag}:
        raise ValueError("output tag must be distinct from both source and replay tags")

    expected_repair_keys = {
        (str(row["sample_id"]), int(row["question_index"]))
        for row in manifest.get("records", [])
    }
    root = Path(args.result_root)
    source_paths = sorted(root.glob(f"*_result_{args.model}_{source_tag}.jsonl"))
    replay_paths = sorted(root.glob(f"*_result_{args.model}_{args.replay_tag}.jsonl"))
    if not source_paths:
        raise FileNotFoundError(f"no complete source files found for tag {source_tag!r}")
    if not replay_paths:
        raise FileNotFoundError(f"no replay files found for tag {args.replay_tag!r}")

    source_rows = [row for path in source_paths for row in load_jsonl(path)]
    replay_rows = [row for path in replay_paths for row in load_jsonl(path)]
    source_by_key = index_rows(source_rows, "source")
    replay_by_key = index_rows(replay_rows, "replay")
    if set(replay_by_key) != expected_repair_keys:
        raise ValueError(
            "replay keys do not exactly match manifest: "
            f"missing={sorted(expected_repair_keys - set(replay_by_key))[:10]} "
            f"extra={sorted(set(replay_by_key) - expected_repair_keys)[:10]}"
        )
    remaining_errors = sorted(key for key, row in replay_by_key.items() if is_execution_error(row))
    if remaining_errors:
        raise ValueError(f"replay still contains execution ERROR rows: {remaining_errors[:10]}")
    missing_source = expected_repair_keys - set(source_by_key)
    if missing_source:
        raise ValueError(f"repair keys absent from complete source results: {sorted(missing_source)[:10]}")

    existing_outputs = sorted(root.glob(f"*_result_{args.model}_{args.output_tag}.jsonl"))
    if existing_outputs:
        raise FileExistsError(
            f"output tag already exists; choose a new version instead of overwriting: {existing_outputs[0]}"
        )

    merged_at = datetime.now(timezone.utc).isoformat()
    audit_rows = []
    output_count = 0
    for source_path in source_paths:
        sample_id = source_path.name.split("_result_", 1)[0]
        output_path = root / f"{sample_id}_result_{args.model}_{args.output_tag}.jsonl"
        merged_rows = []
        for old_row in load_jsonl(source_path):
            key = row_key(old_row)
            if key in replay_by_key:
                replacement = dict(replay_by_key[key])
                replacement["_repair_provenance"] = {
                    "manifest": manifest_path.as_posix(),
                    "source_tag": source_tag,
                    "replay_tag": args.replay_tag,
                    "output_tag": args.output_tag,
                    "merged_at_utc": merged_at,
                    "source_row_sha256": row_sha256(old_row),
                    "replay_row_sha256": row_sha256(replay_by_key[key]),
                }
                merged_rows.append(replacement)
                audit_rows.append({
                    "sample_id": key[0],
                    "question_index": key[1],
                    "before_error": is_execution_error(old_row),
                    "after_error": is_execution_error(replacement),
                    "before_prediction": old_row.get("prediction"),
                    "after_prediction": replacement.get("prediction"),
                    "source_row_sha256": row_sha256(old_row),
                    "replay_row_sha256": row_sha256(replay_by_key[key]),
                })
            else:
                merged_rows.append(old_row)
        output_path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, default=list) + "\n" for row in merged_rows),
            encoding="utf-8",
        )
        output_count += len(merged_rows)

    if output_count != len(source_rows):
        raise AssertionError(f"merged row count changed: {len(source_rows)} -> {output_count}")
    if len(audit_rows) != len(expected_repair_keys):
        raise AssertionError(f"not every repair row was replaced: {len(audit_rows)}/{len(expected_repair_keys)}")

    summary = {
        "manifest": manifest_path.as_posix(),
        "source_tag": source_tag,
        "replay_tag": args.replay_tag,
        "output_tag": args.output_tag,
        "source_files": len(source_paths),
        "source_rows": len(source_rows),
        "replaced_rows": len(audit_rows),
        "output_rows": output_count,
        "before_execution_errors_in_replaced_rows": sum(row["before_error"] for row in audit_rows),
        "after_execution_errors_in_replaced_rows": sum(row["after_error"] for row in audit_rows),
        "merged_at_utc": merged_at,
    }
    report_prefix = Path(args.report_prefix)
    report_prefix.parent.mkdir(parents=True, exist_ok=True)
    report_prefix.with_suffix(".json").write_text(
        json.dumps({"summary": summary, "replacements": audit_rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# 错误行修复合并报告",
        "",
        f"- 原始完整结果：`{source_tag}`",
        f"- 定向重跑结果：`{args.replay_tag}`",
        f"- 修正版完整结果：`{args.output_tag}`",
        f"- 完整行数：{len(source_rows)} -> {output_count}",
        f"- 替换行数：{len(audit_rows)}",
        f"- 被替换行中的执行 ERROR：{summary['before_execution_errors_in_replaced_rows']} -> {summary['after_execution_errors_in_replaced_rows']}",
        "",
        "| Sample | Q | Before ERROR | After ERROR | Source SHA256 | Replay SHA256 |",
        "|---|---:|---:|---:|---|---|",
    ]
    for row in audit_rows:
        lines.append(
            f"| {row['sample_id']} | {row['question_index']} | {int(row['before_error'])} | "
            f"{int(row['after_error'])} | `{row['source_row_sha256'][:12]}` | "
            f"`{row['replay_row_sha256'][:12]}` |"
        )
    report_prefix.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["after_execution_errors_in_replaced_rows"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
