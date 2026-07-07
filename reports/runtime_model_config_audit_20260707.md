# Runtime Model Configuration Audit — 2026-07-07

## Scope

This audit checks whether current experiment commands actually use the intended
SiliconFlow DeepSeek/Qwen models, and whether old Gemini/Claude defaults can still
affect MRAgent medium-core validation.

## Key Finding

The command below is not a valid medium-core validation command:

```text
/data/nishome/cuiwenjia/MRAgent-Reproduction/.venv/bin/python3 run_stratified.py --sample_ids 26 --model deepseek
```

It has three problems:

1. No `--subset_manifest`, so it does not use the fixed 100-question manifest.
2. No `--file mragent_100q`, so results are written under `_deepseek_0`.
3. No `--re_model v4flash`, so rewrite/keyword follow the main model.

After the config fix, `--model deepseek` resolves to:

```text
MODEL=deepseek-ai/DeepSeek-V4-Pro
LLM_BASE_URL=https://api.siliconflow.cn/v1
```

but the command is still not the intended 100q experiment.

## Required Preflight

Before every server run, execute:

```text
python repro/audit_runtime_config.py \
  --data locomo \
  --sample_ids 26 \
  --model deepseek \
  --re_model v4flash \
  --file mragent_100q \
  --subset_manifest data/subsets/locomo10_100q_seed42.json
```

Expected core fields:

```text
MODEL=deepseek-ai/DeepSeek-V4-Pro
RE_MODEL=deepseek-ai/DeepSeek-V4-Flash
LLM_BASE_URL=https://api.siliconflow.cn/v1
SUBSET_MANIFEST=data/subsets/locomo10_100q_seed42.json
ADDITIONAL_RE=_deepseek_mragent_100q
result_template=result/{dataset}/{sample_id}_result_deepseek_mragent_100q.jsonl
```

## Code Locations Checked

| File | Finding |
|---|---|
| `common/config.py` | Fixed model alias resolution. Added `v4pro`, `v4flash`, `qwen397`; `deepseek` now defaults to V4-Pro, not V3; SiliconFlow models default to SiliconFlow base URL. |
| `agent/agent.py` | rewrite/keyword and rerank calls use `config.RE_MODEL`. |
| `memory/controller.py` | tag reranking uses `config.RE_MODEL`. |
| `llm/controller.py` | default function arguments still show `config.MODEL`, but callers pass explicit models for current pipeline paths; timeout logs now include stage. |
| `llm/embeddings.py` | embedding model is controlled by `EMBED_MODEL`; if `EMBED_BASE_URL` is SiliconFlow and `EMBED_MODEL` is unset, default is now `Qwen/Qwen3-Embedding-4B`. |
| `eval/judge.py` | judge model is controlled by `JUDGE_MODEL`; default remains `openai/gpt-4o-mini`, so SiliconFlow-only runs must set a local judge model explicitly. |
| `README.md` / old docs | Many historical examples still mention Gemini/Claude; current medium-core validation should follow `docs/medium_core_validation_handoff.md`. |

## Remaining Risk

`agent.py` has a Gemini-specific branch:

```text
if config.MODEL_NAME == "gemini":
    ...
```

This branch only runs when `--model gemini`; it is not active for `--model deepseek`.
It is not the current timeout cause.

## Operational Rule

Do not infer the real model from the shell command alone. Always use:

```text
repro/audit_runtime_config.py
repro/audit_api_models.py
```

The first proves intended config before the run. The second proves actual API
calls after the run.
