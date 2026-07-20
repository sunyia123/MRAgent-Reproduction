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
- 主实验 5 个 ERROR 和两组 active 的 13 个 ERROR 组成 schema replay 清单；重复题保留条件标签。

验收标准：

- 20 题三类 context id 字段完整；合法 topic id 调用成功率 100%。
- schema 异常不再导致 `.get()` 崩溃；fallback 和 retry 均可追踪。
- 修复前后结果独立保存，不覆盖第一轮数据。

停止条件：任一题仍出现无日志的 ERROR、上下文字段缺失或无法关联 request id，先修复，不进入 E1。

### E1：修复后的主动消融

数据：继续使用 `locomo10_200q_ablation_seed42`，不重新抽题。

方法：

| 方法 | 图视图 | 检索方式 | 用途 |
|---|---|---|---|
| CTE active v2 | CTE | 多轮 | 修复后事件级主动基线 |
| CTC active v2 | CTC | 多轮 | 修复后完整内容工具方法 |
| CTE passive | CTE | 单次 | 沿用第一轮固定结果 |
| CTC passive | CTC | 单次 | 沿用第一轮固定结果 |

CTE/CTC active v2 使用同一模型、temperature、轮数上限、总工具调用上限和代码 commit。若 schema 修复改变所有题的正常候选排序，则 passive 也要重跑；若只改变 active 工具边界，则 passive 保持不动。

报告指标：逐题 F1、完整 Evidence hit、Judge、ERROR、schema fallback、工具调用、轮数、输入/输出 token、runtime；同时给出 conversation-clustered 配对 95% CI。

关键判定：

- active 相对 passive 的 CI 是否仍不跨 0。
- CTC active v2 相对 CTE active v2 是否转为稳定正增益。
- 内容工具错误率是否下降，额外 F1 是否值得额外调用和延迟。

### E2：内容层拆分与预算控制

先从 200 题 manifest 固定抽取 50 题，保持 conversation 和类别平衡。方法如下：

| 方法 | 开放内容 | 模式 | 控制变量 |
|---|---|---|---|
| CTE passive budget | 无 | 被动 | 固定最终 context token 预算 |
| CTC passive budget | topic + person | 被动 | 与 CTE 相同 token 预算 |
| CTE active budget | 无 | 主动 | 固定轮数和工具预算 |
| CTC topic-only | 仅 topic | 主动 | 禁用 person 工具 |
| CTC person-only | 仅 person/aspect | 主动 | 禁用 topic 工具 |
| CTC full | topic + person | 主动 | 完整内容工具 |

先完成 10 题接口闸门，再运行 50 题。只有某个内容来源相对 CTE 的配对增益方向稳定、工具成功率合格且不存在明显成本失控，才扩到完整 200 题。

该实验回答：CTC 的收益究竟来自 topic、person、上下文数量，还是仅来自更多调用机会。

### E3：主实验 Judge 与 badcase 闭环

- 断点补齐 RAG Judge 46 题、GraphRAG Judge 110 题，使三种主方法均为 400/400 ordinary questions。
- 固定 Qwen Judge 模型、thinking=false、prompt version 和 provenance。
- 在同一 400 题上计算 Judge 配对差值与 conversation-clustered 95% CI。
- 对 Full MRAgent 的 88 个 Judge=0 题执行自动归因和人工复核。

badcase 分类：执行/schema 错误、初始检索缺失、工具路径偏离、内容工具参数错误、命中证据但利用失败、语义正确但 Judge 错判、gold/evidence 问题。

每类报告 3-5 个完整案例，包含原始问题、gold、prediction、初始上下文、逐轮工具轨迹、最终上下文、raw response、Judge 与人工结论。

### E4：外部 baseline 闭环

- 先完成 Mem0 剩余 203 题，再完成 A-Mem 剩余 404 题。
- 五种主方法必须使用同一 500 题 manifest、QA 模型、embedding 模型和 thinking 设置。
- 分开记录 memory build wall-clock、QA wall-clock、API 次数、cache hit 和逐题 runtime。
- 补齐后运行同一 Judge，生成五方法完整主表和逐题 CSV。

### E5：CBR/Q-learning 检索路径改造

从通过 E0-E3 验收的 active trace 建立路径经验库：

- 状态：问题表示、已见证据、当前图前沿、已调用工具和剩余预算。
- 动作：下一工具及规范化参数。
- 结果：新证据、工具错误、重复访问、答案与 Judge。
- 奖励：答案正确性和 evidence gain 为正，调用成本、重复路径和错误为负。

比较四组：Full MRAgent、CBR 路径提示、离线 Q-learning 动作排序、CBR + Q-learning。按 conversation 划分开发/测试，测试题不允许在线更新后再次评测。先做 20-50 题 gate，再进入固定 200 题。

## 5. 交付物

每个阶段推送：

- 固定 manifest 及 SHA256；
- 每题结果 JSONL；
- 每题 prompt/response/tool/retry trace；
- 配置与模型 provenance；
- 汇总 JSON、逐题 CSV 和中文 Markdown 报告；
- 运行日志和服务器目录 manifest。

主报告只引用完整、同题、同配置结果。部分结果和修复前结果保留为历史批次，不进入最终排名，也不得被后续运行静默覆盖。
