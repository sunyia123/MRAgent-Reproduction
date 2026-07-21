# MRAgent 全量判错归因

- 题目总数：400
- Judge 判错或执行失败：88
- 非错误但缺少 Judge 结果：0
- Trace 目录：`result/diagnostics/mragent_main500_traces`

## 主因分布

| 主因 | 错例数 | 占全部错例 | 占全部题目 |
|---|---:|---:|---:|
| tool_selection_or_path_failure | 54 | 61.4% | 13.5% |
| multi_hop_composition_failure | 13 | 14.8% | 3.2% |
| temporal_reasoning_failure | 8 | 9.1% | 2.0% |
| answer_synthesis_failure | 8 | 9.1% | 2.0% |
| execution_or_schema_failure | 4 | 4.5% | 1.0% |
| initial_key_extraction_failure | 1 | 1.1% | 0.2% |

## 分类别主因

- Category 1: multi_hop_composition_failure=13, tool_selection_or_path_failure=10, execution_or_schema_failure=1
- Category 2: tool_selection_or_path_failure=14, temporal_reasoning_failure=8, execution_or_schema_failure=1
- Category 3: tool_selection_or_path_failure=24, answer_synthesis_failure=7, execution_or_schema_failure=2, initial_key_extraction_failure=1
- Category 4: tool_selection_or_path_failure=6, answer_synthesis_failure=1

## 解释边界

- 自动归因只使用可观察证据；`manual_review_needed=true` 的主因不是最终因果结论。
- `judge_false_negative` 只有在人工复核标记 `semantic_correct=true` 后才能成立。
- 图构建缺失、视觉证据缺失和路径过早停止不能凭 F1 猜测，必须查看图快照与完整 trace。
