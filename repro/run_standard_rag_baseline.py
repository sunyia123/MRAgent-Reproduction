#!/usr/bin/env python3
"""
Standard RAG baseline: retrieve top-k rewrite sentences by embedding similarity,
send as context + question to the QA model, write prediction JSONL compatible
with eval/evaluate_reasoning.py.

No graph traversal, no tool calling, no multi-round reasoning — plain RAG.

Usage:
  # Smoke
  python repro/run_standard_rag_baseline.py --data locomo --model deepseek \
    --file rag_smoke --sample_ids 30 --top_k 20

  # Explore-50
  python repro/run_standard_rag_baseline.py --data locomo --model deepseek \
    --file rag_explore50 --sample_ids 30,42,44,48,50 --top_k 20

  # Full LoCoMo-10
  python repro/run_standard_rag_baseline.py --data locomo --model deepseek \
    --file rag_locomo10 --top_k 20
"""

import os, sys, json, pickle, argparse, logging, time, re
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.controller import LLM
from common import config
from data.get_data import get_data
from common.logging_utils import per_sample_log

logger = logging.getLogger("rag_baseline")

RAG_SYSTEM_PROMPT = """Answer the question based ONLY on the provided conversation context.
If the context does not contain enough information, answer "no information available".
Give a concise answer — just the key fact, entity, date, or phrase asked for."""


def cosine_similarity(a, b):
    """Cosine similarity between two vectors (both should be numpy arrays or lists)."""
    a = np.asarray(a).flatten()
    b = np.asarray(b).flatten()
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10)


def load_rewrite_sentences(rewrite_path: str) -> List[Dict]:
    """Load rewrite JSONL, return flat list of {sentence_id, text, origin}."""
    sentences = []
    if not os.path.exists(rewrite_path):
        return sentences
    with open(rewrite_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            for sid, data in obj.items():
                if data is None or not isinstance(data, dict):
                    continue
                sent_list = data.get("sentence")
                if not isinstance(sent_list, list):
                    continue
                for s in sent_list:
                    sentences.append({
                        "sentence_id": s.get("id", "?"),
                        "text": s.get("text", ""),
                        "origin": s.get("origin", "?"),
                        "tag": s.get("tag", ""),
                    })
    return sentences


def load_embeddings(embedding_path: str) -> dict:
    """Load the embedding pkl and return id2emb and question_embeddings."""
    if not os.path.exists(embedding_path):
        return {"id2emb": {}, "question_embeddings": None}
    db = pickle.load(open(embedding_path, "rb"))
    embeddings = db.get("embeddings", [])
    sentence_ids = db.get("sentence_id", [])
    id2emb = {sid: embeddings[i] for i, sid in enumerate(sentence_ids) if i < len(embeddings)}
    return {
        "id2emb": id2emb,
        "question_embeddings": db.get("question_embeddings"),
        "topic_embeddings": db.get("topic"),
        "topic_list": db.get("topic_list"),
        "sentence_ids": sentence_ids,
    }


def retrieve_top_k(question_emb, sentences: List[Dict], id2emb: dict, top_k: int = 20) -> List[Dict]:
    """Retrieve top-k sentences by embedding cosine similarity."""
    if question_emb is None:
        return sentences[:top_k]

    scored = []
    for sent in sentences:
        emb = id2emb.get(sent["sentence_id"])
        if emb is None:
            continue
        sim = cosine_similarity(question_emb, emb)
        scored.append((sim, sent))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:top_k]]


def build_context(top_sentences: List[Dict]) -> str:
    """Build a context string from top-k sentences."""
    lines = []
    for s in top_sentences:
        lines.append(f"[{s['sentence_id']}] ({s['tag']}) {s['text']}")
    return "\n".join(lines)


