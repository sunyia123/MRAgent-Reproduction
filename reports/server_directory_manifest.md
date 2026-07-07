# Server Directory Manifest

Generated: `2026-07-07T19:50:55`
Root: `/data/nishome/cuiwenjia/MRAgent-Reproduction`

## Scan Policy

- Skipped directories: `.git, .mypy_cache, .pytest_cache, .venv, __pycache__`
- Use `repro/update_server_directory_manifest.py --include_venv` only for local debugging; do not commit huge virtualenv manifests.

## Summary

- Files listed: `194`

### Top-Level Counts

| top-level path | files |
|---|---:|
| `.agents` | 1 |
| `.claude` | 1 |
| `.env` | 1 |
| `.env.example` | 1 |
| `.gitignore` | 1 |
| `README.md` | 1 |
| `README_REPRODUCTION.md` | 1 |
| `agent` | 3 |
| `common` | 4 |
| `data` | 17 |
| `diagnose_rewrite.py` | 1 |
| `docs` | 10 |
| `eval` | 5 |
| `llm` | 4 |
| `log` | 19 |
| `memory` | 3 |
| `prompts` | 3 |
| `reports` | 27 |
| `repro` | 19 |
| `requirements.txt` | 1 |
| `result` | 68 |
| `result_judge_locomo_deepseek_stratified.jsonl` | 1 |
| `run.py` | 1 |
| `run_stratified.py` | 1 |

### Suffix Counts

| suffix | files |
|---|---:|
| `.json` | 60 |
| `.py` | 46 |
| `.md` | 40 |
| `.jsonl` | 21 |
| `.log` | 19 |
| `[no suffix]` | 4 |
| `.example` | 1 |
| `.pkl` | 1 |
| `.tmp` | 1 |
| `.txt` | 1 |

## Files

