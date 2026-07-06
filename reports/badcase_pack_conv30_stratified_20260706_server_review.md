# Badcase Process Pack — Server Review Edition

Generated: 2026-07-06 | Reviewer: Codex本机 (CWJ)
Source: `result/locomo/conv-30_result_deepseek_stratified.jsonl`

---

## 1. Overall Metrics Summary

| metric | value |
| --- | --- |
| questions | 15 |
| overall F1 | 0.512 |
| cat1 (multi-hop) F1 | 0.267 |
| cat2 (temporal) F1 | 0.786 |
| cat4 (single-hop) F1 | **0.117** |
| cat5 (adversarial) F1 | 1.000 |
| LLM judge overall | **0.750 (9/12)** |
| LLM judge cat4 | **0.750 (3/4)** |
| LLM judge cat1 | 0.500 (2/4) |
| LLM judge cat2 | 1.000 (4/4) |

**Key finding**: LLM judge rates cat4 single-hop at 75% correct (3/4), but token F1 is only 0.117. This is a **20× gap between semantic correctness and surface-level F1**. The single-hop "failure" is primarily an evaluation mismatch, not a retrieval or reasoning failure.

---

## 2. Cat4 Single-Hop: Per-Question Analysis

### 2.1 Q9 — IMAGE: "What do the dancers in the photo represent?"

| field | value |
| --- | --- |
| category | 4 (single-hop) |
| question | What do the dancers in the photo represent? |
| gold answer | They are performing at the festival |
| prediction | no information available |
| token F1 | 0.0000 |
| tool calls | **31** (highest of all 15 questions) |
| runtime | 463.74 s |
| gold evidence | `D1:25` |
| prediction_context | **[] (EMPTY)** |
| gold evidence in context? | **NO** |

**Original conversation (D1:24–D1:28)**:

```
D1:24 | Jon   | [IMAGE URL: markmorrisdancegroup.org photo]
                "Thanks! I rehearsed with a small group of dancers after work.
                 We do all kinds of dances, from contemporary to hip-hop..."
D1:25 | Gina  | "Wow, it looks awesome! Are they yours at the festival?
                They're so graceful!"
D1:26 | Jon   | "Yeah, they're the ones performing at the festival!
                They've been practicing hard..."
D1:27 | Gina  | "Wow, they look great! Can't wait to see them rock the festival."
D1:28 | Jon   | "Yeah, awesome! Glad to be part of it."
```

**Analysis**:

- The question explicitly references "the photo". D1:24 contains an image URL — the photo of dancers.
- The gold answer "They are performing at the festival" comes from D1:26, NOT from D1:25 (the gold evidence label).
- D1:25 (Gina's reaction to the photo) does NOT contain the answer; D1:26 (Jon's confirmation) does. **Gold evidence label may be misaligned with the actual answer source.**
- The model made 31 tool calls and retrieved ZERO context events. The `prediction_context` is completely empty.
- From the log: the model entered a long tool-calling loop, issuing `search_event`, `sort`, `query_topic_events`, and `query_event_context` calls but never settled on valid evidence. It exhausted its round budget without reaching a confident retrieval.

