# MRAgent Reproduction Workspace

This private fork is the reproducibility and extension workspace for MRAgent.

Read first:

1. `docs/goal.md`
2. `docs/handoff.md`
3. `docs/reproduction_plan.md`
4. `.agents/codex_experience_review.md`

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
- LongMemEval data is currently blocked by GitHub LFS quota on upstream.

LongMemEval blocker:

`data/dataset_LM.json` may appear in the working tree, but the current clone only has the Git LFS pointer because the upstream repository exceeded its LFS budget. This means the real LongMemEval dataset has not been downloaded. Treat LongMemEval as unavailable until the file is verified as a real hundreds-of-MB JSON file.

Check:

```bash
ls -lh data/dataset_LM.json
head data/dataset_LM.json
```

If the file starts with `version https://git-lfs.github.com/spec/v1`, it is only a pointer file and cannot be used for reproduction.

## Minimal Smoke

```bash
conda create -n mragent-repro python=3.10 -y
conda activate mragent-repro
pip install -r requirements.txt
cp .env.example .env
python run.py --data locomo --model gemini --file smoke --sample 0
```

Do not run full experiments before the smoke report is written.
