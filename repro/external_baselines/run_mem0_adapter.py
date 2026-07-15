#!/usr/bin/env python3
"""Run pinned OSS Mem0 on an exact LoCoMo subset with project-standard QA/output."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common import config
from llm.controller import LLM
from llm.embeddings import EMBED_MODEL, get_openai_embedding
from repro.external_baselines.adapter_common import (
    answer_question,
    append_result,
    build_context,
    completed_question_indices,
    conversation_units,
    file_sha256,
    load_locomo_run,
    memory_input_text,
    question_items,
    require_repo_commit,
    result_path,
    source_ids_from_text,
    write_provenance,
    write_trace,
)


MEM0_COMMIT = "ccbe5861a138c7583e01bb3a3aa6168e52526a23"
logger = logging.getLogger("mem0_adapter")


class LoggedCompletions:
    def __init__(self, target, log_path: Path):
        self.target = target
        self.log_path = log_path

    def create(self, **kwargs):
        request = dict(kwargs)
        extra_body = dict(request.get("extra_body") or {})
        extra_body["enable_thinking"] = False
        request["extra_body"] = extra_body
        started = time.time()
        record = {"status": "started", "stage": "mem0_memory", "request": request}
        self._write(record)
        try:
            response = self.target.create(**request)
        except Exception as exc:
            self._write(
                {
                    "status": "error",
                    "stage": "mem0_memory",
                    "latency_s": round(time.time() - started, 3),
                    "error": repr(exc),
                }
            )
            raise
        payload = response.model_dump(mode="json") if hasattr(response, "model_dump") else str(response)
        self._write(
            {
                "status": "success",
                "stage": "mem0_memory",
                "latency_s": round(time.time() - started, 3),
                "response": payload,
            }
        )
        return response

    def _write(self, record: dict[str, Any]) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


class LoggedClient:
    def __init__(self, client, log_path: Path):
        self._client = client
        self.chat = type("LoggedChat", (), {})()
        self.chat.completions = LoggedCompletions(client.chat.completions, log_path)

    def __getattr__(self, name: str):
        return getattr(self._client, name)


def import_mem0(repo_path: str):
    os.environ.setdefault("MEM0_TELEMETRY", "false")
    sys.path.insert(0, str(Path(repo_path).resolve()))
    from mem0 import Memory

    return Memory


def safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")


def make_memory(Memory, sample_id: str, cache_dir: str, namespace: str, embedding_dims: int):
    root = Path(cache_dir) / safe_name(namespace) / sample_id
    root.mkdir(parents=True, exist_ok=True)
    collection = safe_name(f"mragent_{namespace}_{sample_id}")[:60]
    mem0_config = {
        "version": "v1.1",
        "llm": {
            "provider": "openai",
            "config": {
                "model": config.RE_MODEL,
                "api_key": config.API_KEY,
                "openai_base_url": config.LLM_BASE_URL,
                "temperature": 0.0,
                "max_tokens": 4096,
                "is_reasoning_model": False,
            },
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": EMBED_MODEL,
                "api_key": config.API_KEY,
                "openai_base_url": config.EMBED_BASE_URL,
            },
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": collection,
                "path": str(root / "qdrant"),
                "embedding_model_dims": embedding_dims,
            },
        },
        "history_db_path": str(root / "history.db"),
    }
    memory = Memory.from_config(mem0_config)
    if memory.llm.config.model != config.RE_MODEL:
        raise RuntimeError(f"Mem0 LLM route mismatch: {memory.llm.config.model} != {config.RE_MODEL}")
    if memory.embedding_model.config.model != EMBED_MODEL:
        raise RuntimeError(
            f"Mem0 embedding route mismatch: {memory.embedding_model.config.model} != {EMBED_MODEL}"
        )
    raw_log = Path("result/diagnostics") / f"mem0_raw_api_calls_{os.getenv('RUN_ID', 'default')}.jsonl"
    raw_client = OpenAI(
        api_key=config.API_KEY,
        base_url=config.LLM_BASE_URL,
        timeout=config.API_TIMEOUT_SECONDS,
        max_retries=config.API_CLIENT_MAX_RETRIES,
    )
    memory.llm.client = LoggedClient(raw_client, raw_log)
    return memory, root, mem0_config


def load_progress(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"completed_sources": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_progress(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def ingest(memory, root: Path, sample_id: str, units: list[dict[str, str]], namespace: str) -> str:
    progress_path = root / "ingestion_progress.json"
    progress = load_progress(progress_path)
    expected_config = {
        "mem0_commit": MEM0_COMMIT,
        "memory_model": config.RE_MODEL,
        "embedding_model": EMBED_MODEL,
    }
    for key, expected in expected_config.items():
        actual = progress.get(key)
        if actual is not None and actual != expected:
            raise RuntimeError(
                f"Mem0 cache {progress_path} has {key}={actual!r}, expected {expected!r}"
            )
    expected = [unit["origin"] for unit in units]
    completed = list(progress.get("completed_sources", []))
    if completed != expected[: len(completed)]:
        raise RuntimeError(f"Mem0 cache source order does not match {sample_id}")
    user_id = safe_name(f"mragent-{namespace}-{sample_id}")
    for index in range(len(completed), len(units)):
        unit = units[index]
        content = memory_input_text(unit)
        memory.add(
            [{"role": unit.get("role", "user"), "content": content}],
            user_id=user_id,
            metadata={
                "source_id": unit["origin"],
                "session_date": unit.get("session_date", ""),
                "speaker": unit.get("speaker", ""),
            },
            infer=True,
        )
        completed.append(unit["origin"])
        save_progress(
            progress_path,
            {
                "adapter_version": 1,
                "mem0_commit": MEM0_COMMIT,
                "memory_model": config.RE_MODEL,
                "embedding_model": EMBED_MODEL,
                "user_id": user_id,
                "completed_sources": completed,
            },
        )
        logger.info("%s: Mem0 ingestion %d/%d source=%s", sample_id, index + 1, len(units), unit["origin"])
    return user_id


def normalize_search_results(payload: Any) -> list[dict[str, Any]]:
    results = payload.get("results", []) if isinstance(payload, dict) else payload
    rows = []
    for item in results or []:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata") or {}
        text = str(item.get("memory") or item.get("text") or "")
        source_ids = []
        if metadata.get("source_id"):
            source_ids.append(str(metadata["source_id"]))
        source_ids.extend(source_ids_from_text(text))
        rows.append(
            {
                "id": str(item.get("id", "")),
                "source_id": source_ids[0] if source_ids else str(item.get("id", "")),
                "source_ids": list(dict.fromkeys(source_ids)),
                "text": text,
                "session_date": metadata.get("session_date", ""),
                "score": item.get("score"),
                "metadata": metadata,
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Pinned OSS Mem0 LoCoMo adapter")
    parser.add_argument("--data", default="locomo", choices=["locomo"])
    parser.add_argument("--external_repo", default="external/mem0")
    parser.add_argument("--dataset_path", default="data/dataset_locomo.json")
    parser.add_argument("--subset_manifest", required=True)
    parser.add_argument("--sample_ids", default=None)
    parser.add_argument("--model", default="deepseek")
    parser.add_argument("--re_model", default=None)
    parser.add_argument("--qa_model", default=None)
    parser.add_argument("--file", required=True)
    parser.add_argument("--retrieve_k", type=int, default=10)
    parser.add_argument("--cache_namespace", default="v4flash-qwen4b-v1")
    parser.add_argument("--cache_dir", default="data/locomo/external_cache/mem0")
    parser.add_argument("--embedding_dims", type=int, default=0)
    args = parser.parse_args()

    commit = require_repo_commit(args.external_repo, MEM0_COMMIT, "Mem0")
    Memory = import_mem0(args.external_repo)
    raw_conversations, questions, subset = load_locomo_run(
        args.dataset_path, args.subset_manifest, args.sample_ids
    )
    embedding_dims = args.embedding_dims
    if not embedding_dims:
        embedding_dims = len(get_openai_embedding(["embedding dimension probe"], model=EMBED_MODEL)[0])
    llm = LLM()

    write_provenance(
        "mem0",
        args.file,
        {
            "external_repo": Path(args.external_repo).resolve(),
            "external_commit": commit,
            "license": "Apache-2.0",
            "implementation_note": "current pinned OSS Mem0; deleted memory-benchmarks feat/v3-pipeline is unavailable",
            "manifest": args.subset_manifest,
            "manifest_sha256": file_sha256(args.subset_manifest),
            "dataset_sha256": file_sha256(args.dataset_path),
            "memory_model": config.RE_MODEL,
            "embedding_model": EMBED_MODEL,
            "embedding_dims": embedding_dims,
            "qa_model": config.QA_MODEL,
            "enable_thinking": False,
            "retrieve_k": args.retrieve_k,
            "cache_namespace": args.cache_namespace,
        },
    )

    for sample_id, indices in subset.items():
        memory, root, mem0_config = make_memory(
            Memory, sample_id, args.cache_dir, args.cache_namespace, embedding_dims
        )
        units = conversation_units(raw_conversations[sample_id])
        user_id = ingest(memory, root, sample_id, units, args.cache_namespace)
        output = result_path(sample_id, args.model, args.file)
        done = completed_question_indices(output)
        for question_index, qa, formatted_question in question_items(
            sample_id, questions[sample_id], indices
        ):
            if question_index in done:
                continue
            started = time.time()
            search_payload = memory.search(
                formatted_question,
                top_k=args.retrieve_k,
                filters={"user_id": user_id},
                threshold=0.0,
            )
            retrieved = normalize_search_results(search_payload)
            context = build_context(retrieved)
            prediction = answer_question(llm, formatted_question, context, qa.get("category"))
            runtime = round(time.time() - started, 2)
            prediction_context = list(
                dict.fromkeys(
                    source_id
                    for row in retrieved
                    for source_id in (row.get("source_ids") or [row.get("source_id")])
                    if source_id
                )
            )
            row = {
                "answer": qa.get("answer"),
                "prediction": prediction,
                "category": qa.get("category"),
                "evidence": qa.get("evidence", []),
                "question": qa.get("question", ""),
                "prediction_context": prediction_context,
                "sample": sample_id,
                "question_index": question_index,
                "question_index_1based": question_index + 1,
                "retrieved_memories": retrieved,
                "_metrics": {
                    "method": "mem0",
                    "tool_calls": 0,
                    "runtime_sec": runtime,
                    "retrieve_k": args.retrieve_k,
                    "retrieved_count": len(retrieved),
                    "external_commit": commit,
                    "memory_model": config.RE_MODEL,
                    "embedding_model": EMBED_MODEL,
                    "embedding_dims": embedding_dims,
                    "qa_model": config.QA_MODEL,
                    "memory_cache": str(root),
                },
            }
            append_result(output, row)
            write_trace(
                "mem0",
                sample_id,
                question_index,
                {
                    "formatted_question": formatted_question,
                    "search_payload": search_payload,
                    "context": context,
                    "effective_config": {
                        "llm_model": mem0_config["llm"]["config"]["model"],
                        "embedding_model": mem0_config["embedder"]["config"]["model"],
                        "enable_thinking": False,
                    },
                    **row,
                },
            )
            logger.info("%s Q%d complete (%ss)", sample_id, question_index + 1, runtime)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
    main()
