# VLM-Enriched Rewrite Smoke — 2026-07-03

## 1. Purpose

Inject VLM visual evidence into the MRAgent rewrite pipeline for conv-30 (first 3 sessions),
and compare VLM-enriched rewrite output against the baseline rewrite.

**This is a rewrite-stage smoke test only.** It is NOT a VLM-QA improvement experiment
and NOT a full benchmark reproduction.

## 2. Configuration

- **dataset**: `locomo`
- **sample**: `conv-30`
- **text model**: `deepseek-ai/DeepSeek-V4-Pro`
- **VLM model**: `Qwen/Qwen3.5-397B-A17B` (via SiliconFlow)
- **max_sessions**: 3
- **limit_image_turns**: 10
- **command**: `python repro/run_vlm_enriched_rewrite.py --data locomo --model deepseek --sample 30 --file vlmrewrite_smoke --limit_image_turns 10 --max_sessions 3 --rewrite`

## 3. Results Summary

### 3.1 Image Turn Discovery

| Scope | Image turns found |
|-------|------------------:|
| First 3 sessions (D1, D2, D3) | 7 |
| All sessions (up to limit=10) | 10 |

### 3.2 VLM Call Outcomes

| Status | Count | Detail |
|--------|------:|--------|
| **OK** | 3 | VLM returned valid visual evidence (JSON) |
| **Error** | 7 | URL not accessible from SiliconFlow server |

### 3.3 Visual Evidence Injection

| Session | Image turns | VLM-OK injected | Caption-only fallback |
|---------|-----------:|----------------:|---------------------:|
| D1 (session_1) | 4 | 1 (D1:20) | 3 (D1:14, D1:17, D1:24) |
| D2 (session_2) | 1 | 0 | 1 (D2:4) |
| D3 (session_3) | 2 | 1 (D3:4) | 1 (D3:2) |
| **Total (first 3)** | **7** | **2** | **5** |

### 3.4 URL Failures

All 7 errors are `BadRequestError 20040` — the SiliconFlow API server cannot download
external image URLs (China network restriction). This matches the prior A1 VLM validation
result (0/5 URLs accessible in July 2026 test).

| Turn | Image domain | Error |
|------|-------------|-------|
| D1:14 | upload.wikimedia.org | 20040: URL not downloadable |
| D1:17 | upload.wikimedia.org | 20040: URL not downloadable |
| D1:24 | markmorrisdancegroup.org | 20040: URL not downloadable |
| D2:4 | avvay-aws-production.imgix.net | 20015: Unsupported format (mpo) |
| D3:2 | s0.geograph.org.uk | 20040: URL not downloadable |
| D5:12 | live.staticflickr.com | 20040 (rate/access intermittent) |

The 3 successful VLM calls used `live.staticflickr.com` URLs (D1:20 two prior step runs also
accessed flickr successfully), suggesting Flickr CDN is reachable from SiliconFlow's servers
while Wikimedia, custom WP sites, and geograph.org.uk are blocked.

## 4. Manual Comparison: Baseline vs VLM-Enriched Rewrite

### 4.1 Image Turn D1:20 (VLM OK — "dance studio by the water")

| Aspect | Baseline Rewrite | VLM-Enriched Rewrite |
|--------|-----------------|---------------------|
| Sentence | `[D1:20-2] (Sharing) Check Jon's ideal dance studio by the water.` | `[D1:20-2] (Dance Studio Vision) Check Jon's ideal dance studio by the water.` |
| Photo sentence | `[D1:20-3] (Photo Sharing) and shared a photography of a room with a view of the ocean and a few yoga mats` | *(absorbed into sentence above — no separate Photo Sharing tag)* |
| Tag change | "Sharing" + "Photo Sharing" (passive) | "Dance Studio Vision" (semantic, domain-aware) |
| blip_caption | "a photography of a room with a view of the ocean and a few yoga mats" | Enriched with: "visual_answer: The image shows a spacious, dimly lit room with a polished wooden floor. Several yoga mats and blocks are arranged on the floor, facing large floor-to-ceiling windows." |
| Sentence count (whole D1) | 82 sentences | 63 sentences (-23% more compact) |

