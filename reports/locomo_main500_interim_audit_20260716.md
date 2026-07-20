# LoCoMo 500 题主实验中期审计

更新时间：2026-07-20
审计分支基线：`exp/20260716-gate10-500q-main-results-v2`
审计提交：`265aa72d918991faa02e96be99b3ba928dee84a4`
实验协议：`docs/locomo_500q_ablation_protocol.md`

## 1. 审计结论

本轮仍不能标记为“全部完成”，但主动消融已经从部分结果推进为完整 200 题。准确状态是：

- 500 题主实验的 Full MRAgent、RAG、GraphRAG 已完整提交，逐题键对齐，无重复或额外行。
- A-Mem 完成 96/500，Mem0 完成 297/500，仍不能进入五方法公平比较。
- 五组 200 题消融均为 200/200，题目键、类别分布、memory view 和 active/passive 标记通过验收。
- Full MRAgent Judge 已完成 400/400，语义正确 312 题（0.7800）；RAG 和 GraphRAG Judge 分别只完成 354/400、290/400，不能直接把当前比例作为完整主表排名。
- Full MRAgent 的 5 个执行级 `ERROR` 已提交摘要 trace。代码与日志可以确认它们都发生在初始 tag-score 排序，但上传的 raw prompt/response 仍是占位摘要，不是可按 request id 串联的原始调用记录。
- 远端汇报中列出的 `reports/comparison_500q_main.md` 并未出现在提交 `265aa72` 的 Git tree 中；当前正式对比报告仍以本文为准。

因此，目前已有配对实验支持“主动图搜索优于同图视图下的被动读取”：CTE 和 CTC 视图上的主动增益均为正且 95% CI 不跨 0。与此同时，CTC active 相对 CTE active 的增量很小且 CI 跨 0，尚不能证明完整内容层在主动搜索时继续提供稳定收益。外部 baseline、完整 Judge、active 上下文可观测性和执行错误修复仍未闭环。

## 2. 数据与对齐验收

| 项目 | 结果 |
|---|---:|
| 主实验 manifest | 500 题 |
| 类别 1/2/3/4/5 | 102 / 101 / 96 / 101 / 100 |
| Conversation 数 | 10 |
| 消融 manifest | 200 题，仅类别 1/2，各 100 题 |
| 主实验重复键/额外键 | 0 / 0 |
| 主三方法缺题 | 0 |

主实验结果均包含 `sample` 和 `question_index`，可以做严格逐题配对。RAG 与 GraphRAG 行内记录的 QA 模型为 `deepseek-ai/DeepSeek-V4-Flash`；A-Mem/Mem0 provenance 记录了 V4-Flash、Qwen3-Embedding-4B 和 `enable_thinking=False`。Full MRAgent 行内没有保存 QA 模型、embedding 模型和 thinking 状态，仍需从本轮配置日志提取为紧凑 provenance，才能由 GitHub 独立验证同模型条件。

### 2.1 缩写和实验变量

| 缩写/设置 | 完整含义 | 当前代码中的可见记忆和行为 |
|---|---|---|
| CE | Cue-Episode，线索-事件 | query cue/key 直接检索 episode；禁用 tag 边和 topic/person content 工具 |
| CTE | Cue-Tag-Episode，线索-标签-事件 | 在 CE 上加入 tag 层，可由 key/tag 找到 episode；禁用 topic/person content 工具 |
| CTC | Cue-Tag-Content，线索-标签-内容 | 在 CTE 上再开放 topic event、person information、person aspect 等内容工具；episode 仍然可用 |
| passive | 被动、一次性读取 | 仍执行问题 key 提取和固定初始检索，但不进入 agent tool loop，`tool_calls=0` |
| active | 主动、多轮搜索 | 在初始检索后，由 LLM 根据当前状态选择图工具，最多 8 轮、总计 80 次工具调用 |
| Full MRAgent | 完整方法 | CTC + active |

五组消融是两个正交变量的组合，不是五种互不相关的方法：

