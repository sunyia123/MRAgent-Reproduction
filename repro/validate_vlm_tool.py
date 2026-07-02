#!/usr/bin/env python3
"""
Validate the VLM visual-evidence tool before wiring it into MRAgent QA.

This script scans real LoCoMo image turns, calls an OpenAI-compatible VLM, and
writes auditable JSONL + Markdown artifacts. It does not modify baseline result
files and does not inject VLM output into benchmark answers.
"""

import argparse
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from dotenv import load_dotenv
from openai import OpenAI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Qwen VLM as a visual-evidence tool.")
    parser.add_argument("--data", default="locomo", help="Dataset name, default: locomo")
    parser.add_argument("--sample", default="30", help="Sample number or id, e.g. 30 or conv-30")
    parser.add_argument("--limit", type=int, default=5, help="Max image turns to validate")
    parser.add_argument("--file", default="vlm_tool", help="Run tag for output filenames")
    parser.add_argument("--model", default=os.getenv("VLM_MODEL", "Qwen/Qwen3.5-397B-A17B"))
    parser.add_argument("--max_tokens", type=int, default=int(os.getenv("VLM_MAX_TOKENS", "1024")))
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--dry_run", action="store_true", help="Build payloads without calling the API")
    parser.add_argument(
        "--question",
        default="Describe only the visual evidence that may help answer a long-dialogue memory question.",
        help="Probe question sent with each image.",
    )
    return parser.parse_args()


def normalize_sample_id(sample: str) -> str:
    sample = str(sample).strip()
    if sample.startswith("conv-"):
        return sample
    return f"conv-{sample}"


def load_sample(dataset: str, sample_id: str) -> Dict[str, Any]:
    path = Path("data") / f"dataset_{dataset}.json"
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    for sample in data:
        if sample.get("sample_id") == sample_id:
            return sample
    raise ValueError(f"sample_id not found: {sample_id}")


def iter_image_turns(sample: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    sample_id = sample.get("sample_id")
    conversation = sample.get("conversation") or {}
    speaker_a = conversation.get("speaker_a")
    speaker_b = conversation.get("speaker_b")

    session_keys = [
        key for key in conversation
        if re.fullmatch(r"session_\d+", key) and isinstance(conversation.get(key), list)
    ]
    session_keys.sort(key=lambda key: int(key.split("_")[1]))

    for session_key in session_keys:
        session_time = conversation.get(f"{session_key}_date_time")
        for turn_index, turn in enumerate(conversation.get(session_key, [])):
            image_urls = turn.get("img_url") or []
            if isinstance(image_urls, str):
                image_urls = [image_urls]
            if not image_urls:
                continue
            yield {
                "sample_id": sample_id,
                "session": session_key,
                "session_time": session_time,
                "turn_index": turn_index,
                "dia_id": turn.get("dia_id"),
                "speaker": turn.get("speaker"),
                "speaker_a": speaker_a,
                "speaker_b": speaker_b,
                "text": turn.get("text"),
                "blip_caption": turn.get("blip_caption"),
                "image_url": image_urls[0],
                "image_urls": image_urls,
            }


def build_prompt(turn: Dict[str, Any], question: str) -> str:
    return (
        f"{question}\n\n"
        "Return concise JSON with keys: visual_answer, visible_entities, confidence, failure_reason.\n"
        "Use the image as primary evidence. Use the caption and dialogue only as context.\n\n"
        f"sample_id: {turn.get('sample_id')}\n"
        f"event_id: {turn.get('dia_id')}\n"
        f"session: {turn.get('session')}\n"
        f"session_time: {turn.get('session_time')}\n"
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
    latency_s = round(time.time() - started, 2)
    raw = response_to_dict(resp)
    choice = raw.get("choices", [{}])[0] if raw.get("choices") else {}
    message = choice.get("message") or {}
    usage = raw.get("usage") or {}
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
            "usage": usage,
            "latency_s": latency_s,
        },
        "raw_response": raw,
    }


