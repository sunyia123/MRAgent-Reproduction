# MRAgent

## Reproduction Workspace Notice

This checkout is maintained as `sunyia123/MRAgent-Reproduction`, a private reproduction and extension workspace.

Before running experiments, read:

- [README_REPRODUCTION.md](README_REPRODUCTION.md)
- [docs/goal.md](docs/goal.md)
- [docs/handoff.md](docs/handoff.md)
- [docs/claude_code_next_steps.md](docs/claude_code_next_steps.md)
- [docs/claude_code_full_experiment_instructions.md](docs/claude_code_full_experiment_instructions.md)
- [docs/experiment_master_agenda.md](docs/experiment_master_agenda.md)
- [docs/next_iteration_handoff.md](docs/next_iteration_handoff.md)
- [docs/medium_core_validation_handoff.md](docs/medium_core_validation_handoff.md)
- [docs/locomo_500q_ablation_protocol.md](docs/locomo_500q_ablation_protocol.md)
- [docs/cte_ctc_next_experiment_plan_20260720.md](docs/cte_ctc_next_experiment_plan_20260720.md)
- [docs/locomo_gate10_to_500_handoff.md](docs/locomo_gate10_to_500_handoff.md)
- [docs/benchmark_reproduction_plan.md](docs/benchmark_reproduction_plan.md)
- [docs/reproduction_plan.md](docs/reproduction_plan.md)
- [reports/mragent_experiment_progress_20260703.md](reports/mragent_experiment_progress_20260703.md)
- [reports/mragent_vlm_cbr_qlearning_design_20260702.md](reports/mragent_vlm_cbr_qlearning_design_20260702.md)
- [.agents/codex_experience_review.md](.agents/codex_experience_review.md)

Current server-side execution entry:

```bash
cat docs/locomo_gate10_to_500_handoff.md
python repro/update_server_directory_manifest.py --root /data/nishome/cuiwenjia/MRAgent-Reproduction
python repro/audit_runtime_config.py --data locomo --sample_ids 26 --model deepseek --re_model v4flash --qa_model v4flash --file mragent_full_gate10_qflash --subset_manifest data/subsets/locomo_conv26_10q_core_seed42.json
```

For the current medium-core validation, do not run `run_stratified.py --sample_ids 26 --model deepseek` as a bare command. It omits the fixed subset manifest, uses the default result tag `0`, and leaves QA model routing implicit. In this workspace, `--model deepseek` resolves to `deepseek-ai/DeepSeek-V4-Pro`; graph-building rewrite/keyword should normally use `--re_model v4flash`, while QA must explicitly use `--qa_model v4flash` or `--qa_model deepseek`. Generated baseline caches, VLM rewrite caches, logs, raw results, and secrets must stay out of Git unless a small manifest/report is explicitly written.

Canonical server graph-build command for one sample:

```bash
export RUN_ID=conv26_graphbuild_$(date +%Y%m%d_%H%M%S)
export API_CLIENT_MAX_RETRIES=0
export API_CALL_MAX_RETRIES=1
export API_TIMEOUT_SECONDS=600
export API_HARD_TIMEOUT_SECONDS=720
export API_CALL_COOLDOWN_SECONDS=60
export RAW_API_LOG=1
export RAW_API_LOG_MAX_CHARS=0
export ENABLE_THINKING=0
python repro/audit_runtime_config.py \
  --data locomo \
  --sample_ids 26 \
  --model deepseek \
  --re_model v4flash \
  --qa_model v4flash \
  --file graphbuild_100q \
  --subset_manifest data/subsets/locomo10_100q_seed42.json
python run_stratified.py \
  --data locomo \
  --sample_ids 26 \
  --model deepseek \
  --re_model v4flash \
  --qa_model v4flash \
  --file graphbuild_100q \
  --subset_manifest data/subsets/locomo10_100q_seed42.json
```

Immediately verify model routing after the first rewrite call:

