# Codex Experience Review

## Project Role

This repository is the working reproduction and extension project for:

- Paper: `Memory is Reconstructed, Not Retrieved: Graph Memory for LLM Agents`
- arXiv: https://arxiv.org/abs/2606.06036
- Upstream code: https://github.com/Ji-shuo/MRAgent

Memento is used only as a design reference for case-based reasoning, Q-learning-style utility estimation, and experiment handoff discipline. Do not treat Memento as the primary codebase.

## Operating Rules

1. Preserve upstream MRAgent as read-only `upstream`.
2. Use private `origin` for all local/server synchronization.
3. Do not commit `.env`, API keys, full logs, generated embeddings, checkpoints, SQLite caches, or large raw experiment outputs.
4. Commit code, documentation, configuration templates, small result summaries, and reproducible scripts.
5. Every experiment must write a Markdown summary under `reports/` and a machine-readable summary under `reports/*.csv` or `reports/*.json`.
6. Every failed run must record the concrete failure: environment, command, error line, expected behavior, and next fix.
7. If an experiment claims a memory module is active, verify the trace contains actual retrieved memories/tool calls. Empty retrieval must fail fast, not silently continue.

## Required Review Before New Work

Before changing code or running server experiments, read:

1. `README.md`
2. `docs/goal.md`
3. `docs/handoff.md`
4. `docs/reproduction_plan.md`
5. `docs/intermediate_artifact_checklist.md`

## Reproduction Discipline

For each run, record:

- Git commit and branch.
- Dataset and subset.
- Model and API backend.
- Exact command.
- Whether generated rewrite/keyword/embedding caches were reused.
- Number of questions attempted and completed.
- Accuracy / F1 / LLM-judge result.
- Evidence recall if available.
- Average turns, tool calls, tokens, and runtime if available.
- Failure cases with original question, gold answer, prediction, retrieved evidence, and graph traversal path.
- Intermediate artifact status: rewrite, keyword, embedding, memory audit, metrics, clean logs, and artifact manifest.

If intermediate artifacts are missing, stop and document the gap before running more samples. Do not describe the run as a valid reproduction until `docs/intermediate_artifact_checklist.md` passes.

## Extension Discipline

For CBR/Q-learning-style extensions, do not claim improvement unless:

1. A baseline MRAgent run on the same cached data exists.
2. The extension actually injects or uses retrieved cases/policy scores.
3. The trace shows which tool/action/event choices changed.
4. Fixed and broken cases are reported against the same baseline.
5. Data leakage across conversations/samples is explicitly ruled out.
