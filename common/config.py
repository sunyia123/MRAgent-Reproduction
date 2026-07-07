import logging
import os
import argparse
from dotenv import load_dotenv
load_dotenv()  # read API key from .env
parser = argparse.ArgumentParser(description="Configure dataset and model parameters.")
parser.add_argument("--data", type=str, default="locomo", help="Dataset name, e.g., AR / LM / locomo")
parser.add_argument("--model", type=str, default="gemini", help="Model short name or explicit model id, e.g., deepseek / v4flash / qwen397 / gemini")
parser.add_argument("--file", type=str, default="0", help="Run/experiment tag appended to result filenames")
parser.add_argument("--sample", type=int, default=None, help="Sample id to run (e.g. 42). Omit to run all samples.")
parser.add_argument("--qu", type=int, default=0, help="Dataset name, e.g., AR / LM / locomo")
parser.add_argument("--re_model", type=str, default=None, help="Rewrite/keyword model short name or explicit model id")
parser.add_argument("--ca", type=int, default=1, help="LM category index: 0=multi-session,1=single-session-user,2=temporal-reasoning,3=single-session-preference,4=knowledge-update,5=single-session-assistant")
parser.add_argument("--lm_batch", type=int, default=1, help="LM: sessions merged per rewrite call. 1=per-session (key=session_i, compatible with existing files/per-session readers); >1=merged (key=session_first-session_last)")
parser.add_argument("--max_questions", type=int, default=None, help="Max questions to answer per sample (smoke: 3-5)")
parser.add_argument("--per_category", type=int, default=3, help="Stratified sampling: min questions per category (default 3)")
parser.add_argument("--total", type=int, default=15, help="Stratified sampling: total questions (default 15)")
parser.add_argument("--seed", type=int, default=42, help="Stratified sampling: random seed (default 42)")
parser.add_argument("--max_samples", type=int, default=None, help="Max samples to process for subset runs")
parser.add_argument("--sample_ids", type=str, default=None, help="Comma-separated sample ids, e.g. 26,30,41 or conv-26,conv-30")
parser.add_argument("--subset_manifest", type=str, default=None, help="Fixed subset manifest with sample_id and question_index records")

# parse_known_args (not parse_args) so importing this module under a foreign argv
# (pytest, notebooks, helper scripts) does not crash on unrecognized arguments.
args, _ = parser.parse_known_args()


def _resolve_model(name: str) -> str:
    aliases = {
        "gpt4.1mini": "openai/gpt-4.1-mini",
        "gpt4omini": "gpt-4o-mini-2024-07-18",
        "claude": "anthropic/claude-sonnet-4.5",
        "gpt4o": "openai/gpt-4o",
        "claude3.5": "anthropic/claude-3.5-haiku",
        "qwen": os.getenv("QWEN_MODEL_ID", "Qwen/Qwen3.5-397B-A17B"),
        "qwen397": "Qwen/Qwen3.5-397B-A17B",
        "gemini": "google/gemini-2.5-flash",
        "deepseek": os.getenv("DEEPSEEK_MODEL_ID", "deepseek-ai/DeepSeek-V4-Pro"),
        "v4pro": "deepseek-ai/DeepSeek-V4-Pro",
        "v4flash": "deepseek-ai/DeepSeek-V4-Flash",
    }
    return aliases.get(name, name)