```bash
tail -n 5 result/diagnostics/api_call_log_${RUN_ID}.jsonl
tail -n 2 result/diagnostics/raw_api_calls_${RUN_ID}.jsonl
python repro/audit_rewrite_cache.py data/locomo/rewrite_deepseek/conv-26_rewrite.json.tmp
```

The rewrite-stage API log must show `stage=rewrite` and `model=deepseek-ai/DeepSeek-V4-Flash`. If it shows `deepseek-ai/DeepSeek-V4-Pro`, stop the run, back up the partial `.tmp`, and restart with the canonical command above. Do not mix V4-Pro and V4-Flash rewrite outputs in the same graph-build cache unless the report explicitly labels that sample as mixed-model.

For API hangs, use the log state, not terminal silence:

- `api_call_log_${RUN_ID}.jsonl` records `started`, `success`, and `error` metadata, including `request_id`.
- `raw_api_calls_${RUN_ID}.jsonl` records the complete request messages and response payload for each call when `RAW_API_LOG=1`.
- If a call hangs below the SDK timeout layer, `API_HARD_TIMEOUT_SECONDS` should raise an error and write an `error` record. If the process is killed externally, the last `started` record without a matching `success` or `error` identifies the exact input that hung.
- For graph-building rewrite runs, keep `API_CALL_COOLDOWN_SECONDS=60` unless there is evidence that the provider is stable. The observed SiliconFlow failure pattern is 2-4 large rewrite calls succeeding, followed by the next large call hanging or timing out.
- For SiliconFlow DeepSeek/Qwen calls, `ENABLE_THINKING=0` injects `extra_body.enable_thinking=false`. Verify this in `raw_api_calls_${RUN_ID}.jsonl`; the request should contain `"extra_body":{"enable_thinking":false}` and the response should not contain large `reasoning_content`.

Every run writes persistent logs. Set `RUN_ID=<short-readable-id>` before long runs, then inspect:

```text
log/<dataset>/runs/<RUN_ID>_<model>_<file>.log
log/<dataset>/<sample>_<model>_<file>_<RUN_ID>.log
result/diagnostics/api_call_log_<RUN_ID>.jsonl
```

Before every server push, update and commit:

```text
reports/server_directory_manifest.md
reports/server_directory_manifest.jsonl
```

These files are generated by `repro/update_server_directory_manifest.py` and are the source of truth for what exists under `/data/nishome/cuiwenjia/MRAgent-Reproduction`.

The original upstream repository is preserved as read-only `upstream`.

## Current LoCoMo Core Protocol

The current primary experiment is the fixed `LoCoMo-10 / 500 questions` protocol in [docs/locomo_500q_ablation_protocol.md](docs/locomo_500q_ablation_protocol.md). It compares Full MRAgent, native RAG, GraphRAG, A-Mem, and Mem0 on 400 ordinary questions plus 100 separately reported adversarial questions. Oracle is retained only as a historical diagnostic and is not a main baseline.

Generate the committed manifests with:

```bash
python repro/build_main_experiment_manifests.py
```

Expected distributions are:

- `locomo10_500q_main_seed42.json`: cat1/2/3/4/5 = `102/101/96/101/100`.
- `locomo10_200q_ablation_seed42.json`: cat1/2 = `100/100` and every key is contained in the 500-question manifest.

The graph/retrieval ablation uses two explicit switches instead of approximating no-reasoning with one LLM round:

```text
--memory_view ce|cte|ctc
--retrieval_mode passive|active
```

`passive` performs one deterministic graph read and no agent tool loop. `active` uses the original multi-round tool-calling loop. CTE exposes cue/tag/episode navigation; CTC retains those paths and additionally exposes topic-event and person-aspect content tools. The five 200-question conditions are complete; their interpretation, measurement gaps, and next experiments are documented in [docs/cte_ctc_next_experiment_plan_20260720.md](docs/cte_ctc_next_experiment_plan_20260720.md).