- `CTE passive - CE passive`：tag 层的增量作用；
- `CTC passive - CTE passive`：topic/person content 层的增量作用；
- `CTE active - CTE passive`：在 CTE 视图上，多轮主动搜索的作用；
- `CTC active - CTC passive`：在完整 CTC 视图上，多轮主动搜索的作用。

`passive` 不等于完全不调用 LLM，也不等于普通向量 RAG；它共享 MRAgent 的问题 key、图和初始上下文，只去掉多轮工具决策。因此它适合做 MRAgent 内部因果消融，而 RAG/GraphRAG 适合做外部检索范式对比。

### 2.2 CTE 与 CTC 到底有什么区别

CTE 和 CTC 不是两套独立建图算法，也不是两张完全不同的图。当前实现中，CTC 是 CTE 的可见节点和工具超集；二者共享同一批 rewrite、embedding、keyword、episode 和底层图缓存，差异发生在回答阶段允许读取哪些记忆层。

```text
CTE：问题线索 -> 标签 -> 事件 -> 事件时间 / 关键词 / 邻近上下文
                         \-> 通过 key-tag 边继续找事件

CTC：保留 CTE 的全部路径
     + 问题线索 -> 主题 -> 主题下的一组事件
     + 人物 -> 人物属性 -> 与该属性相关的事件
```

| 对比维度 | CTE | CTC |
|---|---|---|
| 核心结构 | Cue-Tag-Episode | Cue-Tag-Content，且保留 Episode 路径 |
| 可用的共同工具 | `edges_by_tag`、`query_event_context`、`query_event_keywords`、`query_conversation_time` | 与 CTE 相同 |
| CTC 新增工具 | 无 | `query_topic_events`、`query_personal_information`、`query_personal_aspect` |
| 适合的问题 | 已知实体/标签后定位具体事件，或围绕事件补上下文与时间 | 需要汇总同一主题的多个事件，或沿人物属性聚合长期信息 |
| passive 行为 | 一次性使用事件和标签检索结果 | 在相同初始检索上额外展开命中的 topic/person content |
| active 行为 | LLM 多轮选择标签、事件、时间与上下文工具 | LLM 还可以主动选择主题和人物内容工具 |

因此，`CTC passive - CTE passive` 测到的是“开放内容层并展开更多内容”的联合效果，不是纯粹的图结构效果；如果 CTC 获得了更多上下文 token，收益也可能来自上下文数量。正式结论需要增加 context-token budget matching。`CTC active - CTE active` 则更接近“新增内容工具的边际价值”，但必须检查模型是否真的调用新增工具、调用参数是否有效，并在相同轮数/工具预算下比较。

本轮 CTC active 的 200 题中，140 题至少调用一次内容工具；共调用 `query_topic_events` 416 次、`query_personal_information` 30 次、`query_personal_aspect` 78 次，说明 treatment 确实被使用。但 18 题出现 37 次内容工具错误，其中 35 次来自 topic 参数格式错误：模型传入 `D3:t1:描述文字`，而后端只接受 `D3:t1`。另外两次是不存在的人名。故当前 `CTC active - CTE active` 不显著，不能直接解释为“内容层无效”；它也可能受到工具参数契约和额外无效调用的拖累。

## 3. 500 题主实验进度

| 方法 | 完成 | ERROR | 状态 | 是否可正式比较 |
|---|---:|---:|---|---|
| Full MRAgent | 500/500 | 5 | 完整 | 可与 RAG/GraphRAG 比较 |
| RAG | 500/500 | 0 | 完整 | 是 |
| GraphRAG | 500/500 | 0 | 完整 | 是 |
| A-Mem | 96/500 | 0 | 仅 conv-26/30 | 否 |
| Mem0 | 297/500 | 0 | 仅 conv-26/30/41/42/43/44 | 否 |

A-Mem/Mem0 的当前均值只反映已完成 conversation，不能与完整 500 题结果并排排名。其 `_metrics.runtime_sec` 也只覆盖逐题检索/回答，未证明包含 memory 构建成本，不能用于端到端耗时比较。

## 4. 当前可比结果

