#!/usr/bin/env python3
"""Run pinned A-Mem on an exact LoCoMo subset with project-standard QA/output."""

from __future__ import annotations

import argparse
import json
import logging
import os
import pickle
import sys
import time
from pathlib import Path
from types import MethodType, SimpleNamespace
from typing import Any

import numpy as np

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
    write_provenance,
    write_trace,
)


AMEM_COMMIT = "0c8039f28fdcc08189a23c07a3437d9d2482f9c2"
logger = logging.getLogger("amem_adapter")


class SiliconFlowTextController:
    """A-Mem's get_completion interface backed by the project's logged LLM client."""

    SYSTEM_MESSAGE = "You are a memory management assistant. Follow the requested output format exactly."

    def __init__(self, llm: LLM, model: str, max_tokens: int):
        self.client = llm
        self.model = model
        self.max_tokens = max_tokens

    def get_completion(self, prompt: str, temperature: float = 0.0) -> str:
        self.client._current_stage = "amem_memory"
        return self.client.chat_plain_text(
            messages=[
                {"role": "system", "content": self.SYSTEM_MESSAGE},
                {"role": "user", "content": prompt},
            ],
            model=self.model,
            temperature=temperature,
            max_tokens=self.max_tokens,
        )


class QwenEmbeddingRetriever:
    """Minimal A-Mem retriever using the experiment's SiliconFlow embedding model."""

    def __init__(self, model: str):
        self.model_name = model
        self.documents: list[str] = []
        self.embeddings: list[list[float]] = []

    def add_documents(self, documents: list[str]) -> None:
        if not documents:
            return
        vectors = get_openai_embedding(documents, model=self.model_name)
        self.documents.extend(documents)
        self.embeddings.extend(vectors)

    def search(self, query: str, k: int = 5) -> list[int]:
        if not self.embeddings:
            return []
        query_vector = np.asarray(
            get_openai_embedding([query], model=self.model_name)[0], dtype=np.float32
        )
        matrix = np.asarray(self.embeddings, dtype=np.float32)
        scores = matrix @ query_vector / (
            np.linalg.norm(matrix, axis=1) * np.linalg.norm(query_vector) + 1e-10
        )
        count = min(max(0, k), len(scores))
        return np.argsort(-scores)[:count].tolist()

    def state_dict(self) -> dict[str, Any]:
        return {
            "model": self.model_name,
            "documents": self.documents,
            "embeddings": self.embeddings,
        }

    @classmethod
    def from_state_dict(cls, state: dict[str, Any]) -> "QwenEmbeddingRetriever":
        retriever = cls(str(state["model"]))
        retriever.documents = list(state.get("documents", []))
        retriever.embeddings = list(state.get("embeddings", []))
        return retriever


def import_amem(repo_path: str):
    sys.path.insert(0, str(Path(repo_path).resolve()))
    from memory_layer_robust import RobustAgenticMemorySystem

    return RobustAgenticMemorySystem


def cache_path(cache_dir: str, sample_id: str) -> Path:
    path = Path(cache_dir) / f"{sample_id}_state.pkl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def make_system(system_class, controller: SiliconFlowTextController, retriever: QwenEmbeddingRetriever):
    system = object.__new__(system_class)
    system.memories = {}
    system.retriever = retriever
    system.llm_controller = SimpleNamespace(llm=controller)
    system.evo_cnt = 0
    system.evo_threshold = 100
    system.consolidate_memories = MethodType(consolidate_qwen_memories, system)
    return system


def consolidate_qwen_memories(system) -> None:
    """Preserve A-Mem consolidation without falling back to its MiniLM retriever."""
    retriever = QwenEmbeddingRetriever(system.retriever.model_name)
    documents = []
    for memory in system.memories.values():
        documents.append(
            "content:"
            + memory.content
            + " context:"
            + memory.context
            + " keywords: "
            + ", ".join(memory.keywords)
            + " tags: "
            + ", ".join(memory.tags)
        )
    retriever.add_documents(documents)
    system.retriever = retriever


