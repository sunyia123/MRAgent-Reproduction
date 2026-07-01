# Stage B: Eval & Audit Infrastructure + Clean Regeneration Attempt — 2026-07-01

## 1. Objective

Per the reproduction audit report (`reports/reproduction_audit_20260701.md`) and the intermediate artifact checklist (`docs/intermediate_artifact_checklist.md`), fix Stage A shortcomings:

1. Make `eval/judge.py` provider-configurable (JUDGE_BASE_URL, JUDGE_API_KEY, JUDGE_MODEL)
2. Add `--f1_only` / `--no_llm_judge` to `evaluate_reasoning.py`
3. Output structured metrics summary per run
4. Output memory audit summary
5. Implement fixed stratified sampling (≥3 per category)
6. Clean regeneration of conv-30 rewrite/keyword/embedding to fix null sessions
7. Fix judge file append pollution

**Branch**: `exp/20260701-stage-b-eval-audit` (rebased on `origin/main` @ `34fbe8c`)

**Base commit (previous round)**: `5c43c85` — Stage B initial implementation

---

## 2. Code Changes (from base `34fbe8c` / `origin/main`)

### 2.1 `eval/judge.py` — Provider-agnostic judge (+15/-5)

```python
JUDGE_API_KEY = os.getenv("JUDGE_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
JUDGE_BASE_URL = os.getenv("JUDGE_BASE_URL", os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1"))
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "openai/gpt-4o-mini")
```

Lazy-initialized client via `_get_client()`. Defaults preserved for OpenRouter backward compat.

### 2.2 `eval/evaluate_reasoning.py` — Enhanced evaluation (+210/-27)

- **New flags**: `--f1_only`, `--no_llm_judge` — skip LLM judge for fast eval
- **Judge file dedup**: Old `result_judge_*.jsonl` deleted before each run (prevents append pollution)
- **Structured metrics summary** printed to console AND saved as JSON:
  - samples, total questions, category breakdown
  - tool calls/q (avg/min/max), schema retries total, forced accepts total
  - runtime/q (avg/min/max), total runtime
  - errors count
  - F1 by category + overall
  - LLM-judge by category + overall (if not --f1_only)
- **Metrics extraction** from `_metrics` field in result JSONL rows

### 2.3 `eval/memory_audit.py` — New file (+295)

Scans rewrite + keyword artifacts:
- **Rewrite**: sessions, sentences, topics, personal events, tags, persons, null-field counts, sentence distribution, time range
- **Keyword**: sentences, keyword instances, unique keywords, keywords-per-sentence distribution
- **Graph estimate**: KeyNodes, EpisodeEvents, Links, Topics, PersonaEvents, unique counts

### 2.4 `llm/controller.py` — Tool call tracking (+3)

```python
self.last_tool_calls = 0  # per-question tool call count
```

### 2.5 `agent/agent.py` — Per-question metrics instrumentation (+21)

```python
self.schema_retries = 0    # schema validation retry counter
self.forced_accepts = 0    # forced accept on final attempt
self._last_question_metrics = {}  # {tool_calls, schema_retries, forced_accepts, runtime_sec}
```

Instrumented at:
- `rewrite()`: `self.schema_retries += 1` per retry
- `extract_keys()`: `self.schema_retries += 1` per retry + `self.forced_accepts += 1` on final accept
- `answer_question()`: timer + metrics reset + `_last_question_metrics` populated

### 2.6 `run.py` — Metrics in result JSONL (+3)

Each result line carries `_metrics`:
```json
{"_metrics": {"tool_calls": 28, "schema_retries": 0, "forced_accepts": 0, "runtime_sec": 343.2}, ...}
```

### 2.7 `run_stratified.py` — Stratified sampling runner (+267, new)

- CLI args: `--per_category` (default 3), `--total` (default 15), `--seed` (default 42)
- Algorithm: Phase 1 — take `per_category` from each category; Phase 2 — fill to `total` from remaining shuffled pools
- Uses existing pipeline (rewrite→keyword→embedding→store→QA), answers only stratified-selected questions
- Correct embedding index mapping via original question indices

### 2.8 `common/config.py` — Stratified args (+6)

