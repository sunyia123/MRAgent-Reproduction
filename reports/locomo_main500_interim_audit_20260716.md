# LoCoMo 500 题主实验中期审计

更新时间：2026-07-16  
审计分支基线：`exp/20260716-gate10-500q-main-results`  
审计提交：`a4e59fe8715bf58ed93f6fc663a8a8170f756589`
实验协议：`docs/locomo_500q_ablation_protocol.md`

## 1. 审计结论

本轮不能标记为“全部完成”，准确状态是：

- 500 题主实验的 Full MRAgent、RAG、GraphRAG 已完整提交，逐题键对齐，无重复或额外行。
- A-Mem 仅完成 54/500，Mem0 仅完成 145/500，不能进入五方法公平比较。
- 200 题被动消融已完整；两组主动消融分别只完成 40/200 和 60/200。
- 三个主方法的 Judge 文件在服务器清单中均为 0 字节；统一 Judge 和基于 Judge 的全量 badcase 归因尚未完成。
- Full MRAgent 的 5 个执行级 `ERROR` 已提交摘要 trace。代码与日志可以确认它们都发生在初始 tag-score 排序，但上传的 raw prompt/response 仍是占位摘要，不是可按 request id 串联的原始调用记录。

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

这里的 95% CI 是“配对方法差值的不确定性区间”，不是单个方法分数的波动范围。计算时先对齐同一道题的 Full MRAgent 与 baseline F1，再以 conversation 为 cluster 有放回抽样，重复计算平均差值，取 bootstrap 分布的 2.5% 和 97.5% 分位数。按频率学派口径，它不表示“真实差值有 95% 概率在区间内”；更合适的解释是：若重复从类似 conversation 总体抽样并按同样程序构造区间，约 95% 的区间会覆盖总体差值。

CI 不跨 0 表示当前 LoCoMo-10 上的优势对 conversation 重采样较稳定；跨 0 则不能排除无差异或反向差异。当前只有 10 个独立 conversation cluster，因此即使题目有 400 道，外推力度仍受 cluster 数限制。

### 4.3 F1、Judge 和 Evidence hit 的区别

- F1 衡量 prediction 与 gold answer 的词元重叠，便宜、确定、可复算，但会惩罚同义改写和长答案。
- LLM Judge 读取 question、gold answer、prediction，判断语义是否正确，能识别同义表达，但受 judge 模型偏差、prompt 和随机性影响。
- Evidence hit 只判断 gold evidence 是否进入最终检索上下文，衡量检索而不是答案生成。命中证据仍答错属于利用/推理问题；未命中但答对可能来自猜测或模型先验。
- 类别 5 是不可回答/对抗题，当前按 `Not mentioned` 规则单列，不调用普通题 Judge。

完整 500 题主实验中，每个方法需要 Judge 的是类别 1-4 共 400 题。五方法完成后共 2000 次 Judge；五组 200 题消融再需要 1000 次。完全相同的 question/gold/prediction 三元组可以按哈希复用，但不能只因题号相同就复制 Judge。

当前 `eval/judge.py` 默认 judge 是 `openai/gpt-4o-mini`，且 `evaluate_reasoning.py` 会先删除旧 Judge 文件、没有断点续跑，也没有保存完整 judge raw response。用户当前没有 OpenAI/Claude/Gemini API，因此不能直接按默认配置全量运行。公开可验收方案应固定使用独立于回答模型的 `Qwen/Qwen3.5-397B-A17B` 作为文本 Judge，并明确标注它与论文 Judge 的差异；不建议让 DeepSeek-V4-Flash 自评自己的答案。

全量 Judge 前应先修改 runner：显式传 `JUDGE_BASE_URL`、`JUDGE_MODEL`、`JUDGE_ENABLE_THINKING=0` 和较小输出上限；按 `sample + question_index` 断点续跑而不是删除旧文件；记录 model、prompt version、request id、content、finish_reason、usage、retry 和解析错误。先在每类抽题完成 smoke，确认每行都有唯一题目键和 0/1 label，再运行三个已完成主方法；A-Mem/Mem0 完成 500 题后再进入同一主表。

