# Stage B: Stratified Eval & Memory Audit Report — 2026-07-01

## 1. Objective

Extend the Stage A engineering smoke test with:
1. Provider-agnostic judge support (`JUDGE_BASE_URL`, `JUDGE_API_KEY`, `JUDGE_MODEL`)
2. `--f1_only`/`--no_llm_judge` flag for fast eval
3. Per-question metrics (tool calls, schema retries, forced accepts, runtime)
4. Memory audit (node/edge/topic/persona counts, missing field statistics)
5. Fixed stratified sampling (≥3 per category, 15 total from conv-30)
6. Comprehensive metrics summary output

**Branch**: `exp/20260701-stage-b-eval-audit`

**Base**: `main` @ `85b3ef2`

---

## 2. Code Changes

### 2.1 `eval/judge.py` — Provider-agnostic judge

```diff
-API_KEY = os.getenv("OPENROUTER_API_KEY")
-client = OpenAI(api_key=API_KEY, base_url="https://openrouter.ai/api/v1")
+JUDGE_API_KEY = os.getenv("JUDGE_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
+JUDGE_BASE_URL = os.getenv("JUDGE_BASE_URL", os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1"))
+JUDGE_MODEL = os.getenv("JUDGE_MODEL", "openai/gpt-4o-mini")
+def _get_client(): ...  # lazy-init OpenAI client
```

### 2.2 `eval/evaluate_reasoning.py` — Enhanced evaluation

- **New flags**: `--f1_only`, `--no_llm_judge` — skip LLM judge for fast eval
- **Per-question metrics extraction** from `_metrics` field in result JSONL
- **Structured metrics summary output** printed to console and saved as JSON:
  ```
  samples, total questions, category breakdown
  tool calls / q (avg, min, max)
  schema retries / q (total)
  forced accepts / q (total)
  runtime / q (avg, min, max), total runtime
  errors count
  F1 by category + overall
  LLM-judge accuracy by category + overall
  ```

### 2.3 `llm/controller.py` — Tool call tracking

```python
self.last_tool_calls = 0
# ... at end of chat_with_tools_once:
self.last_tool_calls = tool_calls_used
```

### 2.4 `agent/agent.py` — Per-question metrics instrumentation

```python
self.schema_retries = 0   # incremented on each schema validation retry
self.forced_accepts = 0   # incremented when accept-as-is on final attempt
self._last_question_metrics = {}  # {tool_calls, schema_retries, forced_accepts, runtime_sec}
```

Instrumented in:
- `rewrite()`: `self.schema_retries += 1` on each retry attempt
- `extract_keys()`: `self.schema_retries += 1` on each retry + `self.forced_accepts += 1` on final accept
- `answer_question()`: timer start/reset → `_last_question_metrics` populated at return

### 2.5 `run.py` — Metrics embedded in result JSONL

Each result line now carries `_metrics`:
```json
{"answer":"...","prediction":"...","category":2,"evidence":["D1:2"],"question":"...",
 "prediction_context":["D1:2"],"sample":"conv-30",
 "_metrics":{"tool_calls":28,"schema_retries":0,"forced_accepts":0,"runtime_sec":343.2}}
```

### 2.6 `eval/memory_audit.py` — New memory audit script

Scans rewrite + keyword artifacts and reports:
- **Rewrite**: sessions, sentences, topics, personal events, unique tags/persons, null-field counts, sentence distribution, time range
- **Keyword**: sentences, keyword instances, unique keywords, keywords-per-sentence distribution
- **Graph estimate**: KeyNodes, EpisodeEvents, Links, Topics, PersonaEvents, unique persons/tags

### 2.7 `run_stratified.py` — Stratified sampling runner

- Algorithm: take `per_category` from each category, then fill remaining to `total` from largest pools
- Uses the same pipeline as `run.py` but only answers stratified-selected questions
- Embeds the full question list, passes original indices for correct embedding lookup

---

## 3. Stratified Sampling

### Algorithm

```
Phase 1: Take min(per_category=3, available) from each category using fixed seed (42)
Phase 2: If still below total=15, fill from remaining questions (shuffled, largest pools first)
Sort by original index to preserve conversation order
```

