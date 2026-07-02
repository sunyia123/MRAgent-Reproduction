#!/usr/bin/env python3
"""
Stratified-sampling run: run the full MRAgent pipeline on ONE sample but answer only a
fixed stratified subset of questions (≥3 per category).

Usage:
  python run_stratified.py --data locomo --model deepseek --file stratified \
      --sample 30 --per_category 3 --total 15
"""

import os
import sys
import json
import re
import logging
import random
import shutil
from pathlib import Path
from collections import defaultdict

from llm.controller import LLM
from memory.controller import MemoryController
from memory.system import MemorySystem
from agent.agent import Agent
from common import config
from data.get_data import get_data
from data.embed_rewrite import embed_sample
from common.logging_utils import per_sample_log

logger = logging.getLogger(__name__)


# --- Cache validation ---

def _validate_rewrite_cache(rewrite_path: str, expected_sessions: int) -> tuple:
    """Check rewrite cache completeness. Returns (valid: bool, reason: str)."""
    if not os.path.exists(rewrite_path):
        return False, "file not found"
    try:
        sessions = []
        with open(rewrite_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    sessions.append(json.loads(line))
        if len(sessions) != expected_sessions:
            return False, f"session count mismatch: {len(sessions)} lines vs {expected_sessions} expected"
        null_count = 0
        schema_failures = 0
        for obj in sessions:
            for sid, data in obj.items():
                if data is None:
                    null_count += 1
                elif isinstance(data, dict):
                    if data.get("sentence") is None:
                        null_count += 1
                    elif not isinstance(data.get("sentence"), list):
                        schema_failures += 1
        if null_count > 0:
            return False, f"{null_count} sessions have null sentence data"
        if schema_failures > 0:
            return False, f"{schema_failures} sessions have invalid sentence structure"
        return True, "ok"
    except Exception as e:
        return False, f"validation error: {e}"


def _validate_keyword_cache(keyword_path: str, expected_sentence_count: int) -> tuple:
    """Check keyword cache completeness. Returns (valid: bool, reason: str)."""
    if not os.path.exists(keyword_path):
        return False, "file not found"
    try:
        total = 0
        with open(keyword_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    obj = json.loads(line)
                    sentences = obj.get("sentence", [])
                    total += len(sentences) if isinstance(sentences, list) else 0
        if total != expected_sentence_count:
            return False, f"keyword sentence count {total} != rewrite sentence count {expected_sentence_count}"
        return True, "ok"
    except Exception as e:
        return False, f"validation error: {e}"


def stratified_sample(question_list: dict, sample_id: str, per_category: int = 3, total: int = 15,
                       seed: int = 42) -> list:
    """
    Select a fixed stratified subset of questions.

    Strategy:
      1. Group questions by category.
      2. Take min(per_category, available) from each category.
      3. If we still haven't reached `total`, fill from remaining questions
         (largest categories first) until we hit the target.
    """
    rng = random.Random(seed)
    qa_list = question_list.get(sample_id, [])
    if not qa_list:
        return []

    by_cat = defaultdict(list)
    for i, qa in enumerate(qa_list):
        by_cat[qa.get("category", "?")].append((i, qa))

    selected = {}  # index -> qa

    # Phase 1: take per_category from each category
    for cat, items in sorted(by_cat.items(), key=lambda x: str(x[0])):
        take = min(per_category, len(items))
        chosen = rng.sample(items, take)
        for idx, qa in chosen:
            selected[idx] = qa
        logger.info(f"  stratified: cat {cat} → {take}/{len(items)} selected")

    # Phase 2: if we need more to hit total, fill from largest remaining pools
    if total and len(selected) < total:
        remaining = []
        for cat, items in by_cat.items():
            for idx, qa in items:
                if idx not in selected:
                    remaining.append((idx, qa))
        rng.shuffle(remaining)
        needed = total - len(selected)
        for idx, qa in remaining[:needed]:
            selected[idx] = qa
        logger.info(f"  stratified: filled {needed} more to reach total={total}")

    # Reconstruct in original order, returning (original_index, qa) pairs
    result = [(i, selected[i]) for i in sorted(selected)]
    return result


def answer_questions(dataset, agent, selected_qa, sample_id, memory, result_path, question_embeddings=None):
    """Answer only the selected questions. selected_qa is list of (original_index, qa_dict) tuples."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    logger.info(f"---------------{sample_id} ({len(selected_qa)} stratified questions)-------------------")
    memory_system = agent.memory

    # resumable
    done_count = 0
    if os.path.exists(result_path):
        with open(result_path, encoding="utf-8") as _f:
            done_count = sum(1 for line in _f if line.strip())
    if done_count >= len(selected_qa):
        logger.info(f"All {len(selected_qa)} questions already done, skipping.")
        return
    if done_count > 0:
        logger.info(f"Resuming from question {done_count + 1} (already done: {done_count})")

    remaining = selected_qa[done_count:]

    def _run_one(seq, orig_idx, qa):
        category = qa.get("category")
        question = Agent.question_format(dataset, qa)
        evidence_labels = qa.get("evidence")

        q_llm = LLM()
        q_mc = MemoryController(memory_system, q_llm)
        q_agent = Agent(q_llm, memory_system, q_mc)

        try:
            q_emb = question_embeddings[orig_idx] if question_embeddings is not None else None
            results, evidence_support = q_agent.answer_question(
                question, category, q_emb)
        except Exception as e:
            logger.error(f"question{seq} (orig idx {orig_idx}) failed: {e}", exc_info=True)
            return seq, {
                "answer": qa.get("answer"), "prediction": "ERROR", "category": category,
                "evidence": evidence_labels, "question": qa.get("question"),
                "prediction_context": [], "sample": sample_id,
                "_metrics": {"tool_calls": 0, "schema_retries": 0, "forced_accepts": 0, "runtime_sec": 0},
            }

        _metrics = getattr(q_agent, "_last_question_metrics", {})
        evaluation = {
            "answer": qa.get("answer"), "prediction": results, "category": category,
            "evidence": evidence_labels, "question": qa.get("question"),
            "prediction_context": evidence_support, "sample": sample_id,
            "_metrics": _metrics,
        }
        return seq, evaluation

    MAX_WORKERS = 10
    results_dict = {}
    # remaining items are (orig_idx, qa) pairs; assign sequence numbers 1..N
    indexed_remaining = [(seq + 1, orig_idx, qa) for seq, (orig_idx, qa) in enumerate(remaining)]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_seq = {executor.submit(_run_one, seq, orig_idx, qa): seq
                         for seq, orig_idx, qa in indexed_remaining}
        for fut in as_completed(future_to_seq):
            seq = future_to_seq[fut]
            try:
                results_dict[seq] = fut.result()
            except Exception as e:
                logger.error(f"question{seq} future raised: {e}", exc_info=True)
                results_dict[seq] = None

    for seq, orig_idx, qa in indexed_remaining:
        result_tuple = results_dict.get(seq)
        if result_tuple is None:
            continue
        seq_ret, evaluation = result_tuple
        logger.info(f"---------------question{seq_ret} (cat {qa.get('category')})-------------------")
        with open(result_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(evaluation, ensure_ascii=False, default=list) + "\n")


def main():
    import pickle as _pickle

    dataset = config.dataset
    datapath = config.datapath
    conversation_list, question_list, raw_conversation_list, raw_text_list = get_data(dataset, datapath)

    allowed_sample_ids = set(getattr(config, "SAMPLE_IDS", []) or [])
    processed_samples = 0
    for sample_id, sample in conversation_list.items():
        # sample filter
        if config.sample_id is not None:
            num = int(sample_id.split('-')[1])
            if num != config.sample_id:
                continue
        if allowed_sample_ids and sample_id not in allowed_sample_ids:
            continue
        if config.MAX_SAMPLES is not None and processed_samples >= config.MAX_SAMPLES:
            logger.info(f"Reached --max_samples={config.MAX_SAMPLES}; stopping subset run.")
            break

        # stratified sampling
        selected_qa = stratified_sample(
            question_list, sample_id,
            per_category=getattr(config, 'STRATIFIED_PER_CATEGORY', 3),
            total=getattr(config, 'STRATIFIED_TOTAL', 15),
            seed=getattr(config, 'STRATIFIED_SEED', 42),
        )
        logger.info(f"Stratified selection: {len(selected_qa)} questions (sample {sample_id})")
        cat_counts = defaultdict(int)
        for orig_idx, qa in selected_qa:
            cat_counts[qa.get("category", "?")] += 1
        for cat in sorted(cat_counts, key=str):
            logger.info(f"  cat {cat}: {cat_counts[cat]} questions")

        with per_sample_log(sample_id=sample_id, dataset=dataset):
            logger.info(f"=== Start processing sample {sample_id} (stratified) ===")

            llm = LLM()
            memory_system = MemorySystem()
            memory_controller = MemoryController(memory_system, llm)
            agent = Agent(llm, memory_system, memory_controller)

            # --- Pipeline stages with cache validation ---
            expected_sessions = len(sample)
            rewrite_path = config.rewrite_template.format(dataset=dataset, sample_id=sample_id)
            rewrite_tmp = rewrite_path + ".tmp"

            rewrite_valid, rewrite_reason = _validate_rewrite_cache(rewrite_path, expected_sessions)
            if rewrite_valid:
                logger.info(f"Rewrite cache valid ({rewrite_reason}), skipping.")
            else:
                logger.info(f"Rewrite cache invalid ({rewrite_reason}), regenerating...")
                if os.path.exists(rewrite_tmp):
                    os.remove(rewrite_tmp)
                # Write to temp file, validate, then atomically rename
                agent.rewrite_sample(sample, rewrite_tmp)
                tmp_valid, tmp_reason = _validate_rewrite_cache(rewrite_tmp, expected_sessions)
                if tmp_valid:
                    shutil.move(rewrite_tmp, rewrite_path)
                    logger.info(f"Rewrite regenerated and validated: {rewrite_path}")
                else:
                    logger.error(f"Rewrite regeneration FAILED: {tmp_reason}. Keeping temp file: {rewrite_tmp}")
                    # Continue with temp file for debugging but do NOT replace cache

            keyword_path = config.keyword_template.format(dataset=dataset, sample_id=sample_id)
            keyword_tmp = keyword_path + ".tmp"
            # Count rewrite sentences for keyword validation
            rewrite_sentence_count = 0
            with open(rewrite_path, encoding="utf-8") as _rf:
                for _line in _rf:
                    _line = _line.strip()
                    if _line:
                        _obj = json.loads(_line)
                        for _sid, _data in _obj.items():
                            if _data and isinstance(_data, dict):
                                _s = _data.get("sentence")
                                if isinstance(_s, list):
                                    rewrite_sentence_count += len(_s)

            keyword_valid, keyword_reason = _validate_keyword_cache(keyword_path, rewrite_sentence_count)
            if keyword_valid:
                logger.info(f"Keyword cache valid ({keyword_reason}), skipping.")
            else:
                logger.info(f"Keyword cache invalid ({keyword_reason}), regenerating...")
                if os.path.exists(keyword_tmp):
                    os.remove(keyword_tmp)
                agent.extract_keyword_sample(keyword_tmp, rewrite_path)
                tmp_valid, tmp_reason = _validate_keyword_cache(keyword_tmp, rewrite_sentence_count)
                if tmp_valid:
                    shutil.move(keyword_tmp, keyword_path)
                    logger.info(f"Keyword regenerated and validated: {keyword_path}")
                else:
                    logger.error(f"Keyword regeneration FAILED: {tmp_reason}. Keeping temp file: {keyword_tmp}")

            embedding_path = config.embedding_template.format(dataset=dataset, sample_id=sample_id)
            if not os.path.exists(embedding_path):
                embed_sample(question_list[sample_id], rewrite_path, embedding_path)
            else:
                logger.info(f"Embedding for sample {sample_id} already exists, skipping.")

            raw_text = raw_text_list[sample_id]
            id2emb, question_embeddings_all, topic_id_list, topic_embeddings = _get_conv_embeddings(embedding_path)
            agent.store_raw_text(raw_text, id2emb, topic_id_list, topic_embeddings)
            agent.store_keyword(keyword_path, rewrite_path)

            # build per-question embedding list: map sequential position -> embedding
            # (the full all_embs list is indexed by original question position)
            all_embs = question_embeddings_all
            # In answer_questions, _run_one receives (seq, orig_idx, qa) and accesses question_embeddings[orig_idx]
            # so pass all_embs (full list) not selected_question_embs
            result_path = config.result_template.format(dataset=dataset, sample_id=sample_id)
            answer_questions(dataset, agent, selected_qa, sample_id, memory_system,
                             result_path, all_embs)
            processed_samples += 1


def _get_conv_embeddings(embedding_path):
    import pickle
    database = pickle.load(open(embedding_path, 'rb'))
    embeddings = database.get("embeddings")
    sentence_id = database.get("sentence_id")
    topic_embeddings = database.get("topic")
    topic_id = database.get("topic_list")
    question_embeddings = database.get("question_embeddings")
    id2emb = {i: embeddings[r] for r, i in enumerate(sentence_id)}
    return id2emb, question_embeddings, topic_id, topic_embeddings


def log_config(config_module):
    logging.info("========== CONFIGURATION ==========")
    for name in dir(config_module):
        if not re.match(r'^[A-Z0-9_]+$', name):
            continue
        if any(kw in name.lower() for kw in ["key", "url", "secret", "password"]):
            continue
        value = getattr(config_module, name)
        logging.info(f"{name} = {value}")
    logging.info("===================================")


if __name__ == "__main__":
    global_file_handler = logging.FileHandler(
        f"log/run_{config.DATASET}_{config.ADDITIONAL_TK}_{config.ADDITIONAL_RE}.log",
        encoding="utf-8"
    )
    stream_handler = logging.StreamHandler()
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[global_file_handler, stream_handler]
    )
    logging.info("=== Program start (stratified) ===")
    log_config(config)
    root_logger = logging.getLogger()
    root_logger.removeHandler(global_file_handler)
    global_file_handler.close()
    main()
