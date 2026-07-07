#!/usr/bin/env python3
"""Static diagnostics for one LoCoMo rewrite session.

This script does not call any model API. It inspects the source conversation,
the rewrite prompt size, and partial rewrite cache progress so an interrupted
batch can be diagnosed without spending more tokens.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from prompts.prompts import Prompts


def build_locomo_sessions(sample):
    conversation = sample.get("conversation") or {}
    session_keys = []
    for key, value in conversation.items():
        if key.startswith("session_") and isinstance(value, list):
            try:
                session_keys.append((int(key.split("_", 1)[1]), key))
            except ValueError:
                continue
    session_keys.sort()

    sessions = {}
    stats = []
    for idx, key in session_keys:
        turns = conversation.get(key) or []
        session_id = f"D{idx}"
        lines = [f"time:{conversation.get(f'{key}_date_time', '')}".strip()]
        caption_count = 0
        image_url_count = 0
        raw_text_chars = 0
        speakers = {}

        for turn in turns:
            if not isinstance(turn, dict):
                continue
            speaker = (turn.get("speaker") or "UNKNOWN").strip()
            dia_id = (turn.get("dia_id") or f"{key}:{len(lines)}").strip()
            text = (turn.get("text") or "").strip()
            if not text:
                continue
            speakers[speaker] = speakers.get(speaker, 0) + 1
            raw_text_chars += len(text)
            if turn.get("blip_caption") is not None:
                caption_count += 1
                line = f"dia_id:{dia_id} {speaker}:{text} and shared {turn.get('blip_caption')}"
            else:
                line = f"dia_id:{dia_id} {speaker}:{text}"
            if turn.get("img_url") or turn.get("image") or turn.get("image_url"):
                image_url_count += 1
            lines.append(line)

        text = "\n".join(lines)
        prompt = Prompts.extract_rewrite_prompt(json.dumps(text, ensure_ascii=False))
        sessions[session_id] = text
        stats.append(
            {
                "session": session_id,
                "source_key": key,
                "turns": len(turns),
                "nonempty_lines": len(lines),
                "session_chars": len(text),
                "prompt_chars": len(prompt) + len(Prompts.REWRITE_SYSTEM_PROMPT),
                "approx_prompt_tokens": round((len(prompt) + len(Prompts.REWRITE_SYSTEM_PROMPT)) / 3.5),
                "raw_text_chars": raw_text_chars,
                "caption_count": caption_count,
                "image_url_count": image_url_count,
                "speakers": speakers,
                "date": conversation.get(f"{key}_date_time"),
            }
        )
    return sessions, stats


def read_partial_progress(path):
    if not path or not Path(path).exists():
        return {"path": path, "exists": False, "valid_prefix_lines": 0, "sessions": []}
    sessions = []
    valid = 0
    error = None
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            break
        try:
            obj = json.loads(line)
            if not isinstance(obj, dict) or len(obj) != 1:
                error = f"line {line_no}: not a single-key object"
                break
            sid, value = next(iter(obj.items()))
            if not isinstance(value, dict) or not isinstance(value.get("sentence"), list):
                error = f"line {line_no}: invalid rewrite schema"
                break
            sessions.append(sid)
            valid += 1
        except Exception as exc:
            error = f"line {line_no}: {exc}"
            break
    return {
        "path": path,
        "exists": True,
        "valid_prefix_lines": valid,
        "sessions": sessions,
        "error": error,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_path", default="data/dataset_locomo.json")
    parser.add_argument("--sample_id", required=True)
    parser.add_argument("--session", required=True, help="D9 or 9")
    parser.add_argument("--partial_rewrite", default=None)
    parser.add_argument("--dump_prompt", default=None)
    parser.add_argument("--preview_chars", type=int, default=2500)
    args = parser.parse_args()

    target_session = args.session if args.session.startswith("D") else f"D{args.session}"
    data = json.loads(Path(args.dataset_path).read_text(encoding="utf-8"))
    sample = next((item for item in data if item.get("sample_id") == args.sample_id), None)
    if sample is None:
        raise SystemExit(f"sample not found: {args.sample_id}")

    sessions, stats = build_locomo_sessions(sample)
    if target_session not in sessions:
        raise SystemExit(f"session not found: {target_session}")

    target_stats = next(item for item in stats if item["session"] == target_session)
    largest = sorted(stats, key=lambda item: item["session_chars"], reverse=True)[:8]
    session_text = sessions[target_session]
    prompt = Prompts.extract_rewrite_prompt(json.dumps(session_text, ensure_ascii=False))

    report = {
        "sample_id": args.sample_id,
        "target_session": target_session,
        "session_count": len(stats),
        "target_stats": target_stats,
        "largest_sessions_by_chars": largest,
        "partial_rewrite_progress": read_partial_progress(args.partial_rewrite),
        "target_preview": session_text[: args.preview_chars],
        "diagnosis_hint": (
            "If target_stats is not unusually large, repeated 600s timeout is more likely "
            "provider/model behavior, safety review, or structured-output latency than raw input length."
        ),
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.dump_prompt:
        out = Path(args.dump_prompt)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            Prompts.REWRITE_SYSTEM_PROMPT + "\n\n" + prompt,
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
