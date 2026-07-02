# MRAgent Reproduction Handoff

## Repository Setup

This project uses a two-remote workflow:

```bash
git remote -v
```

Expected:

```text
origin   https://github.com/sunyia123/MRAgent-Reproduction.git
upstream https://github.com/Ji-shuo/MRAgent.git
```

- `upstream` is read-only and tracks the official MRAgent repository.
- `origin` is the private synchronization repository for local and server work.

## First Sync

```bash
cd ~/repro
git clone https://github.com/sunyia123/MRAgent-Reproduction.git
cd MRAgent-Reproduction
git status --short --branch
```

Expected:

- Current branch is `main`.
- Working tree is clean.
- Documentation under `docs/` is present.

## Git Safety And Force-Push Rules

Force-push means rewriting the remote branch pointer to a different commit history.
Example commands include:

```bash
git push --force origin exp/...
git push --force-with-lease origin exp/...
```

Why this matters:

- A normal push adds commits. A force-push can remove previously pushed commits from the GitHub branch view.
- If those removed commits contained reports, logs, metrics, or manifests, they disappear from that branch on GitHub.
- Force-push does not directly delete ignored server files such as `data/locomo/rewrite_*` or `embedding.pkl`.
- However, after a force-push, commands such as `git reset --hard`, `git clean -fdx`, deleting/recloning the repo, or switching to a branch that lacks tracked files can delete local tracked/untracked/ignored artifacts depending on the command.
- Therefore, a force-push can make evidence hard to recover even if it does not itself erase every server-side cache.

Rules:

- Never force-push `main`.
- Do not force-push a shared experiment branch after results have been reported.
- Prefer a new corrective commit over rewriting history.
- If history rewrite is unavoidable, use `--force-with-lease`, not plain `--force`.
- Before any force-push, create a safety tag:

```bash
git tag backup/YYYYMMDD-HHMM-before-force
git push origin backup/YYYYMMDD-HHMM-before-force
```

- Before any force-push, write or update an artifact manifest with remote paths, file sizes, and checksums.
- After a force-push, explicitly state which commits were replaced and whether any reports/results/logs were removed from the branch.

Commands to inspect whether a branch was rewritten:

```bash
git fetch origin --prune
git log --oneline --decorate --graph --all -20
git reflog --date=iso
git diff --name-status origin/main..origin/exp/20260701-stage-b-eval-audit
```

Do not use these commands unless explicitly approved:

```bash
git reset --hard
git clean -fdx
rm -rf data/locomo log result reports
```

## Environment

Recommended:

```bash
conda create -n mragent-repro python=3.10 -y
conda activate mragent-repro
pip install -r requirements.txt
python -c "import openai, torch, numpy, requests; print('ok')"
```

Expected:

- Python imports succeed.
- CPU torch is sufficient for upstream MRAgent; GPU is not required for baseline.

Failure handling:

- If dependency resolution fails, record the exact pip error in `reports/environment_check_YYYYMMDD.md`.
- Do not edit requirements blindly; first identify whether the error is Python version, package conflict, or network.

## Secrets

Create `.env` manually:

```bash
cp .env.example .env
```

Then fill:

```text
OPENROUTER_API_KEY=
```

Rules:

- Never commit `.env`.
- Never paste API keys into issue text, reports, prompts, or command history.
- If a key has appeared in chat, rotate it before formal experiments.

## Data

LoCoMo:

- `data/dataset_locomo.json` is tracked and should be usable immediately.

LongMemEval:

- `data/dataset_LM.json` is tracked through Git LFS in the upstream repository.
- The real LFS object was not available when this private reproduction repository was created.
- This private repository intentionally does not track `data/dataset_LM.json` until the real dataset is obtained.
- Until resolved, LongMemEval reproduction is blocked or must use an alternate legitimate dataset source.

What this means:

- Git LFS is used when a repository stores large files outside normal Git history.
- The normal Git checkout only contains a small pointer file. Git LFS then downloads the real large file.
- If only the pointer is pushed to the private repository, fresh clones fail because Git LFS tries to download a large object that is not present in the private repository.
- This is not a MRAgent code bug and not a local Python environment bug.
- LongMemEval cannot be treated as available until `data/dataset_LM.json` is the real dataset file, not a pointer.

If a clone failed with `smudge filter lfs failed`:

```bash
cd /data/nishome/cuiwenjia/MRAgent-Reproduction
GIT_LFS_SKIP_SMUDGE=1 git checkout -f HEAD
git pull --ff-only origin main
```

Check:

```bash
git lfs ls-files
ls -lh data/dataset_LM.json
head data/dataset_LM.json
```

Expected:

- If the file is missing, LongMemEval is not ready.
- If the file is a small pointer and contains `version https://git-lfs.github.com/spec/v1`, LongMemEval is not ready.
- If the file is hundreds of MB, LongMemEval is ready.

Required handling:

