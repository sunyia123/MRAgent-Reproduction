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
| conv-44 | Q029 | What is something that Audrey often dresses up her | schema_type_mismatch | LLM chat_text returned a JSON list where a dict was required; exact caller unverified |
| conv-47 | Q190 | What is the name of James's cousin's dog? | schema_parse_exhaustion | LLM chat_text returned non-dict type after 3 failed JSON parse attempts (CHAT_TE |
| conv-48 | Q024 | Why did Jolene sometimes put off doing yoga? | schema_parse_exhaustion | LLM chat_text returned non-dict type after 3 failed JSON parse attempts (CHAT_TE |

## Root Cause

All 5 errors occur before the main tool loop. Four can be located at `Agent.select_key_tag()`: the code expects `chat_text()` to return a dict and immediately calls `key_out.get("tag_scores")` without validating the root type.

- 4 cases: all 3 JSON parse attempts failed, `chat_text()` returned the last raw string, and `.get()` raised on `str`.
- 1 case (`conv-44 Q029`): JSON parsing returned a list rather than the required object, and `.get()` raised on `list`. The uploaded evidence has neither the raw response nor a complete traceback, so it does not identify whether this was the question-key or tag-score caller.

The common cause is a missing structured-output contract between `chat_text()` and callers that require dictionaries. Existing evidence does not establish that all outputs were truncated: proving truncation requires the original `finish_reason`, token usage and complete response.

## Impact

- 5/500 = 1.0% error rate — within the 5% threshold
- All failures occurred in pre-agent phase (keyword selection / tag scoring) — no tool calls were made
- Each failure was caught by the top-level try/except in `answer_questions._run_one` and returned as ERROR prediction

## Trace Evidence Limit

The five trace summaries are useful for locating the stage and direct exception, but the files named `raw_prompts` and `raw_responses` contain placeholder notes rather than the original API records. They have no request IDs, complete messages, response content, finish reason or token usage. Four log excerpts also include lines from the preceding question. Per-attempt truncation and retry behavior therefore remain unverified.

## Recommendations

1. Validate that tag-score output is a dict containing a dict-valued `tag_scores`; retry or use a deterministic fallback otherwise.
2. Do not return an unvalidated raw string from `chat_text()` to callers that require JSON objects.
3. Re-run only the five failed questions after the boundary fix and preserve before/after rows.
4. Re-extract request-linked raw records from the per-run API log before making a truncation claim.
