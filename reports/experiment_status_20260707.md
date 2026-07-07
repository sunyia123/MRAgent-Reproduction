## Experiment Status — 2026-07-07

Key changes since `8746f67`:

- **v4flash alias** (`common/config.py`): added `--re_model v4flash` shortcut → `deepseek-ai/DeepSeek-V4-Flash`
- **RE_MODEL wiring** (`agent/agent.py`): rewrite & keyword now route through `config.RE_MODEL`; old paths ignored `--re_model`
- **.tmp checkpointing** (`run_stratified.py`): rewrite & keyword resume from `.tmp` partial files
- **chat_text JSON repair** (`llm/controller.py`): when model outputs plain text instead of JSON, calls a repair LLM to reformat into the correct JSON shape (detected from system prompt). Falls back to empty-but-format-correct placeholder if repair fails. Logs to `result/diagnostics/api_call_log.jsonl`.

---

## Current Phase: Medium Core Validation

**Subset:** `data/subsets/locomo10_100q_seed42.json` (100 questions, 10 samples × 10q each)

### Sample Cache Status as of 2026-07-07

| sample | rewrite | keyword | embedding | notes |
|---|:---:|:---:|:---:|---|
| conv-30 | ✅ 19/19 | ✅ | ✅ (23M) | complete; baseline caches from 2026-07-02 |
| conv-26 | ⚠️ 8/19 | ❌ | ❌ | 8 sessions completed via V4-Pro; sessions 9–17 skipped (API timeout, LGBTQ content); sessions 18–19 pending |
| conv-41 | ❌ | ❌ | ❌ | no rewrite (API blocked) |
| conv-42 | ❌ | ❌ | ❌ | partial `.tmp` from Explore-50 (2026-07-02) was deleted per "do not treat partial as complete" rule |
| conv-43 | ❌ | ❌ | ❌ | no rewrite |
| conv-44 | ❌ | ❌ | ❌ | no rewrite |
| conv-47 | ❌ | ❌ | ❌ | no rewrite |
| conv-48 | ❌ | ❌ | ❌ | no rewrite |
| conv-49 | ❌ | ❌ | ❌ | no rewrite |
| conv-50 | ❌ | ❌ | ❌ | no rewrite |

### conv-26 Rewrite Progress

`.tmp` file: `data/locomo/rewrite_deepseek/conv-26_rewrite.json.tmp` — 17 lines

- **sessions 1–8:** completed (V4-Pro, 2026-07-07 morning)
- **sessions 9–17:** skipped (marked with `conversation_time: skipped-api-timeout`)
- **sessions 18–19:** pending (clean content, no LGBTQ keywords)

⚠️ All rewrite API calls to SiliconFlow (`api.siliconflow.cn`) for V4-Flash large prompts began timing out consistently around 16:00 CST 2026-07-07, regardless of session content (D9–D18 all fail after 120–300 s with `httpx.ReadTimeout`). Small QA calls (V4-Flash, < 8K tokens) continue to succeed. Root cause unconfirmed; hypotheses: request-size throttling, cumulative-usage rate limiting, or provider-side degradation.

### MRAgent 100q Results

| sample | result file | rows |
|---|:---:|:---:|
| conv-30 | `result/locomo/conv-30_result_deepseek_mragent_100q.jsonl` | 10 |
| conv-26 | — | — |
| conv-41–50 | — | — |

Only 10 / 100 questions completed.

### Baseline Runs (conv-30 only — other samples blocked on cache)

| method | script | status |
|---|---|---|
| Standard RAG | `repro/run_standard_rag_baseline.py` | ✅ 10/10 rows (conv-30) |
| GraphRAG | `repro/run_graphrag_baseline.py` | ❌ not run |
| Oracle evidence QA | `repro/run_oracle_evidence_qa.py` | ❌ not run |

Finished RAG output: `result/locomo/conv-30_result_deepseek_rag_100q.jsonl`

---

## Previous Phase: conv-30 Diagnosis (completed 2026-07-06)

### conv-30 15q Stratified Results

MRAgent vs Standard RAG on matched 15 questions from conv-30 (see `reports/rag_vs_mragent_conv30_stratified_20260706.md`):

| category | n | MRAgent F1 | RAG F1 | MR evid. hit | RAG evid. hit |
|---|:---:|:---:|:---:|:---:|:---:|
| 1 (multi-hop) | 4 | 0.267 | 0.279 | 75% | 50% |
| 2 (temporal) | 4 | 0.786 | 0.000 | 75% | 100% |
| 4 (single-hop) | 4 | 0.117 | 0.153 | 75% | 75% |
| 5 (adversarial) | 3 | 1.000 | 1.000 | 100% | 100% |
| **OVERALL** | **15** | **0.512** | **0.315** | **80%** | **80%** |

**Key findings:**
- RAG scored 0.000 on all temporal questions (cat2) → flat retrieval cannot handle time reasoning
- Both methods had low single-hop F1 (0.12–0.15) due to evaluation mismatch (gold answers are minimal extractions, model answers are natural-language restatements)
- Q9 (image-dependent "dancers in the photo") had empty context in MRAgent after 31 tool calls — retrieval/tool-path failure, not graph construction failure
- Gold evidence coverage: 75/75 (100%) — graph construction is sound for conv-30

### Graph Snapshot (conv-30)

See `reports/graph_snapshot_conv30_20260706_server.md`.

- 1094 episode events, 1779 keywords, 213 topics, 4 personas
- 75/75 gold evidence turns present in graph (prefix-match correction applied)

### VLM-Enriched Rewrite Smoke (conv-30)

See `reports/vlm_enriched_rewrite_vlmrewrite_smoke_20260703_094151.md`.

- 10 VLM calls: 3 OK (Flickr CDN reachable), 7 error 20040 (URL not downloadable)
- D1 (dance studio): rewrite sentence count -23%, semantically richer tags

---

## Reports Committed

| file | description |
|---|---|
| `reports/rag_vs_mragent_conv30_stratified_20260706.md` | MRAgent vs RAG matched-15 contrast |
| `reports/graph_snapshot_conv30_20260706_server.md` | conv-30 graph snapshot + gold evidence coverage |
| `reports/graph_snapshot_manifest_conv30_20260706.md` | server execution manifest |
| `reports/badcase_pack_conv30_stratified_20260706_server_review.md` | badcase analysis with graph evidence (Q9–Q12) |
| `reports/diagnose_conv26_D9_20260707.md` | conv-26 D9 session diagnosis (NOT the largest; 2651 chars, 17 turns) |
| `reports/badcase_chat_text_parse_20260707.md` | chat_text JSON parse failure history |

---

## Known Issues

1. **Rewrite API timeout** (blocker for 9/10 samples): SiliconFlow V4-Flash rewrite calls timeout with `httpx.ReadTimeout` after ~120 s. Small QA calls succeed. Needs provider-side investigation or alternative endpoint.
2. **chat_text plain-text response** (fixed): model sometimes returns "a few years ago" / "They both have a passion for dance" instead of JSON. Repair LLM added + logs to `api_call_log.jsonl`.
3. **select_key_tag NoneType crash** (fixed): downstream `.items()` call on None when `chat_text` returned None. Prevented by repair fallback.
4. **RAG script used chat_text for plain-text QA** (fixed in `aadcf7e`): switched to `chat_with_tool` with direct text extraction.
5. **conv-42 partial .tmp deleted** (intentional): 27/29 sessions from Explore-50 run were incomplete; deleted per guidelines.