- Prefer LoCoMo for the first reproducible baseline.
- Before any LongMemEval experiment, record the dataset source, file size, checksum, and acquisition method.
- Do not fabricate, truncate, or silently replace `dataset_LM.json`.

## Baseline Smoke

Run one LoCoMo sample:

```bash
python run.py --data locomo --model gemini --file smoke --sample 0
```

Expected:

- Rewrite, keyword, embedding artifacts are created under `data/locomo/`.
- Prediction JSONL is created under `result/locomo/`.
- Logs are created under `log/locomo/`.

Failure handling:

- If API auth fails, check `.env`.
- If embedding fails, check OpenRouter model access and `llm/embeddings.py`.
- If output format validation fails, preserve raw error and sample id.

## Current Next Experiments

Before continuing from the current MRAgent state, read:

```bash
cat docs/claude_code_next_steps.md
```

Current priority:

1. Validate Qwen/Qwen3.5-397B-A17B as a standalone visual-evidence tool.
2. Run a 50-question exploratory LoCoMo subset after VLM connectivity is confirmed.
3. Before calling anything a benchmark reproduction, read `docs/benchmark_reproduction_plan.md`.

Stage 1 command:

```bash
python repro/validate_vlm_tool.py \
  --data locomo \
  --sample 30 \
  --limit 5 \
  --file stage1_vlm
```

Expected:

- At least 3 real image turns return non-empty VLM evidence.
- JSONL is written under `result/diagnostics/`.
- A Markdown validation report is written under `reports/`.
- This is tool validation only; it is not a QA benchmark.

Stage 2 command:

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

- Exactly 5 conversation samples are processed.
- Exactly 10 questions are selected per sample.
- The intended total is 50 QA questions.
- Results are exploratory diagnostics, not a formal validation/test split.
- This run does not yet inject VLM output into MRAgent QA.
- This run is not a paper benchmark reproduction.

Required after Stage 2:

- Write `reports/explore50_vlmready_YYYYMMDD.md`.
- Report exact sample list, selected question counts, category distribution, errors, runtime, tool calls, and badcases.
- Do not claim CBR/Q-learning effect from this run.
- Do not claim full paper reproduction from this run.

## Benchmark Reproduction Requirements

Read:

```bash
cat docs/benchmark_reproduction_plan.md
```

MRAgent benchmark reproduction must cover, or explicitly document inability to cover:

- LoCoMo.
- LongMemEval.
- Standard RAG baseline.
- A-Mem baseline.
- MemoryOS baseline.
- LangMem baseline.
- Mem0 baseline.

Current dataset status:

- `data/dataset_locomo.json` is available locally, but current private repo copy contains 10 conversation samples and 1986 QA items.
- The paper-level LoCoMo data scale must be verified before claiming full LoCoMo reproduction.
- `data/dataset_LM.json` is not available as a real LongMemEval JSON file in this private repository.

Hard rule:

- `explore50_vlmready` is a diagnostic subset.
- It must not be reported as benchmark reproduction.
- A benchmark report must include dataset size, sample ids, question count, category distribution, baseline name, result paths, evaluation paths, and whether the data scale matches the paper.

## Intermediate Artifact Review

Before reporting any experiment as successful, read:

```bash
cat docs/intermediate_artifact_checklist.md
```

Required minimum evidence:

- `result/*.jsonl`: final predictions with gold answer, category, evidence, prediction context, and per-question metrics.
- `result/*metrics*.json`: aggregate F1 / judge / runtime / tool-call summary.
- `result/*memory_audit*.json`: rewrite, keyword, and estimated graph quality summary.
- `reports/*.md`: human-readable report with command, commit, model, dataset subset, failures, and next action.
- A clean or clearly segmented log showing the valid run, not only earlier failed attempts.
- An artifact manifest recording rewrite, keyword, embedding, result, log, metrics, and memory-audit paths.

Large generated caches may stay on the server, but their existence must be auditable:

```bash
ls -lh data/locomo/rewrite_<model>/<sample>_rewrite.json
ls -lh data/locomo/keyword_<model>/<sample>_keyword.json
ls -lh data/locomo/embedding/*/<sample>_embedding.pkl
sha256sum data/locomo/rewrite_<model>/<sample>_rewrite.json
sha256sum data/locomo/keyword_<model>/<sample>_keyword.json
sha256sum data/locomo/embedding/*/<sample>_embedding.pkl
```

Required checks:

- Rewrite must not contain silent `null` sessions.
- Keyword sentence count must align with rewrite sentence count, or the report must explain the gap.
- Embedding question count must cover every selected question original index.
- Memory audit must report node/edge/topic/persona counts.
- Logs must be checked for `Traceback`, `ERROR`, `IndexError`, `ValueError`, and timeout patterns.
- Judge files must not be polluted by repeated append runs.

If any of these are missing:

- Stop expanding the experiment.
- Do not merge the experiment branch into `main`.
- Do not write "reproduction succeeded".
- First add the missing audit summary or an `artifact_manifest_*.json` explaining remote paths, file sizes, checksums, and why the raw artifact is not committed.

