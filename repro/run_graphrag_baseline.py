#!/usr/bin/env python3
"""Minimal GraphRAG baseline over MRAgent rewrite/keyword caches.

This is not the original MRAgent tool-calling loop. It is a controlled baseline:
embedding seed retrieval -> graph neighbor expansion -> single-turn QA.
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import config
from data.get_data import get_data
from llm.controller import LLM


SYSTEM_PROMPT = """Answer the question based ONLY on the provided graph-expanded conversation context.
If the context does not contain enough information, answer "no information available".
Give a concise answer."""


def cosine_similarity(a: Any, b: Any) -> float:
    a = np.asarray(a).flatten()
    b = np.asarray(b).flatten()
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))


def load_subset_manifest(path: str | None) -> dict[str, list[int]] | None:
    if not path:
        return None
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    by_sample: dict[str, list[int]] = {}
    for record in obj.get("records", []):
        sample_id = record.get("sample_id")
        qidx = record.get("question_index")
        if sample_id is not None and qidx is not None:
            by_sample.setdefault(sample_id, []).append(int(qidx))
    return {sample_id: sorted(set(indices)) for sample_id, indices in by_sample.items()}


def load_rewrite_graph(rewrite_path: str) -> dict[str, Any]:
    sentences: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    origin_to_ids: dict[str, list[str]] = {}
    topic_to_ids: dict[str, list[str]] = {}
    with open(rewrite_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            for _, data in obj.items():
                if not isinstance(data, dict):
                    continue
                for sent in data.get("sentence") or []:
                    sid = sent.get("id")
                    if not sid:
                        continue
                    topics = sent.get("topic") or []
                    row = {
                        "sentence_id": sid,
                        "text": sent.get("text", ""),
                        "origin": sent.get("origin", ""),
                        "tag": sent.get("tag", ""),
                        "topics": topics,
                    }
                    sentences.append(row)
                    by_id[sid] = row
                    origin_to_ids.setdefault(row["origin"], []).append(sid)
                    for topic in topics:
                        topic_to_ids.setdefault(topic, []).append(sid)
    return {
        "sentences": sentences,
        "by_id": by_id,
        "origin_to_ids": origin_to_ids,
        "topic_to_ids": topic_to_ids,
    }


def load_keyword_graph(keyword_path: str) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    key_to_ids: dict[str, list[str]] = {}
    id_to_keys: dict[str, list[str]] = {}
    with open(keyword_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line == "null":
                continue
            obj = json.loads(line)
            for item in obj.get("sentence") or []:
                sid = item.get("sentence_id")
                if not sid:
                    continue
                for key in item.get("keyword") or []:
                    key = str(key).strip()
                    if not key:
                        continue
                    key_to_ids.setdefault(key, []).append(sid)
                    id_to_keys.setdefault(sid, []).append(key)
    return key_to_ids, id_to_keys


def load_embeddings(embedding_path: str) -> dict[str, Any]:
    db = pickle.load(open(embedding_path, "rb"))
    embeddings = db.get("embeddings", [])
    sentence_ids = db.get("sentence_id", [])
    id2emb = {sid: embeddings[i] for i, sid in enumerate(sentence_ids) if i < len(embeddings)}
    return {"id2emb": id2emb, "question_embeddings": db.get("question_embeddings")}


def retrieve_seed_ids(question_emb: Any, sentences: list[dict[str, Any]], id2emb: dict[str, Any], k: int) -> list[str]:
    if question_emb is None:
        return [sent["sentence_id"] for sent in sentences[:k]]
    scored = []
    for sent in sentences:
        emb = id2emb.get(sent["sentence_id"])
        if emb is None:
            continue
        scored.append((cosine_similarity(question_emb, emb), sent["sentence_id"]))
    scored.sort(reverse=True, key=lambda x: x[0])
    return [sid for _, sid in scored[:k]]


def expand_graph(
    seed_ids: list[str],
    graph: dict[str, Any],
    key_to_ids: dict[str, list[str]],
    id_to_keys: dict[str, list[str]],
    hops: int,
    per_key_limit: int,
) -> list[str]:
    selected = list(seed_ids)
    selected_set = set(selected)
    frontier = list(seed_ids)

    for _ in range(max(0, hops)):
        new_frontier = []
        for sid in frontier:
            sent = graph["by_id"].get(sid)
            if not sent:
                continue
            candidates = []
            candidates.extend(graph["origin_to_ids"].get(sent.get("origin"), []))
            for topic in sent.get("topics") or []:
                candidates.extend(graph["topic_to_ids"].get(topic, []))
            for key in id_to_keys.get(sid, []):
                candidates.extend(key_to_ids.get(key, [])[:per_key_limit])
            for cid in candidates:
                if cid not in selected_set:
                    selected_set.add(cid)
                    selected.append(cid)
                    new_frontier.append(cid)
        frontier = new_frontier
        if not frontier:
            break
    return selected


def build_context(ids: list[str], graph: dict[str, Any], limit: int) -> str:
    lines = []
    for sid in ids[:limit]:
        sent = graph["by_id"].get(sid)
        if not sent:
            continue
        lines.append(f"[{sid}] ({sent.get('tag')}) origin={sent.get('origin')} text={sent.get('text')}")
    return "\n".join(lines)


def answer(llm: LLM, question: str, context: str) -> str:
    result = llm.chat_plain_text(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Question: {question}\n\nContext:\n{context}\n\nAnswer:"},
        ],
        max_tokens=config.QA_MAX_TOKENS,
    )
    return str(result or "no information available")


def run_sample(args: argparse.Namespace, sample_id: str, qa_list: list[dict[str, Any]], q_indices: list[int] | None) -> None:
    rewrite_path = config.rewrite_template.format(dataset=args.data, sample_id=sample_id)
    keyword_path = config.keyword_template.format(dataset=args.data, sample_id=sample_id)
    embedding_path = config.embedding_template.format(dataset=args.data, sample_id=sample_id)
    for required in [rewrite_path, keyword_path, embedding_path]:
        if not os.path.exists(required):
            raise FileNotFoundError(required)

    graph = load_rewrite_graph(rewrite_path)
    key_to_ids, id_to_keys = load_keyword_graph(keyword_path)
    emb = load_embeddings(embedding_path)
    q_embs = emb.get("question_embeddings")
    if q_embs is None:
        q_embs = []

    result_path = config.result_template.format(dataset=args.data, sample_id=sample_id).replace(
        f"result_{config.ADDITIONAL_RE}", f"result_{args.model}_{args.file}"
    )
    os.makedirs(os.path.dirname(result_path), exist_ok=True)

    items = [(idx, qa_list[idx]) for idx in q_indices] if q_indices is not None else list(enumerate(qa_list))
    done = 0
    if os.path.exists(result_path):
        with open(result_path, encoding="utf-8") as f:
            done = sum(1 for line in f if line.strip())
    if done >= len(items):
        return

    llm = LLM()
    for seq, (orig_idx, qa) in enumerate(items):
        if seq < done:
            continue
        question = qa.get("question", "")
        q_emb = q_embs[orig_idx] if orig_idx < len(q_embs) else None
        seed_ids = retrieve_seed_ids(q_emb, graph["sentences"], emb["id2emb"], args.seed_k)
        expanded_ids = expand_graph(seed_ids, graph, key_to_ids, id_to_keys, args.hops, args.per_key_limit)
        context = build_context(expanded_ids, graph, args.max_context_sentences)
        started = time.time()
        try:
            prediction = answer(llm, question, context)
        except Exception as exc:
            prediction = "ERROR"
            print(f"{sample_id} q{orig_idx+1} failed: {exc}")
        runtime = round(time.time() - started, 2)
        context_origins = []
        for sid in expanded_ids[: args.max_context_sentences]:
            sent = graph["by_id"].get(sid)
            if sent:
                context_origins.append(sent.get("origin"))
        row = {
            "answer": qa.get("answer"),
            "prediction": prediction,
            "category": qa.get("category"),
            "evidence": qa.get("evidence") or [],
            "question": question,
            "prediction_context": sorted(set(context_origins)),
            "sample": sample_id,
            "question_index": orig_idx,
            "question_index_1based": orig_idx + 1,
            "_metrics": {
                "tool_calls": 0,
                "schema_retries": 0,
                "forced_accepts": 0,
                "runtime_sec": runtime,
                "graphrag_seed_k": args.seed_k,
                "graphrag_hops": args.hops,
                "graphrag_expanded_nodes": len(expanded_ids),
                "graphrag_context_sentences": min(len(expanded_ids), args.max_context_sentences),
            },
        }
        with open(result_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        print(f"{sample_id} {seq+1}/{len(items)} orig={orig_idx+1} cat={qa.get('category')} done")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run minimal GraphRAG baseline.")
    parser.add_argument("--data", default="locomo")
    parser.add_argument("--model", default="deepseek")
    parser.add_argument("--file", default="graphrag")
    parser.add_argument("--sample_ids", default=None)
    parser.add_argument("--subset_manifest", default=None)
    parser.add_argument("--seed_k", type=int, default=10)
    parser.add_argument("--hops", type=int, default=1)
    parser.add_argument("--per_key_limit", type=int, default=8)
    parser.add_argument("--max_context_sentences", type=int, default=30)
    args = parser.parse_args()

    _, question_list, _, _ = get_data(args.data, f"data/dataset_{args.data}.json")
    subset = load_subset_manifest(args.subset_manifest)
    if args.sample_ids:
        sample_ids = [s.strip() if s.strip().startswith("conv-") else f"conv-{s.strip()}" for s in args.sample_ids.split(",") if s.strip()]
    elif subset:
        sample_ids = list(subset)
    else:
        sample_ids = list(question_list)

    for sample_id in sample_ids:
        q_indices = subset.get(sample_id) if subset else None
        run_sample(args, sample_id, question_list.get(sample_id, []), q_indices)


if __name__ == "__main__":
    main()
