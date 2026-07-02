# Claude Code Next Steps: VLM Validation And Explore-50

This document is the current server-side execution instruction. It covers only the next two stages:

1. Validate Qwen VLM as a standalone visual-evidence tool.
2. Run a 50-question exploratory LoCoMo subset after VLM connectivity is confirmed.

Do not treat these two stages as full paper reproduction.

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

Optional parallel task:

- If working on LongMemEval unblock, follow `docs/handoff.md` section "LongMemEval Recovery Procedure".
- First download `longmemeval_s_cleaned.json` from HuggingFace into `data/external/`.
- Then print the first sample schema and write a schema audit report.
- Do not directly rename the downloaded file to `data/dataset_LM.json`.
- Do not run full LM until a converter and loader validation pass.

## 0. Sync And Environment

```bash
cd /data/nishome/cuiwenjia/MRAgent-Reproduction
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
EMBED_MODEL=Qwen/Qwen3-Embedding-8B
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

## 3. Stage 2: Explore-50 Diagnostic Run

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

## 4. Required Report After Stage 2

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

## 5. Git Commit Rules

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