以下完全按仓库 `repro/compare_main_experiment.py` 的规则重算：类别 1-4 报普通题词法 F1；类别 5 单列 `not mentioned` 准确率；证据命中把 `D1:25-2` 归一到 turn 级 `D1:25`。

| 方法 | 普通题 F1（400） | 类别 5 准确率（100） | 证据命中（500） | 平均逐题耗时 | 平均工具调用 |
|---|---:|---:|---:|---:|---:|
| Full MRAgent | 0.5252 | 0.8400 | 0.7900 | 208.59 s | 7.42 |
| RAG | 0.3629 | 0.7600 | 0.7420 | 2.18 s | 0 |
| GraphRAG | 0.3517 | 0.7400 | 0.6900 | 2.44 s | 0 |

注意：Full MRAgent 的逐题耗时总和为 104293 秒，但服务器采用并发执行，不能把该总和直接当 wall-clock。当前收益伴随约两个数量级的单题计算开销，后续必须同时报告质量和成本。

### 4.1 分类别结果

| 类别 | 含义 | Full MRAgent | RAG | GraphRAG |
|---|---|---:|---:|---:|
| 1 | 多跳 | 0.4678 | 0.3869 | 0.3311 |
| 2 | 时间推理 | 0.6707 | 0.3771 | 0.4265 |
| 3 | 开放域推断 | 0.3229 | 0.1741 | 0.1761 |
| 4 | 单跳 | 0.6299 | 0.5039 | 0.4647 |
| 5 | 对抗/不可回答准确率 | 0.8400 | 0.7600 | 0.7400 |

当前最明显的优势出现在时间推理。类别 3 仍是绝对表现最低的普通题类别，且 Full MRAgent 的证据命中仅 0.5521，后续 badcase 应优先检查“问题键提取、图遍历路径、证据存在但未进入最终上下文”三层。

此前 15 题小样本中 single-hop F1=0.1170 的结论不再成立：本轮 101 道 single-hop 上 Full MRAgent F1=0.6299、证据命中=0.9010。旧值很可能受极小样本、早期管线和个别 badcase 共同影响；没有把旧 15 题在当前代码上重放之前，不能把变化归因给某一个修复。

### 4.2 配对差值

以 conversation 为 cluster 做 20000 次 bootstrap，普通题逐题配对：

| 对比 | 配对题数 | Full MRAgent F1 差值 | 95% CI |
|---|---:|---:|---:|
| Full MRAgent - RAG | 400 | +0.1623 | [0.1352, 0.1901] |
| Full MRAgent - GraphRAG | 400 | +0.1735 | [0.1456, 0.2017] |

两个区间均不跨 0。这是当前最扎实的中期证据：在同一批 10 个 conversation、同一批题目和已提交结果上，Full MRAgent 明显优于两种被动基线。不过这个差值同时混合了图表示、主动工具迭代、上下文预算和额外推理计算，不能直接解释为“主动搜索”单一机制的因果效果。

这里的 95% CI 是“配对方法差值的不确定性区间”，不是单个方法分数的波动范围。计算时先对齐同一道题的 Full MRAgent 与 baseline F1，再以 conversation 为 cluster 有放回抽样，重复计算平均差值，取 bootstrap 分布的 2.5% 和 97.5% 分位数。按频率学派口径，它不表示“真实差值有 95% 概率在区间内”；更合适的解释是：若重复从类似 conversation 总体抽样并按同样程序构造区间，约 95% 的区间会覆盖总体差值。

CI 不跨 0 表示当前 LoCoMo-10 上的优势对 conversation 重采样较稳定；跨 0 则不能排除无差异或反向差异。当前只有 10 个独立 conversation cluster，因此即使题目有 400 道，外推力度仍受 cluster 数限制。

### 4.3 Judge 当前进度

| 方法 | Judge 完成度 | 语义正确 | 当前正确率 | 可否进入完整主表 |
|---|---:|---:|---:|---|
| Full MRAgent | 400/400 | 312 | 0.7800 | 是 |
| RAG | 354/400 | 209 | 0.5904 | 否，缺 46 题 |
| GraphRAG | 290/400 | 169 | 0.5828 | 否，缺 110 题 |

