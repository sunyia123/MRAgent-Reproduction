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

## Minimal Smoke

```bash
conda create -n mragent-repro python=3.10 -y
conda activate mragent-repro
pip install -r requirements.txt
cp .env.example .env
python run.py --data locomo --model gemini --file smoke --sample 0
```

Do not run full experiments before the smoke report is written.

