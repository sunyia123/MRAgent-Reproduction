#!/usr/bin/env python3
"""Rebuild MRAgent's in-memory graph from existing caches and export a snapshot.

This script does not call rewrite, keyword, embedding, or QA models. It is used
to inspect whether a badcase's gold evidence exists in the graph and how it is
connected to keywords, topics, and persona facts.
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def normalize_sample_id(value: str) -> str:
    value = str(value).strip()
    return value if value.startswith("conv-") else f"conv-{value}"


def load_embeddings(path: Path) -> tuple[dict[str, Any], Any, list[str], Any, dict[str, Any]]:
    with path.open("rb") as f:
        database = pickle.load(f)
    embeddings = database.get("embeddings")
    sentence_ids = database.get("sentence_id")
    topic_embeddings = database.get("topic")
    # data/embed_rewrite.py stores topic ids under "topic_list". Keep
    # "topic_id" as a backward-compatible fallback for older local artifacts.
    topic_source = "topic_list" if database.get("topic_list") is not None else "topic_id"
    topic_ids = database.get("topic_list") or database.get("topic_id")
    question_embeddings = database.get("question_embeddings")
    if embeddings is None or sentence_ids is None:
        raise ValueError(f"Missing embeddings or sentence_id in {path}")
    id2emb = {sid: embeddings[i] for i, sid in enumerate(sentence_ids)}
    audit = {
        "embedding_sentence_count": len(sentence_ids),
        "topic_id_source": topic_source,
        "topic_id_count": len(topic_ids or []),
        "topic_embedding_count": len(topic_embeddings) if topic_embeddings is not None else 0,
        "question_embedding_count": len(question_embeddings) if question_embeddings is not None else 0,
    }
    return id2emb, question_embeddings, topic_ids or [], topic_embeddings, audit


def default_paths(args: argparse.Namespace) -> dict[str, Path]:
    sample_id = normalize_sample_id(args.sample)
    return {
        "rewrite": Path(args.rewrite_path)
        if args.rewrite_path
        else Path("data") / args.data / f"rewrite_{args.model}" / f"{sample_id}_rewrite.json",
        "keyword": Path(args.keyword_path)
        if args.keyword_path
        else Path("data") / args.data / f"keyword_{args.model}" / f"{sample_id}_keyword.json",
        "embedding": Path(args.embedding_path)
        if args.embedding_path
        else Path("data") / args.data / "embedding" / f"gpt_{args.model}" / f"{sample_id}_embedding.pkl",
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def matching_episode_ids(turn_id: str, episode_ids: set[str]) -> list[str]:
    """Return sentence-level episode ids matching a turn-level evidence id.

    LoCoMo gold evidence is usually turn-level, for example D1:25. MRAgent
    rewrite expands one turn into sentence-level nodes such as D1:25-1 and
    D1:25-2. Exact matching therefore creates false missing-evidence reports.
    """

    if turn_id in episode_ids:
        return [turn_id]
    prefix = f"{turn_id}-"
    return sorted(eid for eid in episode_ids if eid.startswith(prefix))


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a MRAgent graph snapshot from caches.")
    parser.add_argument("--data", default="locomo")
    parser.add_argument("--model", default="deepseek")
    parser.add_argument("--sample", required=True)
    parser.add_argument("--rewrite_path", default=None)
    parser.add_argument("--keyword_path", default=None)
    parser.add_argument("--embedding_path", default=None)
    parser.add_argument("--output_dir", default="result/graph_snapshot")
    parser.add_argument("--report", default=None)
    args = parser.parse_args()

    sample_id = normalize_sample_id(args.sample)
    paths = default_paths(args)
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required cache files: " + ", ".join(missing))

    from agent.agent import Agent
    from data.get_data import get_data
    from memory.system import MemorySystem

    conversation_list, question_list, _, raw_text_list = get_data(args.data, f"data/dataset_{args.data}.json")
    if sample_id not in conversation_list:
        raise KeyError(f"{sample_id} not found in data/dataset_{args.data}.json")

    memory = MemorySystem()
    agent = Agent(None, memory, None)
    conv_embeddings, question_embeddings, topic_ids, topic_embeddings, embedding_audit = load_embeddings(paths["embedding"])
    agent.store_raw_text(raw_text_list[sample_id], conv_embeddings, topic_ids, topic_embeddings)
    agent.store_keyword(str(paths["keyword"]), str(paths["rewrite"]))

    topic_by_event: dict[str, list[str]] = {}
    for tid, topic in memory.topic_dict.items():
        for eid in topic.event_list:
            topic_by_event.setdefault(eid, []).append(tid)

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for eid, event in sorted(memory.episode_events.items()):
        nodes.append(
            {
                "id": eid,
                "type": "episode_event",
                "origin": event.origin,
                "text": event.text,
                "tag": event.tag_t,
                "time": event.time,
                "conversation_time": event.conversation_time,
                "keys": sorted(memory.event_to_keys.get(eid, [])),
                "topics": sorted(topic_by_event.get(eid, [])),
            }
        )
        for key in sorted(memory.event_to_keys.get(eid, [])):
            edges.append({"source": key, "target": eid, "type": "keyword_event"})
        for tid in sorted(topic_by_event.get(eid, [])):
            edges.append({"source": tid, "target": eid, "type": "topic_event"})

    for key, node in sorted(memory.keys.items()):
        nodes.append(
            {
                "id": key,
                "type": "keyword",
                "text": node.text,
                "tags": list(node.tag_list),
                "event_count": sum(len(v) for v in node.tag_dict.values()),
            }
        )

    for tid, topic in sorted(memory.topic_dict.items()):
        nodes.append(
            {
                "id": tid,
                "type": "topic",
                "text": topic.text,
                "event_count": len(topic.event_list),
                "events": list(topic.event_list),
            }
        )

    for person, persona in sorted(memory.persona_list.items()):
        nodes.append(
            {
                "id": f"persona:{person}",
                "type": "persona",
                "person": person,
                "tags": list(persona.tag_list),
                "fact_count": len(persona.persona_dict),
            }
        )
        for pid, pe in sorted(persona.persona_dict.items()):
            fact_id = f"personal:{pid}"
            nodes.append(
                {
                    "id": fact_id,
                    "type": "personal_event",
                    "person": person,
                    "origin": pe.origin,
                    "text": pe.text,
                    "tag": pe.tag,
                }
            )
            edges.append({"source": f"persona:{person}", "target": fact_id, "type": "persona_fact"})

    out_dir = Path(args.output_dir)
    node_path = out_dir / f"{sample_id}_nodes.jsonl"
    edge_path = out_dir / f"{sample_id}_edges.jsonl"
    write_jsonl(node_path, nodes)
    write_jsonl(edge_path, edges)

    type_counts = Counter(n["type"] for n in nodes)
    edge_counts = Counter(e["type"] for e in edges)
    gold_evidence_ids = Counter()
    for qa in question_list.get(sample_id, []) or []:
        for eid in qa.get("evidence") or []:
            gold_evidence_ids[eid] += 1
    episode_id_set = set(memory.episode_events)
    gold_matches = {
        eid: matching_episode_ids(eid, episode_id_set)
        for eid in sorted(gold_evidence_ids)
    }
    missing_gold = [eid for eid, matches in gold_matches.items() if not matches]
    total_matched_sentence_nodes = sum(len(matches) for matches in gold_matches.values())

    report = Path(args.report) if args.report else Path("reports") / f"graph_snapshot_{sample_id}_{datetime.now().strftime('%Y%m%d')}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Graph Snapshot - {sample_id}",
        "",
        "## Source Caches",
        "",
        f"- rewrite: `{paths['rewrite']}`",
        f"- keyword: `{paths['keyword']}`",
        f"- embedding: `{paths['embedding']}`",
        f"- embedding sentence count: {embedding_audit['embedding_sentence_count']}",
        f"- topic id source: `{embedding_audit['topic_id_source']}`",
        f"- topic id count: {embedding_audit['topic_id_count']}",
        f"- topic embedding count: {embedding_audit['topic_embedding_count']}",
        f"- question embedding count: {embedding_audit['question_embedding_count']}",
        "",
        "## Outputs",
        "",
        f"- nodes: `{node_path}`",
        f"- edges: `{edge_path}`",
        "",
        "## Node Counts",
        "",
        "| type | count |",
        "| --- | ---: |",
    ]
    for node_type, count in sorted(type_counts.items()):
        lines.append(f"| {node_type} | {count} |")
    lines.extend(["", "## Edge Counts", "", "| type | count |", "| --- | ---: |"])
    for edge_type, count in sorted(edge_counts.items()):
        lines.append(f"| {edge_type} | {count} |")
    lines.extend(
        [
            "",
            "## Gold Evidence Coverage",
            "",
            f"- unique gold evidence ids: {len(gold_evidence_ids)}",
            f"- gold evidence turns with at least one sentence node: {len(gold_evidence_ids) - len(missing_gold)} / {len(gold_evidence_ids)}",
            f"- matched sentence-level evidence nodes: {total_matched_sentence_nodes}",
            "- matching rule: exact event id or sentence-level prefix match, e.g. `D1:25` matches `D1:25-1`",
            f"- missing from episode graph after prefix matching: {len(missing_gold)}",
            f"- missing ids: {', '.join(missing_gold) if missing_gold else 'none'}",
            "",
            "## Manual Badcase Use",
            "",
            "- For a failed question, locate its gold evidence id in the nodes file.",
            "- Check the event text, tag, keys, and topics.",
            "- If the evidence exists but was not retrieved, diagnose retrieval/tool path.",
            "- If the evidence is missing or malformed, diagnose rewrite/keyword/graph construction.",
            "- If the evidence is retrieved and the answer is still wrong, diagnose synthesis or evaluation.",
        ]
    )
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