**Analysis**: The VLM visual evidence ("yoga mats, polished wooden floor, floor-to-ceiling windows,
ocean view") gave the text rewrite model richer context. The baseline labeled this turn as generic
"Sharing" + "Photo Sharing", while the VLM rewrite used the semantically meaningful tag
"Dance Studio Vision" and merged the photo caption into the main sentence instead of emitting a
separate "(Photo Sharing)" sentence. The VLM rewrite is 23% more compact (63 vs 82 sentences for D1),
suggesting the visual context helps the model avoid redundant "photo sharing" filler sentences.

### 4.2 Image Turn D3:4 (VLM OK — "clothing store interior")

| Aspect | Baseline Rewrite | VLM-Enriched Rewrite |
|--------|-----------------|---------------------|
| Sentence | `[D3:4-6] (Photo description) and shared a photography of a clothing store with a lot of clothes on display` | `[D3:4-6] (Photo Sharing) Gina shared a photography of a clothing store with a lot of clothes on display.` |
| Tag | "Photo description" (neutral) | "Photo Sharing" (same as baseline) |
| VLM evidence | N/A | "visual_answer: The image shows the interior of a clothing boutique featuring light wood flooring and rustic wood paneling on the left wall. Central wooden tables display folded jeans..." |
| Impact | — | Minimal: the detailed VLM evidence was available but the rewrite model produced only the blip_caption summary |

**Analysis**: This was a less impactful injection. The VLM described detailed store interior features
(wood flooring, rustic paneling, folded jeans), but the text rewrite only used the blip_caption-level
summary. The rewrite model may have treated the detailed visual evidence as secondary to the dialogue
text, or the detail didn't change any entity/relationship extraction.

### 4.3 Image Turn D1:17 (VLM Error — "dance competition photo")

| Aspect | Baseline Rewrite | VLM-Enriched Rewrite |
|--------|-----------------|---------------------|
| blip_caption | "a photography of a couple of people standing next to each other" | Same caption used (VLM call failed) |
| Nearby sentence | `[D1:16-1] (Photo Explanation, Achievement) The photo is from when Jon's dance crew won first place...` | `[D1:15-2] (Photo Inquiry, Competition Win) What did Jon get? The photo Jon shared is from when Jon's dance crew took home first...` |
| Tag difference | "Photo Explanation, Achievement" | "Photo Inquiry, Competition Win" |
| Sentence count (D1) | 82 (baseline D1 only) | 63 (VLM D1 only) |

**Analysis**: The VLM call for D1:17 failed, so the rewrite used only the blip_caption
("a photography of a couple of people standing next to each other"). This is the baseline
behavior — no visual enrichment. The tag difference ("Achievement" vs "Competition Win")
is likely due to the DeepSeek model's inherent variation between runs (non-deterministic),
not VLM enrichment, since D1:17 had no VLM evidence injected.

## 5. Cross-Session Structural Differences

| Session | Baseline sents | VLM sents | Delta | Notes |
|---------|--------------:|----------:|------:|-------|
| D1 | 82 | 63 | -19 | VLM-injected turn D1:20 enriched; photo-sharing filler reduced |
| D2 | 55 | 55 | 0 | No VLM injection (D2:4 error → caption-only fallback) |
| D3 | 54 | 54 | 0 | VLM-injected turn D3:4 had minimal impact on sentence structure |

- D1 shows the largest difference (-19 sentences, -23%) correlated with the VLM-enriched image turn D1:20.
- D2 and D3 show no sentence-count change, consistent with zero (D2) or low-impact (D3) VLM enrichment.

## 6. Error Classification

| Failure type | Count | Root cause |
|-------------|------:|-----------|
| URL not downloadable (20040) | 6 | SiliconFlow server cannot reach external URLs (Wikimedia, custom domains, geograph.org.uk) |
| Unsupported format (20015) | 1 | `.mpo` image format not accepted by Qwen VLM |
| Empty VLM response | 0 | — |
| Rewrite failure | 0 | All 3 sessions rewritten successfully |

## 7. Artifacts

| Artifact | Path | Size |
|----------|------|------|
| VLM-enriched rewrite | `data/locomo/rewrite_deepseek_vlm/conv-30_rewrite.json` | 3 sessions, 172 sentences |
| Baseline rewrite | `data/locomo/rewrite_deepseek/conv-30_rewrite.json` | 19 sessions, 1094 sentences |
| Visual evidence log | `result/diagnostics/vlm_enriched_rewrite_visual_vlmrewrite_smoke_20260703_094151.jsonl` | 10 records |
| Enriched sessions log | `result/diagnostics/vlm_enriched_rewrite_sessions_vlmrewrite_smoke_20260703_094151.jsonl` | 1 record |

## 8. Scope Statement

- This is a **rewrite-stage smoke test** on a single sample (conv-30), first 3 sessions only.
- It is NOT a VLM-QA improvement experiment. QA accuracy impact cannot be assessed from rewrite output alone.
- It is NOT a full benchmark reproduction.
- Only 2 of 7 image turns received VLM enrichment due to URL accessibility constraints.
- Running keyword → embedding → QA on this rewrite cache (and evaluating against baseline) is the logical next step, but requires the URL accessibility problem to be resolved for meaningful results.

## 9. Conclusion

- **Pipeline functional**: VLM evidence collection → session enrichment → text rewrite runs end-to-end.
- **VLM URL constraint**: 3/10 calls succeeded (Flickr CDN reachable; Wikimedia/custom domains blocked).
- **Observed effect**: VLM-enriched rewrite for D1 (with visual evidence about a dance studio by the water) produced 23% fewer sentences and semantically richer tags ("Dance Studio Vision" vs "Sharing"), suggesting VLM visual context helps the model reduce photo-sharing verbosity.
- **File isolation**: Baseline rewrite cache is NOT modified — output goes to `data/locomo/rewrite_deepseek_vlm/`.
