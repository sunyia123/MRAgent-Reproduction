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
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from llm.controller import LLM
from memory.controller import MemoryController
from memory.system import MemorySystem
from agent.agent import Agent
from common import config
from data.get_data import get_data
from data.embed_rewrite import embed_sample
from common.logging_utils import add_run_file_handler, per_sample_log

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
        skipped_count = 0
        empty_sentence_count = 0
        for obj in sessions:
            for sid, data in obj.items():
                if data is None:
                    null_count += 1
                elif isinstance(data, dict):
                    if str(data.get("conversation_time", "")).startswith("skipped"):
                        skipped_count += 1
                    if data.get("sentence") is None:
                        null_count += 1
                    elif not isinstance(data.get("sentence"), list):
                        schema_failures += 1
                    elif len(data.get("sentence")) == 0:
                        empty_sentence_count += 1
                else:
                    schema_failures += 1
        if null_count > 0:
            return False, f"{null_count} sessions have null sentence data"
        if skipped_count > 0:
            return False, f"{skipped_count} sessions are skip markers"
        if empty_sentence_count > 0:
            return False, f"{empty_sentence_count} sessions have empty sentence lists"
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


def _rewrite_partial_progress(rewrite_path: str, expected_session_ids: list) -> tuple:
    """Return resumable rewrite line count from a partial jsonl cache."""
    if not os.path.exists(rewrite_path):
        return 0, "file not found"
    completed = 0
    stop_reason = ""
    try:
        with open(rewrite_path, encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    stop_reason = f"line {line_no}: blank line"
                    break
                obj = json.loads(line)
                if not isinstance(obj, dict) or len(obj) != 1:
                    stop_reason = f"line {line_no}: expected one-key object"
                    break
                session_id, data = next(iter(obj.items()))
                if completed >= len(expected_session_ids):
                    stop_reason = f"line {line_no}: more rows than expected sessions"
                    break
                if session_id != expected_session_ids[completed]:
                    stop_reason = f"line {line_no}: session id {session_id!r} != expected {expected_session_ids[completed]!r}"
                    break
                if not isinstance(data, dict) or not isinstance(data.get("sentence"), list):
                    stop_reason = f"line {line_no}: sentence is missing or not a list"
                    break
                if str(data.get("conversation_time", "")).startswith("skipped"):
                    stop_reason = f"line {line_no}: skip marker"
                    break
                if len(data.get("sentence")) == 0:
                    stop_reason = f"line {line_no}: empty sentence list"
                    break
                completed += 1
    except Exception as e:
        return completed, f"stopped at {completed}: {e}"
    suffix = f"; stopped: {stop_reason}" if stop_reason else ""
    return completed, f"{completed}/{len(expected_session_ids)} sessions complete{suffix}"


def _keyword_partial_progress(keyword_path: str) -> tuple:
    """Return resumable keyword line count from a partial jsonl cache."""
    if not os.path.exists(keyword_path):
        return 0, "file not found"
    completed = 0
    stop_reason = ""
    try:
        with open(keyword_path, encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    stop_reason = f"line {line_no}: blank line"
                    break
                obj = json.loads(line)
                if obj is None:
                    completed += 1
                    continue
                if not isinstance(obj, dict) or not isinstance(obj.get("sentence"), list):
                    stop_reason = f"line {line_no}: invalid keyword schema"
                    break
                completed += 1
    except Exception as e:
        return completed, f"stopped at {completed}: {e}"
    suffix = f"; stopped: {stop_reason}" if stop_reason else ""
    return completed, f"{completed} keyword rows complete{suffix}"


def _truncate_jsonl_prefix(path: str, keep_lines: int) -> str:
    """Keep only the first keep_lines non-empty JSONL records."""
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        lines = [line for line in f if line.strip()]
    if len(lines) <= keep_lines:
        return ""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}.bak_before_truncate_{stamp}_{os.getpid()}"
    shutil.copyfile(path, backup_path)
    logger.warning(f"Backed up {path} to {backup_path} before truncating {len(lines)} -> {keep_lines} lines.")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines[:keep_lines])
    return backup_path


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