The external A-Mem and Mem0 conv-26 gate has completed 10/10 and verifies only engineering readiness, not statistical performance. The current 500-question runs are partial: A-Mem 96/500 and Mem0 297/500. Complete them only after the active-context, content-tool, and schema fixes in the current next-experiment plan.

The proposed CBR/soft-Q retrieval-path module is deliberately separated from this validation. Its leakage controls, case schema, pretraining idea, and future experiment sequence are in [docs/mragent_cbr_qlearning_module_plan.md](docs/mragent_cbr_qlearning_module_plan.md).

### External baseline adapters

A-Mem and Mem0 are implemented under `repro/external_baselines/`. Prepare the pinned source trees and dependencies once:

```bash
python repro/external_baselines/prepare_sources.py --root external
pip install -r requirements-external-baselines.txt
pip install --no-deps -e external/mem0
```

Pinned sources:

- A-Mem: `WujiangXu/A-mem@0c8039f28fdcc08189a23c07a3437d9d2482f9c2` (MIT).
- Mem0: `mem0ai/mem0@ccbe5861a138c7583e01bb3a3aa6168e52526a23` (Apache-2.0).

The Mem0 `memory-benchmarks` Docker requirement referenced the removed branch `feat/v3-pipeline`. This workspace therefore uses the pinned, currently retrievable OSS Mem0 implementation. Reports must label it as an OSS engineering reproduction, not a bit-identical reproduction of the paper-era Mem0 service.

Run the two adapters on the fixed conv-26 gate:

```bash
export ENABLE_THINKING=0
export RAW_API_LOG=1
export RAW_API_LOG_MAX_CHARS=0
export EMBED_MODEL=Qwen/Qwen3-Embedding-4B

export RUN_ID=gate10_amem_$(date +%Y%m%d_%H%M%S)
python repro/external_baselines/run_amem_adapter.py \
  --external_repo external/A-mem \
  --data locomo --sample_ids 26 --model deepseek \
  --re_model v4flash --qa_model v4flash \
  --file amem_gate10_qflash --retrieve_k 10 --max_context_memories 30 \
  --subset_manifest data/subsets/locomo_conv26_10q_core_seed42.json

export RUN_ID=gate10_mem0_$(date +%Y%m%d_%H%M%S)
python repro/external_baselines/run_mem0_adapter.py \
  --external_repo external/mem0 \
  --data locomo --sample_ids 26 --model deepseek \
  --re_model v4flash --qa_model v4flash \
  --file mem0_gate10_qflash --retrieve_k 10 \
  --subset_manifest data/subsets/locomo_conv26_10q_core_seed42.json
```

The conv-26 gate contains 10 QA items but 419 dialogue turns. A-Mem and Mem0 must ingest all 419 turns before those 10 questions are comparable; “gate10” does not mean “build memory from only 10 turns.” Run the adapters sequentially to avoid API pressure.

Both runners checkpoint ingestion after every turn and are resumable. Their memory stores stay under `data/locomo/external_cache/` and are ignored by Git. A-Mem internal calls use the standard `raw_api_calls_${RUN_ID}.jsonl`; Mem0 writes `mem0_raw_api_calls_${RUN_ID}.jsonl`. Each result row includes retrieved memories and source IDs; full per-question traces remain under `result/diagnostics/external_baselines/`. Validate both outputs before running the other four methods or expanding to 500 questions:

```bash
python repro/validate_baseline_results.py \
  --manifest data/subsets/locomo_conv26_10q_core_seed42.json \
  --result_glob 'result/locomo/conv-26_result_deepseek_amem_gate10_qflash.jsonl' \
  --method amem \
  --provenance reports/external_baselines/amem_gate10_qflash_provenance.md \
  --output reports/external_baselines/amem_gate10_validation.md

python repro/validate_baseline_results.py \
  --manifest data/subsets/locomo_conv26_10q_core_seed42.json \
  --result_glob 'result/locomo/conv-26_result_deepseek_mem0_gate10_qflash.jsonl' \
  --method mem0 \
  --provenance reports/external_baselines/mem0_gate10_qflash_provenance.md \
  --output reports/external_baselines/mem0_gate10_validation.md
```

