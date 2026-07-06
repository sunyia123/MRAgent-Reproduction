# 下一轮实验交接文档：以核心改进是否 solid 为目标

更新时间：2026-07-06

## 1. 总体判断

当前不应继续盲目扩大完整 V4-Pro 全流程。下一轮目标是用更少成本、更清晰证据判断：

1. MRAgent 的图结构记忆是否真的优于扁平 RAG。
2. 低分来自图构建、检索路径、模型综合、图像缺失，还是评估指标。
3. CBR/Q-learning 是否有明确可插入的位置，而不是只做形式上的增强。

因此下一轮优先级是：

```text
数据集/任务审计 -> 图快照 -> badcase 全路径复查 -> Standard RAG -> GraphRAG -> Oracle evidence QA -> CBR probe
```

## 2. 服务器执行前检查

```bash
cd /data/nishome/cuiwenjia/MRAgent-Reproduction
git pull --ff-only origin main
git status --short --branch
conda activate mragent-repro
python -m py_compile \
  repro/audit_dataset_tasks.py \
  repro/export_badcase_pack.py \
  repro/export_graph_snapshot.py \
  repro/run_standard_rag_baseline.py
```

预期：

- `git status` 干净。
- 所有脚本编译通过。
- 不触发任何 LLM/API 调用。

失败处理：

- 如果 `git pull --ff-only` 失败，先 `git status --short --branch`，不要 `reset --hard`。
- 如果脚本编译失败，提交错误日志，不要继续运行实验。

## 3. 任务 A：数据集与任务构建审计

目的：

- 明确当前数据集到底包含多少 conversation、QA、类别、图像 turn。
- 明确后续小样本子集怎么选，避免随意抽样。

命令：

```bash
python repro/audit_dataset_tasks.py \
  --data_path data/dataset_locomo.json \
  --output reports/dataset_task_audit_locomo_20260706.md
```

预期效果：

- 生成 `reports/dataset_task_audit_locomo_20260706.md`。
- 报告包含 sample 数、QA 数、category 分布、每个 sample 的 session/turn/image turn/question 数。

验收标准：

- 明确写出当前是 LoCoMo-10，不是论文完整 LoCoMo。
- 后续所有小样本实验都要引用这份审计报告说明选择理由。

## 4. 任务 B：conv-30 图快照导出

目的：

- 不重跑 rewrite/keyword/embedding。
- 从已有 cache 复建 MRAgent 内存图。
- 检查 single-hop badcase 的 gold evidence 是否存在于图中。

命令：

```bash
python repro/export_graph_snapshot.py \
  --data locomo \
  --model deepseek \
  --sample 30 \
  --output_dir result/graph_snapshot \
  --report reports/graph_snapshot_conv30_20260706.md
```

预期效果：

```text
result/graph_snapshot/conv-30_nodes.jsonl
result/graph_snapshot/conv-30_edges.jsonl
reports/graph_snapshot_conv30_20260706.md
```

验收标准：

- 报告列出 episode_event、keyword、topic、persona、personal_event 数量。
- 报告列出 gold evidence 覆盖率。
- 如果 gold evidence 缺失，说明是图构建或 rewrite 问题。
- 如果 gold evidence 存在但 QA 没检索到，说明是检索/工具路径问题。

GitHub 提交：

- 提交 Markdown 报告。
- 不提交完整 `result/graph_snapshot/*.jsonl`，除非文件很小；否则写 manifest。

## 5. 任务 C：single-hop badcase 全路径复查

当前问题：

- conv-30 的 cat4 single-hop F1 很低。
- 初步 badcase pack 显示：它可能混合了图像题失败、语义正确但 F1 低、回答过长等情况。

命令：

```bash
python repro/export_badcase_pack.py \
  --data locomo \
  --model deepseek \
  --file stratified \
  --sample 30 \
  --output reports/badcase_pack_conv30_stratified_20260706_server_review.md
```

人工补充要求：

对每个 cat4 低分问题，补充：

1. 原始 question。
2. gold answer。
3. prediction。
4. gold evidence id。
5. gold evidence 对应原始对话。
6. gold evidence 对应 rewrite sentence。
7. gold evidence 的 keyword/tag/topic。
8. prediction_context 是否包含 gold evidence。
9. tool path 是否过长或漂移。
10. 判断失败类型：
    - evaluation mismatch；
    - image evidence missing；
    - retrieval miss；
    - graph construction issue；
    - tool path drift；
    - model synthesis issue。

验收标准：

- 不能只写“single-hop 低”。
- 必须逐题判断是否真错。
- 如果语义正确但 F1 低，要明确标为 metric mismatch。
- 如果是图像题，要关联 VLM 图片访问问题。

## 6. 任务 D：流程简化与模型分层

原则：

- 不要所有阶段默认 V4-Pro。
- 只有最终小样本对比和关键 QA 阶段优先用 V4-Pro。
- rewrite/keyword/diagnostic 可以先用更快模型或低 reasoning 配置。