远端汇报中的 `312/400`、`209/354`、`169/290` 混合了“正确题数/已判题数”和“完成度”两个概念。只有 Full MRAgent 的分母 400 表示完整 ordinary 子集；后两者只是部分运行的正确率。

缺失不是随机抽样：RAG 缺少整个 conv-50 和 conv-49 的后 9 题；GraphRAG 缺少整个 conv-49/50，并只完成 conv-48 的前 10 题。这种按运行顺序截断会造成 conversation 选择偏差。仅在已经共同 Judge 的题目上，Full MRAgent 为 0.7684、RAG 为 0.5904（354 题）；Full MRAgent 为 0.7586、GraphRAG 为 0.5828（290 题）。这些只能作为临时一致性检查，不能替代 400 题完整配对结论。

### 4.4 F1、Judge 和 Evidence hit 的区别

- F1 衡量 prediction 与 gold answer 的词元重叠，便宜、确定、可复算，但会惩罚同义改写和长答案。
- LLM Judge 读取 question、gold answer、prediction，判断语义是否正确，能识别同义表达，但受 judge 模型偏差、prompt 和随机性影响。
- Evidence hit 只判断 gold evidence 是否进入最终检索上下文，衡量检索而不是答案生成。命中证据仍答错属于利用/推理问题；未命中但答对可能来自猜测或模型先验。
- 类别 5 是不可回答/对抗题，当前按 `Not mentioned` 规则单列，不调用普通题 Judge。

完整 500 题主实验中，每个方法需要 Judge 的是类别 1-4 共 400 题。五方法完成后共 2000 次 Judge；五组 200 题消融再需要 1000 次。完全相同的 question/gold/prediction 三元组可以按哈希复用，但不能只因题号相同就复制 Judge。

当前提交的 Judge 行只记录 `llm_score`、题目、预测、参考答案、类别和 sample，没有记录 judge model、prompt version、thinking、request id 或原始响应。因此结果数值可复算，但无法从 GitHub 独立确认实际 Judge 模型。后续补跑必须固定使用独立于回答模型的 `Qwen/Qwen3.5-397B-A17B`，并明确标注它与论文 Judge 的差异；不建议让 DeepSeek-V4-Flash 自评自己的答案。

补全 Judge 前应先修改 runner：显式传 `JUDGE_BASE_URL`、`JUDGE_MODEL`、`JUDGE_ENABLE_THINKING=0` 和较小输出上限；按 `sample + question` 或新增的 `sample + question_index` 断点续跑而不是删除旧文件；记录 model、prompt version、request id、content、finish_reason、usage、retry 和解析错误。先验证现有 400/354/290 行没有重复，再只运行缺失题；A-Mem/Mem0 完成 500 题后再进入同一主表。

runner 修复并通过 smoke 后，只续跑 RAG 缺失的 46 题和 GraphRAG 缺失的 110 题，不得删除或从头覆盖现有结果。运行形态应显式指定：

```bash
export JUDGE_BASE_URL=https://api.siliconflow.cn/v1
export JUDGE_MODEL=Qwen/Qwen3.5-397B-A17B
export JUDGE_ENABLE_THINKING=0
# JUDGE_API_KEY 仅在服务器环境中设置，不写入命令、文档或 Git。

for tag in rag_500q_main graphrag_500q_main; do
  python eval/evaluate_reasoning.py \
    --data locomo --model deepseek --file "$tag" --allfile
done
```

验收不是“命令退出为 0”，而是每个已完成主方法得到 400 条普通题 Judge，题目键无缺失/重复，cat5 没有混入，三份文件均可由比较脚本读出 `judge_count=400`，并保存统一 provenance。A-Mem/Mem0 补齐后使用同一 judge 配置运行；五组消融暂不优先运行 Judge，先闭环主方法与 badcase。

## 5. 消融进度与当前含义

10 题 gate 的五条路径均已跑通，只证明接口、memory view 和 active/passive 路由工作，不用于统计结论。