def answer_question_rag(llm: LLM, question: str, context: str) -> str:
    """Simple single-turn RAG QA."""
    user_msg = f"Question: {question}\n\nContext:\n{context}\n\nAnswer:"
    try:
        result = llm.chat_text(
            messages=[
                {"role": "system", "content": RAG_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=config.QA_MAX_TOKENS,
        )
        if isinstance(result, dict):
            return result.get("answer", str(result))
        return str(result or "no information available")
    except Exception as e:
        logger.error(f"RAG QA failed: {e}")
        return "ERROR"


def run_sample(sample_id: str, qa_list: list, rewrite_path: str, embedding_path: str,
               llm: LLM, result_path: str, top_k: int):
    """Run RAG QA for all questions of one sample."""
    logger.info(f"--- {sample_id} ({len(qa_list)} questions, top_k={top_k}) ---")

    # Load rewrite sentences and embeddings
    sentences = load_rewrite_sentences(rewrite_path)
    emb_data = load_embeddings(embedding_path)
    id2emb = emb_data["id2emb"]
    question_embs = emb_data.get("question_embeddings") or []

    logger.info(f"  Loaded {len(sentences)} sentences, {len(id2emb)} embeddings")

    # Resumable
    done = 0
    if os.path.exists(result_path):
        with open(result_path, encoding="utf-8") as f:
            done = sum(1 for l in f if l.strip())
    if done >= len(qa_list):
        logger.info(f"  All {len(qa_list)} done, skipping.")
        return

    for i, qa in enumerate(qa_list):
        if i < done:
            continue

        category = qa.get("category")
        question = qa.get("question")
        gold = qa.get("answer")
        evidence = qa.get("evidence", [])

        # For adversarial (cat 5): format the question with choices
        if category == 5:
            import random
            q_text = question + " Select the correct answer: {} or {}. "
            adv_ans = qa.get("adversarial_answer", "")
            if random.random() < 0.5:
                q_text = q_text.format("Not mentioned in the conversation", adv_ans)
            else:
                q_text = q_text.format(adv_ans, "Not mentioned in the conversation")
        else:
            q_text = question

        # Get question embedding
        q_emb = question_embs[i] if i < len(question_embs) else None

        # Retrieve top-k
        top_sents = retrieve_top_k(q_emb, sentences, id2emb, top_k)
        context = build_context(top_sents)

        # Answer
        _t0 = time.time()
        prediction = answer_question_rag(llm, q_text, context)
        runtime = round(time.time() - _t0, 2)

        # Collect prediction_context (origin IDs)
        pred_ctx = list(set(s["origin"] for s in top_sents))

        evaluation = {
            "answer": gold,
            "prediction": prediction,
            "category": category,
            "evidence": evidence,
            "question": question,
            "prediction_context": pred_ctx,
            "sample": sample_id,
            "_metrics": {
                "tool_calls": 0,
                "schema_retries": 0,
                "forced_accepts": 0,
                "runtime_sec": runtime,
                "rag_top_k": top_k,
            },
        }
        with open(result_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(evaluation, ensure_ascii=False, default=list) + "\n")

        logger.info(f"  Q{i+1}/{len(qa_list)} cat={category} pred={str(prediction)[:60]}")


def main():
    parser = argparse.ArgumentParser(description="Standard RAG baseline")
    parser.add_argument("--data", default="locomo")
    parser.add_argument("--model", default="deepseek")
    parser.add_argument("--file", default="rag_baseline")
    parser.add_argument("--sample_ids", default=None, help="Comma-separated, e.g. 30,42,44")
    parser.add_argument("--top_k", type=int, default=20)
    parser.add_argument("--max_samples", type=int, default=None)
    args = parser.parse_args()

    dataset = args.data
    datapath = f"data/dataset_{dataset}.json"

    conversation_list, question_list, _, _ = get_data(dataset, datapath)

    # Filter samples
    if args.sample_ids:
        target_ids = set()
        for sid in args.sample_ids.split(","):
            sid = sid.strip()
            target_ids.add(sid if sid.startswith("conv-") else f"conv-{sid}")
        sample_keys = [k for k in conversation_list if k in target_ids]
    else:
        sample_keys = list(conversation_list.keys())

    if args.max_samples:
        sample_keys = sample_keys[:args.max_samples]

    logger.info(f"RAG baseline: {len(sample_keys)} samples, top_k={args.top_k}")

    result_dir = f"result/{dataset}"
    os.makedirs(result_dir, exist_ok=True)

    for sample_id in sample_keys:
        rewrite_path = config.rewrite_template.format(dataset=dataset, sample_id=sample_id)
        embedding_path = config.embedding_template.format(dataset=dataset, sample_id=sample_id)
        result_path = config.result_template.format(dataset=dataset, sample_id=sample_id).replace(
            f"result_{config.ADDITIONAL_RE}", f"result_{args.model}_{args.file}")

        if not os.path.exists(rewrite_path):
            logger.warning(f"  {sample_id}: rewrite not found at {rewrite_path}, skipping")
            continue
        if not os.path.exists(embedding_path):
            logger.warning(f"  {sample_id}: embedding not found, skipping")
            continue

        qa_list = question_list.get(sample_id, [])
        with per_sample_log(sample_id=sample_id, dataset=dataset):
            llm = LLM()
            run_sample(sample_id, qa_list, rewrite_path, embedding_path,
                       llm, result_path, args.top_k)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    main()