MODEL = _resolve_model(args.model)
_siliconflow_prefixes = ("deepseek-ai/", "Qwen/")
_default_base_url = "https://api.siliconflow.cn/v1" if MODEL.startswith(_siliconflow_prefixes) else "https://openrouter.ai/api/v1"
LLM_BASE_URL = os.getenv("LLM_BASE_URL", _default_base_url)
EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", LLM_BASE_URL)
OPENROUTER_URL = LLM_BASE_URL  # backward compat: some modules reference OPENROUTER_URL
CHOOSE_MODEL = MODEL
MODEL_NAME = args.model  # short name (gemini/claude/...), used by the LM temporal method answer_question_with_time_lm
RE_MODEL = _resolve_model(args.re_model) if args.re_model else MODEL
API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
MODEL_SORT = MODEL #"anthropic/claude-sonnet-4.5"
K1=80                 # coarse retrieval breadth (embedding similarity)
K2=20                 # fine retrieval breadth (LLM re-ranking)
TAG_MAX=15            # select_key_tag: re-rank a key's tags only when it has more than this many
TAG_LIMIT=10         # select_key_tag: keep at most this many tags after re-ranking
TIME_EVENT_LIMIT=50  # answer_question_with_time: dense-time fast path threshold (locomo)
TOPIC_K=8            # select_topic: number of topic candidates
RERANK_LIMIT=20      # event_by_tag: re-rank events only when more than this many match
MAX_ROUNDS=8         # tool-calling loop: max assistant rounds
MAX_TOOL_CALLS=50    # tool-calling loop: safety cap on total tool calls
# --- Stage-specific max_tokens (env-configurable) ---
# DeepSeek-V4-Pro generates extensive reasoning_content; 4096 causes JSON truncation.
# See reports/model_diagnostics_20260701.md for evidence.
REWRITE_MAX_TOKENS = int(os.getenv("REWRITE_MAX_TOKENS", "16384"))
KEYWORD_MAX_TOKENS = int(os.getenv("KEYWORD_MAX_TOKENS", "16384"))
QA_MAX_TOKENS = int(os.getenv("QA_MAX_TOKENS", "8192"))
DEFAULT_MAX_TOKENS = REWRITE_MAX_TOKENS  # default for unclassified calls (was 4096)
API_TIMEOUT_SECONDS = float(os.getenv("API_TIMEOUT_SECONDS", "600"))
API_CLIENT_MAX_RETRIES = int(os.getenv("API_CLIENT_MAX_RETRIES", "2"))
API_CALL_MAX_RETRIES = int(os.getenv("API_CALL_MAX_RETRIES", "3"))
CHAT_TEXT_PARSE_MAX_ATTEMPTS = int(os.getenv("CHAT_TEXT_PARSE_MAX_ATTEMPTS", "3"))
ENABLE_JSON_REPAIR = os.getenv("ENABLE_JSON_REPAIR", "") == "1"  # strictly opt-in: set ENABLE_JSON_REPAIR=1 to enable
sample_id = args.sample
qu = args.qu
ca = args.ca
LM_REWRITE_BATCH = args.lm_batch  # sessions merged per LM rewrite call
MAX_QUESTIONS = args.max_questions  # limit questions per sample for smoke tests
STRATIFIED_PER_CATEGORY = args.per_category  # stratified sampling: min questions per category
STRATIFIED_TOTAL = args.total  # stratified sampling: total questions
STRATIFIED_SEED = args.seed  # stratified sampling: random seed
MAX_SAMPLES = args.max_samples  # subset sampling: max sample count
SAMPLE_IDS = []
if args.sample_ids:
    for _sid in args.sample_ids.split(","):
        _sid = _sid.strip()
        if not _sid:
            continue
        SAMPLE_IDS.append(_sid if _sid.startswith("conv-") else f"conv-{_sid}")
SUBSET_MANIFEST = args.subset_manifest

dataset = args.data
DATASET = dataset
datapath = f"data/dataset_{dataset}.json"
ADDITIONAL_TK = f"_{args.model}"#"_gpt4o-mini"
ADDITIONAL_EM = f"_{args.model}"#
ADDITIONAL_RE = f"_{args.model}_{args.file}" #"_gpt4o-mini"
base_dir_t = f"data/{{dataset}}/rewrite{ADDITIONAL_TK}/"
base_dir_k = f"data/{{dataset}}/keyword{ADDITIONAL_TK}/"
base_dir_emb = f"data/{{dataset}}/embedding/gpt{ADDITIONAL_EM}/"
# auto-create all output dirs so a fresh checkout runs without manual mkdir
os.makedirs(base_dir_t.format(dataset=dataset), exist_ok=True)      # data/<ds>/rewrite_<model>/
os.makedirs(base_dir_k.format(dataset=dataset), exist_ok=True)      # data/<ds>/keyword_<model>/
os.makedirs(base_dir_emb.format(dataset=dataset), exist_ok=True)    # data/<ds>/embedding/gpt_<model>/
os.makedirs(f"result/{dataset}", exist_ok=True)                    # prediction outputs
os.makedirs(f"log/{dataset}", exist_ok=True)                       # logs (also creates log/ for the run-level handler)

rewrite_template = f"data/{{dataset}}/rewrite{ADDITIONAL_TK}/{{sample_id}}_rewrite.json"
keyword_template = f"data/{{dataset}}/keyword{ADDITIONAL_TK}/{{sample_id}}_keyword.json"
embedding_template = f"data/{{dataset}}/embedding/gpt{ADDITIONAL_EM}/{{sample_id}}_embedding.pkl"
result_template = f"result/{{dataset}}/{{sample_id}}_result{ADDITIONAL_RE}.jsonl"
