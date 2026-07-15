# External Baseline Gate10 Report

Generated: 2026-07-15

## 1. Run Identity

| | A-Mem | Mem0 |
|---|---|---|
| **RUN_ID** | `gate10_amem_20260715_120449` | `gate10_mem0_20260715_172157` |
| **Branch/Commit** | `codex/locomo-500q-ablation` @ `b506262` | same |
| **External commit** | `WujiangXu/A-mem@0c8039f` | `mem0ai/mem0@ccbe586` |
| **License** | MIT | Apache-2.0 |
| **Manifest** | `locomo_conv26_10q_core_seed42.json` | same |
| **Started** | 2026-07-15 12:05 CST | 2026-07-15 17:22 CST |
| **Ended** | 2026-07-15 17:20 CST | 2026-07-15 ~18:27 CST |
| **Wall-clock** | ~5h 15min | ~1h 05min |

## 2. Model Routing

| Component | Resolved Model |
|---|---|
| Memory/Rewrite LLM | `deepseek-ai/DeepSeek-V4-Flash` |
| Embedding | `Qwen/Qwen3-Embedding-4B` (2560-d) |
| QA LLM | `deepseek-ai/DeepSeek-V4-Flash` |
| **enable_thinking** | **false** (verified in all raw API calls) |
| API base URL | `https://api.siliconflow.cn/v1` |

### enable_thinking Evidence

- A-Mem: 1566/1566 requests contain `"extra_body":{"enable_thinking":false}`, all responses `"reasoning_content":null`
- Mem0: 419/419 requests contain `"extra_body":{"enable_thinking":false}`, all responses verified

## 3. Ingestion Audit

### A-Mem

| Metric | Value |
|---|---|
| Turns ingested | **419/419** ✓ |
| Memory nodes created | **419** |
| Embedding vectors | **419** |
| evo_cnt | 412 |
| Memory model | `deepseek-ai/DeepSeek-V4-Flash` |
| Checkpoint | `data/locomo/external_cache/amem/conv-26_state.pkl` (10.3 MB) |
| API calls | 1566 started, 1566 success, **0 errors** |

### Mem0

| Metric | Value |
|---|---|
| Turns ingested | **419/419** ✓ |
| SQLite history rows | 402 (compressed memories) |
| Qdrant vectors | 9.5 MB on disk |
| Memory model | `deepseek-ai/DeepSeek-V4-Flash` |
| Checkpoint | `data/locomo/external_cache/mem0/v4flash-qwen4b-v1/conv-26/` |
| API calls | 419 started, 419 success, **0 errors** |

## 4. Results

### A-Mem (10/10)

| Q# | Cat | Question | Gold | Prediction |
|---|---|---|---|---|
| 1 | 2 | When did Caroline go to the LGBTQ support group? | 7 May 2023 | **7 May, 2023** |
| 12 | 1 | Where did Caroline move from 4 years ago? | Sweden | no information available |
| 31 | 3 | Would Melanie be considered a member of the LGBTQ community? | Likely no... | no information available |
| 53 | 1 | What are Melanie's pets' names? | Oliver, Luna, Bailey | **Luna and Oliver** |
| 57 | 1 | What symbols are important to Caroline? | Rainbow flag, transgender symbol | A necklace... |
| 65 | 3 | Would Melanie likely enjoy "The Four Seasons"? | Yes | **Yes** |
| 69 | 2 | How long has Melanie been practicing art? | Since 2016 | no information available |
| 83 | 4 | What did the charity race raise awareness for? | mental health | **mental health** |
| 102 | 4 | Did Melanie make the black and white bowl? | Yes | **Yes** |
| 149 | 4 | What was Melanie's reaction to children enjoying Grand Canyon? | She was happy and thankful | **She was thankful...** |

### Mem0 (10/10)

| Q# | Cat | Question | Gold | Prediction |
|---|---|---|---|---|
| 1 | 2 | When did Caroline go to the LGBTQ support group? | 7 May 2023 | **July 14, 2026 and May 7, 2023** |
| 12 | 1 | Where did Caroline move from 4 years ago? | Sweden | no information available |
| 31 | 3 | Would Melanie be considered a member of the LGBTQ community? | Likely no... | no information available |
| 53 | 1 | What are Melanie's pets' names? | Oliver, Luna, Bailey | **Luna, Oliver, and Bailey** |
| 57 | 1 | What symbols are important to Caroline? | Rainbow flag, transgender symbol | Her necklace... |
| 65 | 3 | Would Melanie likely enjoy "The Four Seasons"? | Yes | **Yes** |
| 69 | 2 | How long has Melanie been practicing art? | Since 2016 | **7 years** |
| 83 | 4 | What did the charity race raise awareness for? | mental health | **mental health** |
| 102 | 4 | Did Melanie make the black and white bowl? | Yes | No information available |
| 149 | 4 | What was Melanie's reaction to children enjoying Grand Canyon? | She was happy and thankful | no information available |

## 5. Validation

| | A-Mem | Mem0 |
|---|---|---|
| Rows | 10 | 10 |
| Unique manifest keys | 10/10 | 10/10 |
| Missing | 0 | 0 |
| Duplicates | 0 | 0 |
| Invalid rows | 0 | 0 |
| **Status** | **PASS** | **PASS** |

