# global_methods.py

import os
import time
from typing import List, Sequence, Optional, Any

# OpenAI Python SDK v1.x
# pip install openai>=1.0.0
from openai import OpenAI
from openai._exceptions import OpenAIError, RateLimitError, APIStatusError


# embedding via OpenRouter (proxies /embeddings; text-embedding-3-large returns 3072-d)
from dotenv import load_dotenv
load_dotenv()  # read API key from .env
EMBED_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-large")
os.environ["OPENAI_API_KEY"] = EMBED_API_KEY or ""  # for set_openai_key() validation

# --- Embedding diagnostic logging ---
import json as _json
import logging as _logging
_EMBED_DIAG_ENABLED = os.getenv("DIAGNOSTIC_LOG", "0") == "1"
_EMBED_DIAG_PATH = os.path.join("result", "diagnostics", "raw_embedding_calls.jsonl")
if _EMBED_DIAG_ENABLED:
    os.makedirs(os.path.dirname(_EMBED_DIAG_PATH), exist_ok=True)
    _emb_diag_log = _logging.getLogger("embed.diag")
    _emb_diag_log.setLevel(_logging.DEBUG)
    _emb_diag_log.propagate = False
    _emb_diag_fh = _logging.FileHandler(_EMBED_DIAG_PATH, encoding="utf-8")
    _emb_diag_fh.setFormatter(_logging.Formatter('%(message)s'))
    _emb_diag_log.addHandler(_emb_diag_fh)


def _emb_diag_record(model: str, batch_size: int, total_inputs: int, resp: Any = None, error: str = None, latency_s: float = 0.0):
    if not _EMBED_DIAG_ENABLED:
        return
    try:
        rec = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "model": model,
            "batch_size": batch_size,
            "total_inputs": total_inputs,
            "latency_s": round(latency_s, 3),
        }
        if resp is not None:
            rec["response"] = {
                "embedding_count": len(resp.data) if hasattr(resp, 'data') else 0,
                "embedding_dim": len(resp.data[0].embedding) if hasattr(resp, 'data') and resp.data else None,
                "usage_prompt_tokens": getattr(getattr(resp, 'usage', None), 'prompt_tokens', None),
                "usage_total_tokens": getattr(getattr(resp, 'usage', None), 'total_tokens', None),
            }
        if error:
            rec["error"] = str(error)[:500]
        _emb_diag_log.info(_json.dumps(rec, ensure_ascii=False, default=str))
    except Exception:
        pass

# optional helper
def set_openai_key(key_env: str = "OPENAI_API_KEY") -> None:
    """
    Read the OpenAI key from the environment; you may also set os.environ[key_env] beforehand.
    """

    api_key = os.getenv(key_env, "").strip()
    if not api_key:
        raise RuntimeError(
            f"{key_env} is empty. Please export your OpenAI API key, e.g. "
            f'export {key_env}="sk-..."'
        )


def get_openai_embedding(
    texts: Sequence[str],
    model: str = None,
    *,
    batch_size: int = 96,
    max_retries: int = 5,
    initial_backoff: float = 1.0,
    timeout: Optional[float] = 60.0,
) -> List[List[float]]:
    """
    Embed a batch of texts; returns a 2D array aligned 1:1 with the input (list of list of float).

    Args:
    ----
    texts : Sequence[str]
        List of texts to encode; sent in batches, order preserved.
    model : str
        OpenAI embedding model name, common choices:
        - "text-embedding-3-small"   # 1536-d, cheaper
        - "text-embedding-3-large"   # 3072-d, higher quality
    batch_size : int
        Items per request batch; tune to your rate/memory/timeout.
    max_retries : int
        Max retries per batch (exponential backoff).
    initial_backoff : float
        Initial retry wait in seconds, doubled each time.
    timeout : Optional[float]
        Per-request HTTP timeout in seconds; None means no limit.

    Returns:
    ----
    List[List[float]]
        Embeddings of shape (len(texts), dim).
    """
    if model is None:
        model = EMBED_MODEL
    if not isinstance(texts, (list, tuple)):
        raise TypeError("texts must be a list/tuple of strings")

    # preprocess: replace newlines with spaces to avoid length/format issues
    clean_texts = [("" if t is None else str(t)).replace("\n", " ").strip() for t in texts]

    client = OpenAI(timeout=timeout, api_key=EMBED_API_KEY, base_url=EMBED_BASE_URL)

    embeddings: List[List[float]] = []
    n = len(clean_texts)
    if n == 0:
        return embeddings

    # request in batches, preserving order
    for start in range(0, n, batch_size):
        batch = clean_texts[start : start + batch_size]

        # exponential-backoff retry
        attempt = 0
        backoff = initial_backoff
        while True:
            try:
                resp = client.embeddings.create(model=model, input=batch)
                # resp.data order matches the input
                for item in resp.data:
                    embeddings.append(item.embedding)
                break  # success; exit the retry loop

            except (RateLimitError, APIStatusError, OpenAIError, TimeoutError) as e:
                attempt += 1
                if attempt > max_retries:
                    # return partial results and the error position for the caller to debug
                    raise RuntimeError(
                        f"OpenAI embedding request failed after {max_retries} retries "
                        f"at batch [{start}:{start+len(batch)}]: {e}"
                    ) from e
                # wait then retry
                time.sleep(backoff)
                backoff *= 2.0  # exponential backoff

    # assert length match (defensive)
    if len(embeddings) != n:
        raise RuntimeError(
            f"Embedding count mismatch: got {len(embeddings)} for {n} inputs."
        )
    return embeddings