def write_markdown_report(report_path: Path, records: List[Dict[str, Any]], args: argparse.Namespace) -> None:
    ok = sum(1 for item in records if item.get("status") == "ok")
    failed = len(records) - ok
    lines = [
        f"# VLM Tool Validation - {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "## Purpose",
        "",
        "Validate Qwen VLM as a standalone visual-evidence tool before integrating it into MRAgent QA.",
        "",
        "## Configuration",
        "",
        f"- dataset: `{args.data}`",
        f"- sample: `{normalize_sample_id(args.sample)}`",
        f"- model: `{args.model}`",
        f"- limit: `{args.limit}`",
        f"- dry_run: `{args.dry_run}`",
        "",
        "## Result Summary",
        "",
        f"- records: {len(records)}",
        f"- ok: {ok}",
        f"- failed: {failed}",
        "",
        "## Per Image Turn",
        "",
        "| # | event_id | session | status | finish_reason | latency_s | content preview |",
        "| --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for idx, item in enumerate(records, 1):
        turn = item.get("turn") or {}
        resp = item.get("vlm") or {}
        response = resp.get("response") or {}
        content = (response.get("content") or item.get("error") or "").replace("\n", " ")
        if len(content) > 120:
            content = content[:117] + "..."
        lines.append(
            f"| {idx} | `{turn.get('dia_id')}` | `{turn.get('session')}` | "
            f"{item.get('status')} | {response.get('finish_reason')} | "
            f"{response.get('latency_s', '')} | {content} |"
        )
    lines.extend([
        "",
        "## Acceptance Criteria",
        "",
        "- At least 3 real LoCoMo image URLs return non-empty visual evidence.",
        "- Each record contains event_id, image_url, caption, raw response metadata, usage, and latency.",
        "- Failures are classified as API failure, image URL failure, model failure, or parse failure in the JSONL.",
        "- This report is only a VLM tool check; it is not a QA benchmark result.",
    ])
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    load_dotenv()
    args = parse_args()
    sample_id = normalize_sample_id(args.sample)
    sample = load_sample(args.data, sample_id)
    turns = list(iter_image_turns(sample))[: args.limit]
    if not turns:
        raise SystemExit(f"No image turns found for {sample_id}")

    out_dir = Path("result") / "diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir = Path("reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl_path = out_dir / f"vlm_tool_validation_{args.file}_{sample_id}_{stamp}.jsonl"
    report_path = report_dir / f"vlm_tool_validation_{args.file}_{sample_id}_{stamp}.md"

    client: Optional[OpenAI] = None
    if not args.dry_run:
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        base_url = os.getenv("LLM_BASE_URL", "https://api.siliconflow.cn/v1")
        if not api_key:
            raise SystemExit("Missing OPENAI_API_KEY or OPENROUTER_API_KEY in environment/.env")
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=600.0, max_retries=2)

    records: List[Dict[str, Any]] = []
    with jsonl_path.open("w", encoding="utf-8") as f:
        for turn in turns:
            prompt = build_prompt(turn, args.question)
            record: Dict[str, Any] = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "status": "dry_run" if args.dry_run else "pending",
                "turn": turn,
                "prompt": prompt,
            }
            try:
                if args.dry_run:
                    record["vlm"] = {
                        "request": {
                            "model": args.model,
                            "temperature": args.temperature,
                            "max_tokens": args.max_tokens,
                            "image_url": turn["image_url"],
                            "prompt_length": len(prompt),
                        }
                    }
                else:
                    record["vlm"] = call_vlm(
                        client=client,
                        model=args.model,
                        prompt=prompt,
                        image_url=turn["image_url"],
                        max_tokens=args.max_tokens,
                        temperature=args.temperature,
                    )
                    content = ((record["vlm"].get("response") or {}).get("content") or "").strip()
                    record["status"] = "ok" if content else "empty_response"
            except Exception as exc:
                record["status"] = "error"
                record["error"] = repr(exc)
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            records.append(record)

    write_markdown_report(report_path, records, args)
    print(f"Wrote JSONL: {jsonl_path}")
    print(f"Wrote report: {report_path}")


if __name__ == "__main__":
    main()