runner 修复并通过 smoke 后，主实验的运行形态应为：

```bash
export JUDGE_BASE_URL=https://api.siliconflow.cn/v1
export JUDGE_MODEL=Qwen/Qwen3.5-397B-A17B
export JUDGE_ENABLE_THINKING=0
# JUDGE_API_KEY 仅在服务器环境中设置，不写入命令、文档或 Git。

for tag in mragent_500q_main rag_500q_main graphrag_500q_main; do
  python eval/evaluate_reasoning.py \
    --data locomo --model deepseek --file "$tag" --allfile
done
```

验收不是“命令退出为 0”，而是每个已完成主方法得到 400 条普通题 Judge，题目键无缺失/重复，cat5 没有混入，三份文件均非空且可以由比较脚本读出 `judge_count=400`。A-Mem/Mem0 补齐后使用同一 judge 配置运行；消融五组使用 200 题 manifest 验证各 200 条。

## 5. 消融进度与当前含义

10 题 gate 的五条路径均已跑通，只证明接口、memory view 和 active/passive 路由工作，不用于统计结论。

消融只选 200 题是有意的成本/效力折中，不是从 500 题中挑“最容易提升”的题：它由固定 seed 从主实验子集中确定性抽取，包含 100 道多跳和 100 道时间推理，并在 10 个 conversation 间平衡。这两类最直接需要跨事件组合、时间定位和图路径探索，因而最适合检验图层与主动搜索。类别 3 主观开放、类别 4 多为单跳、类别 5 检验拒答，都不是本轮机制消融的首要对象。

每个条件 200 题可以提供逐题配对信号，并把五组消融从 2500 次 QA 降为 1000 次 QA；但结论只能写成“对多跳和时间题有效”，不能外推到全部题型。更重要的是独立统计单位仍只有 10 个 conversation。若 200 题结果显示 active 增益稳定且 CI 不跨 0，再扩展到 400 道普通题验证泛化，比一开始把所有消融都跑满 500 更有效率。

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
| 五方法各 500 题 | A-Mem 54，Mem0 145 | 未完成 |
| 五组消融各 200 题 | 两组 active 仅 40/60 | 未完成 |
| 普通题 Judge | 三个主方法 Judge 文件均 0 字节 | 未完成 |
| 主实验 Markdown | 已提交三方法对比；JSON/逐题 CSV 仍缺 | 部分完成 |
| 5 个 MRAgent 执行错误摘要 | 5/5 trace + 500 行 manifest | 已提交但 raw 证据不完整 |
| MRAgent 全量判错归因 | Judge 尚未运行 | 未完成 |
| Full MRAgent 模型/thinking provenance | trace 摘要记录 V4-Flash、thinking=false；无原始请求佐证 | 部分完成 |
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
4. `compare_main_experiment.py` 生成的 `.json/.csv`；Markdown 已提交。
5. 修复 tag-score schema 边界后只重跑这 5 个 ERROR，并保留修复前后逐题差异。
6. 从 per-run raw API 日志重新抽取 5 题真实 request/response/retry；不得用 `note` 占位，也不得混入相邻题日志。
7. 所有 Judge 错题的自动归因和人工复核状态。
8. Full MRAgent 的紧凑 provenance：实际 QA/embedding 模型、thinking、commit、manifest SHA256、RUN_ID。

完成上述项目后，才进入“核心改进是否 solid”的正式结论。当前可接受的表述是：Full MRAgent 相对 RAG/GraphRAG 的主效果已经得到 500 题支持，图内容视图的被动增益得到 200 题支持；主动检索的独立因果增益、外部 baseline 优势和语义 Judge 结果仍待完成。