消融只选 200 题是有意的成本/效力折中，不是从 500 题中挑“最容易提升”的题：它由固定 seed 从主实验子集中确定性抽取，包含 100 道多跳和 100 道时间推理，并在 10 个 conversation 间平衡。这两类最直接需要跨事件组合、时间定位和图路径探索，因而最适合检验图层与主动搜索。类别 3 主观开放、类别 4 多为单跳、类别 5 检验拒答，都不是本轮机制消融的首要对象。

每个条件 200 题可以提供逐题配对信号，并把五组消融从 2500 次 QA 降为 1000 次 QA；但结论只能写成“对多跳和时间题有效”，不能外推到全部题型。更重要的是独立统计单位仍只有 10 个 conversation。若 200 题结果显示 active 增益稳定且 CI 不跨 0，再扩展到 400 道普通题验证泛化，比一开始把所有消融都跑满 500 更有效率。

| 200 题消融 | 完成 | F1 | 证据命中 | 状态 |
|---|---:|---:|---:|---|
| CE + passive | 200/200 | 0.3544 | 0.7850 | 完整 |
| CTE + passive | 200/200 | 0.3359 | 0.8500 | 完整 |
| CTC + passive | 200/200 | 0.4495 | 0.9750 | 完整 |
| CTE + active | 200/200 | 0.5649 | 0.8200* | 完整，6 ERROR |
| CTC + active | 200/200 | 0.5852 | 0.8450* | 完整，7 ERROR |

这里统一使用 `repro/compare_main_experiment.py` 的词法 F1，ERROR 按 0 分保留。提交中的 `metrics_summary_*.json` 使用另一套 F1 归一化规则，因此会得到 CTE active 0.5769、CTC active 0.5993 等不同数字；两套分数不可混写，正式对比必须固定同一个 evaluator。

在完整 200 题逐题配对、以 conversation 为 cluster 的 20000 次 bootstrap 上：

| 配对差值 | F1 差值 | 95% CI | 结论 |
|---|---:|---:|---|
| CTE passive - CE passive | -0.0185 | [-0.0642, 0.0201] | CI 跨 0，未证明 tag 层单独有效 |
| CTC passive - CTE passive | +0.1135 | [0.0664, 0.1684] | content 层在被动读取中有稳定增益 |
| CTE active - CTE passive | +0.2289 | [0.1812, 0.2754] | 主动搜索在 CTE 视图上有稳定增益 |
| CTC active - CTC passive | +0.1357 | [0.0757, 0.1952] | 主动搜索在完整 CTC 视图上有稳定增益 |
| CTC active - CTE active | +0.0203 | [-0.0138, 0.0567] | CI 跨 0，未证明 active 下 content 层继续增益 |

分题型看，CTE active 的多跳/时间 F1 为 0.4464/0.6834，CTC active 为 0.4887/0.6816。当前主动搜索的主要收益集中在时间题；CTC 相比 CTE 的可见提升主要来自多跳题，但整体配对 CI 仍跨 0。

代价同样明显：CTE active 平均 5.57 次工具调用、4.12 轮、逐题 runtime 之和 46397.77 秒；CTC active 为 7.20 次、4.88 轮、48829.14 秒。两组 passive 的平均逐题耗时约 28-29 秒，而 active 约 232-244 秒，约为 8 倍。后续改进不能只追求 F1，还要报告每题调用数、轮数、延迟和错误率。

`*` Active Evidence hit 当前不可与 passive 严格比较。代码在 passive 分支把 `initial_support_ids` 写入 `prediction_context`，而 active 分支只返回 `_chat_with_tools()` 的 `evidence_support`，没有并入初始上下文；因此 active 的 0.8200/0.8450 是“工具返回证据命中”而不是“模型实际看过的全部证据命中”，只能视作下界。修复时应分别保存 `initial_context_ids`、`tool_context_ids` 和二者并集 `final_context_ids`，否则 badcase 的 retrieval miss 归因会产生假阳性。

## 6. Full MRAgent 的 5 个执行错误