## 6. Raw API Log Summary

| | A-Mem | Mem0 |
|---|---|---|
| Total entries | 3,132 | 838 |
| started | 1,566 | 419 |
| success | 1,566 | 419 |
| error | **0** | **0** |
| unmatched | 0 | 0 |
| Models observed | `deepseek-ai/DeepSeek-V4-Flash` only | `deepseek-ai/DeepSeek-V4-Flash` only |

## 7. Retrieval Case Examples

### 7.1 Temporal: Q01 — When did Caroline go to the LGBTQ support group?

**Gold:** 7 May 2023 | **Evidence:** [D1:3]

**A-Mem** (prediction: 7 May, 2023 ✓):
- Retrieval query: `Caroline, LGBTQ support group, when, date, attended`
- Retrieved 30 memories; key hit: `[D1:3]` ("I went to a LGBTQ support group yesterday and it was so powerful", session_date=1:56 pm on 8 May, 2023)
- Correctly inferred "yesterday" → 7 May 2023 from the source date

**Mem0** (prediction: July 14, 2026 and May 7, 2023 ⚠):
- Top memory fabricated date: "Caroline attended an LGBTQ support group on **July 14, 2026**" (score 0.87)
- The source D1:3 has session_date=1:56 pm on 8 May, 2023 — Mem0 hallucinated the year 2026
- Second memory also hallucinated: "July 14, 2026" — both from summer 2026 (current date)

### 7.2 Multi-hop: Q53 — What are Melanie's pets' names?

**Gold:** Oliver, Luna, Bailey | **Evidence:** [D13:4, D7:18]

**A-Mem** (prediction: Luna and Oliver — missing Bailey):
- Retrieved 30 memories across multiple sessions
- Key hits: `[D7:18]` "Luna and Oliver!" from 12 July, `[D13:4]` "Bailey" from 23 Aug
- Missed Bailey (later session, lower retrieval rank)

**Mem0** (prediction: Luna, Oliver, and Bailey ✓):
- Top memory correctly compressed: "Melanie's dog is named Luna and her cat is named Oliver as of July 12, 2023"
- Inferred from multiple sources into a coherent compressed fact
- Retrieved Bailey from later session context

### 7.3 Single-hop: Q83 — What did the charity race raise awareness for?

**Gold:** mental health | **Evidence:** [D2:2]

**A-Mem** (prediction: mental health ✓):
- Retrieval query expanded to: `charity race, raise awareness, cause, fundraising event, awareness campaign`
- Key hit: `[D2:2]` "That charity race sounds great, Mel! Making a difference & raising awareness for mental health..."
- Direct single-source answer, correctly retrieved

**Mem0** (prediction: mental health ✓):
- Top memory: "Melanie ran a charity race for mental health on May 20, 2023..."
- Note: Mem0 added a date (May 20, 2023) not in the original — mild temporal elaboration

## 8. Key Observations

1. **Mem0 temporal hallucination**: For Q01, Mem0 fabricated "July 14, 2026" (likely from system date leakage). This is a known risk with LLM-based memory compression without anchor-date enforcement.
2. **A-Mem retrieval noise**: Many irrelevant LGBTQ-related memories retrieved for Q01 (charity race question), showing weak keyword separation.
3. **Multi-hop advantage Mem0**: Mem0's compressed memory representation correctly fused information from multiple sessions (Bailey appeared in a later session than Luna/Oliver).
4. **Both methods miss "Sweden"**: Q12 ("Where did Caroline move from 4 years ago?") — both fail. The temporal offset computation is too complex for passive retrieval.

## 9. File Inventory

| File | Path |
|---|---|
| A-Mem result | `result/locomo/conv-26_result_deepseek_amem_gate10_qflash.jsonl` |
| Mem0 result | `result/locomo/conv-26_result_deepseek_mem0_gate10_qflash.jsonl` |
| A-Mem sanitized | `reports/external_baselines/sanitized_amem_gate10.jsonl` |
| Mem0 sanitized | `reports/external_baselines/sanitized_mem0_gate10.jsonl` |
| A-Mem provenance | `reports/external_baselines/amem_gate10_qflash_provenance.md` |
| Mem0 provenance | `reports/external_baselines/mem0_gate10_qflash_provenance.md` |
| A-Mem validation | `reports/external_baselines/amem_gate10_validation.md` |
| Mem0 validation | `reports/external_baselines/mem0_gate10_validation.md` |
| A-Mem raw API | `result/diagnostics/raw_api_calls_gate10_amem_20260715_120449.jsonl` |
| Mem0 raw API | `result/diagnostics/mem0_raw_api_calls_gate10_mem0_20260715_172157.jsonl` |
| A-Mem traces | `result/diagnostics/external_baselines/amem/conv-26/q*.json` (10 files) |
| Mem0 traces | `result/diagnostics/external_baselines/mem0/conv-26/q*.json` (10 files) |
| A-Mem cache | `data/locomo/external_cache/amem/conv-26_state.pkl` |
| Mem0 cache | `data/locomo/external_cache/mem0/v4flash-qwen4b-v1/conv-26/` |