下一轮报告必须记录：

| 阶段 | 模型 | 是否 reasoning | max_tokens | 是否复用 cache |
| --- | --- | --- | ---: | --- |
| rewrite |  |  |  |  |
| keyword |  |  |  |  |
| embedding |  |  |  |  |
| QA |  |  |  |  |
| judge |  |  |  |  |

如果使用已有 cache，必须写清楚 cache 来源和 commit。

## 7. 任务 E：Standard RAG smoke

目的：

- 判断 MRAgent 图工具链是否至少优于扁平向量检索。
- 必须和 MRAgent stratified 的同一批 15 题比较，不能直接拿 RAG 105 题总体分数对比 MRAgent 15 题分数。

前提：

- conv-30 的 rewrite 和 embedding cache 已存在。

命令：

```bash
python repro/run_standard_rag_baseline.py \
  --data locomo \
  --model deepseek \
  --file rag_smoke \
  --sample_ids 30 \
  --top_k 20

python eval/evaluate_reasoning.py \
  --data locomo \
  --model deepseek \
  --file rag_smoke \
  --allfile
```

公平对比：

```bash
python repro/compare_rag_to_mragent_subset.py \
  --mragent_result result/locomo/conv-30_result_deepseek_stratified.jsonl \
  --rag_result result/locomo/conv-30_result_deepseek_rag_smoke.jsonl \
  --output reports/rag_vs_mragent_conv30_stratified_20260706.md \
  --subset_output result/locomo/conv-30_result_deepseek_rag_smoke_stratified_subset.jsonl
```

预期：

- 生成 RAG prediction JSONL。
- 生成评估结果。
- 生成 `reports/rag_vs_mragent_conv30_stratified_20260706.md`。
- 报告对比 MRAgent conv-30 stratified 15 题与 RAG full output 中匹配出来的同一批 15 题。

验收：

- 必须显示 matched questions 为 15/15。
- 报告至少包含 overall、cat1、cat2、cat4、cat5。
- 记录 MRAgent 和 RAG 各自是否命中 gold evidence。
- 如果 RAG full output 没有匹配到 15 题中的任意问题，停止解释原因，不要写结论。

## 8. 任务 F：GraphRAG baseline 设计与实现

当前只要求设计，不立即全量跑。

最低版本：

1. 用 embedding top-k 找 seed episode nodes。
2. 根据 graph snapshot 扩展 keyword/topic/persona 邻居。
3. 将子图转成 context。
4. 单轮 QA。
5. 与 Standard RAG 和 MRAgent 对比。

需要新增脚本：

```text
repro/run_graphrag_baseline.py
```

最小实验：

```text
conv-30 同一批 15 题
top_k_seed = 10
hop = 1 / 2
```

报告必须写：

- seed nodes。
- expanded nodes。
- edge types。
- gold evidence 是否命中。
- 与 Standard RAG 的差异。

## 9. 任务 G：Oracle evidence QA

目的：

- 区分“检索错”还是“模型拿到证据仍答错”。

做法：

- 直接把 gold evidence 对应原始对话或 rewrite sentence 给模型。
- 单轮回答。
- 如果 oracle 答对而 MRAgent 答错，问题在检索/工具路径。
- 如果 oracle 仍答错，问题在模型综合、rewrite 表达或 gold/evaluation。

需要新增脚本：

```text
repro/run_oracle_evidence_qa.py
```

优先只跑 conv-30 badcase 中的 cat4。

## 10. 任务 H：CBR/Q-learning 插入点

当前只做方案，不急于跑完整学习。

CBR 应先作为中间模块：

```text
conversation sample -> 生成 probe questions -> 跑图检索轨迹 -> case bank -> benchmark QA 前检索相似案例 -> 调整检索策略
```

Q-learning 是 CBR 内部的价值学习机制，不是 CBR 本身。

最小 case bank 字段：

```json
{
  "sample_id": "",
  "probe_question": "",
  "question_type": "",
  "retrieved_event_ids": [],
  "tool_path": [],
  "success": null,
  "failure_type": "",
  "lesson": "",
  "state": {},
  "action": "",
  "reward": null
}
```

## 11. 下一次提交要求

服务器端 Claude Code 完成任务 A/B/C 后，提交：

```bash
git add reports/dataset_task_audit_locomo_20260706.md \
        reports/graph_snapshot_conv30_20260706.md \
        reports/badcase_pack_conv30_stratified_20260706_server_review.md
git commit -m "reports: add dataset graph and badcase audits"
git push origin main
```

如果生成了大型 `result/graph_snapshot/*.jsonl`，不要直接提交，改写 manifest：

```text
reports/graph_snapshot_manifest_20260706.md
```

manifest 包含：

- 服务器绝对路径；
- 文件大小；
- SHA256；
- 生成命令；
- 对应 commit hash。
