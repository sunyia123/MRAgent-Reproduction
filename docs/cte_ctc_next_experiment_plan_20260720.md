# MRAgent CTE/CTC 机制闭环与下一轮实验计划

更新时间：2026-07-20

## 1. 目标

本计划优先回答三个问题：

1. 在相同图视图下，多轮主动搜索是否稳定优于一次性被动读取？
2. CTC 新增的主题/人物内容层是否提供独立收益，还是收益主要来自更多上下文和更多工具调用？
3. 在修复 schema、工具参数和观测日志后，MRAgent 相对 RAG、GraphRAG、A-Mem、Mem0 的优势是否仍然成立？

CBR/Q-learning 改造只在上述问题闭环后进入正式主实验，避免在未定位的工程错误上叠加新模块。

## 2. CTE 与 CTC

CTE 和 CTC 共用同一份底层记忆图与缓存。CTC 不是重新建图，而是在 CTE 的事件级路径上开放更高层的内容聚合节点和工具。

```text
CTE：Cue -> Tag -> Episode -> 时间 / 关键词 / 邻近上下文

CTC：CTE 全部路径
     + Topic -> 一组相关 Episode
     + Person -> Aspect -> 一组相关 Episode
```

CTE 可使用标签边、事件上下文、事件关键词和对话时间。CTC 在此基础上增加主题事件、人物信息和人物属性查询。因此：

- `CTE active - CTE passive` 检验事件级图上的主动搜索。
- `CTC active - CTC passive` 检验完整图视图上的主动搜索。
- `CTC passive - CTE passive` 目前同时改变内容层和上下文数量，必须做 token budget matching 后才能解释为内容层效果。
- `CTC active - CTE active` 检验新增内容工具的边际价值，但必须核验新增工具被实际调用且参数有效。

## 3. 当前证据

五组消融均在同一 200 题 manifest 上完成，每个 conversation 20 题，类别 1/2 各 100 题。

| 配对差值 | F1 差值 | 95% CI | 当前判断 |
|---|---:|---:|---|
| CTE active - CTE passive | +0.2289 | [0.1812, 0.2754] | 主动搜索有效 |
| CTC active - CTC passive | +0.1357 | [0.0757, 0.1952] | 主动搜索有效 |
| CTC passive - CTE passive | +0.1135 | [0.0664, 0.1684] | 内容展开有收益，但上下文预算未控制 |
| CTC active - CTE active | +0.0203 | [-0.0138, 0.0567] | 新增内容工具的独立收益未成立 |

CTC active 的 200 题中有 140 题调用内容工具，但 18 题出现 37 次内容工具错误，主要是 topic id 带描述后缀。当前结果足以证明 active 机制有价值，不足以否定 CTC 内容层。

## 4. 实验阶段

### E0：测量与工具契约修复

代码修改：

- active 输出分别保存 `initial_context_ids`、`tool_context_ids`、`final_context_ids`，并以并集作为 `prediction_context`。
- `query_topic_events` 规范化并校验 `D\d+:t\d+`；同时保存原始参数和规范化参数。
- 人物工具只接受图中合法人物；未知人物返回结构化错误，不做模糊静默替换。
- question-key/tag-score 使用本地 schema validator，禁止 raw string/list 流入 dict caller。
- 每次调用保存 request id、stage、prompt、raw response、finish reason、usage、retry 和 error type。

诊断数据：

- 当前 18 道内容工具错误题，加 2 道正常工具调用题，组成固定 20 题工具契约诊断集。
- 主实验 5 个 ERROR、CTE active 的 6 个 ERROR、CTC active 的 7 个 ERROR，以及 CTC 的 18 道内容工具错误题，按来源生成三份 replay manifest；同一道题的多个原因保存在 `replay_reasons`，不重复运行。

验收标准：

- 20 题三类 context id 字段完整；合法 topic id 调用成功率 100%。
- schema 异常不再导致 `.get()` 崩溃；fallback 和 retry 均可追踪。
- 修复前后结果独立保存，不覆盖第一轮数据。

停止条件：任一题仍出现无日志的 ERROR、上下文字段缺失或无法关联 request id，先修复，不进入 E1。

当前不再安排 CTE/CTC 全量重跑或内容层拆分。第一轮 200 题结果作为机制结论保留；只运行以下三个固定 replay manifest：

| 重放条件 | Manifest | 题数 |
|---|---|---:|
| Full MRAgent 主实验 ERROR | `locomo_replay_mragent_main_errors_20260720.json` | 5 |
| CTE active ERROR | `locomo_replay_cte_active_errors_20260720.json` | 6 |
| CTC active ERROR 与内容工具错误 | `locomo_replay_ctc_active_repairs_20260720.json` | 25 |