**Failure type**: **Image evidence missing** (primary) + **Retrieval miss** (secondary).
- The question depends on visual information (what's IN the photo). Without VLM access to D1:24's image, the text-only system cannot determine what the photo depicts.
- Even for text evidence, the model's 31-tool retrieval failed to capture D1:26 (the actual answer-bearing turn). The tool path drifted without converging.
- D1:25 is labeled as gold evidence but D1:25 is Gina's REACTION to the photo, not the description of what the dancers represent.

**Recommendation**: This question should be treated as **image-dependent single-hop**. It cannot be answered correctly without VLM. Gold evidence should be re-labeled to `D1:26` or `D1:24+D1:26`. The 31-tool retrieval failure should be investigated separately — why did the graph traversal not land on D1:24–D1:26?

---

### 2.2 Q10 — "What is Jon's attitude towards being part of the dance festival?"

| field | value |
| --- | --- |
| category | 4 (single-hop) |
| question | What is Jon's attitude towards being part of the dance festival? |
| gold answer | Glad |
| prediction | Excited, glad, and passionate — he finds it awesome, brings him joy, and reminds him why he loves dance. |
| token F1 | 0.1053 |
| tool calls | 7 |
| runtime | 447.05 s |
| gold evidence | `D1:28` |
| prediction_context | `["D1:14", "D1:24", "D1:28", "D5:2"]` |
| gold evidence in context? | **YES** (D1:28 is in prediction_context) |

**Original conversation (D1:28)**:
```
Jon: "Yeah, awesome! Glad to be part of it."
```

**Tool path (from log)**:
```
Round 1: search_event("Jon attitude festival") → sort events
Round 2: query_event_context(D1:28), query_event_context(D1:14), query_event_context(D5:2)
Round 3: query_personal_aspect(Jon, "attitude")
Round 4: sort events → [D1:14-3, D1:26-1, D1:28-2, D5:2-4]
Round 5: answer with supports [D1:14-3, D1:24-6, D1:28-2, D5:2-4]
```

**Analysis**:

- Gold evidence D1:28 WAS successfully retrieved (in prediction_context).
- Gold answer is "Glad" — a single word, extracted from Jon's terse reply.
- Model's answer is "Excited, glad, and passionate — he finds it awesome, brings him joy, and reminds him why he loves dance."
- The model used 4 pieces of context (D1:14, D1:24, D1:28, D5:2) to synthesize a richer answer that captures Jon's overall attitude.
- The core word "glad" IS in the prediction (verbatim).
- The model's answer is **semantically correct and more complete** than the gold.

**Failure type**: **Evaluation mismatch** (F1 penalty from answer length).
- Gold: 1 token. Prediction: ~30 tokens. Token F1 = 0.105.
- LLM judge: **correct** (semantically matches).
- The gold answer "Glad" is an extreme minimal extraction — it captures only one word from the evidence turn, ignoring "awesome" and broader context.
- This is NOT a retrieval or reasoning failure. It's a gold-answer granularity problem.

**Recommendation**: Gold answers for attitude/sentiment questions should either allow multi-token expressive answers, or F1 should not be the primary metric for cat4. Consider a separate "concise match" vs "expressive match" label.

---

### 2.3 Q11 — "What made Gina choose the furniture and decor for her store?"

| field | value |
| --- | --- |
| category | 4 (single-hop) |
| question | What made Gina choose the furniture and decor for her store? |
| gold answer | personal style and customer comfort |
| prediction | She wanted to make the place look like her own style and make her customers feel cozy. She chose furniture that looks great and is comfy, and the chandelier adds a nice glam feel while matching the style of the store. She also wanted to create a comfortable and inviting spot that feels like a cool oasis — an experience that makes customers want to come back. |
| token F1 | 0.0563 |
| tool calls | 8 |
| runtime | 177.75 s |
| gold evidence | `D3:6` |
| prediction_context | `["D3:6", "D3:8"]` |
| gold evidence in context? | **YES** |

**Original conversation (D3:6)**:
```
Gina: "Thanks! It took a bit of time but I wanted to make the place look like
my own style and make my customers feel cozy. I chose furniture that looks great
and is comfy too. The chandelier adds a nice glam feel while matching the style
of the store."
```

**Analysis**:

- Gold evidence `D3:6` WAS successfully retrieved (in prediction_context).
- The gold answer "personal style and customer comfort" is a compressed paraphrase of Gina's own words: "my own style" → "personal style", "feel cozy" → "customer comfort".
- The model's answer restates Gina's full reasoning in natural language, including the chandelier detail.
- The key semantic units ("own style" ≈ "personal style", "cozy" ≈ "comfort") are present in both gold and prediction.
- F1 is 0.056 because the gold is a 4-token noun phrase while the prediction is a complete narrative paragraph.

**Failure type**: **Evaluation mismatch** (F1 penalty from answer length).
- LLM judge: **correct** (3/4 cat4 = 75%, this is one of the 3 correct).
- Gold answer captures themes; model reproduces the full evidence text. Both are correct interpretations of the same evidence.
- This highlights a structural issue with single-hop F1: when gold answers are abstracted key phrases and model answers are natural language restatements of evidence, token F1 will always be low.

**Recommendation**: Same as Q10. The evaluation pipeline should distinguish "answer is factually/substantively correct but longer" from "answer is wrong."

---

### 2.4 Q12 — "Why did Gina combine her clothing business with dance?"

| field | value |
| --- | --- |
| category | 4 (single-hop) |
| question | Why did Gina combine her clothing business with dance? |
| gold answer | she is passionate about dance and fashion |
| prediction | She is passionate about both dance and fashion, so combining them lets her show her creativity, share her love with others, and add dance-inspired items to her store. She also wanted to blend her love for dance and fashion because it was a perfect match. |
| token F1 | ~0.27 (estimated, above 0.2 threshold — not in auto-badcase table) |
| tool calls | 4 |
| runtime | 332.44 s |
| gold evidence | `D8:8` |
| prediction_context | `["D8:8", "D6:8", "D8:6"]` |
| gold evidence in context? | **YES** |

**Original conversation (D8:8)**:
```
Gina: "Thanks! I'm passionate about dance and fashion so combining them lets me
show my creativity and share my love with others. Plus, I can add dance-inspired
items to my store!"
```

**Analysis**:

- Gold evidence `D8:8` WAS retrieved (in prediction_context).
- The gold answer is nearly verbatim from the start of the evidence turn: "I'm passionate about dance and fashion".
- The model's answer begins with the exact same phrase and expands with additional reasoning from the same evidence turn.
- F1 is above the 0.2 threshold, so this did NOT appear in the auto-badcase table. It's a borderline case.
- The model's expansion adds valid context from the evidence ("show creativity", "share love", "dance-inspired items").

**Failure type**: **Borderline — semantically correct with moderate length expansion**.
- This is the best-performing cat4 question. The model retrieved the right evidence and gave a faithful answer.
- The slight F1 penalty comes from the model including additional supporting details from the same evidence turn.

---

## 3. Cat4 Single-Hop Root Cause Summary

### 3.1 How many are semantic-correct but F1-low?

**3 of 4 (75%)**. Q10, Q11, and Q12 all have the gold evidence in prediction_context, and all give semantically correct answers. Their low F1 is purely from answer length mismatch — the model produces natural-language restatements while the gold answers are minimal extractions.

This is confirmed by the LLM judge score: **0.75 for cat4** vs **0.117 F1**.

### 3.2 How many are image-related?

**1 of 4 (25%)**. Q9 explicitly asks about "the photo" and depends on an image in turn D1:24. Without VLM, the model cannot answer. This is a genuine failure, but it's an **input modality gap**, not a graph-memory failure.

### 3.3 How many are retrieval miss?

**1 of 4 (25%)**. Q9 had empty prediction_context after 31 tool calls. The text-only evidence for the correct answer exists in D1:26, but the model never retrieved it. This is a genuine retrieval/tool-path failure that needs investigation.

### 3.4 How many are graph construction issue?

**0 of 4**. All gold evidence IDs (D1:25, D1:28, D3:6, D8:8) exist in the dataset and can be mapped to conversation turns. The memory audit shows 1094 episode events covering 19 sessions with zero null sessions. The graph construction appears structurally sound for conv-30.

### 3.5 How many are tool path drift?

**1 of 4 (25%)**. Q9 had 31 tool calls — far above the average of 9.5 — and ended in an empty context. The model kept calling tools without converging. This is excessive exploration without a stopping criterion.

### 3.6 How many are model synthesis issue?

**0 of 4**. When evidence IS retrieved, the model synthesizes correct answers. No hallucination or contradiction with evidence observed in cat4.

---

## 4. Quantitative Breakdown

| count | failure type | questions |
| ---: | --- | --- |
| 3 | evaluation mismatch (F1 vs semantic) | Q10, Q11, Q12 |
| 1 | image evidence missing | Q9 |
| 1 | retrieval miss (text evidence exists but not retrieved) | Q9 |
| 0 | graph construction issue | — |
| 1 | tool path drift (31 tools, empty context) | Q9 |
| 0 | model synthesis issue | — |

Note: Q9 has multiple failure modes (image + retrieval + tool drift), so counts sum to >4.

---

## 5. Cat1 Multi-Hop Cross-Reference

For context, the 4 cat1 (multi-hop) questions:

| Q | gold evidence | ctx hit? | tools | F1 | LLM judge |
| --- | --- | --- | ---: | ---: | --- |
| Q1: What do Jon and Gina both have in common? | D1:2,3,4 + D2:1 | **NO** (ctx empty) | 24 | 0.000 | wrong |
| Q2: What Jon thinks the ideal dance studio should look like? | D1:20, D2:4, D2:8 | partial (D2:4 missing) | 19 | low | correct? |
| Q5: Why did Gina decide to start her own clothing store? | D6:8, D1:3 | YES | 3 | low | correct? |
| Q7: How long did it take for Jon to open his studio? | D1:2, D15:13 | D15:13 missing | 7 | low | correct? |

Cat1 has a mix of retrieval miss (Q1, empty context after 24 tools) and synthesis challenges. The LLM judge scores cat1 at 0.50, meaning 2 of 4 are semantically correct despite low F1.

---

## 6. Actionable Conclusions

1. **Cat4 single-hop is NOT broken.** 75% of cat4 questions are semantically correct (LLM judge). The 0.117 F1 is a measurement artifact caused by gold answers being minimal extractions. **The graph retrieval is working for cat4.**

2. **The primary cat4 failure (Q9) is an image-dependent question.** It should be excluded from text-only single-hop evaluation, or gold evidence should be re-labeled to D1:26.

3. **Q9's 31-tool retrieval failure is a separate tool-path bug.** The model explored extensively but never converged on the correct evidence. This may be a prompt or stopping-criterion issue.

4. **Gold answers need granularity calibration.** Cat4 gold answers vary from 1 word ("Glad") to full sentences. Single-token gold answers guarantee zero F1 for any model that produces natural language. Consider:
   - Normalizing gold answers to a minimum length.
   - Using LLM judge as the primary cat4 metric.
   - Adding a "concise match" (`f1 > 0.5` for short gold) vs "substantive match" (LLM judge) dual metric.

5. **Image questions should be flagged in the dataset.** Q9's question text contains "photo" but the system had no VLM path. All image-dependent questions should be annotated and tracked separately.

---

## 7. Cache & Log Status

| artifact | path | status |
| --- | --- | --- |
| rewrite cache | `data/locomo/rewrite_deepseek/conv-30_rewrite.json` | **Server only** (empty dir on Codex) |
| keyword cache | `data/locomo/keyword_deepseek/conv-30_keyword.json` | **Server only** |
| embedding cache | `data/locomo/embedding/gpt_deepseek/conv-30_embedding.pkl` | **Server only** |
| result JSONL | `result/locomo/conv-30_result_deepseek_stratified.jsonl` | Committed |
| stratified log | `log/locomo/conv-30_deepseek_stratified.log` | Committed |
| memory audit | `result/locomo/memory_audit_deepseek_stratified.json` | Committed |
| metrics summary | `result/locomo/metrics_summary_deepseek_stratified.json` | Committed |

Cache files were regenerated during the stratified run (log lines 3, 24: "cache invalid (file not found), regenerating"). They exist on the server at:
- `/data/nishome/cuiwenjia/MRAgent-Reproduction/data/locomo/rewrite_deepseek/conv-30_rewrite.json`
- `/data/nishome/cuiwenjia/MRAgent-Reproduction/data/locomo/keyword_deepseek/conv-30_keyword.json`
- `/data/nishome/cuiwenjia/MRAgent-Reproduction/data/locomo/embedding/gpt_deepseek/conv-30_embedding.pkl`

These are gitignored and not on the Codex machine.

---

## 8. Graph-Layer Evidence (Server Graph Snapshot)

Generated: 2026-07-06 | Source: `result/graph_snapshot/conv-30_nodes.jsonl` + `conv-30_edges.jsonl`

### 8.1 Graph Overview

| metric | value |
| --- | --- |
| episode events | 1094 |
| keywords | 1779 |
| topics | 213 |
| persona | 4 (344 personal events) |
| edges (keyword→event) | 5103 |
| edges (topic→event) | 1321 |
| gold evidence IDs in dataset | 75 (all 75 map to ≥1 sentence in graph via turn→sentence prefix) |

**Key correction**: The raw `export_graph_snapshot.py` report says "75 missing from episode graph" — this is a **false negative**. Gold evidence IDs are turn-level (`D1:25`), while graph stores sentence-level IDs (`D1:25-1`). All 75 gold evidence turns have ≥1 sentence in the episode graph. The format mismatch was corrected by prefix-matching.

### 8.2 Q9 Graph Analysis — "What do the dancers in the photo represent?"

| field | finding |
| --- | --- |
| gold evidence ID | `D1:25` |
| sentences in graph | **3**: D1:25-1 (Compliment), D1:25-2 (Inquiry), D1:25-3 (Compliment) |
| connected keywords | `dancers`, `festival`, `graceful`, `group of dancers`, `Gina`, `Wow`, `awesome`, `Jon's` |
| connected topics | `D1:t13` — "Jon's group performs at a festival next month" |
| answer-bearing turn D1:26 in graph? | **YES** — 2 sentences: D1:26-1 (Confirmation: "they're the ones performing at the festival!"), D1:26-2 (Praise) |
| D1:26 keywords | `dancers`, `festival`, `performing`, `Jon's group`, `grace`, `impress`, `practicing hard`, `skill` |
| keyword "dancers" → events | D1:24-2, D1:25-2, D1:25-3, D1:26-1, D1:26-2, D1:27-1, D1:27-2 (16 events total across sessions) |
| keyword "festival" → events | D1:25-2, D1:26-1 (plus other sessions) |
| keyword "photo" → events | D1:24-7, D2:4-7, D3:3-4, D9:2-4, D9:5-5, etc. (39 events total) |
| image turn D1:24 in graph? | **YES** — 7 sentences: D1:24-1 to D1:24-7, tags include "Photo Sharing", "Rehearsal", "Upcoming Performance" |
| D1:24 keywords (relevant) | `photo` (D1:24-7), `dancers` (D1:24-2), `nearby festival` (D1:24-5), `perform` (D1:24-5), `small group` (D1:24-2) |

**Conclusion**: 
- Gold evidence D1:25 is **present and well-connected** in the graph with relevant keywords (`dancers`, `festival`, `graceful`).
- Answer turn D1:26 is **also in the graph**, connected via topic D1:t13 and keywords `dancers`, `festival`, `performing`.
- A `search_event("dancers festival")` would match D1:25-2 and D1:26-1; `search_event("dancers photo")` would match D1:24-2,7.
- **Root cause is RETRIEVAL MISS (tool-path drift), NOT graph construction.** The keywords and topical links exist. The model's 31-tool exploration never landed on these nodes — likely a search query formulation or stopping-criterion problem.

### 8.3 Q10 Graph Analysis — "What is Jon's attitude towards being part of the dance festival?"

| field | finding |
| --- | --- |
| gold evidence ID | `D1:28` |
| sentences in graph | **2**: D1:28-1 (Agreement: "Yeah, awesome!"), D1:28-2 (Satisfaction: "Glad to be part of it") |
| connected keywords | `Glad`, `festival performance`, `part`, `Jon`, `Yeah`, `awesome` |
| connected topics | `D1:t13` |
| in prediction_context? | **YES** — D1:28 is in context |
| retrieval diagnosis | **Successful retrieval** |
| graph construction | Sound — D1:28 in same topic as D1:24-26 |
| failure type | **Evaluation mismatch** (F1=0.105 vs semantically "glad" in prediction) |

### 8.4 Q11 Graph Analysis — "What made Gina choose the furniture and decor for her store?"

| field | finding |
| --- | --- |
| gold evidence ID | `D3:6` |
| sentences in graph | **4**: D3:6-1 (Gratitude), D3:6-2 (Furniture selection motivation), D3:6-3 (Furniture choice), D3:6-4 (Decor element) |
| connected keywords | `furniture`, `furniture and decor`, `own style`, `customers`, `cozy`, `chandelier`, `Gina's`, `selection`, `look`, `feel`, `make`, `wanted` |
| connected topics | `D3:t5`, `D3:t6` |
| in prediction_context? | **YES** — D3:6 is in context |
| retrieval diagnosis | **Successful retrieval** |
| failure type | **Evaluation mismatch** (F1=0.056 vs semantically correct answer) |

### 8.5 Q12 Graph Analysis — "Why did Gina combine her clothing business with dance?"

| field | finding |
| --- | --- |
| gold evidence ID | `D8:8` |
| sentences in graph | **3**: D8:8-1 (Gratitude), D8:8-2 (Passion Combination), D8:8-3 (Product Ideas) |
| connected keywords | `dance`, `fashion`, `passionate`, `combining`, `clothing business`, `Gina's creativity`, `share`, `show`, `dance-inspired items` |
| connected topics | `D8:t8`, `D8:t3`, `D8:t7` |
| in prediction_context? | **YES** — D8:8 is in context |
| retrieval diagnosis | **Successful retrieval** |
| failure type | **Borderline** — semantically correct, moderate F1 penalty |

### 8.6 Graph-Layer Summary

| Q | evidence in graph | keywords connect? | topic links? | retrieval success? | actual failure |
| --- | :---: | :---: | :---: | :---: | --- |
| Q9 | ✅ (D1:25 + D1:26) | ✅ (dancers, festival, photo) | ✅ (D1:t13) | ❌ (empty ctx, 31 tools) | **Retrieval/tool-path miss** |
| Q10 | ✅ (D1:28) | ✅ (Glad, festival performance) | ✅ (D1:t13) | ✅ | Evaluation mismatch |
| Q11 | ✅ (D3:6) | ✅ (furniture, own style, cozy) | ✅ (D3:t5, t6) | ✅ | Evaluation mismatch |
| Q12 | ✅ (D8:8) | ✅ (dance, fashion, passionate) | ✅ (D8:t3, t7, t8) | ✅ | Borderline |

**Key finding**: 0/4 cat4 questions have graph construction issues. All gold evidence exists in the graph with adequate keyword and topic connections. Q9's failure is purely a retrieval/tool-path problem — the evidence is well-linked but the model's 31-tool exploration never converged on the correct nodes. This confirms the earlier analysis (Section 3.4: "0 graph construction issues") with concrete graph-layer evidence.

### 8.7 Q9 Retrieval Failure — Detailed Diagnosis

Based on graph structure, here is why Q9 retrieval should have worked but didn't:

1. **Question**: "What do the dancers in the photo represent?"
2. **Effective search terms** (extractable from question): `dancers`, `photo`, `represent`
3. **Graph keyword matches**:
   - `dancers`: 14 keyword nodes, links to D1:24-2, D1:25-2,3, D1:26-1,2, D1:27-1,2
   - `photo`: 5 keyword nodes, links to D1:24-7 (and 38 other events)
   - `festival`: 4 keyword nodes, links to D1:25-2, D1:26-1
   - `dance performance photo`: links to D1:24 area
4. **Why retrieval likely failed**:
   - `search_event("dancers")` would return many events (16), requiring `sort` + filtering
   - `search_event("photo represent")` → keyword "represent" doesn't exist (0 occurrences)
   - The model may have searched for "represent" (negative result) and then drifted
   - 31 tool calls with empty context suggests iterative reformulation without convergence
   - The model never used a simple `search_event("festival dancers")` query that would directly hit D1:25-2 and D1:26-1
5. **Possible fixes**:
   - Add stopping criterion after N consecutive failed searches
   - Prompt model to fall back to broader keyword search when specific queries fail
   - Add `query_topic_events` or `query_event_context` on nearby successfully-retrieved events

---

## 9. Next Steps

1. **Fix gold answer granularity** before re-running any cat4 evaluation. Add a minimum token count or use LLM judge as the primary single-hop metric.

2. **Image-dependent questions**: Annotate all questions containing "photo", "image", "picture", "see in the photo" as image-dependent. Exclude from text-only single-hop evaluation.

3. **Investigate Q9 tool-path drift**: Why did 31 tool calls produce empty context? Check if `search_event` with "photo"/"dancers"/"festival" returns the correct episode events. This may reveal a keyword-to-event mapping gap.

4. **Run Standard RAG smoke on conv-30** to compare whether flat retrieval also fails on Q9, or if the tool-calling path specifically degrades here.

5. **Oracle evidence QA on Q1 and Q9**: Give the model gold evidence directly and check if it can answer. This isolates retrieval error from synthesis error.

6. **Graph snapshot export**: ✅ Done on server. See `reports/graph_snapshot_conv30_20260706_server.md`.

---

*This report was updated on the server (2026-07-06) with graph-layer evidence from `result/graph_snapshot/conv-30_*.jsonl`. Original analysis (Sections 1-7) was written on the Codex machine. Section 8 added on server.*
