#!/usr/bin/env python3
"""Audit rewrite JSONL caches for completeness and placeholder contamination."""

import argparse
import json
from pathlib import Path


def audit_file(path: Path):
    rows = []
    errors = []
    if not path.exists():
        return {"path": str(path), "exists": False}

    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception as exc:
            errors.append({"line": line_no, "error": f"json parse error: {exc}"})
            continue
        if not isinstance(obj, dict) or len(obj) != 1:
            errors.append({"line": line_no, "error": "expected one-key object"})
            continue
        session_id, data = next(iter(obj.items()))
        entry = {"line": line_no, "session_id": session_id}
        if not isinstance(data, dict):
            entry["valid"] = False
            entry["error"] = "session value is not an object"
        else:
            sentence = data.get("sentence")
            conversation_time = str(data.get("conversation_time", ""))
            entry["conversation_time"] = conversation_time
            entry["sentence_count"] = len(sentence) if isinstance(sentence, list) else None
            entry["is_skip_marker"] = conversation_time.startswith("skipped")
            entry["valid"] = (
                isinstance(sentence, list)
                and len(sentence) > 0
                and not entry["is_skip_marker"]
            )
            if entry["is_skip_marker"]:
                entry["error"] = "skip marker"
            elif not isinstance(sentence, list):
                entry["error"] = "sentence is not a list"
            elif len(sentence) == 0:
                entry["error"] = "empty sentence list"
        rows.append(entry)

    valid_rows = [row for row in rows if row.get("valid")]
    invalid_rows = [row for row in rows if not row.get("valid")]
    return {
        "path": str(path),
        "exists": True,
        "line_count": len(rows),
        "valid_prefix_count": _valid_prefix_count(rows),
        "valid_count": len(valid_rows),
        "invalid_count": len(invalid_rows),
        "sessions": [row.get("session_id") for row in rows],
        "invalid_rows": invalid_rows,
        "parse_errors": errors,
    }


def _valid_prefix_count(rows):
    count = 0
    for row in rows:
        if not row.get("valid"):
            break
        count += 1
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    reports = [audit_file(Path(p)) for p in args.paths]
    if args.json:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
        return

    for report in reports:
        print(f"# {report['path']}")
        if not report.get("exists"):
            print("missing")
            continue
        print(f"lines: {report['line_count']}")
        print(f"valid_prefix_count: {report['valid_prefix_count']}")
        print(f"valid_count: {report['valid_count']}")
        print(f"invalid_count: {report['invalid_count']}")
        print(f"sessions: {', '.join(report['sessions'])}")
        if report["invalid_rows"]:
            print("invalid_rows:")
            for row in report["invalid_rows"]:
                print(f"  line {row.get('line')}: {row.get('session_id')} - {row.get('error')}")
        if report["parse_errors"]:
            print("parse_errors:")
            for row in report["parse_errors"]:
                print(f"  line {row.get('line')}: {row.get('error')}")


if __name__ == "__main__":
    main()
