# conv-26 Rewrite Cache Audit — 2026-07-07

**Audit time:** 2026-07-07T20:08:35 CST  
**File:** `data/locomo/rewrite_deepseek/conv-26_rewrite.json.tmp`  
**Commit:** `e1198dfdf84de533f91094ede80195ff5434f922`

---

## Raw Statistics

| Metric | Value |
|---|---|
| File size | 9,705 bytes |
| Total raw lines | 1 |
| Parsable JSON lines | 1 |
| Empty lines | 0 |
| Parse errors | 0 |
| Skip markers | 0 |

## Session Detail

| Line | Session ID | conversation_time | Sentences | Topics | Personal Sentences | Skip Marker | Valid |
|:---:|---|---:|---:|---:|:---:|:---:|
| 1 | session_1 | 2023-05-08 | 37 | 12 | 17 | ❌ | ✅ |

## Valid Prefix Count: **1**

Only session_1 is present and valid.

## Missing Sessions (18/19)

`session_2` `session_3` `session_4` `session_5` `session_6` `session_7` `session_8` `session_9` `session_10` `session_11` `session_12` `session_13` `session_14` `session_15` `session_16` `session_17` `session_18` `session_19`

## Contradiction with `experiment_status_20260707.md`

`experiment_status_20260707.md` (line 33) states:

> `.tmp` file: `data/locomo/rewrite_deepseek/conv-26_rewrite.json.tmp` — 17 lines
> - sessions 1–8: completed
> - sessions 9–17: skipped (skip markers)
> - sessions 18–19: pending

**This is incorrect.** The .tmp currently contains **1 line** (session_1 only), not 17. The discrepancy has two causes:

1. **Original state** (before 19:00 CST 2026-07-07): the .tmp had 17 lines — sessions 1-8 valid, 9-17 skip markers from `smart_retry_batch.py`. This matches the report.

2. **Cleanup step** (19:00 CST): skip markers (sessions 9-17) were stripped per audit rules, leaving 8 valid sessions.

3. **`_truncate_jsonl_prefix` bug** (19:14 CST): when `run_stratified.py --model deepseek` resumed, `_rewrite_partial_progress` encountered blank lines between JSON records (introduced by the cleanup script writing `line + '\n'` when `line` already had `\n`). The function `break`s on empty lines (line 110), returning `completed=1` instead of `8`. `_truncate_jsonl_prefix` then truncated the file to 1 line, destroying sessions 2-8.

## Root Cause Chain

```
cleanup script: f.write(line + '\n')  # line already has \n → double \n
    ↓
_rewrite_partial_progress: if not line: break  # hits blank line after session_1
    ↓
_truncate_jsonl_prefix: lines[:1]  # deletes sessions 2-8
```

## Fix Status

- `_rewrite_partial_progress` and `_keyword_partial_progress` empty-line handling: **fixed in stash `stash@{0}`** (`break` → `continue`)
- `_truncate_jsonl_prefix` backup before truncation: **fixed in main `ba64913`** (merged)
- Sessions 2-8 data: **lost** (not in git, no backup). Must be regenerated via API.

## Conclusion

- **Skip markers found:** 0 in current .tmp (were 9 in original, cleaned up)
- **Valid sessions:** 1 (session_1)
- **Missing:** sessions 2-19 (18 sessions)
- **Ready to resume:** No — sessions 2-8 must be regenerated first
- **`experiment_status_20260707.md` is stale:** needs update to reflect current 1-line state
