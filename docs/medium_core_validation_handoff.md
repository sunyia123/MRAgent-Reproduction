# 中型核心验证阶段交接文档

更新时间：2026-07-06

## Context

当前小样本诊断已经完成：

- conv-30 的 15 题 MRAgent 小样本跑通。
- graph snapshot 已证明 conv-30 的 gold evidence coverage 是 75/75。
- single-hop 低分主要不是图构建缺失，而是 evaluation mismatch、图像证据缺失、tool path 漂移。
- 现在要进入中型核心验证阶段，目标是判断 MRAgent 的图结构检索是否真的比更简单的检索方法强。

不要直接全量跑 LoCoMo-10 的 1986 题。当前阶段固定为：

```text
LoCoMo-10 / 100 questions / 同一题集 / 多方法对比
```

方法：

1. MRAgent 原图工具调用。
2. Standard RAG。
3. GraphRAG。
4. Oracle evidence QA。

## 当前阻塞与处理原则

2026-07-07 的中型验证启动时发现：

- conv-30 的 rewrite、keyword、embedding cache 完整。
- conv-26 只有 rewrite cache，缺 keyword 和 embedding。
- conv-42 有不完整 `.tmp` rewrite，不能当作完整 cache。
- conv-41、conv-43、conv-44、conv-47、conv-48、conv-49、conv-50 缺 rewrite、keyword、embedding。
- DeepSeek-V4-Pro 太慢；DeepSeek-V4-Flash 速度更好，但下午高峰仍可能 API 超时。

这不是模型能力问题，而是工程可恢复性问题：旧逻辑只有整批 session 全完成后才会把 rewrite cache 视为有效，中断后容易丢进度。

现在 `run_stratified.py` 已改为可恢复：

- 不删除已有 `.tmp`。
- rewrite 按已完成 session 数续跑。
- keyword 按已完成 jsonl 行数续跑。
- 如果 `.tmp` 最后一行损坏，会截断到最后一个完整有效记录。
- 完整校验通过后才把 `.tmp` 移动为正式 cache。

因此下一步不是继续手工清理目录，而是直接分批补 cache，并保留每批报告。

推荐模型策略：

- rewrite / keyword：优先使用 `deepseek-ai/DeepSeek-V4-Flash`。
- QA 对比：可以继续使用同一模型，保证方法间公平。
- 如果 Flash 在同一个 session 连续超时，停止该 batch，记录 session id、日志路径和 `.tmp` 已完成行数。

不要为了提速临时改变 prompt、抽样题集或评价脚本，否则 100 题对比会失去可解释性。

## Request

请完成中型核心验证实验的准备和第一轮运行。重点不是追求最大规模，而是保证所有方法在同一批 100 题上比较。

### 任务 1：构建固定 100 题 subset manifest

使用代码：

```text
repro/build_stratified_subset.py
```

数据大约长这样：

- `data/dataset_locomo.json`
- 10 个 conversation samples。
- 1986 个 QA。
- 每个 QA 包含 question、answer、category、evidence。

要做什么：

- 生成固定 manifest。
- 每个 sample 抽 10 题。
- 总计 100 题。
- 尽量覆盖 cat1/cat2/cat3/cat4/cat5。

输出：

```text
data/subsets/locomo10_100q_seed42.json
```

这个 manifest 可以提交 GitHub，因为它是小型可复现实验配置。

### 任务 2：运行 MRAgent on 100q subset

使用代码：

```text
run_stratified.py
```

当前 `run_stratified.py` 已支持 `--subset_manifest`。它会读取 manifest 中的 `sample_id` 和 `question_index`，确保 MRAgent 与其他 baseline 使用同一批题。

输出：

```text
result/locomo/<sample>_result_deepseek_mragent_100q.jsonl
```

要点：

- 可以复用已有 rewrite/keyword/embedding cache。
- 如果某个 sample 缺 cache，使用可恢复逻辑分批补齐，不要删除 `.tmp`。
- 每个 sample 只跑 manifest 指定的 10 题。

分批推进顺序：

1. Batch 1：conv-26、conv-42。
   - conv-26 需要 keyword + embedding + MRAgent 10 题。
   - conv-42 需要从 `.tmp` rewrite 续跑或重建完整 rewrite，然后 keyword + embedding + MRAgent 10 题。
   - 输出 `reports/cache_batch1_conv26_conv42_20260707.md`。
2. Batch 2：conv-41、conv-43、conv-44。
   - 每个 sample 需要 rewrite + keyword + embedding + MRAgent 10 题。
   - 输出 `reports/cache_batch2_conv41_conv43_conv44_20260707.md`。
3. Batch 3：conv-47、conv-48、conv-49、conv-50。
   - 每个 sample 需要 rewrite + keyword + embedding + MRAgent 10 题。
   - 输出 `reports/cache_batch3_conv47_conv48_conv49_conv50_20260707.md`。