| path | size bytes | modified |
|---|---:|---|
| `.agents/codex_experience_review.md` | 3215 | `2026-07-01T22:25:26` |
| `.claude/settings.local.json` | 586 | `2026-07-01T14:58:26` |
| `.env` | 403 | `2026-07-01T15:36:59` |
| `.env.example` | 753 | `2026-07-07T19:50:07` |
| `.gitignore` | 682 | `2026-07-02T13:08:58` |
| `README.md` | 10060 | `2026-07-07T19:50:07` |
| `README_REPRODUCTION.md` | 2316 | `2026-07-01T22:25:26` |
| `agent/__init__.py` | 0 | `2026-06-30T21:42:53` |
| `agent/agent.py` | 45294 | `2026-07-07T16:18:49` |
| `agent/tools.py` | 6158 | `2026-06-30T21:42:53` |
| `common/__init__.py` | 0 | `2026-06-30T21:42:53` |
| `common/config.py` | 7358 | `2026-07-07T19:50:25` |
| `common/logging_utils.py` | 2885 | `2026-07-07T19:50:07` |
| `common/utils.py` | 4472 | `2026-06-30T21:42:53` |
| `data/README.md` | 978 | `2026-07-02T11:20:10` |
| `data/__init__.py` | 0 | `2026-06-30T21:42:53` |
| `data/conversation_list_LM.json` | 34524611 | `2026-07-02T11:25:19` |
| `data/conversation_list_locomo.json` | 948789 | `2026-07-07T19:39:46` |
| `data/dataset_LM.json` | 274933366 | `2026-07-02T11:25:06` |
| `data/dataset_locomo.json` | 2805274 | `2026-06-30T21:42:53` |
| `data/embed_rewrite.py` | 2943 | `2026-07-01T06:31:52` |
| `data/external/longmemeval_s_cleaned.json` | 277383467 | `2026-07-02T11:23:21` |
| `data/get_data.py` | 4262 | `2026-06-30T21:42:53` |
| `data/locomo/embedding/gpt_deepseek/conv-30_embedding.pkl` | 23147326 | `2026-07-02T05:00:01` |
| `data/locomo/keyword_deepseek/conv-30_keyword.json` | 99767 | `2026-07-02T04:59:07` |
| `data/locomo/rewrite_deepseek/conv-26_rewrite.json.tmp` | 9705 | `2026-07-07T19:14:06` |
| `data/locomo/rewrite_deepseek/conv-30_rewrite.json` | 235782 | `2026-07-02T04:13:40` |
| `data/locomo/rewrite_deepseek_vlm/conv-30_rewrite.json` | 38468 | `2026-07-03T10:07:25` |
| `data/question_list_LM.json` | 182958 | `2026-07-02T11:25:19` |
| `data/question_list_locomo.json` | 427821 | `2026-07-07T19:39:46` |
| `data/subsets/locomo10_100q_seed42.json` | 32935 | `2026-07-06T22:57:31` |
| `diagnose_rewrite.py` | 15057 | `2026-07-03T09:36:37` |
| `docs/benchmark_reproduction_plan.md` | 9498 | `2026-07-02T11:20:10` |
| `docs/claude_code_full_experiment_instructions.md` | 16002 | `2026-07-07T19:50:07` |
| `docs/claude_code_next_steps.md` | 10517 | `2026-07-07T19:50:07` |
| `docs/experiment_master_agenda.md` | 10022 | `2026-07-06T14:47:09` |
| `docs/goal.md` | 1545 | `2026-07-01T15:57:27` |
| `docs/handoff.md` | 21161 | `2026-07-03T09:36:32` |
| `docs/intermediate_artifact_checklist.md` | 10120 | `2026-07-07T19:50:07` |
| `docs/medium_core_validation_handoff.md` | 16177 | `2026-07-07T19:50:07` |
| `docs/next_iteration_handoff.md` | 8695 | `2026-07-06T22:13:14` |
| `docs/reproduction_plan.md` | 8099 | `2026-07-01T15:57:27` |
| `eval/__init__.py` | 0 | `2026-06-30T21:42:54` |
| `eval/evaluate_reasoning.py` | 10359 | `2026-07-01T16:00:03` |
| `eval/evaluation.py` | 1111 | `2026-06-30T21:42:54` |
| `eval/judge.py` | 4616 | `2026-07-01T15:57:27` |
| `eval/memory_audit.py` | 12009 | `2026-07-01T15:57:27` |
| `llm/__init__.py` | 0 | `2026-06-30T21:42:54` |
| `llm/controller.py` | 20535 | `2026-07-07T19:50:07` |
| `llm/embeddings.py` | 6307 | `2026-07-07T19:50:07` |
| `llm/rag_utils.py` | 1202 | `2026-06-30T21:42:54` |
| `log/locomo/conv-26_deepseek_0.log` | 731 | `2026-07-07T19:39:47` |
| `log/locomo/conv-26_deepseek_mragent_100q.log` | 5874 | `2026-07-07T17:16:23` |
| `log/locomo/conv-26_deepseek_smoke.log` | 897 | `2026-06-30T22:31:42` |
| `log/locomo/conv-26_gemini_0.log` | 576 | `2026-07-07T19:13:36` |
| `log/locomo/conv-26_gemini_smoke.log` | 363 | `2026-06-30T22:06:24` |
| `log/locomo/conv-30_deepseek_explore50.log` | 214535 | `2026-07-02T11:46:58` |
| `log/locomo/conv-30_deepseek_mragent_100q.log` | 158621 | `2026-07-07T18:07:03` |
| `log/locomo/conv-30_deepseek_rag_100q.log` | 9265 | `2026-07-07T18:42:09` |
| `log/locomo/conv-30_deepseek_rag_smoke.log` | 32185 | `2026-07-06T22:55:40` |
| `log/locomo/conv-30_deepseek_smoke.log` | 54279 | `2026-07-01T06:38:50` |
| `log/locomo/conv-30_deepseek_stratified.log` | 331746 | `2026-07-02T05:32:03` |
| `log/locomo/conv-42_deepseek_explore50.log` | 4379 | `2026-07-02T17:01:23` |
| `log/run_locomo__deepseek__deepseek_0.log` | 3928 | `2026-07-07T19:39:46` |
| `log/run_locomo__deepseek__deepseek_explore50.log` | 1735 | `2026-07-02T11:31:01` |
| `log/run_locomo__deepseek__deepseek_mragent_100q.log` | 19520 | `2026-07-07T17:42:34` |
| `log/run_locomo__deepseek__deepseek_stratified.log` | 6873 | `2026-07-02T02:11:44` |
| `log/run_locomo__gemini__gemini_0.log` | 1940 | `2026-07-07T19:13:34` |
| `log/run_locomo_deepseek_deepseek_smoke.log` | 11037 | `2026-07-01T06:33:23` |
| `log/run_locomo_gemini_gemini_smoke.log` | 3534 | `2026-06-30T22:06:22` |
| `memory/__init__.py` | 0 | `2026-06-30T21:42:54` |
| `memory/controller.py` | 18135 | `2026-06-30T21:42:54` |
| `memory/system.py` | 13817 | `2026-07-01T06:32:35` |
| `prompts/__init__.py` | 0 | `2026-06-30T21:42:54` |
| `prompts/prompts.py` | 12322 | `2026-06-30T21:42:54` |
| `prompts/schema.py` | 5088 | `2026-06-30T21:42:54` |
| `reports/.gitkeep` | 1 | `2026-06-30T21:42:54` |
| `reports/badcase_chat_text_parse_20260707.md` | 1776 | `2026-07-07T18:50:18` |
| `reports/badcase_pack_conv30_stratified_20260706.md` | 2273 | `2026-07-06T14:47:09` |
| `reports/badcase_pack_conv30_stratified_20260706_server_review.md` | 24192 | `2026-07-06T21:44:30` |
| `reports/benchmark_data_audit_20260702.md` | 2419 | `2026-07-02T11:30:16` |
| `reports/dataset_task_audit_locomo_20260706.md` | 1659 | `2026-07-06T14:47:09` |
| `reports/dataset_task_audit_locomo_20260706_server.md` | 1659 | `2026-07-06T14:47:09` |
| `reports/diagnose_conv26_D9_20260707.md` | 6660 | `2026-07-07T16:04:22` |
| `reports/experiment_status_20260707.md` | 6217 | `2026-07-07T18:58:21` |
| `reports/graph_snapshot_conv30_20260706_server.md` | 2516 | `2026-07-06T21:44:26` |
| `reports/graph_snapshot_manifest_conv30_20260706.md` | 2462 | `2026-07-06T21:44:49` |
| `reports/locomo_smoke_20260701.md` | 15450 | `2026-07-01T08:50:06` |
| `reports/longmemeval_schema_audit_20260702.md` | 4638 | `2026-07-02T11:25:38` |
| `reports/model_diagnostics_20260701.md` | 8945 | `2026-07-02T09:26:48` |
| `reports/mragent_experiment_progress_20260703.md` | 11203 | `2026-07-06T14:47:09` |
| `reports/mragent_vlm_cbr_qlearning_design_20260702.md` | 21448 | `2026-07-02T11:20:10` |
| `reports/rag_vs_mragent_conv30_stratified_20260706.md` | 4735 | `2026-07-06T22:56:19` |
| `reports/reproduction_audit_20260701.md` | 12714 | `2026-07-01T15:57:27` |
| `reports/runtime_model_config_audit_20260707.md` | 3107 | `2026-07-07T19:50:07` |
| `reports/stage_b_clean_conv30_20260702.md` | 10209 | `2026-07-02T09:33:02` |
| `reports/stage_b_eval_audit_20260701.md` | 16758 | `2026-07-02T09:12:13` |
| `reports/standard_rag_baseline_20260702.md` | 2956 | `2026-07-02T13:08:40` |
| `reports/vlm_enriched_rewrite_vlmrewrite_smoke_20260703_093703.md` | 1009 | `2026-07-03T09:36:49` |
| `reports/vlm_enriched_rewrite_vlmrewrite_smoke_20260703_093713.md` | 1013 | `2026-07-03T09:41:01` |
| `reports/vlm_enriched_rewrite_vlmrewrite_smoke_20260703_094151.md` | 9233 | `2026-07-03T10:09:48` |
| `reports/vlm_tool_validation_stage1_vlm_conv-30_20260702_112837.md` | 1101 | `2026-07-02T11:27:56` |
| `reports/vlm_tool_validation_stage1_vlm_conv-30_20260702_112850.md` | 1692 | `2026-07-02T11:29:20` |
| `repro/.gitkeep` | 1 | `2026-06-30T21:42:54` |
| `repro/audit_api_models.py` | 1981 | `2026-07-07T16:18:49` |
| `repro/audit_dataset_tasks.py` | 5207 | `2026-07-06T14:47:09` |
| `repro/audit_rewrite_cache.py` | 3750 | `2026-07-07T19:08:19` |
| `repro/audit_runtime_config.py` | 2623 | `2026-07-07T19:50:07` |
| `repro/build_stratified_subset.py` | 4018 | `2026-07-06T22:57:31` |
| `repro/compare_rag_to_mragent_subset.py` | 9687 | `2026-07-06T22:57:43` |
| `repro/convert_longmemeval_to_mragent.py` | 5318 | `2026-07-02T11:24:53` |
| `repro/diagnose_rewrite_session.py` | 6221 | `2026-07-07T16:03:36` |
| `repro/export_badcase_pack.py` | 8625 | `2026-07-06T14:47:09` |
| `repro/export_graph_snapshot.py` | 11235 | `2026-07-06T22:13:14` |
| `repro/run_graphrag_baseline.py` | 11467 | `2026-07-06T22:57:31` |
| `repro/run_oracle_evidence_qa.py` | 6516 | `2026-07-06T22:57:31` |
| `repro/run_standard_rag_baseline.py` | 11610 | `2026-07-06T22:57:43` |
| `repro/run_vlm_enriched_rewrite.py` | 18390 | `2026-07-03T09:36:32` |
| `repro/smart_retry_batch.py` | 5239 | `2026-07-07T16:46:39` |
| `repro/summarize_core_validation.py` | 5936 | `2026-07-06T22:57:31` |
| `repro/update_server_directory_manifest.py` | 5323 | `2026-07-07T19:50:07` |
| `repro/validate_vlm_tool.py` | 11002 | `2026-07-02T11:20:10` |
| `requirements.txt` | 470 | `2026-06-30T21:42:54` |
| `result/diagnostics/api_call_log.jsonl` | 155198 | `2026-07-07T19:13:36` |
| `result/diagnostics/raw_api_calls.jsonl` | 0 | `2026-07-01T22:28:08` |
| `result/diagnostics/rewrite/diagnostic_manifest_20260701-222826.json` | 1814 | `2026-07-01T22:38:35` |
| `result/diagnostics/rewrite/diagnostic_manifest_20260701-223958.json` | 4594 | `2026-07-01T23:49:32` |
| `result/diagnostics/rewrite/diagnostic_manifest_20260702-002219.json` | 13122 | `2026-07-02T02:10:05` |
| `result/diagnostics/rewrite/raw/session17_deepseek_16384_20260701-223958.json` | 60706 | `2026-07-01T23:47:26` |
| `result/diagnostics/rewrite/raw/session17_deepseek_baseline_20260701-223958.json` | 60641 | `2026-07-01T23:41:49` |
| `result/diagnostics/rewrite/raw/session17_ds_16384_20260702-002219.json` | 37467 | `2026-07-02T01:54:33` |
| `result/diagnostics/rewrite/raw/session17_ds_16384_json_20260702-002219.json` | 50819 | `2026-07-02T02:03:51` |
| `result/diagnostics/rewrite/raw/session17_ds_32768_20260702-002219.json` | 65607 | `2026-07-02T01:59:52` |
| `result/diagnostics/rewrite/raw/session17_ds_4096_20260702-002219.json` | 43418 | `2026-07-02T01:51:46` |
| `result/diagnostics/rewrite/raw/session17_qw_16384_20260702-002219.json` | 51611 | `2026-07-02T02:07:57` |
| `result/diagnostics/rewrite/raw/session17_qw_16384_json_20260702-002219.json` | 59082 | `2026-07-02T02:10:05` |
| `result/diagnostics/rewrite/raw/session17_qw_4096_20260702-002219.json` | 54009 | `2026-07-02T02:05:52` |
| `result/diagnostics/rewrite/raw/session17_qwen3_397b_20260701-223958.json` | 48265 | `2026-07-01T23:49:31` |
| `result/diagnostics/rewrite/raw/session1_deepseek_16384_20260701-223958.json` | 82737 | `2026-07-01T23:06:24` |
| `result/diagnostics/rewrite/raw/session1_deepseek_baseline_20260701-223958.json` | 93245 | `2026-07-01T22:49:11` |
| `result/diagnostics/rewrite/raw/session1_ds_16384_20260702-002219.json` | 58844 | `2026-07-02T00:30:05` |
| `result/diagnostics/rewrite/raw/session1_ds_16384_json_20260702-002219.json` | 59754 | `2026-07-02T00:49:49` |
| `result/diagnostics/rewrite/raw/session1_ds_32768_20260702-002219.json` | 67460 | `2026-07-02T00:45:07` |
| `result/diagnostics/rewrite/raw/session1_ds_4096_20260702-002219.json` | 54349 | `2026-07-02T00:26:01` |
| `result/diagnostics/rewrite/raw/session1_qw_16384_20260702-002219.json` | 46744 | `2026-07-02T00:53:53` |
| `result/diagnostics/rewrite/raw/session1_qw_16384_json_20260702-002219.json` | 52694 | `2026-07-02T00:56:05` |
| `result/diagnostics/rewrite/raw/session1_qw_4096_20260702-002219.json` | 53100 | `2026-07-02T00:52:02` |
| `result/diagnostics/rewrite/raw/session1_qwen3_397b_20260701-223958.json` | 58177 | `2026-07-01T23:08:36` |
| `result/diagnostics/rewrite/raw/session6_deepseek_16384_20260701-222826.json` | 72004 | `2026-07-01T22:36:46` |
| `result/diagnostics/rewrite/raw/session6_deepseek_baseline_20260701-222826.json` | 32707 | `2026-07-01T22:30:55` |
| `result/diagnostics/rewrite/raw/session6_ds_16384_20260702-002219.json` | 70455 | `2026-07-02T01:05:16` |
| `result/diagnostics/rewrite/raw/session6_ds_16384_json_20260702-002219.json` | 67464 | `2026-07-02T01:14:22` |
| `result/diagnostics/rewrite/raw/session6_ds_32768_20260702-002219.json` | 45699 | `2026-07-02T01:08:52` |
| `result/diagnostics/rewrite/raw/session6_ds_4096_20260702-002219.json` | 50935 | `2026-07-02T00:59:35` |
| `result/diagnostics/rewrite/raw/session6_qw_16384_20260702-002219.json` | 44291 | `2026-07-02T01:17:49` |
| `result/diagnostics/rewrite/raw/session6_qw_16384_json_20260702-002219.json` | 48470 | `2026-07-02T01:19:46` |
| `result/diagnostics/rewrite/raw/session6_qw_4096_20260702-002219.json` | 41892 | `2026-07-02T01:16:02` |
| `result/diagnostics/rewrite/raw/session6_qwen3_397b_20260701-222826.json` | 52227 | `2026-07-01T22:38:35` |
| `result/diagnostics/rewrite/raw/session8_deepseek_16384_20260701-223958.json` | 85035 | `2026-07-01T23:34:19` |
| `result/diagnostics/rewrite/raw/session8_deepseek_baseline_20260701-223958.json` | 90110 | `2026-07-01T23:27:11` |
| `result/diagnostics/rewrite/raw/session8_ds_16384_20260702-002219.json` | 55828 | `2026-07-02T01:30:17` |
| `result/diagnostics/rewrite/raw/session8_ds_16384_json_20260702-002219.json` | 99866 | `2026-07-02T01:42:12` |
| `result/diagnostics/rewrite/raw/session8_ds_32768_20260702-002219.json` | 64882 | `2026-07-02T01:34:30` |
| `result/diagnostics/rewrite/raw/session8_ds_4096_20260702-002219.json` | 81465 | `2026-07-02T01:26:18` |
| `result/diagnostics/rewrite/raw/session8_qw_16384_20260702-002219.json` | 56094 | `2026-07-02T01:45:35` |
| `result/diagnostics/rewrite/raw/session8_qw_16384_json_20260702-002219.json` | 64373 | `2026-07-02T01:48:23` |
| `result/diagnostics/rewrite/raw/session8_qw_4096_20260702-002219.json` | 47415 | `2026-07-02T01:43:40` |
| `result/diagnostics/rewrite/raw/session8_qwen3_397b_20260701-223958.json` | 52624 | `2026-07-01T23:36:17` |
| `result/diagnostics/vlm_enriched_rewrite_sessions_vlmrewrite_smoke_20260703_093703.jsonl` | 9274 | `2026-07-03T09:36:49` |
| `result/diagnostics/vlm_enriched_rewrite_sessions_vlmrewrite_smoke_20260703_093713.jsonl` | 11520 | `2026-07-03T09:41:01` |
| `result/diagnostics/vlm_enriched_rewrite_sessions_vlmrewrite_smoke_20260703_094151.jsonl` | 11003 | `2026-07-03T09:43:22` |
| `result/diagnostics/vlm_enriched_rewrite_visual_vlmrewrite_smoke_20260703_093703.jsonl` | 7890 | `2026-07-03T09:36:49` |
| `result/diagnostics/vlm_enriched_rewrite_visual_vlmrewrite_smoke_20260703_093713.jsonl` | 47570 | `2026-07-03T09:41:01` |
| `result/diagnostics/vlm_enriched_rewrite_visual_vlmrewrite_smoke_20260703_094151.jsonl` | 37191 | `2026-07-03T09:43:22` |
| `result/diagnostics/vlm_tool_validation_stage1_vlm_conv-30_20260702_112837.jsonl` | 8060 | `2026-07-02T11:27:56` |
| `result/diagnostics/vlm_tool_validation_stage1_vlm_conv-30_20260702_112850.jsonl` | 7931 | `2026-07-02T11:29:20` |
| `result/graph_snapshot/conv-30_edges.jsonl` | 463357 | `2026-07-06T21:41:16` |
| `result/graph_snapshot/conv-30_nodes.jsonl` | 772975 | `2026-07-06T21:41:16` |
| `result/locomo/artifact_manifest_20260701.json` | 2745 | `2026-07-02T00:23:10` |
| `result/locomo/artifact_manifest_20260702_clean.json` | 4035 | `2026-07-02T09:33:11` |
| `result/locomo/conv-30_result_deepseek_explore50.jsonl` | 4204 | `2026-07-02T11:46:58` |
| `result/locomo/conv-30_result_deepseek_graphrag_100q.jsonl` | 3334 | `2026-07-07T18:42:12` |
| `result/locomo/conv-30_result_deepseek_mragent_100q.jsonl` | 4082 | `2026-07-07T18:07:03` |
| `result/locomo/conv-30_result_deepseek_rag_100q.jsonl` | 5649 | `2026-07-07T18:42:09` |
| `result/locomo/conv-30_result_deepseek_rag_smoke.jsonl` | 53997 | `2026-07-06T22:55:40` |
| `result/locomo/conv-30_result_deepseek_rag_smoke_stratified_subset.jsonl` | 8276 | `2026-07-06T22:56:19` |
| `result/locomo/conv-30_result_deepseek_smoke.jsonl` | 660 | `2026-07-01T06:38:50` |
| `result/locomo/conv-30_result_deepseek_stratified.jsonl` | 6408 | `2026-07-02T05:32:03` |
| `result/locomo/diagnostic_evidence_20260701.json` | 14783 | `2026-07-01T22:22:10` |
| `result/locomo/memory_audit_deepseek_stratified.json` | 11466 | `2026-07-02T05:32:18` |
| `result/locomo/metrics_summary_deepseek_stratified.json` | 606 | `2026-07-02T09:12:58` |
| `result_judge_locomo_deepseek_stratified.jsonl` | 3537 | `2026-07-02T05:34:51` |
| `run.py` | 12944 | `2026-07-02T00:21:03` |
| `run_stratified.py` | 24864 | `2026-07-07T19:50:07` |
