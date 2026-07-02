# VLM Tool Validation - 2026-07-02

## Purpose

Validate Qwen VLM as a standalone visual-evidence tool before integrating it into MRAgent QA.

## Configuration

- dataset: `locomo`
- sample: `conv-30`
- model: `Qwen/Qwen3.5-397B-A17B`
- limit: `5`
- dry_run: `False`

## Result Summary

- records: 5
- ok: 0
- failed: 5

## Per Image Turn

| # | event_id | session | status | finish_reason | latency_s | content preview |
| --- | --- | --- | --- | --- | ---: | --- |
| 1 | `D1:14` | `session_1` | error | None |  | BadRequestError("Error code: 400 - {'code': 20040, 'message': 'The image URL must be a valid and downloadable URL or ... |
| 2 | `D1:17` | `session_1` | error | None |  | BadRequestError("Error code: 400 - {'code': 20040, 'message': 'The image URL must be a valid and downloadable URL or ... |
| 3 | `D1:20` | `session_1` | error | None |  | BadRequestError("Error code: 400 - {'code': 20040, 'message': 'The image URL must be a valid and downloadable URL or ... |
| 4 | `D1:24` | `session_1` | error | None |  | BadRequestError("Error code: 400 - {'code': 20040, 'message': 'The image URL must be a valid and downloadable URL or ... |
| 5 | `D2:4` | `session_2` | error | None |  | BadRequestError("Error code: 400 - {'code': 20040, 'message': 'The image URL must be a valid and downloadable URL or ... |

## Acceptance Criteria

- At least 3 real LoCoMo image URLs return non-empty visual evidence.
- Each record contains event_id, image_url, caption, raw response metadata, usage, and latency.
- Failures are classified as API failure, image URL failure, model failure, or parse failure in the JSONL.
- This report is only a VLM tool check; it is not a QA benchmark result.
