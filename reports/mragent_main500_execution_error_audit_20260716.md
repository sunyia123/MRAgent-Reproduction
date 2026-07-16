# MRAgent 500q Execution Error Audit

Generated: 2026-07-16

## Summary

- Total questions: 500
- ERROR count: 5 / 500 (1.0%)
- Total tool calls: 3709
- Total reasoning rounds: 2374

## Error Cases

| Sample | Q# | Question | Failure | Attribution |
|--------|-----|----------|---------|-------------|
| conv-41 | Q054 | When did John help renovate his hometown community | schema_parse_exhaustion | LLM chat_text returned non-dict type after 3 failed JSON parse attempts (CHAT_TE |
| conv-43 | Q068 | What would be a good hobby related to his travel d | schema_parse_exhaustion | LLM chat_text returned non-dict type after 3 failed JSON parse attempts (CHAT_TE |
| conv-44 | Q029 | What is something that Audrey often dresses up her | schema_parse_exhaustion | LLM chat_text returned non-dict type after 3 failed JSON parse attempts (CHAT_TE |
| conv-47 | Q190 | What is the name of James's cousin's dog? | schema_parse_exhaustion | LLM chat_text returned non-dict type after 3 failed JSON parse attempts (CHAT_TE |
| conv-48 | Q024 | Why did Jolene sometimes put off doing yoga? | schema_parse_exhaustion | LLM chat_text returned non-dict type after 3 failed JSON parse attempts (CHAT_TE |

## Root Cause

All 5 errors stem from `chat_text` returning a non-dict type after exhausting `CHAT_TEXT_PARSE_MAX_ATTEMPTS=3` retries.
The LLM (deepseek-ai/DeepSeek-V4-Flash) produced truncated or malformed JSON that could not be parsed even with retry.

4 cases: returned `str` instead of `dict` (expected JSON object)
1 case (conv-44 Q029): returned `list` instead of `dict`

## Impact

- 5/500 = 1.0% error rate — within the 5% threshold
- All failures occurred in pre-agent phase (keyword selection / tag scoring) — no tool calls were made
- Each failure was caught by the top-level try/except in `answer_questions._run_one` and returned as ERROR prediction

## Recommendations

1. Increase CHAT_TEXT_PARSE_MAX_ATTEMPTS for the sorting/meta operations
2. Add JSON repair (`ENABLE_JSON_REPAIR=1`) for the tag-sort and keyword selection stages
3. Consider shorter prompts or lower max_tokens for the sort operations to reduce truncation risk