def save_cache(path: Path, system, units: list[dict[str, str]], completed: int) -> None:
    payload = {
        "adapter_version": 1,
        "amem_commit": AMEM_COMMIT,
        "memory_model": config.RE_MODEL,
        "embedding_model": EMBED_MODEL,
        "source_ids": [unit["origin"] for unit in units],
        "completed": completed,
        "memories": system.memories,
        "retriever": system.retriever.state_dict(),
        "evo_cnt": system.evo_cnt,
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        pickle.dump(payload, handle)
    temporary.replace(path)


def load_or_build_memory(
    system_class,
    controller: SiliconFlowTextController,
    sample_id: str,
    units: list[dict[str, str]],
    cache_dir: str,
):
    path = cache_path(cache_dir, sample_id)
    expected_sources = [unit["origin"] for unit in units]
    completed = 0
    if path.exists():
        with path.open("rb") as handle:
            state = pickle.load(handle)
        checks = {
            "amem_commit": AMEM_COMMIT,
            "memory_model": config.RE_MODEL,
            "embedding_model": EMBED_MODEL,
        }
        for key, expected in checks.items():
            if state.get(key) != expected:
                raise RuntimeError(f"A-Mem cache {path} has {key}={state.get(key)!r}, expected {expected!r}")
        completed = int(state.get("completed", 0))
        if state.get("source_ids", [])[:completed] != expected_sources[:completed]:
            raise RuntimeError(f"A-Mem cache source order does not match {sample_id}")
        system = make_system(
            system_class,
            controller,
            QwenEmbeddingRetriever.from_state_dict(state["retriever"]),
        )
        system.memories = state["memories"]
        system.evo_cnt = int(state.get("evo_cnt", 0))
        logger.info("%s: resuming A-Mem ingestion at %d/%d", sample_id, completed, len(units))
    else:
        system = make_system(system_class, controller, QwenEmbeddingRetriever(EMBED_MODEL))

    for index in range(completed, len(units)):
        unit = units[index]
        system.add_note(
            memory_input_text(unit),
            time=unit.get("session_date") or None,
            id=unit["origin"],
        )
        save_cache(path, system, units, index + 1)
        logger.info("%s: A-Mem ingestion %d/%d source=%s", sample_id, index + 1, len(units), unit["origin"])
    return system, path


def query_keywords(controller: SiliconFlowTextController, question: str) -> str:
    prompt = (
        "Given the following question, generate several retrieval keywords separated by commas.\n\n"
        f"Question: {question}\n\nKeywords:"
    )
    return controller.get_completion(prompt, temperature=0.0).strip() or question


def retrieve_rows(system, query: str, retrieve_k: int, max_context_memories: int) -> list[dict[str, Any]]:
    seed_indices = system.retriever.search(query, retrieve_k)
    memories = list(system.memories.values())
    expanded: list[int] = []
    for index in seed_indices:
        if index not in expanded:
            expanded.append(index)
        if 0 <= index < len(memories):
            for neighbor in memories[index].links:
                if isinstance(neighbor, int) and 0 <= neighbor < len(memories) and neighbor not in expanded:
                    expanded.append(neighbor)
    rows = []
    for index in expanded[:max_context_memories]:
        note = memories[index]
        rows.append(
            {
                "id": note.id,
                "source_id": note.id,
                "text": note.content,
                "timestamp": note.timestamp,
                "context": note.context,
                "keywords": note.keywords,
                "tags": note.tags,
                "links": note.links,
                "is_seed": index in seed_indices,
                "memory_index": index,
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Pinned A-Mem LoCoMo adapter")
    parser.add_argument("--data", default="locomo", choices=["locomo"])
    parser.add_argument("--external_repo", default="external/A-mem")
    parser.add_argument("--dataset_path", default="data/dataset_locomo.json")
    parser.add_argument("--subset_manifest", required=True)
    parser.add_argument("--sample_ids", default=None)
    parser.add_argument("--model", default="deepseek")
    parser.add_argument("--re_model", default=None)
    parser.add_argument("--qa_model", default=None)
    parser.add_argument("--file", required=True)
    parser.add_argument("--retrieve_k", type=int, default=10)
    parser.add_argument("--max_context_memories", type=int, default=30)
    parser.add_argument("--memory_max_tokens", type=int, default=4096)
    parser.add_argument("--cache_dir", default="data/locomo/external_cache/amem")
    args = parser.parse_args()

    commit = require_repo_commit(args.external_repo, AMEM_COMMIT, "A-Mem")
    system_class = import_amem(args.external_repo)
    raw_conversations, questions, subset = load_locomo_run(
        args.dataset_path, args.subset_manifest, args.sample_ids
    )
    llm = LLM()
    controller = SiliconFlowTextController(llm, config.RE_MODEL, args.memory_max_tokens)

    write_provenance(
        "amem",
        args.file,
        {
            "external_repo": Path(args.external_repo).resolve(),
            "external_commit": commit,
            "license": "MIT",
            "manifest": args.subset_manifest,
            "manifest_sha256": file_sha256(args.subset_manifest),
            "dataset_sha256": file_sha256(args.dataset_path),
            "memory_model": config.RE_MODEL,
            "embedding_model": EMBED_MODEL,
            "qa_model": config.QA_MODEL,
            "enable_thinking": config.ENABLE_THINKING,
            "retrieve_k": args.retrieve_k,
            "max_context_memories": args.max_context_memories,
        },
    )

    for sample_id, indices in subset.items():
        units = conversation_units(raw_conversations[sample_id])
        system, memory_cache = load_or_build_memory(
            system_class, controller, sample_id, units, args.cache_dir
        )
        output = result_path(sample_id, args.model, args.file)
        done = completed_question_indices(output)
        for question_index, qa, formatted_question in question_items(
            sample_id, questions[sample_id], indices
        ):
            if question_index in done:
                continue
            started = time.time()
            query = query_keywords(controller, formatted_question)
            retrieved = retrieve_rows(system, query, args.retrieve_k, args.max_context_memories)
            context = build_context(retrieved)
            prediction = answer_question(llm, formatted_question, context, qa.get("category"))
            runtime = round(time.time() - started, 2)
            prediction_context = list(dict.fromkeys(row["source_id"] for row in retrieved))
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
                    "method": "amem",
                    "tool_calls": 0,
                    "runtime_sec": runtime,
                    "retrieve_k": args.retrieve_k,
                    "retrieved_count": len(retrieved),
                    "memory_count": len(system.memories),
                    "external_commit": commit,
                    "memory_model": config.RE_MODEL,
                    "embedding_model": EMBED_MODEL,
                    "qa_model": config.QA_MODEL,
                    "memory_cache": str(memory_cache),
                },
            }
            append_result(output, row)
            write_trace(
                "amem",
                sample_id,
                question_index,
                {"formatted_question": formatted_question, "retrieval_query": query, "context": context, **row},
            )
            logger.info("%s Q%d complete (%ss)", sample_id, question_index + 1, runtime)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
    main()
