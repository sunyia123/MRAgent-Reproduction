# VLM-Enriched Rewrite Report - 2026-07-03

## Purpose

Inject VLM visual evidence into the rewrite input without overwriting baseline rewrite caches.

## Configuration

- dataset: `locomo`
- text model short name: `deepseek`
- VLM model: `Qwen/Qwen3.5-397B-A17B`
- output suffix: `vlm`
- dry_run: `False`
- skip_vlm: `False`
- rewrite: `False`
- limit_image_turns: `10`
- max_sessions: `3`

## Samples

| sample | sessions | turns | image turns | VLM injected | caption-only image turns | rewrite path | status |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `conv-30` | 3 | 58 | 7 | 3 | 4 | `data/locomo/rewrite_deepseek_vlm/conv-30_rewrite.json` | prepared_only_no_rewrite_flag |

## Notes

- This is a rewrite-stage experiment, not a QA result.
- Baseline rewrite caches are not modified.
- If VLM URL access fails, the script records failures and falls back to caption-only input for those turns.
- Run keyword, embedding, and QA on this rewrite cache only after the rewrite structure is audited.
