# MRAgent 500 题 legacy Judge WRONG 离线归因报告

## 范围与证据边界

- 审计对象：旧版 MRAgent 400 道普通题 Judge 中的 88 个 WRONG。
- 本次没有调用任何模型，没有重跑 QA，也没有读取或修改 A-Mem/Mem0 cache。
- 旧 Judge 缺少模型、prompt version、thinking 和 question_index provenance；本报告不替代统一新版 Judge。
- 原主实验的 4 个普通题执行 ERROR 已在 repaired-v3 中定向修复，旧 Judge 对这些题的结论已经过时。
- Raw request 对齐：88/88；raw response 对齐：88/88；歧义匹配：0。

## 总体分布

- Gold turn 在 rewrite/episode 表示中的覆盖：88/88。
- 最终上下文完全未覆盖 gold：59/88。
- 最终上下文部分覆盖 gold：18/88。
- 最终上下文完整覆盖 gold：11/88。

| 主因 | 题数 | 占 88 个判错 |
|---|---:|---:|
| active_search_path_failure | 54 | 61.4% |
| partial_retrieval_then_incomplete_answer | 18 | 20.5% |
| temporal_reasoning_failure | 5 | 5.7% |
| execution_or_schema_failure | 4 | 4.5% |
| multi_hop_composition_failure | 3 | 3.4% |
| judge_false_negative_likely | 2 | 2.3% |
| gold_annotation_error | 1 | 1.1% |
| answer_synthesis_failure | 1 | 1.1% |

## 分题型判错率

| Category | WRONG | 总题数 | WRONG rate |
|---:|---:|---:|---:|
| 1 | 24 | 102 | 23.5% |
| 2 | 23 | 101 | 22.8% |
| 3 | 34 | 96 | 35.4% |
| 4 | 7 | 101 | 6.9% |

## 对核心创新的判断

### 图结构

- 88/88 个错题的 evidence turn 均能在 rewrite/episode 表示中找到，错误不是由原始内容整体漏建造成。
- 这只证明事件内容存在，不证明 tag/topic/person 边组织正确，也不证明被动 CTC 的收益完全来自图结构。
- 200 题消融中 CTC passive 相对 CTE passive 为正，但上下文 token 未预算匹配；CTE passive 相对 CE passive 未显著提升。因此图结构贡献部分成立。

### 主动搜索

- CTE active 和 CTC active 均稳定优于各自 passive，支持主动搜索的平均增益。
- 但判错中 54 题完全未检索到 gold，18 题只部分检索，路径策略仍是主要剩余瓶颈。
- 严格结论：主动搜索有效且相对 solid；图内容层有价值信号，但图结构各层的独立因果贡献尚未完全 solid。

## 人工确认的 Judge 或数据问题

- conv-42 Q1：预测 Yes，gold 也以 Yes 开头，高置信 Judge false negative 候选。
- conv-47 Q11：week before 12 April 与 evidence 的 5 April 及 gold 的 first week of April 等价，高置信 Judge false negative 候选。
- conv-47 Q32：evidence 为 11 July 到 20 July，gold 标成 19 days，高置信 gold annotation error。

## 产物

- 总 manifest：result/diagnostics/mragent_main500_judge_wrong_offline_20260721/manifest.jsonl
- 汇总 JSONL：reports/mragent_main500_judge_wrong_offline_20260721.jsonl
- 汇总 CSV：reports/mragent_main500_judge_wrong_offline_20260721.csv
- 每题证据包：result/diagnostics/mragent_main500_judge_wrong_offline_20260721/<sample>/qNNN/
- 每题包含 case.json、raw_prompts.jsonl、raw_responses.jsonl、tool_trace.jsonl、retrieval_path.md。

## 下一步验收

1. A-Mem/Mem0 完成后，对 repaired-v3 运行统一 V4-Flash Judge 400 题。
2. 重新生成 repaired-v3 WRONG 集；旧 88 题只作为历史错误分析。
3. 对路径失败题进一步统计首个错误动作、无效工具、提前 Finish 和预算耗尽。
4. 对 CTC/CTE 做相同 token/context 预算匹配，再下最终图结构因果结论。

## Source SHA256

- data/subsets/locomo10_500q_main_seed42.json: 969777b18ccfa0db8666a156b413446b1d2b72308a92d77eb26c3035fea54b29
- result_judge_locomo_deepseek_mragent_500q_main.jsonl: 662dcfac6b64f8f6c5e20f6b7f1b7fb6b46c59e60482f820eff0e188efd901f2
- result/diagnostics/raw_api_calls_mragent_500q_main_20260715_220124.jsonl: 0fe72114a2773fc09c426d939c81903948e33bbe68dd6f5fac6554be1ee2f342
- result/locomo/conv-26_result_deepseek_mragent_500q_main.jsonl: 4dd1d7c478cad7fa6aa4abf4981e433ecd338222806f21bcf0b7a295d8d60149
- result/locomo/conv-30_result_deepseek_mragent_500q_main.jsonl: 8093440b3ee1461205f4e1bd8bea965b89b046c51697169b527136ab52a9bda1
- result/locomo/conv-41_result_deepseek_mragent_500q_main.jsonl: cef8fb7018ba5f8426d1bbb9117945bb9eb9e016af9f6696dab24b5e44ff7ac9
- result/locomo/conv-42_result_deepseek_mragent_500q_main.jsonl: 8e5294157fbb668e74e63939b347af184c4edd54b9fb465c0aed9c4e7b43243b
- result/locomo/conv-43_result_deepseek_mragent_500q_main.jsonl: 65c11a2acb4b690af1a22fda372b96ef27a47c1b93c5456f548a5b45a21152fd
- result/locomo/conv-44_result_deepseek_mragent_500q_main.jsonl: 8f7bc3695225af9fdb7ab5ead700d3f4ad01c5567de963ebef7916a1d547841d
- result/locomo/conv-47_result_deepseek_mragent_500q_main.jsonl: 9db8e0ab47f67b87090e20f646696232a03803e3ed3b9ba0022655219c7a4e18
- result/locomo/conv-48_result_deepseek_mragent_500q_main.jsonl: e0d91ab7a7a4bdcd0a7c216d8731669db671d1e9bf1979d0c4490fb938616313
- result/locomo/conv-49_result_deepseek_mragent_500q_main.jsonl: e97e1ab0aebea1a1f2fddb2a19220797d8495700c6a64a0fb6c7dd20d6069395
- result/locomo/conv-50_result_deepseek_mragent_500q_main.jsonl: 3bce06b82255909cc95fdf28729b23e3753b66ab56b16e30c4fbf0400d60cfe2