每个 batch 报告必须写清楚：

- 使用的模型 id。
- 每个 sample 的 rewrite session 完成数。
- keyword 行数是否等于 rewrite session 数。
- embedding 文件是否生成。
- MRAgent result JSONL 是否为 10 行。
- 是否存在 API timeout、retry、坏 JSON、schema error。
- 如果中断，`.tmp` 文件路径和已完成行数。

### 任务 3：运行 Standard RAG on 100q subset

使用代码：

```text
repro/run_standard_rag_baseline.py
```

输入：

- subset manifest：`data/subsets/locomo10_100q_seed42.json`
- 每个 sample 的 rewrite cache。
- 每个 sample 的 embedding cache。

输出：

```text
result/locomo/<sample>_result_deepseek_rag_100q.jsonl
```

要点：

- 只跑 manifest 指定的 100 题。
- 不要跑全量 1986 题。
- 不重跑 rewrite、keyword、embedding。

### 任务 4：运行 GraphRAG on 100q subset

使用代码：

```text
repro/run_graphrag_baseline.py
```

GraphRAG 数据大约长这样：

- rewrite sentence 是图节点。
- keyword、topic、origin turn 是边或邻接关系。
- 先用 embedding 找 seed nodes。
- 再扩展 keyword/topic/origin 邻居。
- 将扩展子图转成 context，单轮 QA。

输出：

```text
result/locomo/<sample>_result_deepseek_graphrag_100q.jsonl
```

本轮默认：

- seed_k = 10
- hops = 1
- max_context_sentences = 30

### 任务 5：运行 Oracle evidence QA on 100q subset

使用代码：

```text
repro/run_oracle_evidence_qa.py
```

Oracle 数据大约长这样：

- 直接使用 QA 的 gold evidence id。
- 从 rewrite cache 中找到对应 sentence-level evidence。
- 把 gold evidence context 直接给模型回答。

目的：

- 判断模型拿到证据后能不能答对。
- 如果 Oracle 答对而 RAG/MRAgent 答错，问题在检索。
- 如果 Oracle 也错，问题在模型综合、rewrite 表达或评估。

输出：

```text
result/locomo/<sample>_result_deepseek_oracle_100q.jsonl
```

### 任务 6：生成对比报告

使用代码：

```text
repro/compare_rag_to_mragent_subset.py
repro/summarize_core_validation.py
```

当前它可以比较任意 baseline 与 MRAgent subset，只是参数名 `--rag_result` 保留了历史名称。

生成：

```text
reports/medium_core_validation_100q_YYYYMMDD.md
```

报告必须包含：

- subset manifest 路径。
- 每个方法实际完成题数。
- 每类题数量。
- overall / cat1 / cat2 / cat3 / cat4 / cat5 分数。
- evidence hit rate。
- Q9 类型 image/tool-path 案例在更大集合中是否普遍。
- 哪些错误是 retrieval，哪些是 synthesis，哪些是 metric mismatch。

当四种方法都跑完同一 manifest 后，使用 `repro/summarize_core_validation.py` 生成总表。它读取 manifest 和各方法 JSONL，输出每个方法的完成题数、overall/category score 和 evidence hit rate。

## Output Format

最终反馈：

1. 当前 commit hash。
2. subset manifest 是否生成，路径是什么，包含多少题。
3. 每个方法是否运行：
   - MRAgent 100q：完成/未完成/阻塞原因。
   - Standard RAG 100q：完成/未完成。
   - GraphRAG 100q：完成/未完成。
   - Oracle 100q：完成/未完成。
4. 每个方法输出路径。
5. 每个方法完成题数。
6. 是否有任何方法不是同一批题。
7. 初步指标。
8. 是否有任何 runner 未按 manifest 运行。
9. 新提交的报告路径和 commit hash。

## Constraints

1. 不要全量跑 1986 题。
2. 允许补齐缺失 cache，但必须使用可恢复逻辑，禁止删除 `.tmp` 后从零开始。
3. 不要把不同题集的结果当作公平对比。
4. 不要提交大型 cache、embedding、rewrite、keyword、log。
5. result JSONL 如果较小可以提交；如果过大，写 manifest。
6. 如果 API 成本或时间明显超预期，先停下来反馈，不要继续扩大。
7. 不要临时改实验设计；需要代码改动时交给 Codex。

## Checkpoint

遇到以下情况必须停下来：

1. 同一个 session 连续超时，导致 batch 无法继续。
2. Standard RAG、GraphRAG、Oracle 使用的题集不一致。
3. MRAgent 无法保证与 manifest 同题。
4. GraphRAG 报错或输出空 context。
5. Oracle evidence 找不到 gold evidence。
6. 100 题运行时间超过预期。
7. 需要修改核心代码而不是实验脚本。