| Sample | 题号 | 类别 | 直接异常 | 证据支持的原因 |
|---|---:|---:|---|---|
| conv-41 | 54 | 2 | `'str' object has no attribute 'get'` | 3 次 JSON 解析失败后返回 raw string |
| conv-43 | 68 | 3 | `'str' object has no attribute 'get'` | 3 次 JSON 解析失败后返回 raw string |
| conv-44 | 29 | 1 | `'list' object has no attribute 'get'` | JSON 根类型为 list；缺完整 traceback，无法确定具体 caller |
| conv-47 | 190 | 5 | `'str' object has no attribute 'get'` | 3 次 JSON 解析失败后返回 raw string |
| conv-48 | 24 | 3 | `'str' object has no attribute 'get'` | 3 次 JSON 解析失败后返回 raw string |

其中四题可以由日志中的 `tag_scores` 输出头和解析警告定位到 `Agent.select_key_tag()`：该阶段调用 `chat_text()` 生成 `{"keyword": ..., "tag_scores": {...}}`，随后直接执行 `key_out.get("tag_scores")`。`chat_text()` 在 3 次解析失败后按当前策略返回 raw string，导致 `.get()` 崩溃。`conv-44 Q029` 只保留了 list 类型异常，没有原始响应和完整 traceback；它可能发生在 question-key 或 tag-score caller，不能进一步确定。五题都没有进入主 agent tool loop，因此 `tool_calls=0`。

这不是 HTTP/API transport failure：现有日志片段显示请求返回 HTTP 200。更准确的共同根因是“结构化输出契约没有在调用边界执行”：`chat_text()` 允许返回任意 JSON 类型或 raw string，而下游 caller 假定必然得到 dict。

### 6.1 Trace 完整性审计

本次提交包含 500 行 manifest，5 个 ERROR 均标记 `has_trace=true`，并为每题提供五类文件。但是证据包只达到“摘要 trace”，没有达到此前约定的“完整 raw trace”：

- `raw_prompts.jsonl` 没有 `request_id`、messages、model、max_tokens、temperature 或 response_format；
- `raw_responses.jsonl` 没有原始 content、finish_reason、usage、reasoning_content 或 request_id；
- `retry_log.jsonl` 没有 attempt 编号，`ts` 字段被错误写成异常文本；
- 5 份 trace 都缺完整 traceback，4 份 `log_context` 混入了上一道题的日志；
- 因此目前不能验证输出是否真的因 `max_tokens` 截断，也不能重建每一次失败重试的原始输出。

当前已经足以定位代码缺陷和失败阶段，但不足以支持远端报告中的“模型输出被截断”这一更强结论。后者必须由 `finish_reason`、usage 和完整 response 证明。

### 6.2 Schema 问题的修复方案

只增加 `CHAT_TEXT_PARSE_MAX_ATTEMPTS` 或打开通用 `ENABLE_JSON_REPAIR` 不能根治问题：前者会重复生成同样的大对象，后者增加调用成本且可能改写 tag 分数。正确修复应放在结构化输出边界：

1. 为 question-key 和 tag-score 分别定义 validator；tag-score 必须是 dict，且 `tag_scores` 必须是键为字符串、值为有限数值的 dict。
2. `chat_text()` 不得在要求 JSON object 的 caller 中返回 raw string；解析或 schema 失败时抛出带 stage、request id 和 raw response 的 typed error，或进入显式 fallback。
3. list、缺少 `tag_scores`、非法分数和截断字符串都算 schema failure，并计入 `_metrics.schema_retries`；当前内部三次解析没有反映到该指标，需要修正。
4. 重试时使用同一 schema 和更短的错误反馈。若仍失败，采用确定性的安全 fallback，例如 embedding/string 预排序后的前 `TAG_LIMIT` 个 tag；必须记录 `forced_accept=true`，不能静默伪装成正常输出。
5. tag 数量很大时，先用非生成式相似度预筛到固定候选数，再让 LLM rerank，可降低长 JSON 风险；这是检索策略变化，必须单独记录版本并做小规模回归，不与纯 bug fix 混为一谈。
6. 增加单元测试覆盖：正确 dict、JSON list、缺字段、非法数值、截断 JSON、全部重试失败和 fallback；任何情况都不得再出现对 str/list 直接 `.get()`。
7. 修复后只重跑当前 5 个 ERROR，保留修复前后逐题结果并重算主表。若修改了 tag 候选预筛策略，则需要在固定小样本回归后重新运行 Full MRAgent，而不能只替换 5 行。

