# Claude Code Next Steps: VLM Validation, VLM Rewrite, And Explore-50

This document is the current server-side execution instruction. It covers only the next three stages:

1. Validate Qwen VLM as a standalone visual-evidence tool.
2. Test VLM-enriched rewrite without overwriting baseline rewrite cache.
3. Run a 50-question exploratory LoCoMo subset after VLM connectivity is confirmed.

Do not treat these two stages as full paper reproduction.

For the complete experiment roadmap and all command groups, read:

```bash
cat docs/experiment_master_agenda.md
cat docs/next_iteration_handoff.md
cat docs/medium_core_validation_handoff.md
cat docs/claude_code_full_experiment_instructions.md
```

Before writing any benchmark-level conclusion, also read:

```bash
cat docs/benchmark_reproduction_plan.md
```

Important:

- `explore50_vlmready` is a diagnostic subset only.
- MRAgent paper-level reproduction also requires benchmark and baseline replication.
- The paper benchmarks are LoCoMo and LongMemEval.
- Current private repo LoCoMo file contains 10 conversation samples and 1986 QA items.
- LongMemEval is still blocked until the real `data/dataset_LM.json` is obtained.
- Do not run every stage with DeepSeek-V4-Pro by default. Use cheaper/faster models for diagnostics when the question is engineering validity rather than final model capability.
- Current priority is to explain low single-hop performance with badcase process evidence, then compare MRAgent against Standard RAG and GraphRAG baselines.
- For Standard RAG, do not compare 105-question aggregate against the 15-question MRAgent stratified subset. Use `repro/compare_rag_to_mragent_subset.py` to extract matched questions and produce a fair comparison report.
- Current medium-scale target is LoCoMo-10 / 100 questions / same subset / MRAgent + Standard RAG + GraphRAG + Oracle evidence QA. `run_stratified.py` now supports `--subset_manifest`.

## Current Priority: Dataset, Graph, And Badcase Audit

Run these before expanding more expensive full-pipeline experiments:

```bash
python repro/audit_dataset_tasks.py \
  --data_path data/dataset_locomo.json \
  --output reports/dataset_task_audit_locomo_20260706.md

python repro/export_graph_snapshot.py \
  --data locomo \
  --model deepseek \
  --sample 30 \
  --output_dir result/graph_snapshot \
  --report reports/graph_snapshot_conv30_20260706.md
```

Expected:

- Dataset/task audit explains the sample, category, and image-turn structure.
- Graph snapshot rebuilds the in-memory graph from existing rewrite, keyword, and embedding caches.
- No rewrite, keyword, embedding, or QA model call is made by the graph snapshot step.

## Current Priority: Single-Hop Badcase Audit

Run this before expanding more expensive full-pipeline experiments:

```bash
python repro/export_badcase_pack.py \
  --data locomo \
  --model deepseek \
  --file stratified \
  --sample 30 \
  --output reports/badcase_pack_conv30_stratified_20260706.md
```

Expected:

- A small Markdown report under `reports/`.
- Cat4 single-hop cases clearly listed with question, gold, prediction, gold evidence, retrieved context, tool calls, and failure type.
- Manual notes added for whether each low-F1 single-hop case is a real wrong answer, paraphrase/F1 mismatch, image-related failure, retrieval miss, or tool-path drift.

Commit this report to GitHub.

Optional parallel task:

- If working on LongMemEval unblock, follow `docs/handoff.md` section "LongMemEval Recovery Procedure".
- First download `longmemeval_s_cleaned.json` from HuggingFace into `data/external/`.
- Then print the first sample schema and write a schema audit report.
- Do not directly rename the downloaded file to `data/dataset_LM.json`.
- Do not run full LM until a converter and loader validation pass.

## 0. Sync And Environment

If a long experiment is still running in this checkout, wait for it to finish before pulling new code. If the server has local committed results that are not on GitHub yet, push them first or use a separate clone.

```bash
cd /data/nishome/cuiwenjia/MRAgent-Reproduction
git status --short --branch
git log --oneline --decorate -5
git branch -vv
git pull --ff-only origin main
git status --short --branch
conda activate mragent-repro
```

Expected:

- Branch is `main`.
- Working tree is clean before new experiments.
- Python environment already has `openai`, `python-dotenv`, `numpy`, `torch`.

If dependency import fails:

```bash
pip install -r requirements.txt
```

## 1. Configure Secrets

Create or edit `.env` manually:

```bash
cp .env.example .env
nano .env
```

Required SiliconFlow settings:

```text
LLM_BASE_URL=https://api.siliconflow.cn/v1
OPENAI_API_KEY=<new key here>
DEEPSEEK_MODEL_ID=deepseek-ai/DeepSeek-V4-Pro
VLM_MODEL=Qwen/Qwen3.5-397B-A17B
VLM_MAX_TOKENS=1024
EMBED_MODEL=Qwen/Qwen3-Embedding-4B
```

Rules:

- Do not commit `.env`.
- Do not paste API keys into reports, logs, GitHub issues, or prompts.
- If an API key was exposed in chat, rotate it before formal runs.

## 2. Stage 1: VLM Tool Validation

First run a dry run:

```bash
python repro/validate_vlm_tool.py \
  --data locomo \
  --sample 30 \
  --limit 5 \
  --file stage1_vlm \
  --dry_run
```

Expected:

- Script finds 5 real image turns in `conv-30`.
- It writes a JSONL under `result/diagnostics/`.
- It writes a Markdown report under `reports/`.
- No API request is sent in dry-run mode.