> This repository contains the code for the paper
> **"Memory is Reconstructed, Not Retrieved: Graph Memory for LLM Agents"** ([arXiv:2606.06036](https://arxiv.org/abs/2606.06036)).

A retrieval-augmented question-answering system that builds a **graph-structured
episodic memory** from long multi-session dialogues and answers questions through an
**LLM tool-calling reasoning loop**. The system is evaluated on the **LoCoMo** and
**LongMemEval (LM)** benchmarks.

The pipeline has two phases:

**Phase 1 — Build the graph memory** (once per conversation sample):

- **rewrite** — rewrite each dialogue turn into a self-contained sentence: resolve pronouns to explicit entities, convert relative times to absolute `YYYY-MM-DD` dates, attach a topic tag, and extract topics and person-level facts.
- **extract_keyword** — extract salient keywords for each rewritten sentence.
- **store** — build the in-memory graph from the above: key nodes, episode / topic / personal events, and the links between them.

**Phase 2 — Answer questions** (per question):

- **answer** — run a tool-calling reasoning loop (keyword / topic / personal / temporal / context tools) to produce a short final answer.

---

## 1. Repository Structure

```
run.py                    # main entry point
common/
    config.py             # CLI args, models, paths
    utils.py              # JSON + similarity helpers
    logging_utils.py      # per-sample logging
memory/
    system.py             # in-memory graph store
    controller.py         # graph query tools
llm/
    controller.py         # LLM tool-calling wrapper
    embeddings.py         # text-embedding client
    rag_utils.py          # batched embedding helper
agent/
    agent.py              # pipeline orchestration
    tools.py              # tool schemas + dispatch
prompts/
    prompts.py            # all LLM prompts
    schema.py             # output JSON validators
data/
    get_data.py           # load benchmark dataset
    embed_rewrite.py      # build embedding files
    dataset_locomo.json   # LoCoMo benchmark data
    dataset_LM.json       # LongMemEval benchmark data
eval/
    judge.py              # LLM-as-judge scorer
    evaluation.py         # F1 / EM helpers
    evaluate_reasoning.py # eval entry (F1 + judge)
```

---

## 2. Installation

Python 3.9+. The LongMemEval dataset (`data/dataset_LM.json`) is stored with **Git LFS**,
so install Git LFS *before* cloning, otherwise that file arrives as a small pointer stub.

```bash
# install Git LFS once: https://git-lfs.com   (e.g. `apt install git-lfs` / `brew install git-lfs`)
git lfs install
git clone https://github.com/Ji-shuo/MRAgent.git
cd MRAgent

pip install -r requirements.txt
```

> `torch` is used only for embedding tensor ops (L2 normalization); a CPU build is
> sufficient. `nltk` is required only by the `eval/` scripts.

---

## 3. Configuration

All components — the chat LLM, the text-embedding model, and the LLM-as-judge
evaluator — are accessed through a single **OpenRouter** key (OpenAI-compatible API).
The key is read from a `.env` file at the repository root; **no key is hard-coded**.

Copy the template and fill in your key:

```bash
cp .env.example .env
# then edit .env:
# OPENROUTER_API_KEY=sk-or-v1-xxxxxxxx
```

`.env` is git-ignored. The same `OPENROUTER_API_KEY` is used everywhere:

| Component | File | Model |
| --- | --- | --- |
| Chat / reasoning | `common/config.py` (`--model` → `MODEL`) | e.g. `gemini` → `google/gemini-2.5-flash` |
| Embedding | `llm/embeddings.py` | `text-embedding-3-large` (3072-d) |
| LLM-as-judge | `eval/judge.py` | `openai/gpt-4o-mini` |

---

## 4. Data Layout

The two benchmarks shipped in `data/` come from:

- **LoCoMo** (`dataset_locomo.json`) — Maharana et al., *Evaluating Very Long-Term
  Conversational Memory of LLM Agents*, ACL 2024. [arXiv:2402.17753](https://arxiv.org/abs/2402.17753)
- **LongMemEval** (`dataset_LM.json`) — Wu et al., *LongMemEval: Benchmarking Chat
  Assistants on Long-Term Interactive Memory*, ICLR 2025. [arXiv:2410.10813](https://arxiv.org/abs/2410.10813)

Place the benchmark file at `data/dataset_<name>.json`. Generated intermediate
artifacts and results are written under per-dataset subfolders:

```
data/<dataset>/rewrite_<model>/<sample_id>_rewrite.json   # stage 1 output
data/<dataset>/keyword_<model>/<sample_id>_keyword.json       # stage 3 output
data/<dataset>/embedding/gpt_<model>/<sample_id>_embedding.pkl# stage 2 output
result/<dataset>/<sample_id>_result_<model>_<file>.jsonl      # predictions (the only run output)
```

The run writes a single output per sample — the `_result_*.jsonl` predictions file
(one JSON line per question: gold answer, prediction, category, evidence labels,
retrieved support). A stage is **skipped if its output file already exists**, so
generation runs once and subsequent runs reuse the cached `rewrite` / `keyword` /
`embedding` files.

---

## 5. Usage

The single entry point is `run.py`, invoked from the repository root.

### 5.1 Arguments

| Argument | Meaning | Default |
| --- | --- | --- |
| `--data` | dataset name (`locomo` / `LM`) | `locomo` |
| `--model` | chat model short name (`gemini` / `claude` / `gpt4o` / `qwen`) | `gemini` |
| `--file` | run/experiment tag appended to result filenames | `0` |
| `--sample` | (LoCoMo) run a single sample id, e.g. `42`; omit to run all | `None` |
| `--ca` | (LM) category index: `0`=multi-session, `1`=single-session-user, `2`=temporal-reasoning | `1` |
| `--lm_batch` | (LM) sessions merged per rewrite call (`1` recommended) | `1` |

### 5.2 LoCoMo

```bash
# all conversations
python run.py --data locomo --model gemini --file myrun

# a single conversation
python run.py --data locomo --model gemini --file myrun --sample 42
```

### 5.3 LongMemEval (LM)

`--ca` selects the question category (one run per category):

```bash
python run.py --data LM --model gemini --file myrun --ca 0 --lm_batch 10   # multi-session
python run.py --data LM --model gemini --file myrun --ca 1 --lm_batch 10   # single-session-user
python run.py --data LM --model gemini --file myrun --ca 2 --lm_batch 10   # temporal-reasoning
```

`--lm_batch` controls rewrite granularity. `--lm_batch 1` (default) rewrites one
session per LLM call and produces per-session records compatible with all downstream
readers. Values `>1` merge multiple sessions per call (range-keyed records, handled by
the robust readers and the origin-prefixed graph store).

Each question is answered concurrently (10 worker threads); predictions stream to the
`result/<dataset>/` files and runs are resumable (already-answered questions are
skipped on restart).

---

## 6. Evaluation

```bash
# F1 + LLM-as-judge accuracy (writes result_judge_<data>_<model>_<file>.jsonl)
python eval/evaluate_reasoning.py --data locomo --model gemini --file myrun --allfile
```

The LLM judge (`eval/judge.py`) grades a prediction `CORRECT`/`WRONG` against the gold
answer with `gpt-4o-mini`, using lenient matching (topic overlap; date equivalence for
temporal questions).

---

## 7. Notes

- The pipeline is **cache-based**: delete the corresponding `rewrite` / `keyword` /
  `embedding` files to force regeneration of a sample.
- Per-sample reasoning traces are logged under `log/<dataset>/`.
- Tool inventory (7 tools): `edges_by_tag`, `query_conversation_time`,
  `query_event_keywords`, `query_event_context`, `query_personal_information`,
  `query_personal_aspect`, `query_topic_events`.