只有定向重放显示同类问题仍在正常题中系统性出现，才重新讨论扩大 CTE/CTC 实验。

三次重放必须写入新的结果 tag，不原位改写第一轮 JSONL。重放完成后使用 `repro/compare_targeted_replays.py` 生成修复前后逐题对照；验收要求是题数完整、执行 ERROR 清零、内容工具非法参数清零、三类 context id 字段齐全。F1 变化只作诊断，不用这 36 个定向样本估计总体增益。

### E1：主实验 Judge 与 badcase 闭环

- 当前 Judge 缺少统一 provenance，且新 runner 修正了互相矛盾的 JSON prompt。最终结果应先备份旧文件，再使用 `Qwen/Qwen3.5-397B-A17B`、thinking=false 对三个主方法各自完整重判 400 题，而不是把新结果追加到未知配置的旧文件中。
- 先以 `--judge_manifest data/subsets/locomo10_500q_main_seed42.json --judge_max_new 20` 对三方法同一 20 道普通题做 Judge v2 smoke，检查 label、原始响应、finish reason、usage 和断点续跑，再移除数量上限运行 3 x 400。
- smoke 和完整结果均使用 `repro/validate_judge_results.py` 校验题目键、重复行、统一模型、prompt version、thinking 设置和审计字段；任何一项失败都不得进入比较脚本。
- 在同一 400 题上计算 Judge 配对差值与 conversation-clustered 95% CI。
- 对 Full MRAgent 的 88 个 Judge=0 题执行自动归因和人工复核。

badcase 分类：执行/schema 错误、初始检索缺失、工具路径偏离、内容工具参数错误、命中证据但利用失败、语义正确但 Judge 错判、gold/evidence 问题。

每类报告 3-5 个完整案例，包含原始问题、gold、prediction、初始上下文、逐轮工具轨迹、最终上下文、raw response、Judge 与人工结论。

### E2：外部 baseline 闭环

- 先完成 Mem0 剩余 203 题，再完成 A-Mem 剩余 404 题。
- 五种主方法必须使用同一 500 题 manifest、QA 模型、embedding 模型和 thinking 设置。
- 分开记录 memory build wall-clock、QA wall-clock、API 次数、cache hit 和逐题 runtime。
- 补齐后运行同一 Judge，生成五方法完整主表和逐题 CSV。

### E3：CBR/Q-learning 检索路径改造

从通过 E0-E2 验收的 active trace 建立路径经验库：

- 状态：问题表示、已见证据、当前图前沿、已调用工具和剩余预算。
- 动作：下一工具及规范化参数。
- 结果：新证据、工具错误、重复访问、答案与 Judge。
- 奖励：答案正确性和 evidence gain 为正，调用成本、重复路径和错误为负。

比较五组：Full MRAgent、CBR 路径提示、return ranker、离线 Q-learning 动作排序、CBR + Q-learning。return ranker 只学习完整轨迹回报，是用来证明 TD bootstrap 是否必要的对照，不能写成 Q-learning。按 conversation 划分开发/测试，测试题不允许在线更新后再次评测。先做 20-50 题 gate，再进入固定 200 题。

## 5. 下一次服务器执行顺序

1. 拉取本分支后运行静态检查与单元测试，不调用 API。
2. 按三份 replay manifest 定向运行 Full、CTE active、CTC active，分别使用新 tag；每组结束立即生成 before/after 对照报告。不要再跑五组 200 题消融。
3. 固定 Qwen Judge、thinking=false，先对 Full/RAG/GraphRAG 各运行 20 个新判断并校验；三组均通过后，从现有文件断点续跑至各 400 条普通题。
4. 先续跑 Mem0 的 4 个缺失 conversation，再续跑 A-Mem 的 8 个缺失 conversation。复用已完成 memory cache，记录构建和 QA 两段耗时。
5. 五方法结果和 Judge 完整后，更新主比较、MRAgent 全量 badcase 归因和中期报告。
6. 只有上述数据闭环后，开始 transition 导出与 CBR/return-ranker/Q-learning 的 20-50 题接口实验。

Checkpoint：定向重放仍有执行 ERROR；Judge 20 题出现缺字段、混合 provenance 或重复键；外部 baseline cache provenance 不一致；任一情况先停在当前阶段并反馈日志，不继续扩大运行。

## 6. 交付物

每个阶段推送：

- 固定 manifest 及 SHA256；
- 每题结果 JSONL；
- 每题 prompt/response/tool/retry trace；
- 配置与模型 provenance；
- 汇总 JSON、逐题 CSV 和中文 Markdown 报告；
- 运行日志和服务器目录 manifest。

主报告只引用完整、同题、同配置结果。部分结果和修复前结果保留为历史批次，不进入最终排名，也不得被后续运行静默覆盖。