Then run the real VLM validation:

```bash
python repro/validate_vlm_tool.py \
  --data locomo \
  --sample 30 \
  --limit 5 \
  --file stage1_vlm
```

Expected:

- At least 3 of 5 image URLs return non-empty visual evidence.
- JSONL records include event_id, image_url, caption, raw response metadata, usage, latency, and status.
- Markdown report summarizes ok/failed counts and per-image content previews.

Failure handling:

- If auth fails, check `.env` and SiliconFlow key validity.
- If every image fails, inspect whether image URLs are reachable from the server.
- If API response is empty, preserve the raw JSONL record and do not conclude that MRAgent failed.

Acceptance:

- Only after Stage 1 passes should VLM be considered available as a tool.
- This stage does not modify MRAgent QA behavior.

## 3. Stage 2: VLM-Enriched Rewrite Smoke

Purpose:

- Verify whether Qwen VLM can add visual facts before MRAgent rewrite.
- Keep the generated rewrite under `data/locomo/rewrite_deepseek_vlm/`.
- Do not overwrite `data/locomo/rewrite_deepseek/`.

Dry run:

```bash
python repro/run_vlm_enriched_rewrite.py \
  --data locomo \
  --model deepseek \
  --sample 30 \
  --file vlmrewrite_smoke \
  --limit_image_turns 10 \
  --max_sessions 3 \
  --dry_run
```

Real visual-evidence collection, no text rewrite yet:

```bash
python repro/run_vlm_enriched_rewrite.py \
  --data locomo \
  --model deepseek \
  --sample 30 \
  --file vlmrewrite_smoke \
  --limit_image_turns 10 \
  --max_sessions 3
```

Full VLM-enriched rewrite smoke:

```bash
python repro/run_vlm_enriched_rewrite.py \
  --data locomo \
  --model deepseek \
  --sample 30 \
  --file vlmrewrite_smoke \
  --limit_image_turns 10 \
  --max_sessions 3 \
  --rewrite
```

Expected:

- `reports/vlm_enriched_rewrite_vlmrewrite_smoke_*.md` exists.
- `result/diagnostics/vlm_enriched_rewrite_visual_vlmrewrite_smoke_*.jsonl` exists.
- `result/diagnostics/vlm_enriched_rewrite_sessions_vlmrewrite_smoke_*.jsonl` exists.
- With `--rewrite`, `data/locomo/rewrite_deepseek_vlm/conv-30_rewrite.json` exists.

Report requirements:

- Number of image turns found.
- Number of VLM calls attempted.
- Number of successful VLM evidence injections.
- Whether failures are due to image URL reachability, API/model response, or rewrite parsing.
- A short comparison against baseline rewrite for at least 3 image turns.

Do not claim:

- VLM-enhanced QA improvement.
- Benchmark reproduction.
- CBR/Q-learning effect.

## 4. Stage 3: Explore-50 Diagnostic Run

Definition:

- 5 LoCoMo conversation samples.
- 10 questions per sample.
- Total: 50 QA questions.
- This is exploratory diagnosis, not a validation/test split.

Fixed sample list:

```text
conv-30, conv-42, conv-44, conv-48, conv-50
```

Rationale:

- `conv-30` preserves continuity with the clean run.
- `conv-42`, `conv-44`, `conv-48`, and `conv-50` have enough image turns for later VLM-related badcase analysis.
- Every selected sample has enough category coverage for stratified sampling.

Run command:

```bash
python run_stratified.py \
  --data locomo \
  --model deepseek \
  --file explore50_vlmready \
  --sample_ids 30,42,44,48,50 \
  --per_category 2 \
  --total 10 \
  --seed 42
```

Expected:

- The runner processes exactly 5 samples.
- Each sample selects 10 stratified questions.
- Total expected QA count is 50.
- Result files are written under `result/locomo/` with tag `deepseek_explore50_vlmready`.
- Logs are written under `log/locomo/`.
- Existing rewrite/keyword/embedding caches may be reused if valid.

Important:

- This command does not yet inject VLM into QA.
- The purpose is to collect a wider baseline and failure traces after confirming that VLM is available.
- Do not overwrite or delete the earlier `stratified` clean run.

## 5. Required Report After Stage 3

Write:

```text
reports/explore50_vlmready_YYYYMMDD.md
```

Minimum contents:

- Command and commit hash.
- Exact sample list.
- Per-sample selected question counts.
- Per-category counts.
- Number of completed answers.
- Errors, schema retries, forced accepts.
- Runtime and average tool calls.
- Badcase table, especially:
  - image-related failures,
  - multi-hop synthesis failures,
  - temporal calculation failures,
  - `no information available` despite retrieved evidence.
- Paths to result files and logs.
- Whether caches were reused or regenerated.

Do not claim:

- Full paper reproduction.
- Benchmark reproduction.
- VLM-enhanced QA result.
- CBR/Q-learning effect.

## 6. Git Commit Rules

Commit only:

- Code changes.
- Markdown reports.
- Small metrics summaries.
- Small artifact manifests.

Do not commit:

- `.env`
- raw API keys
- full `result/`
- full `log/`
- embedding `.pkl`
- large rewrite/keyword caches

After the report is written:

```bash
git status --short
git add reports/explore50_vlmready_YYYYMMDD.md
git commit -m "reports: add explore50 VLM-ready diagnostic"
git push origin main
```

If generated files under `result/` or `log/` are needed for audit, write a small manifest with absolute server paths, file sizes, and SHA256 checksums instead of committing the raw files.
