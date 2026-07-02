# Benchmark Data Audit — 2026-07-02

## 1. LoCoMo Dataset

- **Path**: `data/dataset_locomo.json`
- **Samples**: 10
- **Sample IDs**: conv-26, conv-30, conv-41, conv-42, conv-43, conv-44, conv-47, conv-48, conv-49, conv-50
- **Total questions**: 1,986

### Category Distribution

| Category | Description | Count |
|----------|------------|-------|
| 1 | multi-hop | 282 |
| 2 | temporal | 321 |
| 3 | open-domain | 96 |
| 4 | single-hop | 841 |
| 5 | adversarial | 446 |

### Per-Sample Breakdown

| Sample | Sessions | Questions | cat1 | cat2 | cat3 | cat4 | cat5 |
|--------|----------|-----------|------|------|------|------|------|
| conv-26 | 19 | 199 | 32 | 37 | 13 | 70 | 47 |
| conv-30 | 19 | 105 | 11 | 26 | — | 44 | 24 |
| conv-41 | 32 | 193 | 31 | 27 | 8 | 86 | 41 |
| conv-42 | 29 | 260 | 37 | 40 | 11 | 111 | 61 |
| conv-43 | 29 | 242 | 31 | 26 | 14 | 107 | 64 |
| conv-44 | 28 | 158 | 30 | 24 | 7 | 62 | 35 |
| conv-47 | 31 | 190 | 20 | 34 | 13 | 83 | 40 |
| conv-48 | 30 | 239 | 21 | 42 | 10 | 118 | 48 |
| conv-49 | 25 | 196 | 37 | 33 | 13 | 73 | 40 |
| conv-50 | 30 | 204 | 32 | 32 | 7 | 87 | 46 |

### Scope Statement

- This private repo has **LoCoMo-10** (10 conversations, 1,986 questions).
- This is **NOT** the full paper LoCoMo dataset. The paper may include more conversations.
- Reports must use "LoCoMo-10" not "full paper LoCoMo" unless verified.

## 2. LongMemEval Dataset

- **Status**: Recovered from HuggingFace `xiaowu0162/longmemeval-cleaned`
- **Path**: `data/dataset_LM.json` (generated, not committed)
- **Samples**: 500
- **Questions**: 500
- **Categories**: multi-session(133), single-session-user(70), temporal-reasoning(133), single-session-preference(30), knowledge-update(78), single-session-assistant(56)
- **Loader**: `data.get_data("LM", "data/dataset_LM.json")` ✅ PASSED
- **See**: `reports/longmemeval_schema_audit_20260702.md`

## 3. VLM Image Accessibility

- **Test**: 5 image turns from conv-30, Qwen/Qwen3.5-397B-A17B via SiliconFlow
- **Result**: 0/5 succeeded — all returned error 20040 "image URL must be a valid and downloadable URL"
- **Root cause**: Image URLs (Wikipedia, Flickr, etc.) are not accessible from the SiliconFlow API server (China network restriction)
- **Impact**: VLM-enhanced QA is blocked until image URLs are accessible or blip_caption fallback is used
- **See**: `reports/vlm_tool_validation_stage1_vlm_conv-30_20260702_112850.md`
