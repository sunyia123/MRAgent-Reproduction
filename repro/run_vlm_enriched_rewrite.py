#!/usr/bin/env python3
"""
Run VLM-enriched rewrite without touching the original MRAgent rewrite cache.

Pipeline:
1. Load LoCoMo conversation sample(s).
2. For image turns, call an OpenAI-compatible VLM to produce visual evidence.
3. Inject the visual evidence into the per-session text sent to MRAgent rewrite.
4. Write rewrite JSONL to a separate directory, e.g.
   data/locomo/rewrite_deepseek_vlm/conv-30_rewrite.json

This script is intentionally separate from run.py so VLM rewrite experiments do
not pollute the baseline rewrite/keyword/embedding caches.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run VLM-enriched rewrite for LoCoMo samples.")
    parser.add_argument("--data", default="locomo", help="Dataset name. Currently only locomo is supported.")
    parser.add_argument("--model", default="deepseek", help="Text rewrite model short name parsed by common.config.")
    parser.add_argument("--sample", default=None, help="Single sample number or id, e.g. 30 or conv-30.")
    parser.add_argument("--sample_ids", default=None, help="Comma-separated sample ids, e.g. 30,42 or conv-30,conv-42.")
    parser.add_argument("--file", default="vlmrewrite", help="Run tag used in reports and diagnostics.")
    parser.add_argument("--vlm_model", default=os.getenv("VLM_MODEL", "Qwen/Qwen3.5-397B-A17B"))
    parser.add_argument("--vlm_max_tokens", type=int, default=int(os.getenv("VLM_MAX_TOKENS", "1024")))
    parser.add_argument("--vlm_temperature", type=float, default=0.0)
    parser.add_argument("--limit_image_turns", type=int, default=None, help="Limit VLM calls per sample for smoke tests.")
    parser.add_argument("--max_sessions", type=int, default=None, help="Rewrite only the first N sessions per sample.")
    parser.add_argument("--output_suffix", default="vlm", help="Rewrite dir suffix: rewrite_<model>_<suffix>.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing VLM rewrite output.")
    parser.add_argument("--dry_run", action="store_true", help="Build enriched sessions and reports without API calls.")
    parser.add_argument("--skip_vlm", action="store_true", help="Do not call VLM; inject captions only and record skipped status.")
    parser.add_argument("--rewrite", action="store_true", help="Actually call the text rewrite LLM after enrichment.")
    parser.add_argument(
        "--visual_question",
        default=(
            "Describe the image facts that are useful for long-dialogue memory. "
            "Focus on people, actions, objects, scene, text in image, and event type."
        ),
    )
    return parser.parse_args()


def normalize_sample_id(value: str) -> str:
    value = str(value).strip()
    if value.startswith("conv-"):
        return value
    return f"conv-{value}"


def requested_sample_ids(args: argparse.Namespace) -> Optional[set]:
    ids: List[str] = []
    if args.sample:
        ids.append(normalize_sample_id(args.sample))
    if args.sample_ids:
        ids.extend(normalize_sample_id(item) for item in args.sample_ids.split(",") if item.strip())
    return set(ids) if ids else None


def load_dataset(dataset: str) -> List[Dict[str, Any]]:
    path = Path("data") / f"dataset_{dataset}.json"
    if not path.exists():
        raise FileNotFoundError(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected list dataset at {path}, got {type(data)}")
    return data


def session_keys(conversation: Dict[str, Any]) -> List[str]:
    keys = [
        key for key, value in conversation.items()
        if re.fullmatch(r"session_\d+", key) and isinstance(value, list)
    ]
    return sorted(keys, key=lambda key: int(key.split("_")[1]))


def first_image_url(turn: Dict[str, Any]) -> Optional[str]:
    urls = turn.get("img_url") or []
    if isinstance(urls, str):
        urls = [urls]
    if not urls:
        return None
    return urls[0]


def cache_key(sample_id: str, dia_id: str, image_url: str) -> str:
    raw = f"{sample_id}\n{dia_id}\n{image_url}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def build_vlm_prompt(turn: Dict[str, Any], sample_id: str, session: str, session_time: str, question: str) -> str:
    return (
        f"{question}\n\n"
        "Return concise JSON with keys: visual_answer, visible_entities, scene, confidence, failure_reason.\n"
        "Use the image as primary evidence. Use dialogue text and caption only as context.\n\n"
        f"sample_id: {sample_id}\n"
        f"session: {session}\n"
        f"session_time: {session_time}\n"
        f"event_id: {turn.get('dia_id')}\n"
        f"speaker: {turn.get('speaker')}\n"
        f"dialogue_text: {turn.get('text')}\n"
        f"blip_caption: {turn.get('blip_caption')}\n"
    )


def response_to_dict(resp: Any) -> Dict[str, Any]:
    if hasattr(resp, "model_dump"):
        return resp.model_dump()
    if hasattr(resp, "dict"):
        return resp.dict()
    return {"repr": repr(resp)}


def compact_visual_text(response: Dict[str, Any]) -> str:
    content = ((response.get("response") or {}).get("content") or "").strip()
    if not content:
        return ""
    try:
        obj = json.loads(content)
        parts = []
        for key in ("visual_answer", "scene", "visible_entities", "confidence"):
            value = obj.get(key)
            if value:
                parts.append(f"{key}: {value}")
        return "; ".join(parts) if parts else content
    except Exception:
        return content


def call_vlm(
    client: OpenAI,
    model: str,
    prompt: str,
    image_url: str,
    max_tokens: int,
    temperature: float,
) -> Dict[str, Any]:
    request = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    started = time.time()
    resp = client.chat.completions.create(**request)
    raw = response_to_dict(resp)
    choice = raw.get("choices", [{}])[0] if raw.get("choices") else {}
    message = choice.get("message") or {}
    return {
        "request": {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "image_url": image_url,
            "prompt_length": len(prompt),
        },
        "response": {
            "content": message.get("content"),
            "reasoning_content": message.get("reasoning_content"),
            "finish_reason": choice.get("finish_reason"),
            "usage": raw.get("usage"),
            "latency_s": round(time.time() - started, 2),
        },
        "raw_response": raw,
    }


def collect_visual_evidence(
    sample: Dict[str, Any],
    args: argparse.Namespace,
    client: Optional[OpenAI],
    jsonl_path: Path,
) -> Dict[str, Dict[str, Any]]:
    sample_id = sample.get("sample_id")
    conversation = sample.get("conversation") or {}
    evidence_by_dia: Dict[str, Dict[str, Any]] = {}
    calls_used = 0

    with jsonl_path.open("a", encoding="utf-8") as out:
        for session in session_keys(conversation):
            session_time = conversation.get(f"{session}_date_time")
            for turn in conversation.get(session, []):
                if not isinstance(turn, dict):
                    continue
                image_url = first_image_url(turn)
                dia_id = turn.get("dia_id")
                if not image_url or not dia_id:
                    continue
                if args.limit_image_turns is not None and calls_used >= args.limit_image_turns:
                    continue

                prompt = build_vlm_prompt(turn, sample_id, session, session_time, args.visual_question)
                record: Dict[str, Any] = {
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "sample_id": sample_id,
                    "session": session,
                    "session_time": session_time,
                    "dia_id": dia_id,
                    "speaker": turn.get("speaker"),
                    "text": turn.get("text"),
                    "blip_caption": turn.get("blip_caption"),
                    "image_url": image_url,
                    "cache_key": cache_key(sample_id, dia_id, image_url),
                    "status": "pending",
                }
                try:
                    if args.dry_run:
                        record["status"] = "dry_run"
                        record["vlm"] = {
                            "request": {
                                "model": args.vlm_model,
                                "max_tokens": args.vlm_max_tokens,
                                "temperature": args.vlm_temperature,
                                "image_url": image_url,
                                "prompt_length": len(prompt),
                            }
                        }
                    elif args.skip_vlm:
                        record["status"] = "skipped"
                        record["error"] = "skip_vlm enabled"
                    else:
                        assert client is not None
                        record["vlm"] = call_vlm(
                            client=client,
                            model=args.vlm_model,
                            prompt=prompt,
                            image_url=image_url,
                            max_tokens=args.vlm_max_tokens,
                            temperature=args.vlm_temperature,
                        )
                        visual_text = compact_visual_text(record["vlm"])
                        record["visual_text"] = visual_text
                        record["status"] = "ok" if visual_text else "empty_response"
                except Exception as exc:
                    record["status"] = "error"
                    record["error"] = repr(exc)

                out.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
                evidence_by_dia[dia_id] = record
                calls_used += 1

    return evidence_by_dia


def build_enriched_sessions(
    sample: Dict[str, Any],
    visual_evidence: Dict[str, Dict[str, Any]],
    max_sessions: Optional[int],
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    conversation = sample.get("conversation") or {}
    sessions: Dict[str, str] = {}
    stats = {
        "sessions": 0,
        "turns": 0,
        "image_turns": 0,
        "vlm_ok_injected": 0,
        "caption_only_image_turns": 0,
    }

    for session in session_keys(conversation):
        if max_sessions is not None and stats["sessions"] >= max_sessions:
            break
        idx = int(session.split("_")[1])
        session_id = f"D{idx}"
        session_time = conversation.get(f"{session}_date_time")
        lines = [f"time:{session_time}".strip()]
        for turn in conversation.get(session, []):
            if not isinstance(turn, dict):
                continue
            speaker = (turn.get("speaker") or "UNKNOWN").strip()
            dia_id = (turn.get("dia_id") or f"{session}:{len(lines)}").strip()
            text = (turn.get("text") or "").strip()
            if not text:
                continue
            stats["turns"] += 1
            line = f"dia_id:{dia_id} {speaker}:{text}"
            caption = turn.get("blip_caption")
            if caption is not None:
                line += f" and shared {caption}"
            if first_image_url(turn):
                stats["image_turns"] += 1
                record = visual_evidence.get(dia_id) or {}
                visual_text = (record.get("visual_text") or "").strip()
                if visual_text:
                    line += f" Visual evidence from the image: {visual_text}"
                    stats["vlm_ok_injected"] += 1
                else:
                    stats["caption_only_image_turns"] += 1
            lines.append(line)
        sessions[session_id] = "\n".join(lines)
        stats["sessions"] += 1
    return sessions, stats


def write_report(report_path: Path, args: argparse.Namespace, sample_reports: List[Dict[str, Any]]) -> None:
    lines = [
        f"# VLM-Enriched Rewrite Report - {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "## Purpose",
        "",
        "Inject VLM visual evidence into the rewrite input without overwriting baseline rewrite caches.",
        "",
        "## Configuration",
        "",
        f"- dataset: `{args.data}`",
        f"- text model short name: `{args.model}`",
        f"- VLM model: `{args.vlm_model}`",
        f"- output suffix: `{args.output_suffix}`",
        f"- dry_run: `{args.dry_run}`",
        f"- skip_vlm: `{args.skip_vlm}`",
        f"- rewrite: `{args.rewrite}`",
        f"- limit_image_turns: `{args.limit_image_turns}`",
        f"- max_sessions: `{args.max_sessions}`",
        "",
        "## Samples",
        "",
        "| sample | sessions | turns | image turns | VLM injected | caption-only image turns | rewrite path | status |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for item in sample_reports:
        stats = item.get("stats") or {}
        lines.append(
            f"| `{item.get('sample_id')}` | {stats.get('sessions')} | {stats.get('turns')} | "
            f"{stats.get('image_turns')} | {stats.get('vlm_ok_injected')} | "
            f"{stats.get('caption_only_image_turns')} | `{item.get('rewrite_path')}` | {item.get('status')} |"
        )
    lines.extend([
        "",
        "## Notes",
        "",
        "- This is a rewrite-stage experiment, not a QA result.",
        "- Baseline rewrite caches are not modified.",
        "- If VLM URL access fails, the script records failures and falls back to caption-only input for those turns.",
        "- Run keyword, embedding, and QA on this rewrite cache only after the rewrite structure is audited.",
    ])
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    load_dotenv()
    args = parse_args()
    if args.data != "locomo":
        raise SystemExit("VLM-enriched rewrite currently supports only --data locomo")

    # Import after parse_args so common.config sees --data/--model from sys.argv.
    from llm.controller import LLM
    from memory.controller import MemoryController
    from memory.system import MemorySystem
    from agent.agent import Agent

    sample_filter = requested_sample_ids(args)
    data = load_dataset(args.data)
    samples = [sample for sample in data if sample_filter is None or sample.get("sample_id") in sample_filter]
    if not samples:
        raise SystemExit("No matching samples found")

    client: Optional[OpenAI] = None
    if not args.dry_run and not args.skip_vlm:
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        base_url = os.getenv("LLM_BASE_URL", "https://api.siliconflow.cn/v1")
        if not api_key:
            raise SystemExit("Missing OPENAI_API_KEY or OPENROUTER_API_KEY in .env")
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=600.0, max_retries=2)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    diag_dir = Path("result") / "diagnostics"
    diag_dir.mkdir(parents=True, exist_ok=True)
    report_dir = Path("reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    visual_jsonl = diag_dir / f"vlm_enriched_rewrite_visual_{args.file}_{stamp}.jsonl"
    enriched_jsonl = diag_dir / f"vlm_enriched_rewrite_sessions_{args.file}_{stamp}.jsonl"
    report_path = report_dir / f"vlm_enriched_rewrite_{args.file}_{stamp}.md"

    out_dir = Path("data") / args.data / f"rewrite_{args.model}_{args.output_suffix}"
    out_dir.mkdir(parents=True, exist_ok=True)

    sample_reports: List[Dict[str, Any]] = []
    for sample in samples:
        sample_id = sample.get("sample_id")
        rewrite_path = out_dir / f"{sample_id}_rewrite.json"
        if rewrite_path.exists() and not args.force:
            sample_reports.append({
                "sample_id": sample_id,
                "rewrite_path": str(rewrite_path),
                "status": "skipped_existing_use_force_to_overwrite",
                "stats": {},
            })
            continue
        if rewrite_path.exists() and args.force:
            rewrite_path.unlink()

        visual_evidence = collect_visual_evidence(sample, args, client, visual_jsonl)
        enriched_sessions, stats = build_enriched_sessions(sample, visual_evidence, args.max_sessions)
        with enriched_jsonl.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "sample_id": sample_id,
                "stats": stats,
                "sessions": enriched_sessions,
            }, ensure_ascii=False) + "\n")

        status = "prepared_enriched_sessions"
        if args.rewrite:
            llm = LLM()
            memory_system = MemorySystem()
            memory_controller = MemoryController(memory_system, llm)
            agent = Agent(llm, memory_system, memory_controller)
            agent.rewrite_sample(enriched_sessions, str(rewrite_path))
            status = "rewrite_completed"
        elif not args.dry_run:
            status = "prepared_only_no_rewrite_flag"

        sample_reports.append({
            "sample_id": sample_id,
            "rewrite_path": str(rewrite_path),
            "status": status,
            "stats": stats,
        })

    write_report(report_path, args, sample_reports)
    print(f"Wrote visual evidence JSONL: {visual_jsonl}")
    print(f"Wrote enriched sessions JSONL: {enriched_jsonl}")
    print(f"Wrote report: {report_path}")
    for item in sample_reports:
        print(f"{item['sample_id']}: {item['status']} -> {item['rewrite_path']}")


if __name__ == "__main__":
    main()
