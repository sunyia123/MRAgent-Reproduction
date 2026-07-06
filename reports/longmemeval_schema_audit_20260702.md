# LongMemEval Schema Audit Report — 2026-07-02

## 1. Source

| Field | Value |
|-------|-------|
| Dataset | `xiaowu0162/longmemeval-cleaned` |
| File | `longmemeval_s_cleaned.json` |
| URL | `https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned` |
| Download | `curl -L -o data/external/longmemeval_s_cleaned.json https://hf-mirror.com/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_s_cleaned.json` |
| Local path | `data/external/longmemeval_s_cleaned.json` (not committed) |
| File size | 277,496,593 bytes (~265 MB) |
| SHA256 | `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442` |

## 2. LFS Pointer Check

```
head -c 200 data/external/longmemeval_s_cleaned.json
```

Result: `[\n    {\n        "question_id": "e47becba",` — **real JSON, not a Git LFS pointer.** ✅

## 3. HuggingFace Schema

Top-level: `list[500]`

Each item is a dict with 9 keys:

| Key | Type | Description |
|-----|------|-------------|
| `question_id` | `str` | Hex string, unique per sample |
| `question_type` | `str` | One of 6 LM categories |
| `question` | `str` | QA question text |
| `question_date` | `str` | Format `YYYY/MM/DD (Day) HH:MM` |
| `answer` | `str` | Gold answer |
| `answer_session_ids` | `list[str]` | Evidence session IDs |
| `haystack_sessions` | `list[list[dict]]` | 53 sessions per sample, each a list of `{"role","content"}` turns |
| `haystack_session_ids` | `list[str]` | Session identifiers |
| `haystack_dates` | `list[str]` | Session dates, aligned with haystack_sessions |

### Question type distribution (500 samples)

| question_type | Count | MRAgent Category |
|---------------|-------|-----------------|
| multi-session | 133 | 0 |
| single-session-user | 70 | 1 |
| temporal-reasoning | 133 | 2 |
| single-session-preference | 30 | 3 |
| knowledge-update | 78 | 4 |
| single-session-assistant | 56 | 5 |

### Session structure

Each element in `haystack_sessions` is a dialogue:
```json
[
  {"role": "user", "content": "..."},
  {"role": "assistant", "content": "..."}
]
```

Sessions have varying lengths (2–20+ turns). Both user and assistant turns are present.
MRAgent's `get_data("LM", ...)` filters to user-only turns.

## 4. MRAgent Compatibility

**Cannot be read directly** by `data/get_data.py`. The HuggingFace schema differs from
MRAgent's expected `data/dataset_LM.json` format in several ways:

| Aspect | HuggingFace | MRAgent Expected |
|--------|------------|-----------------|
| Sample id | `question_id` (hex string) | `sample_id` |
| Conversation | `haystack_sessions` (list of lists of dicts) | `conversation` (dict with `session_N` + `session_N_date_time` keys) |
| Turn format | `{"role":"user","content":"..."}` | `{"speaker":"user","dia_id":"D1:1","text":"..."}` |
| QA | Single item per sample | `qa` list per sample |
| Category | `question_type` (string) | `category` (int) in qa |
| Question date | Top-level `question_date` | `metadata.question_date` |

## 5. Conversion

**Script**: `repro/convert_longmemeval_to_mragent.py`

**Conversion logic**:
1. `question_id` → `sample_id`
2. `haystack_sessions[i]` → `session_{i+1}` with turns converted to MRAgent format
3. `haystack_dates[i]` → `session_{i+1}_date_time`
4. `question_type` → `category` (int mapping)
5. `question`, `answer`, `answer_session_ids` → `qa` list
6. `question_date` → `metadata.question_date`

**Command**:
```bash
python repro/convert_longmemeval_to_mragent.py \
  --input data/external/longmemeval_s_cleaned.json \
  --output data/dataset_LM.json
```

**Result**:
- 500 samples, 0 skipped
- Output: `data/dataset_LM.json` (274,933,366 bytes)
- SHA256: `24caf0ca7af87c09b2f7c24e5f1d6ae0b17c3b3a...`

## 6. Loader Validation

```python
from data.get_data import get_data
c, q, _, _ = get_data("LM", "data/dataset_LM.json")
```

| Metric | Value |
|--------|-------|
| Samples | 500 |
| Questions | 500 |
| First sample | `e47becba`, 53 sessions |
| Category 0 (multi-session) | 133 |
| Category 1 (single-session-user) | 70 |
| Category 2 (temporal-reasoning) | 133 |
| Category 3 (single-session-preference) | 30 |
| Category 4 (knowledge-update) | 78 |
| Category 5 (single-session-assistant) | 56 |

**Loader validation: PASSED** ✅

## 7. Files Not Committed

| Path | Reason |
|------|--------|
| `data/external/longmemeval_s_cleaned.json` | Large (265 MB), in `.gitignore` |
| `data/dataset_LM.json` | Large (275 MB), generated, in `.gitignore` |

## 8. Committed Files

| Path | Description |
|------|-------------|
| `repro/convert_longmemeval_to_mragent.py` | Conversion script |
| `reports/longmemeval_schema_audit_20260702.md` | This report |