`response_format={"type":"json_object"}` 可以作为第一层约束，但不能替代本地 schema validation；OpenAI-compatible 服务仍可能返回错误根类型、截断文本或不满足业务字段的合法 JSON。

## 7. 与协议的偏离和缺失产物

| 要求 | 当前证据 | 判定 |
|---|---|---|
| 五方法各 500 题 | A-Mem 96，Mem0 297 | 未完成 |
| 五组消融各 200 题 | 五组均 200/200，键与配置通过验收 | 已完成 |
| 普通题 Judge | MRAgent 400/400；RAG 354/400；GraphRAG 290/400 | 部分完成 |
| 主实验 Markdown | 远端声称的 `comparison_500q_main.md` 未进入 Git tree；JSON/逐题 CSV 仍缺 | 未完成 |
| 5 个 MRAgent 执行错误摘要 | 5/5 trace + 500 行 manifest | 已提交但 raw 证据不完整 |
| MRAgent 全量判错归因 | Judge 已完成，但 `audit_mragent_judged_errors` 尚未执行 | 未完成 |
| Full MRAgent 模型/thinking provenance | trace 摘要记录 V4-Flash、thinking=false；无原始请求佐证 | 部分完成 |
| Active 全上下文证据 | 仅保存 tool evidence，缺 initial context ids | 未完成，影响 Evidence hit/badcase 归因 |
| 大体积 raw API 日志 | 服务器存在 | 正确地未直接提交 |

Judge 文件已经不再为空，但 RAG/GraphRAG 是按 conversation 顺序中断的部分结果；必须断点补齐，不能把当前分母当作完整数据集规模。

## 8. Git 交付规则调整

原 `.gitignore` 整体忽略 `result/` 和 `result_judge_*.jsonl`，迫使远端使用 `git add -f`，也会让空/新增 Judge 与逐题审计数据在正常 `git status` 中不可见。本次改为只放行：

- `result/locomo/*_result_*.jsonl`：逐题实验结果；
- 当前 500 题主实验与 200 题消融的 Judge JSONL；
- `result/diagnostics/mragent_main500_traces/`：脱敏、按题切分的审计 trace。
- `result/diagnostics/judge_errors_*.jsonl`：不含密钥的 Judge 失败 attempt 与原始响应。

仍然忽略 `log/`、完整 `raw_api_calls_*.jsonl`、cache、embedding、checkpoint 和密钥。不得上传 108.7 MB 全量 raw API 文件；应上传可逐题复核、无请求头和 API key 的抽取结果。

## 9. 下一步实验计划

下一轮不应立即扩大题量，而应先把已经得到的核心信号变成可审计、可解释的结论。

### P0：修复测量与执行错误

1. 修复 active 上下文记录：分别输出 `initial_context_ids`、`tool_context_ids`、`final_context_ids`，`prediction_context` 使用并集；增加单元测试，证明答案输入不因日志修复而改变。
2. 修复 CTC 工具参数边界：`query_topic_events` 在 ToolBridge 层只提取并校验 `D\d+:t\d+`，保留原始参数和规范化参数；人物工具对名字做合法候选校验，但不得把不存在的人名静默映射到另一个人。
3. 修复 question-key/tag-score 的 schema 边界，禁止 raw string/list 流入 `.get()`；为 fallback、retry 和 typed error 写测试。
4. 使用已提交的三份 manifest 定向重放：Full MRAgent 5 题、CTE active 6 题、CTC active 25 题。最后一组包含 7 个执行错误和 18 个内容工具错误；不同原因不合并计数。
5. 原 200 题消融及 Evidence hit 限制保留为第一轮记录，不覆盖、不扩大重跑。只有定向重放证明同类问题仍系统性影响正常题，才重新讨论全量 CTE/CTC。