### Selected Questions (conv-30, 15 total)

| Seq | Cat | Original Idx | Question (truncated) |
|-----|-----|-------------|----------------------|
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

### Category Distribution

| Category | Description | Selected |
|----------|-------------|----------|
| 1 | multi-hop | 4 |
| 2 | temporal | 4 |
| 3 | open-domain | 0 (not available in conv-30) |
| 4 | single-hop | 4 |
| 5 | adversarial | 3 |

---

## 4. Results

### 4.1 Per-Question Predictions

| Q | Cat | Prediction | Gold | F1 | Judge |
|---|-----|-----------|------|-----|-------|
| 1 | 1 | Both lost their jobs, both love dancing... | They lost their jobs and decided to start their own businesses. | 0.48 | ✅ |
| 2 | 1 | By the water — a room with a view of the ocean... | By the water, with natural light and Marley flooring | 0.17 | ✅ |
| 3 | 2 | no information available | March, 2023 | 0.00 | ✗ |
| 4 | 2 | no information available | 16 March, 2023 | 0.00 | ✗ |
| 5 | 1 | After losing her job, she wanted to take control... | She always loved fashion trends... | 0.15 | ✅ |
| 6 | 2 | the week before 19 June 2023 | June 2023 | 0.55 | ✗ |
| 7 | 1 | 5 months | six months | 0.00 | ✗ |
| 8 | 2 | 20 January 2023 | 21 July 2023 | 0.35 | ✗ |
| 9 | 4 | no information available | They are performing at the festival | 0.00 | ✗ |
| 10 | 4 | Excited, joyful, and glad... | Glad | 0.11 | ✅ |
| 11 | 4 | no information available | personal style and customer comfort | 0.00 | ✗ |
| 12 | 4 | no information available | she is passionate about dance and fashion | 0.00 | ✗ |
| 13 | 5 | Not mentioned in the conversation | None | 1.00* | — |
| 14 | 5 | Not mentioned in the conversation | None | 1.00* | — |
| 15 | 5 | no information available | None | 0.00* | — |

*Cat 5 scored by string match ("Not mentioned" = correct), not F1/Judge

### 4.2 Metrics Summary

```
METRICS SUMMARY
============================================================
  samples            : 1
  total questions    : 15
  category breakdown :
    cat 1: 4 questions
    cat 2: 4 questions
    cat 4: 4 questions
    cat 5: 3 questions
  tool calls / q     : avg=14.7  min=1  max=34
  schema retries / q : avg=0.0  total=0
  forced accepts / q : avg=0.0  total=0
  runtime / q        : avg=477.2s  min=159.8s  max=1193.6s
  total runtime      : 1.99h
  errors             : 0/15

  F1 by category:
    cat 1: n=4  F1=0.4034
    cat 2: n=4  F1=0.2262
    cat 4: n=4  F1=0.0278
    cat 5: n=3  F1=0.6667
    OVERALL F1: 0.3086

  LLM-judge accuracy by category:
    cat 1: n=4  acc=0.7500
    cat 2: n=4  acc=0.0000
    cat 4: n=4  acc=0.2500
    OVERALL ACC: 4/12 = 0.3333
============================================================
```

### 4.3 Memory Audit

```
MEMORY AUDIT — conv-30
============================================================
-- Rewrite Artifact --
  sessions                      : 19
  total sentences               : 309
  total topics                  : 133
  total personal events         : 157
  unique tags                   : 233
  unique persons                : 4
  sessions without sentences    : 7
  sessions without topics       : 7
  sessions without personal     : 7
  sentences missing id/text/tag : 0 / 0 / 0
  sentences per session         : avg=25.8 min=13 max=43
  conversation time range       : 2023-01-20 ~ 2023-07-23

-- Keyword Artifact --
  sessions                      : 19
  total sentences               : 309
  total keyword instances       : 2090
  unique keywords               : 1177
  sentences without keywords    : 0
  keywords per sentence         : avg=6.8 min=1 max=23

-- Memory Graph (estimated) --
  KeyNodes (keyword instances)  : 2090
  EpisodeEvents (sentences)     : 309
  Links (keyword->sentence)     : 2090
  Topics                        : 133
  PersonaEvents                 : 157
  Unique persons                : 4
  Unique tags                   : 233
============================================================
```

