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

- `data/dataset_LM.json` is tracked through Git LFS upstream.
- Current local clone hit upstream LFS quota: `This repository exceeded its LFS budget`.
- Until resolved, LongMemEval reproduction is blocked or must use an alternate legitimate dataset source.

What this means:

- Git LFS is used when a repository stores large files outside normal Git history.
- The normal Git checkout only contains a small pointer file. Git LFS then downloads the real large file.
- In this clone, GitHub refused the large-file download because the upstream repository exceeded its LFS bandwidth/storage budget.
- This is not a MRAgent code bug and not a local Python environment bug.
- LongMemEval cannot be treated as available until `data/dataset_LM.json` is the real dataset file, not a pointer.

Check:

```bash
git lfs ls-files
Get-Item data/dataset_LM.json
cat data/dataset_LM.json | head
```

Expected:

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