def load_subset_manifest(path: str) -> dict:
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    by_sample = defaultdict(list)
    for record in obj.get("records", []):
        sample_id = record.get("sample_id")
        qidx = record.get("question_index")
        if sample_id is None or qidx is None:
            continue
        by_sample[sample_id].append(int(qidx))
    return {sample_id: sorted(set(indices)) for sample_id, indices in by_sample.items()}


def subset_from_manifest(question_list: dict, sample_id: str, subset_by_sample: dict) -> list:
    qa_list = question_list.get(sample_id, [])
    result = []
    for qidx in subset_by_sample.get(sample_id, []):
        if 0 <= qidx < len(qa_list):
            result.append((qidx, qa_list[qidx]))
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
    subset_by_sample = load_subset_manifest(config.SUBSET_MANIFEST) if config.SUBSET_MANIFEST else None

    allowed_sample_ids = set(getattr(config, "SAMPLE_IDS", []) or [])
    if subset_by_sample:
        allowed_sample_ids = set(subset_by_sample) if not allowed_sample_ids else allowed_sample_ids & set(subset_by_sample)
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

        # fixed manifest takes precedence over local random stratification
        if subset_by_sample:
            selected_qa = subset_from_manifest(question_list, sample_id, subset_by_sample)
        else:
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
            expected_session_ids = list(sample.keys())

            rewrite_valid, rewrite_reason = _validate_rewrite_cache(rewrite_path, expected_sessions)
            logger.info(
                "Stage=rewrite sample=%s expected_sessions=%s rewrite_path=%s rewrite_tmp=%s valid=%s reason=%s",
                sample_id, expected_sessions, rewrite_path, rewrite_tmp, rewrite_valid, rewrite_reason
            )
            if rewrite_valid:
                logger.info(f"Rewrite cache valid ({rewrite_reason}), skipping.")
            else:
                logger.info(f"Rewrite cache invalid ({rewrite_reason}), regenerating/resuming...")
                if not os.path.exists(rewrite_tmp) and os.path.exists(rewrite_path):
                    shutil.copyfile(rewrite_path, rewrite_tmp)
                    logger.info(f"Copied invalid rewrite cache to resumable temp file: {rewrite_tmp}")
                completed, progress_reason = _rewrite_partial_progress(rewrite_tmp, expected_session_ids)
                logger.info(f"Rewrite resume progress: {progress_reason}")
                _truncate_jsonl_prefix(rewrite_tmp, completed)
                # Append only missing sessions. agent.rewrite_sample uses 1-based session_id_ref.
                agent.rewrite_sample(sample, rewrite_tmp, session_id_ref=completed + 1)
                tmp_valid, tmp_reason = _validate_rewrite_cache(rewrite_tmp, expected_sessions)
                if tmp_valid:
                    shutil.move(rewrite_tmp, rewrite_path)
                    logger.info(f"Rewrite regenerated and validated: {rewrite_path}")
                else:
                    logger.error(f"Rewrite regeneration FAILED: {tmp_reason}. Keeping temp file: {rewrite_tmp}")
                    logger.error("Skipping this sample until rewrite cache is complete.")
                    continue

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
            logger.info(
                "Stage=keyword sample=%s expected_sentence_count=%s keyword_path=%s keyword_tmp=%s valid=%s reason=%s",
                sample_id, rewrite_sentence_count, keyword_path, keyword_tmp, keyword_valid, keyword_reason
            )
            if keyword_valid:
                logger.info(f"Keyword cache valid ({keyword_reason}), skipping.")
            else:
                logger.info(f"Keyword cache invalid ({keyword_reason}), regenerating/resuming...")
                if not os.path.exists(keyword_tmp) and os.path.exists(keyword_path):
                    shutil.copyfile(keyword_path, keyword_tmp)
                    logger.info(f"Copied invalid keyword cache to resumable temp file: {keyword_tmp}")
                completed, progress_reason = _keyword_partial_progress(keyword_tmp)
                logger.info(f"Keyword resume progress: {progress_reason}")
                _truncate_jsonl_prefix(keyword_tmp, completed)
                agent.extract_keyword_sample(keyword_tmp, rewrite_path, ref_id=completed)
                tmp_valid, tmp_reason = _validate_keyword_cache(keyword_tmp, rewrite_sentence_count)
                if tmp_valid:
                    shutil.move(keyword_tmp, keyword_path)
                    logger.info(f"Keyword regenerated and validated: {keyword_path}")
                else:
                    logger.error(f"Keyword regeneration FAILED: {tmp_reason}. Keeping temp file: {keyword_tmp}")
                    logger.error("Skipping this sample until keyword cache is complete.")
                    continue

            embedding_path = config.embedding_template.format(dataset=dataset, sample_id=sample_id)
            logger.info("Stage=embedding sample=%s embedding_path=%s exists=%s", sample_id, embedding_path, os.path.exists(embedding_path))
            if not os.path.exists(embedding_path):
                embed_sample(question_list[sample_id], rewrite_path, embedding_path)
            else:
                logger.info(f"Embedding for sample {sample_id} already exists, skipping.")

            raw_text = raw_text_list[sample_id]
            id2emb, question_embeddings_all, topic_id_list, topic_embeddings = _get_conv_embeddings(embedding_path)
            logger.info(
                "Stage=store sample=%s event_embeddings=%s topic_ids=%s question_embeddings=%s",
                sample_id,
                len(id2emb) if id2emb is not None else 0,
                len(topic_id_list) if topic_id_list is not None else 0,
                len(question_embeddings_all) if question_embeddings_all is not None else 0,
            )
            agent.store_raw_text(raw_text, id2emb, topic_id_list, topic_embeddings)
            agent.store_keyword(keyword_path, rewrite_path)

            # build per-question embedding list: map sequential position -> embedding
            # (the full all_embs list is indexed by original question position)
            all_embs = question_embeddings_all
            # In answer_questions, _run_one receives (seq, orig_idx, qa) and accesses question_embeddings[orig_idx]
            # so pass all_embs (full list) not selected_question_embs
            result_path = config.result_template.format(dataset=dataset, sample_id=sample_id)
            logger.info("Stage=qa sample=%s selected_questions=%s result_path=%s", sample_id, len(selected_qa), result_path)
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