```python
parser.add_argument("--per_category", type=int, default=3)
parser.add_argument("--total", type=int, default=15)
parser.add_argument("--seed", type=int, default=42)
STRATIFIED_PER_CATEGORY = args.per_category
STRATIFIED_TOTAL = args.total
STRATIFIED_SEED = args.seed
```

---

## 3. Clean Regeneration Attempt

### 3.1 Command

```bash
python run_stratified.py --data locomo --model deepseek --file stratified \
    --sample 30 --per_category 3 --total 15 --seed 42
```

### 3.2 Timeline

| Time | Phase | API Calls (cumulative) | Status |
|------|-------|----------------------|--------|
| 16:00 | Start | 0 | Caches deleted, fresh run |
| 16:00–21:45 | Rewrite | ~19 (with retries) | 17/19 sessions written |
| 21:45–22:05 | Keyword | ~55 (with retries) | 0 output lines produced |
| 22:05 | Interrupted | 55 | Stopped — impractical latency |

### 3.3 Rewrite Artifact (partial)

| Metric | Value |
|--------|-------|
| Sessions written | 17 / 19 |
| Sessions with data | 10 |
| Sessions NULL | 7 (sessions 4, 6, 8, 10, 14, 15, 17) |
| Sessions MISSING | 2 (sessions 18, 19 never written) |
| Total sentences | 252 |
| Total topics | 113 |
| Total personal events | 138 |
| Unique tags | 185 |
| Unique persons | 7 |
| NULL failure rate | **41%** (7/17) |

### 3.4 Comparison: Old vs New NULL Sessions

| Run | NULL Sessions | Overlap |
|-----|--------------|---------|
| Old (Stage A cache, buggy) | 2, 3, 6, 8, 9, 17, 18 | — |
| New (clean regeneration) | 4, 6, 8, 10, 14, 15, 17 | 6, 8, 17 |

Only 3 sessions consistently fail (6, 8, 17). The other 4 are different each run,
confirming this is **non-deterministic model output** rather than cached data corruption.

### 3.5 Keyword Extraction

- 35+ API calls beyond rewrite (55 total - 19 rewrite ≈ 36 keyword)
- 0 lines written to `conv-30_keyword.json`
- Schema validation failures triggered extensive retries (3 retries × 5–10 min each)
- Never completed before interruption

### 3.6 Root Cause Analysis

The null sessions CANNOT be fixed by cache regeneration because:

1. **All 7 null sessions contain normal text dialogue** (not image-only). The model simply produces
   `{"sentence": null, "topics": null, "personal_sentences": null}` for these sessions.
2. **Non-deterministic**: different sessions fail each run, suggesting marginal JSON validity.
3. **Keyword schema retries are excessive**: DeepSeek-V4-Pro cannot consistently produce valid
   keyword JSON that passes `check_key_json()` validation, causing 2–3× API call inflation.
4. **Latency is prohibitive**: 5–10 min per API call × 38 sessions × 1.5× retry multiplier ≈
   5+ hours just for rewrite+keyword, with QA still ahead.

**Conclusion: DeepSeek-V4-Pro is not a viable model for this pipeline's schema requirements.**

---

## 4. Stratified Sampling Design

### Algorithm

```
Phase 1: min(per_category=3, available) from each category (seed=42)
Phase 2: fill to total=15 from remaining shuffled pools
```

### Selected Questions (conv-30, seed=42)

| Seq | Cat | OrigIdx | Question |
|-----|-----|---------|----------|
| 1 | 1 | 3 | What do Jon and Gina both have in common? |
| 2 | 1 | 5 | What Jon thinks the ideal dance studio should look like? |
| 3 | 2 | 12 | When did Jon start to go to the gym? |
| 4 | 2 | 13 | When did Gina open her online clothing store? |
| 5 | 1 | 17 | Why did Gina decide to start her own clothing store? |
| 6 | 2 | 28 | When was Jon in Rome? |
| 7 | 1 | 31 | How long did it take for Jon to open his studio? |
| 8 | 2 | 36 | When did Jon and Gina decide to collaborate to create dance content? |
| 9 | 4 | 43 | What do the dancers in the photo represent? |
| 10 | 4 | 45 | What is Jon's attitude towards being part of the dance festival? |
| 11 | 4 | 51 | What made Gina choose the furniture and decor for her store? |
| 12 | 4 | 59 | Why did Gina combine her clothing business with dance? |
| 13 | 5 | 98 | Where is Jon's fashion internship? |
| 14 | 5 | 102 | What did Jon make a limited edition line of? |
| 15 | 5 | 104 | What plans does Gina have after receiving advice at the networking event? |