## OpenAI-Compatible Provider Notes

OpenAI-compatible means the provider exposes endpoints shaped like the OpenAI API, usually:

```text
/v1/chat/completions
/v1/embeddings
```

This does not guarantee identical behavior across providers or models.

Must verify for each provider/model:

- Whether `message.content` contains the final answer.
- Whether important output is instead placed in `reasoning_content`.
- Whether `tool_calls` follow the OpenAI schema exactly.
- Whether `response_format={"type":"json_object"}` is supported.
- Whether strict JSON schema output is supported.
- Whether `parallel_tool_calls` is ignored, rejected, or honored.
- Whether `seed` is ignored.
- Whether `max_tokens` is interpreted as output tokens, total tokens, or provider-specific limit.
- Whether `finish_reason` reports `stop`, `length`, `tool_calls`, or provider-specific values.
- Whether `usage.prompt_tokens`, `usage.completion_tokens`, and `usage.total_tokens` are present and reliable.

If a run fails under an OpenAI-compatible provider, do not immediately conclude that the model is weak. First identify whether the failure is caused by provider compatibility, response parsing, token truncation, schema mismatch, or prompt fragility.

## Model Diagnostic Evidence Requirements

When rewrite, keyword extraction, tool calling, or evaluation fails, the experiment report must include enough evidence to distinguish model capability from implementation/provider issues.

Required for every failed rewrite/keyword session:

- Raw prompt sent to the model, with API keys and private secrets redacted.
- Raw API response, with secrets redacted.
- `message.content`.
- `reasoning_content`, if the provider returns it.
- `finish_reason`.
- `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`.
- JSON parse error text.
- Schema validation error text.
- Whether `max_tokens` truncation occurred or is suspected.
- Retry number, retry temperature, output length, and error type.
- Whether the output was `None`, empty string, invalid JSON, valid JSON with null fields, or valid JSON failing schema.

Required comparison tests before blaming a model:

- DeepSeek-V4-Pro with current settings.
- DeepSeek-V4-Pro with `response_format={"type":"json_object"}` if the provider supports it.
- DeepSeek-V4-Pro with larger `max_tokens`, at least 16384 and preferably 32768 if supported.
- Qwen3-235B on the same failed sessions.
- Gemini-2.5-Flash or Claude-Sonnet-4.5 on the same failed sessions, because these are closer to the original paper/repository settings.

Minimum diagnostic subset:

```text
1 known-success session
3 failed sessions
same prompt
same parser
same schema checker
same report format
```

For the current `conv-30` investigation, use:

```text
failed sessions: 6, 8, 17 if available
plus one successful session from the same rewrite file
```

Required diagnostic artifact:

```text
reports/model_diagnostics_YYYYMMDD.md
result/locomo/model_diagnostic_manifest_YYYYMMDD.json
```

The manifest must include:

```json
{
  "run_id": "",
  "sample_id": "conv-30",
  "session_id": "",
  "model": "",
  "provider": "",
  "base_url": "",
  "response_format": "",
  "max_tokens": 0,
  "temperature": 0.0,
  "retry_id": 0,
  "prompt_sha256": "",
  "raw_response_sha256": "",
  "content_length": 0,
  "reasoning_content_length": 0,
  "finish_reason": "",
  "usage": {
    "prompt_tokens": null,
    "completion_tokens": null,
    "total_tokens": null
  },
  "parse_status": "ok|json_parse_error|schema_error|empty|truncated|unknown",
  "parse_error": "",
  "schema_error": "",
  "output_status": "valid|valid_with_null_fields|invalid|none"
}
```

Raw prompts/responses may be kept on the server if large, but the report must record their absolute paths, sizes, checksums, and redaction status. Do not commit secrets.

## Evaluation

```bash
python eval/evaluate_reasoning.py --data locomo --model gemini --file smoke --allfile
```

Expected:

- Evaluation file is written.
- LLM-judge correctness and F1/EM summary are available.

## Branch Protocol

Use experiment branches:

```bash
git pull --ff-only origin main
git switch -c exp/YYYYMMDD-short-topic
```

Commit only:

- Code changes.
- Scripts.
- Small data subsets.
- Markdown/CSV/JSON summaries.
- Configuration templates.

Do not commit:

- `.env`
- `result/`
- `log/`
- `data/locomo/rewrite_*`
- `data/locomo/keyword_*`
- `data/locomo/embedding/`
- checkpoints
- large raw artifacts

## Required Report Per Experiment

Write `reports/<experiment_name>_YYYYMMDD.md` with:

1. Purpose.
2. Branch and commit.
3. Dataset/subset.
4. Model/backend.
5. Command.
6. Expected result.
7. Actual result.
8. Metrics.
9. Failure cases.
10. Next action.
11. Intermediate artifact status: rewrite, keyword, embedding, memory audit, trace, metrics, and manifest.
12. Whether the run passes `docs/intermediate_artifact_checklist.md`.