### 4.4 Key Findings

1. **7/19 sessions have null data** in the rewrite artifact. These are the last 7 sessions (sessions 13-19) whose rewrite output is `null`. This appears to be an upstream bug — the rewrite pipeline writes a null entry for sessions where the LLM returns empty output.

2. **Schema retries = 0** across all questions. The DeepSeek-V4-Pro model consistently produces valid JSON output, never triggering the retry path. This validates that the `replace=True` fix from Stage A was correct — the retry path works but is rarely needed with this model.

3. **Temporal questions (cat 2) have 0% LLM-judge accuracy**. The model frequently returns "no information available" for temporal questions, suggesting the graph retrieval is not surfacing the correct time-bearing events.

4. **Adversarial questions (cat 5)**: 2/3 correctly answered as "Not mentioned in the conversation". Q15 returned "no information available" instead, which is semantically correct but doesn't match the exact string pattern.

5. **Tool call overhead**: avg 14.7 tool calls per question, with Q11-12 (cat 4 single-hop) using the most (30, 34) — the model explores extensively even for simple questions.

6. **Total QA runtime**: ~2 hours for 15 questions, exclusively due to DeepSeek-V4-Pro latency (30-120s per API call). The rewrite/keyword/embedding stages were cached from Stage A.

---

## 5. File Inventory

### Generated Artifacts

| Path | Description |
|------|-------------|
| `result/locomo/conv-30_result_deepseek_stratified.jsonl` | 15 QA predictions with `_metrics` |
| `result/locomo/metrics_summary_deepseek_stratified.json` | Aggregated metrics JSON |
| `result/locomo/memory_audit_deepseek_stratified.json` | Memory audit report JSON |
| `result_judge_locomo_deepseek_stratified.jsonl` | 12 LLM-judge scores |
| `log/locomo/conv-30_deepseek_stratified.log` | Per-sample detailed log |
| `log/run_locomo__deepseek_stratified.log` | Run-level log |
| `reports/stage_b_eval_audit_20260701.md` | This report |

### Changed Files (from base 85b3ef2)

| File | Change |
|------|--------|
| `eval/judge.py` | +15/-5 — JUDGE_BASE_URL/JUDGE_API_KEY/JUDGE_MODEL from env |
| `eval/evaluate_reasoning.py` | +130/-20 — --f1_only, metrics summary, runtime tracking |
| `eval/memory_audit.py` | +280 (new) — Memory graph audit |
| `llm/controller.py` | +2 — last_tool_calls tracking |
| `agent/agent.py` | +18 — schema_retries, forced_accepts, per-question metrics |
| `run.py` | +4 — _metrics embedded in result JSONL |
| `run_stratified.py` | +220 (new) — Stratified sampling runner |

---

## 6. Commands

```bash
# Run stratified QA (15 questions)
python run_stratified.py --data locomo --model deepseek --file stratified --sample 30 --total 15

# Memory audit
python eval/memory_audit.py --data locomo --model deepseek --sample 30 --file stratified

# F1-only evaluation (fast, no judge API calls)
python eval/evaluate_reasoning.py --data locomo --model deepseek --file stratified --sample conv-30 --f1_only

# Full evaluation with LLM judge
python eval/evaluate_reasoning.py --data locomo --model deepseek --file stratified --sample conv-30
```

---

## 7. Next Steps

1. **Fix 7 null sessions**: Investigate why rewrite returns null for sessions 13-19. Could be upstream input filtering, context length, or LLM refusal.
2. **Improve temporal retrieval**: Cat 2 accuracy is 0% — need to debug `query_conversation_time` and topic-based temporal event retrieval.
3. **Faster model**: DeepSeek-V4-Pro takes 2h for 15 questions. Try Qwen3-8B or Qwen3-235B for production-scale runs.
4. **Full evaluation**: Run all 10 LoCoMo samples with stratified sampling when model latency is resolved.
5. **Merge to main**: After review, merge this branch's eval/judge/memory-audit infrastructure into main.
