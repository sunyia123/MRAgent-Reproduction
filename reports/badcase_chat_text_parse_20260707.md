# chat_text JSON Parse Failures

Generated: 2026-07-07

## Root Cause

`llm/controller.py:chat_text()` expects JSON output from the model but some LLM
responses are plain text (dates, short answers, full sentences). The old code
returned `None` after exhausting retries, causing downstream `AttributeError:
'NoneType' object has no attribute 'items'` crashes.

## Fix (commit: upcoming)

`chat_text` now wraps the last raw text as `{"_fallback_text": "..."}` instead
of returning `None`. A `chat_text_fallback` entry is written to
`result/diagnostics/api_call_log.jsonl` for every occurrence.

## Prompt Location

- `prompts/prompts.py:104-116` — `ANSWER_SORT_PROMPT` / `ANSWER_SORT_PROMPT2` (sort/re-rank stage)
- `agent/agent.py:260-265` — `select_finegrained_sentence_sort()`
- `agent/agent.py:326-338` — `select_finegrained_sentence_sort()` (sort prompt variant)
- `agent/agent.py:415-431` — `select_key_tag()`

## Historical Occurrences (from server run logs)

| Date | head | Notes |
|------|------|-------|
| 2026-07-06 | `2023-01-19` | RAG plain-text answer |
| 2026-07-06 | `2023-01-15` | RAG plain-text answer |
| 2026-07-06 | `They both like to dance to destress.` | RAG plain-text answer |
| 2026-07-06 | `By the water` | RAG plain-text answer |
| 2026-07-06 | `2023-02-14` | RAG plain-text answer |
| 2026-07-06 | `no information available` | RAG plain-text answer |
| 2026-07-06 | `Jon decided to start his dance studio because he is passionate...` | RAG long answer |
| 2026-07-07 | `They both have a passion for dance.` | MRAgent sort stage, conv-30 |

Note: July 6 failures were from the old Standard RAG script which used `chat_text`
for plain-text QA. That was fixed separately by switching to `chat_with_tool`
in the RAG baseline (commit aadcf7e).