def warn_suspicious_run_config(config_module):
    if getattr(config_module, "SAMPLE_IDS", None) and not getattr(config_module, "SUBSET_MANIFEST", None):
        logging.warning(
            "--sample_ids was provided without --subset_manifest; this will use local stratified sampling, "
            "not the fixed 100q manifest."
        )
    if getattr(config_module, "SAMPLE_IDS", None) and getattr(config_module.args, "file", "0") == "0":
        logging.warning(
            "--file is still the default '0'; result files will be written as *_result_<model>_0.jsonl, "
            "not *_mragent_100q.jsonl."
        )
    if getattr(config_module.args, "model", "") == "deepseek" and "api.siliconflow.cn" not in getattr(config_module, "LLM_BASE_URL", ""):
        logging.warning(
            "--model deepseek is active but LLM_BASE_URL is not SiliconFlow. Check .env or use an explicit provider URL."
        )


if __name__ == "__main__":
    stream_handler = logging.StreamHandler()
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[stream_handler]
    )
    _, run_log = add_run_file_handler(dataset=config.DATASET)
    logging.info("=== Program start (stratified) ===")
    logging.info("Run log path: %s", run_log)
    log_config(config)
    warn_suspicious_run_config(config)
    try:
        main()
    finally:
        logging.info("=== Program end (stratified) ===")