P0 闸门验收：三份 replay 共 36 题且无重复键；active 的三类 context id 均有列表字段；合法 topic id 调用成功率 100%；非法 topic/person 参数返回结构化错误；schema 异常不再导致 `.get()` 崩溃；每题可按 request id 串联 prompt、response、tool trace 和 retry。

### P1：闭环现有主实验

1. Judge runner 已改为默认断点续跑，并在 overwrite 时先备份旧文件。由于旧 Judge 缺少统一模型 provenance，最终版应固定 Qwen3.5-397B-A17B、thinking=false 和新版严格 JSON prompt，对 MRAgent/RAG/GraphRAG 各完整重判 400 题。
2. 使用固定 main manifest 排序先做三方法同一 20 题 Judge v2 smoke，再运行 3 x 400；每阶段用 Judge validator 检查键、重复和 provenance。在相同 400 题上生成配对差值和 conversation-clustered 95% CI。旧 400/354/290 行只作历史记录。
3. 执行 `audit_mragent_judged_errors`，覆盖 Full MRAgent 的 88 个 Judge=0 ordinary badcase。归因至少区分：执行/schema 错误、初始检索缺失、工具路径偏离、检索到证据但利用失败、答案语义正确但 Judge 错判、gold/evidence 标注问题。
4. 每类抽取 3-5 个案例，保留 question、gold、prediction、初始上下文、逐轮工具调用、最终上下文、raw response、Judge 与人工结论。
5. 运行统一比较脚本并提交 `.md/.json/.csv`；当前缺失的 `reports/comparison_500q_main.md` 必须真正进入 Git。

### P2：补齐外部 baseline

1. 先完成 Mem0 剩余 203 题，再完成 A-Mem 剩余 404 题。两者当前逐题 QA 平均仅约 3.65 秒和 5.15 秒，服务器感知的长耗时更可能来自每个 conversation 的 memory 构建；必须额外记录 build wall-clock、QA wall-clock、API 次数和 cache hit，不能只看 `_metrics.runtime_sec`。
2. 对每种方法验收 500/500、同一 manifest、同一 QA/embedding 模型、thinking=false、无重复/额外题；单独报告 memory build 成本。
3. 补齐后再运行同一 Qwen Judge，形成 Full MRAgent、RAG、GraphRAG、A-Mem、Mem0 的五方法完整主表。

### P3：进入 Q-learning 检索路径改造

1. 不再追加 CTE/CTC 大规模结构消融；以当前 active 优势和完成 badcase 审计后的轨迹作为学习依据。
2. 基于完整 active trace 构造 transition：状态为问题、已见证据和图前沿；动作为工具及规范化参数；下一状态记录新增证据、空结果、重复访问与剩余预算。
3. 先实现无学习的 CBR 路径提示和 Monte-Carlo return 排序基线，再实现真正使用 `r + gamma * max Q(s', a')` 目标的离线 Q-learning；不能把成功分类器直接称为 Q-learning。
4. 比较 `Full MRAgent`、`+ CBR`、`+ return ranker`、`+ offline Q`、`+ CBR + offline Q`。模块只重排合法候选动作，不替换图、工具执行器或最终答案器。
5. 按 conversation 划分开发与测试，测试集冻结；统一工具预算后报告 F1、Judge、Evidence hit、首次命中步数、空/重复调用率、总调用数、延迟和失败率。先做 20-50 题 gate，再扩大到固定 200 题。

当前可以写出的严格结论是：Full MRAgent 相对 RAG/GraphRAG 的 500 题 F1 主效果成立；CTC content 在 passive 下有稳定增益；active 相对 passive 在 CTE、CTC 两种视图下都有稳定增益。尚不能写成“每一层都有效”，因为 CTE passive 相对 CE passive、CTC active 相对 CTE active 均未表现出稳定增益；外部 baseline 和完整语义 Judge 也尚未闭环。
