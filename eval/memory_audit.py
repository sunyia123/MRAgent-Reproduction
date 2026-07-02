#!/usr/bin/env python3
"""
Memory audit: scan built memory artifacts (keyword + rewrite) and report:
  - Node counts: KeyNode, EpisodeEvent, Link, Topic, Persona
  - Missing / null-field statistics in rewrite.json and keyword.json
  - Edge density

Usage:
  python eval/memory_audit.py --data locomo --model deepseek --sample 30 --file stratified
"""

import os, sys
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

import json
import argparse
from collections import defaultdict

from common import config as _cfg_module


def parse_args():
    p = argparse.ArgumentParser(description="Memory graph audit over rewrite + keyword artifacts")
    p.add_argument("--data", type=str, default="locomo", help="Dataset (locomo / LM)")
    p.add_argument("--model", type=str, default="deepseek", help="Model short name")
    p.add_argument("--sample", type=str, default="30", help="Sample id (e.g. 30 for conv-30)")
    p.add_argument("--file", type=str, default="smoke", help="Run tag for file suffix")
    return p.parse_args()


def load_rewrite(path: str) -> list:
    """Load rewrite JSONL. Each line: {session_id: {sentence:[...], topics:{...}, personal_sentences:[...]}}"""
    sessions = []
    if not os.path.exists(path):
        return sessions
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                obj = json.loads(line)
                sessions.append(obj)
    return sessions


def load_keyword(path: str) -> list:
    """Load keyword JSONL. Each line: {sentence: [{sentence_id, keyword:[...]}]}"""
    sessions = []
    if not os.path.exists(path):
        return sessions
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                obj = json.loads(line)
                sessions.append(obj)
    return sessions


def audit_rewrite(sessions: list) -> dict:
    """Audit rewrite artifacts for field completeness."""
    stats = {
        "total_sessions": 0,
        "total_sentences": 0,
        "total_topics": 0,
        "total_personal_events": 0,
        "sessions_without_sentences": 0,
        "sessions_without_topics": 0,
        "sessions_without_personal": 0,
        "sentences_without_id": 0,
        "sentences_without_text": 0,
        "sentences_without_tag": 0,
        "sentences_without_origin": 0,
        "topics_without_text": 0,
        "personal_without_id": 0,
        "personal_without_text": 0,
        "sentence_count_distribution": [],
        "unique_tags": set(),
        "unique_persons": set(),
        "all_conversation_times": [],
    }
    for obj in sessions:
        for session_id, data in obj.items():
            stats["total_sessions"] += 1
            if data is None:
                stats["sessions_without_sentences"] += 1
                continue

            # conversation_time
            ct = data.get("conversation_time")
            if ct:
                stats["all_conversation_times"].append(ct)

            # sentences
            sentences = data.get("sentence")
            if sentences is None:
                stats["sessions_without_sentences"] += 1
            else:
                stats["total_sentences"] += len(sentences)
                stats["sentence_count_distribution"].append(len(sentences))
                for s in sentences:
                    if not s.get("id"):
                        stats["sentences_without_id"] += 1
                    if not s.get("text"):
                        stats["sentences_without_text"] += 1
                    if not s.get("tag"):
                        stats["sentences_without_tag"] += 1
                    if not s.get("origin"):
                        stats["sentences_without_origin"] += 1
                    tag = s.get("tag", "")
                    if tag:
                        stats["unique_tags"].add(tag)

            # topics
            topics = data.get("topics")
            if topics is None:
                stats["sessions_without_topics"] += 1
            else:
                stats["total_topics"] += len(topics)
                for topic_id, topic_text in topics.items():
                    if not topic_text:
                        stats["topics_without_text"] += 1

            # personal_sentences
            personal = data.get("personal_sentences")
            if personal is None:
                stats["sessions_without_personal"] += 1
            else:
                stats["total_personal_events"] += len(personal)
                for p in personal:
                    if not p.get("id"):
                        stats["personal_without_id"] += 1
                    if not p.get("text"):
                        stats["personal_without_text"] += 1
                    person = p.get("person", "")
                    if person:
                        stats["unique_persons"].add(person)

    result = {k: v for k, v in stats.items() if not isinstance(v, set)}
    result["unique_tags"] = len(stats["unique_tags"])
    result["unique_persons"] = len(stats["unique_persons"])
    return result


def audit_keyword(sessions: list) -> dict:
    """Audit keyword artifacts. Each line: {sentence: [{sentence_id, keyword:[...]}]}"""
    stats = {
        "total_sessions": len(sessions),
        "total_sentences": 0,
        "total_keywords": 0,
        "unique_keywords": set(),
        "sentences_without_keywords": 0,
        "keyword_count_distribution": [],
    }
    for obj in sessions:
        sentences = obj.get("sentence", [])
        stats["total_sentences"] += len(sentences)
        for s in sentences:
            kw_list = s.get("keyword") or []
            stats["total_keywords"] += len(kw_list)
            stats["keyword_count_distribution"].append(len(kw_list))
            for kw in kw_list:
                stats["unique_keywords"].add(kw)
            if not kw_list:
                stats["sentences_without_keywords"] += 1
    result = {k: v for k, v in stats.items() if not isinstance(v, set)}
    result["unique_keywords"] = len(stats["unique_keywords"])
    return result