Category distribution: cat 1=4, cat 2=4, cat 3=0 (not in conv-30), cat 4=4, cat 5=3

---

## 5. Memory Audit (partial rewrite)

```
MEMORY AUDIT — conv-30
============================================================
-- Rewrite Artifact --
  sessions                      : 17 (should be 19)
  total sentences               : 252
  total topics                  : 113
  total personal events         : 138
  unique tags                   : 185
  unique persons                : 7
  sessions without sentences    : 7   ← CHECKLIST FAIL (must be 0)
  sessions without topics       : 7
  sessions without personal     : 7
  sentences missing id          : 0   ← PASS
  sentences missing text        : 0   ← PASS
  sentences missing tag         : 0   ← PASS
  sentences per session         : avg=25.2 min=13 max=44
  conversation time range       : 2023-01-20 ~ 2023-06-21

-- Keyword Artifact --
  NOT GENERATED (0 sessions, 0 keywords)

-- Embedding Artifact --
  NOT GENERATED

-- Memory Graph (estimated) --
  KeyNodes                      : 0 (no keyword data)
  EpisodeEvents                 : 252
  Topics                        : 113
  PersonaEvents                 : 138
  Unique persons                : 7
  Unique tags                   : 185
============================================================
```

### Checklist Assessment

| Criterion | Required | Actual | Status |
|-----------|----------|--------|--------|
| `sessions_without_sentences` | 0 | 7 | ❌ FAIL |
| `sentences_without_id` | 0 | 0 | ✅ |
| `sentences_without_text` | 0 | 0 | ✅ |
| `sentences_without_tag` | 0 | 0 | ✅ |
| keyword `total_sentences` == rewrite `total_sentences` | 252 | 0 | ❌ FAIL |
| `sentences_without_keywords` | 0 | N/A | ❌ FAIL |
| `forced_accepts_total` | 0 or explained | N/A | — |
| Judge file dedup | yes | yes | ✅ |
| Log free of failed runs | yes | yes | ✅ |

---

## 6. Artifact Manifest

Generated at `result/locomo/artifact_manifest_20260701.json`.

Key entries:

```json
{
  "run_id": "20260701-stage-b-eval-audit",
  "status": "interrupted",
  "blockers": [
    "DeepSeek-V4-Pro produces NULL output for 7/17 rewrite sessions (41% failure rate)",
    "Keyword extraction has extensive schema retries (35+ API calls, 0 output)",
    "Model latency makes full pipeline impractical (6+ hours, incomplete)",
    "CHECKLIST FAIL: sessions_without_sentences=7 (must be 0)"
  ],
  "merge_status": "blocked"
}
```

### Remote Paths, Sizes, Checksums

| Artifact | Path | Size | SHA256 | Status |
|----------|------|------|--------|--------|
| Rewrite | `data/locomo/rewrite_deepseek/conv-30_rewrite.json` | 87 KB | `781bf13cea95...` (see manifest) | Partial (17/19) |
| Keyword | — | — | — | Not generated |
| Embedding | — | — | — | Not generated |
| Result | — | — | — | Not generated |
| Log | `log/locomo/conv-30_deepseek_stratified.log` | — | committed | Clean (1 run, 0 err) |
| Memory Audit | `result/locomo/memory_audit_deepseek_stratified.json` | — | committed | 7 null sessions |
| Manifest | `result/locomo/artifact_manifest_20260701.json` | — | committed | This file |

---

## 7. File Inventory

### Committed (in this branch)

