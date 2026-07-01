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