def estimate_memory_graph(rewrite_sessions: list, keyword_sessions: list) -> dict:
    """Estimate memory graph size from artifacts."""
    graph = {
        "key_nodes": 0,
        "episode_events": 0,
        "links_estimated": 0,
        "topics": 0,
        "persona_events": 0,
        "unique_persons": 0,
        "unique_tags": 0,
        "sessions": len(rewrite_sessions),
    }
    tags = set()
    persons = set()

    for obj in rewrite_sessions:
        for session_id, data in obj.items():
            if data is None:
                continue
            sentences = data.get("sentence") or []
            graph["episode_events"] += len(sentences)
            for s in sentences:
                tag = s.get("tag", "")
                if tag:
                    tags.add(tag)
            topics = data.get("topics") or {}
            graph["topics"] += len(topics)
            personal = data.get("personal_sentences") or []
            graph["persona_events"] += len(personal)
            for p in personal:
                person = p.get("person", "")
                if person:
                    persons.add(person)

    for obj in keyword_sessions:
        sentences = obj.get("sentence", [])
        for s in sentences:
            kw_list = s.get("keyword") or []
            graph["key_nodes"] += len(kw_list)
            graph["links_estimated"] += len(kw_list)  # each keyword links to its sentence

    graph["unique_persons"] = len(persons)
    graph["unique_tags"] = len(tags)
    return graph


def print_audit_report(rewrite_audit, keyword_audit, graph_audit, sample_id):
    print("\n" + "=" * 60)
    print(f"MEMORY AUDIT — {sample_id}")
    print("=" * 60)

    print("\n-- Rewrite Artifact --")
    print(f"  sessions                      : {rewrite_audit['total_sessions']}")
    print(f"  total sentences               : {rewrite_audit['total_sentences']}")
    print(f"  total topics                  : {rewrite_audit['total_topics']}")
    print(f"  total personal events         : {rewrite_audit['total_personal_events']}")
    print(f"  unique tags                   : {rewrite_audit['unique_tags']}")
    print(f"  unique persons                : {rewrite_audit['unique_persons']}")
    print(f"  sessions without sentences    : {rewrite_audit['sessions_without_sentences']}")
    print(f"  sessions without topics       : {rewrite_audit['sessions_without_topics']}")
    print(f"  sessions without personal     : {rewrite_audit['sessions_without_personal']}")
    print(f"  sentences missing id          : {rewrite_audit['sentences_without_id']}")
    print(f"  sentences missing text        : {rewrite_audit['sentences_without_text']}")
    print(f"  sentences missing tag         : {rewrite_audit['sentences_without_tag']}")
    if rewrite_audit.get("sentence_count_distribution"):
        scd = rewrite_audit["sentence_count_distribution"]
        print(f"  sentences per session         : avg={sum(scd)/len(scd):.1f} min={min(scd)} max={max(scd)}")
    if rewrite_audit.get("all_conversation_times"):
        print(f"  conversation time range       : {min(rewrite_audit['all_conversation_times'])} ~ {max(rewrite_audit['all_conversation_times'])}")

    print("\n-- Keyword Artifact --")
    print(f"  sessions                      : {keyword_audit['total_sessions']}")
    print(f"  total sentences               : {keyword_audit['total_sentences']}")
    print(f"  total keyword instances       : {keyword_audit['total_keywords']}")
    print(f"  unique keywords               : {keyword_audit['unique_keywords']}")
    print(f"  sentences without keywords    : {keyword_audit['sentences_without_keywords']}")
    if keyword_audit.get("keyword_count_distribution"):
        kcd = keyword_audit["keyword_count_distribution"]
        print(f"  keywords per sentence         : avg={sum(kcd)/len(kcd):.1f} min={min(kcd)} max={max(kcd)}")

    print("\n-- Memory Graph (estimated) --")
    print(f"  KeyNodes (unique keywords)    : {graph_audit['key_nodes']}")
    print(f"  EpisodeEvents (sentences)     : {graph_audit['episode_events']}")
    print(f"  Links (keyword->sentence est) : {graph_audit['links_estimated']}")
    print(f"  Topics                        : {graph_audit['topics']}")
    print(f"  PersonaEvents                 : {graph_audit['persona_events']}")
    print(f"  Unique persons                : {graph_audit['unique_persons']}")
    print(f"  Unique tags                   : {graph_audit['unique_tags']}")
    print("=" * 60)

    return {
        "rewrite": rewrite_audit,
        "keyword": keyword_audit,
        "graph": graph_audit,
    }


def main():
    args = parse_args()
    sample_id = f"conv-{args.sample}" if args.data == "locomo" else args.sample

    rewrite_path = _cfg_module.rewrite_template.format(dataset=args.data, sample_id=sample_id)
    keyword_path = _cfg_module.keyword_template.format(dataset=args.data, sample_id=sample_id)

    print(f"Rewrite path: {rewrite_path}  (exists: {os.path.exists(rewrite_path)})")
    print(f"Keyword path: {keyword_path}  (exists: {os.path.exists(keyword_path)})")

    rewrite_sessions = load_rewrite(rewrite_path)
    keyword_sessions = load_keyword(keyword_path)

    rewrite_audit = audit_rewrite(rewrite_sessions)
    keyword_audit = audit_keyword(keyword_sessions)
    graph_audit = estimate_memory_graph(rewrite_sessions, keyword_sessions)

    report = print_audit_report(rewrite_audit, keyword_audit, graph_audit, sample_id)

    # Save report
    report_path = f"result/{args.data}/memory_audit_{args.model}_{args.file}.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as rf:
        json.dump(report, rf, ensure_ascii=False, indent=2, default=list)
    print(f"\nMemory audit report saved to {report_path}")


if __name__ == "__main__":
    main()
