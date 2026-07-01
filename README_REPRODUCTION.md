# MRAgent Reproduction Workspace

This private fork is the reproducibility and extension workspace for MRAgent.

Read first:

1. `docs/goal.md`
2. `docs/handoff.md`
3. `docs/reproduction_plan.md`
4. `docs/intermediate_artifact_checklist.md`
5. `.agents/codex_experience_review.md`

## Local Path

```text
D:\Desktop\Study\0-Project\MRAgent-Reproduction
```

## GitHub

```text
https://github.com/sunyia123/MRAgent-Reproduction
```

## Current Status

- Official MRAgent code is checked out at upstream commit `7441506`.
- `upstream` points to `https://github.com/Ji-shuo/MRAgent.git`.
- `origin` points to the private reproduction repository.
- LoCoMo data is available.
- LongMemEval data is currently blocked because the upstream Git LFS object was not available.

LongMemEval blocker:

`data/dataset_LM.json` is intentionally not tracked in this private reproduction repository. During initial setup, only the Git LFS pointer was available, not the real 275MB dataset object. Keeping that pointer makes fresh clones fail because Git LFS tries to download an object that does not exist in this private repository. Treat LongMemEval as unavailable until the real dataset is obtained and verified as a hundreds-of-MB JSON file.

Check:

```bash
ls -lh data/dataset_LM.json
head data/dataset_LM.json
```

If the file is missing, LongMemEval is not ready. If the file starts with `version https://git-lfs.github.com/spec/v1`, it is only a pointer file and cannot be used for reproduction.

## Minimal Smoke

```bash
conda create -n mragent-repro python=3.10 -y
conda activate mragent-repro
pip install -r requirements.txt
cp .env.example .env
python run.py --data locomo --model gemini --file smoke --sample 0
```

Do not run full experiments before the smoke report is written.

## Review Gate

Before accepting any remote experiment as a valid reproduction result, check:

```text
docs/intermediate_artifact_checklist.md
```

If rewrite, keyword, embedding, memory audit, metrics, logs, or artifact manifest are missing, the run is only a partial result and must not be treated as paper-level reproduction.

Also read the `Git Safety And Force-Push Rules` and `Model Diagnostic Evidence Requirements` sections in `docs/handoff.md` before rewriting branch history or blaming a model for failed structured extraction.