| File | Change | Description |
|------|--------|-------------|
| `eval/judge.py` | modified | Provider-agnostic judge |
| `eval/evaluate_reasoning.py` | modified | --f1_only, metrics, judge dedup |
| `eval/memory_audit.py` | new | Memory graph audit |
| `common/config.py` | modified | --per_category, --total, --seed |
| `agent/agent.py` | modified | Metrics instrumentation |
| `llm/controller.py` | modified | Tool call tracking |
| `run.py` | modified | _metrics in result JSONL |
| `run_stratified.py` | new | Stratified sampling runner |
| `reports/stage_b_eval_audit_20260701.md` | new | This report |
| `log/locomo/conv-30_deepseek_stratified.log` | new | Clean single-run log |
| `result/locomo/memory_audit_deepseek_stratified.json` | new | Memory audit |
| `result/locomo/artifact_manifest_20260701.json` | new | Artifact manifest |

### Not Committed (by design)

- `.env` — contains API keys, in `.gitignore`
- `data/locomo/rewrite_deepseek/conv-30_rewrite.json` — large, in `.gitignore`
- `data/locomo/keyword_deepseek/` — not generated
- `data/locomo/embedding/gpt_deepseek/` — not generated
- `result/locomo/conv-30_result_deepseek_stratified.jsonl` — not generated

---

## 8. Previous Round Results (from `5c43c85`, now superseded)

The first round of this branch ran conv-30 stratified QA using the old (buggy) Stage A rewrite cache:

| Metric | Value |
|--------|-------|
| Questions | 15 (stratified) |
| F1 overall | 0.3086 |
| LLM-judge overall | 0.3333 |
| Tool calls/q | avg 14.7 |
| Schema retries | 0 (cached rewrite/keyword) |
| Runtime | 1.99h (QA only) |
| Errors | 0/15 |

These metrics are now SUPERSEDED because:
1. The rewrite had 7/19 null sessions from the buggy Stage A cache
2. The null sessions contaminate memory construction
3. Clean regeneration with DeepSeek-V4-Pro could not produce a valid rewrite

---

## 9. Conclusions

### What Was Achieved

1. ✅ All 7 code infrastructure items from the audit report are implemented
2. ✅ Branch rebased on latest main, audit report preserved
3. ✅ Stratified sampling works correctly (verified with seed=42)
4. ✅ Memory audit infrastructure works (detects null sessions)
5. ✅ Judge file append pollution fixed
6. ✅ Clean log maintained (single run, no errors mixed in)

### What Was NOT Achieved

1. ❌ `sessions_without_sentences=0` — DeepSeek-V4-Pro produces 41% null output
2. ❌ keyword/embedding/QA never reached — model too slow and unreliable
3. ❌ Checklist minimum acceptance criteria not met
4. ❌ No valid result JSONL or metrics to evaluate

### Blockers to Merging

1. **Model capability**: DeepSeek-V4-Pro is fundamentally unsuitable for this pipeline.
   Must switch to a model that reliably produces valid JSON output.
2. **Latency**: Even with a reliable model, rewrite+keyword for 19 sessions is ~3–6 hours.
   Need a faster model for production-scale runs.

### Recommended Next Steps

1. **Switch chat model** to `Qwen/Qwen3-235B-A22B` (SiliconFlow) or `google/gemini-2.5-flash` (OpenRouter)
   for reliable JSON output and faster latency
2. **Regenerate rewrite** from scratch with the new model, verify `sessions_without_sentences=0`
3. **Complete keyword + embedding + QA** with clean rewrite
4. **Run full evaluation** with F1 + LLM judge
5. **Document model differences** vs. paper settings per audit report requirements
6. **Merge to main** only after all checklist items pass

---

## 10. Commands Reference

```bash
# Stratified run
python run_stratified.py --data locomo --model deepseek --file stratified \
    --sample 30 --per_category 3 --total 15 --seed 42

# Memory audit
python eval/memory_audit.py --data locomo --model deepseek --sample 30 --file stratified

# F1-only evaluation (no judge API needed)
python eval/evaluate_reasoning.py --data locomo --model deepseek --file stratified \
    --sample conv-30 --f1_only

# Full evaluation with LLM judge
python eval/evaluate_reasoning.py --data locomo --model deepseek --file stratified \
    --sample conv-30
```
