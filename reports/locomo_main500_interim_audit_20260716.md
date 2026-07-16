# LoCoMo 500 题主实验中期审计

更新时间：2026-07-16  
审计分支基线：`exp/20260716-gate10-500q-main-results`  
审计提交：`3845cb77e3775e576e091a5103272eb840e2e881`  
实验协议：`docs/locomo_500q_ablation_protocol.md`

## 1. 审计结论

本轮不能标记为“全部完成”，准确状态是：

- 500 题主实验的 Full MRAgent、RAG、GraphRAG 已完整提交，逐题键对齐，无重复或额外行。
- A-Mem 仅完成 54/500，Mem0 仅完成 145/500，不能进入五方法公平比较。
- 200 题被动消融已完整；两组主动消融分别只完成 40/200 和 60/200。
- 三个主方法的 Judge 文件在服务器清单中均为 0 字节；统一 Judge、逐题对比表、正式置信区间报告和 MRAgent 全量 badcase 归因尚未提交。
- Full MRAgent 有 5 个执行级 `ERROR`，但对应 raw prompt、raw response、retry/error 和阶段定位尚未进入仓库，因此当前不能给出真实根因。

因此，目前已有较强的中期信号支持“主动图搜索优于被动检索”，但还不足以宣称 MRAgent 的每个组成机制都已被独立验证，也不足以完成与 A-Mem、Mem0 的正式比较。

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

## 3. 500 题主实验进度

| 方法 | 完成 | ERROR | 状态 | 是否可正式比较 |
|---|---:|---:|---|---|
| Full MRAgent | 500/500 | 5 | 完整 | 可与 RAG/GraphRAG 比较 |
| RAG | 500/500 | 0 | 完整 | 是 |
| GraphRAG | 500/500 | 0 | 完整 | 是 |
| A-Mem | 54/500 | 0 | 仅 conv-26 | 否 |
| Mem0 | 145/500 | 0 | 仅 conv-26/30/41 | 否 |

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

## 5. 消融进度与当前含义

10 题 gate 的五条路径均已跑通，只证明接口、memory view 和 active/passive 路由工作，不用于统计结论。

| 200 题消融 | 完成 | F1 | 证据命中 | 状态 |
|---|---:|---:|---:|---|
| CE + passive | 200/200 | 0.3544 | 0.7850 | 完整 |
| CTE + passive | 200/200 | 0.3359 | 0.8500 | 完整 |
| CTC + passive | 200/200 | 0.4495 | 0.9750 | 完整 |
| CTE + active | 40/200 | 0.5967 | 0.8250 | 不完整，不可排名 |
| CTC + active | 60/200 | 0.7037 | 0.8833 | 不完整，不可排名 |

在完整 200 题配对上：

- CTC passive - CE passive = +0.0950，95% CI [0.0414, 0.1520]。
- CTC passive - CTE passive = +0.1135，95% CI [0.0668, 0.1693]。
- CTE passive 反而低于 CE passive，说明仅增加当前 tag/topic/event 视图没有形成稳定收益；content 展开才是这轮被动图视图的主要贡献。

主动消融目前只覆盖前 2-3 个 conversation，存在完成顺序带来的样本选择偏差。补齐到同一 200 题之前，不能用 0.5967/0.7037 证明主动检索增益，也不能比较 CTE active 与 CTC active。

## 6. Full MRAgent 的 5 个执行错误

| Sample | 题号（1-based） | 类别 | 问题 | 当前可确认阶段 |
|---|---:|---:|---|---|
| conv-41 | 54 | 2 | When did John help renovate his hometown community center? | 未进入 agent loop |
| conv-43 | 68 | 3 | What would be a good hobby related to his travel dreams for Tim to pick up? | 未进入 agent loop |
| conv-44 | 29 | 1 | What is something that Audrey often dresses up her dogs with? | 未进入 agent loop |
| conv-47 | 190 | 5 | What is the name of James's cousin's dog? | 未进入 agent loop |
| conv-48 | 24 | 3 | Why did Jolene sometimes put off doing yoga? | 未进入 agent loop |

五行均为 `tool_calls=0`、`runtime_sec=0`。这只能证明失败发生在 agent loop 之前或错误被上层统一吞并，不能据此猜测是 timeout、JSON parse、问题键抽取还是数据错误。服务器 manifest 显示本轮 raw API 日志存在，但 108.7 MB 的全量文件未提交。应从它和主日志中抽取这 5 题的 request id、raw prompt、raw response、finish reason、usage、每次 retry 和原始异常，形成脱敏逐题 trace。

## 7. 与协议的偏离和缺失产物

| 要求 | 当前证据 | 判定 |
|---|---|---|
| 五方法各 500 题 | A-Mem 54，Mem0 145 | 未完成 |
| 五组消融各 200 题 | 两组 active 仅 40/60 | 未完成 |
| 普通题 Judge | 三个主方法 Judge 文件均 0 字节 | 未完成 |
| 主实验 Markdown/JSON/逐题 CSV | 未提交 | 未完成 |
| MRAgent 全量判错归因 | 未提交；仅结果行可见 | 未完成 |
| Full MRAgent 模型/thinking provenance | 结果行未记录 | 证据不足 |
| 大体积 raw API 日志 | 服务器存在 | 正确地未直接提交 |

服务器清单中的三个空 Judge 文件不能算“已生成”。空文件应保留现场并先做 2 题 Judge smoke，确认输出 schema、模型路由和断点写入后再跑全量。

## 8. Git 交付规则调整

原 `.gitignore` 整体忽略 `result/` 和 `result_judge_*.jsonl`，迫使远端使用 `git add -f`，也会让空/新增 Judge 与逐题审计数据在正常 `git status` 中不可见。本次改为只放行：

- `result/locomo/*_result_*.jsonl`：逐题实验结果；
- 当前 500 题主实验与 200 题消融的 Judge JSONL；
- `result/diagnostics/mragent_main500_traces/`：脱敏、按题切分的审计 trace。

仍然忽略 `log/`、完整 `raw_api_calls_*.jsonl`、cache、embedding、checkpoint 和密钥。不得上传 108.7 MB 全量 raw API 文件；应上传可逐题复核、无请求头和 API key 的抽取结果。

## 9. 下一检查点

下一次远端推送至少应包含：

1. A-Mem 500/500、Mem0 500/500 的结果文件和完成度验证。
2. CTE active 200/200、CTC active 200/200，同题键对齐。
3. 非空 Judge 文件；先报告 2 题 smoke，再报告完整数量。
4. `compare_main_experiment.py` 生成的 `.md/.json/.csv`，不得只给手写汇总。
5. 5 个执行 ERROR 的脱敏 trace，以及所有 Judge 错题的自动归因和人工复核状态。
6. Full MRAgent 的紧凑 provenance：实际 QA/embedding 模型、thinking、commit、manifest SHA256、RUN_ID。

完成上述项目后，才进入“核心改进是否 solid”的正式结论。当前可接受的表述是：Full MRAgent 相对 RAG/GraphRAG 的主效果已经得到 500 题支持，图内容视图的被动增益得到 200 题支持；主动检索的独立因果增益、外部 baseline 优势和语义 Judge 结果仍待完成。
