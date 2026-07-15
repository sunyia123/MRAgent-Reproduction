# LoCoMo 500 题主实验与消融协议

更新时间：2026-07-14

## 1. 目标与边界

本轮唯一主命题是：**在相同模型、相同题目、相同时间信息和可比检索预算下，MRAgent 的主动图搜索是否显著优于被动向量检索。**

围绕主命题，再拆成两个机制问题：

1. Cue-Tag-Content 图结构是否比被动检索更容易找回证据。
2. 基于中间证据的多轮主动重建是否比一次性检索更有效。

主实验使用 `LoCoMo-10` 中已有完整图 cache 的 10 个 conversation，而不是论文的完整 50 个 conversation。因此它是**中型、可审计验证**，不能直接声称复现论文 Table 1 的绝对数值。

论文主表使用 Gemini-2.5-Flash 与 Claude-Sonnet-4.5，排除了 adversarial 的 cat5；每种方法运行三次，并使用 GPT-4o-mini judge。论文同时限制最多 8 个 reasoning turns、每轮最多 10 次工具调用。当前没有这些同一模型与 judge，所以只能比较机制趋势，不能将绝对分数与论文表格混写。

## 2. 旧 100 题结果的状态

旧结果必须保留，但标签为 `pre-protocol diagnostic`，不能作为新的主结论。原因：

- MRAgent QA 实际使用 `DeepSeek-V4-Flash`，而 RAG/GraphRAG/Oracle 直接使用 `DeepSeek-V4-Pro`；模型不一致。
- 旧 RAG、GraphRAG、Oracle 在构造 context 时丢弃了 `event_time/session_date`。例如 RAG 已命中 `D1:3`，仍回答 `Yesterday` 而不是 `7 May 2023`。旧 RAG temporal 中 evidence hit 很高但 F1 很低，说明其主要问题是时间锚点被 runner 删除，而不能直接解释成“图一定更强”。
- 旧 MRAgent 使用总工具上限 50，没有论文所述的每轮 10 次工具调用限制。
- 旧 100 题包含 cat5；论文 LoCoMo 主比较排除了 cat5。

旧 100 题仍适合定位问题、对照修复前后差异、检查 trace；新的主结论以本协议指定的 core manifest 为准。

## 3. 固定题集

| manifest | 用途 | 题数 | 类别 | 与旧 100 题关系 |
| --- | --- | ---: | --- | --- |
| `data/subsets/locomo10_100q_seed42.json` | 历史诊断 | 100 | cat1-5 | 已完成，不改写 |
| `data/subsets/locomo_conv26_10q_core_seed42.json` | 全方法闸门 | 10 | cat1-4 | conv-26，cat1/2/3/4=3/2/2/3 |
| `data/subsets/locomo10_100q_core_seed42.json` | 可选调试集 | 100 | cat1-4 | 不再是进入 500 题的必经阶段 |
| `data/subsets/locomo10_500q_core_seed42.json` | 正式 500 题主实验 | 500 | cat1-4 | 主报告唯一口径 |
| `data/subsets/locomo10_500q_allcats_seed42.json` | 附录鲁棒性 | 500 | cat1-5 | 完整包含历史 100 题 |

`500q_core` 的类别分布为 cat1=125、cat2=130、cat3=91、cat4=154，cat3 在这 10 个 conversation 中可用题较少；报告必须展示真实计数而不是把类别平均化。`500q_allcats` 完整包含旧 100 题，但不得用于论文主表比较。

## 4. 公平运行条件

所有新的 core 实验必须满足：

- 图构建 cache namespace 保持 `--model deepseek --re_model v4flash`，复用现有 `rewrite_deepseek`、`keyword_deepseek`、`embedding/gpt_deepseek` cache。
- QA 必须显式传 `--qa_model v4flash`，让 MRAgent 与所有内部 baseline 使用相同问答模型；`ENABLE_THINKING=0`。
- A-Mem 与 Mem0 的记忆抽取/更新也必须路由到同一个 V4-Flash endpoint，并使用 Qwen3-Embedding-4B；若官方实现无法替换默认模型，该结果只能进入附录，不能进入主公平对比。
- MRAgent 使用 `--max_rounds 8 --max_tool_calls_per_round 10 --max_tool_calls 80`。
- 被动 baseline 使用相同 Qwen3-Embedding-4B 向量模型；native RAG 以原始 dialogue turn（含 session 时间与已有 BLIP caption）作为 unit，不使用 MRAgent 的 rewrite 内容。
- 所有方法严格读取同一个 manifest。结果 JSONL 必须保留 `sample`、`question_index`、`prediction_context`、`_metrics`。
- core 主实验只包括 cat1-4。cat5 只运行 `allcats` 附录，并单独报告 “Not mentioned” 判定。

## 5. 先做 10 题全方法闸门

先在 `locomo_conv26_10q_core_seed42.json` 上运行 Full MRAgent、native RAG、GraphRAG、Oracle、A-Mem 和 Mem0。该集合直接取自固定 100 题 core manifest，覆盖四个非对抗类别，并且只需要 A-Mem/Mem0 为一个 conversation 构建记忆。

10 题只用于验证接口、模型路由、时间字段、输出 schema、日志和具体案例，不用于显著性结论。六种方法均完成 10/10 后直接进入 500 题，不再强制跑修复后 100 题。

### 5.1 构建 native RAG cache

```bash
python repro/build_native_rag_cache.py \
  --sample_ids 26
```

预期：每个 sample 在 `data/locomo/rag_native/` 产生一个 `*_raw_turn.pkl`。该文件可断点续写，不能提交 Git。

### 5.2 Full MRAgent

```bash
export RUN_ID=gate10_full_$(date +%Y%m%d_%H%M%S)
export ENABLE_THINKING=0
python run_stratified.py \
  --data locomo --sample_ids 26 \
  --model deepseek --re_model v4flash --qa_model v4flash \
  --file mragent_full_gate10_qflash \
  --subset_manifest data/subsets/locomo_conv26_10q_core_seed42.json \
  --max_rounds 8 --max_tool_calls_per_round 10 --max_tool_calls 80
```

预期：结果文件 10 行；每题 `_metrics.tool_trace` 有实际工具名、参数和结果摘要；`raw_api_calls_${RUN_ID}.jsonl` 显示 `enable_thinking:false`。

### 5.3 Native RAG

```bash
export RUN_ID=gate10_rag_native_$(date +%Y%m%d_%H%M%S)
export ENABLE_THINKING=0
python repro/run_standard_rag_baseline.py \
  --data locomo --sample_ids 26 \
  --model deepseek --qa_model v4flash \
  --file rag_native_gate10_qflash --source raw --top_k 20 \
  --subset_manifest data/subsets/locomo_conv26_10q_core_seed42.json
```

预期：context 每行均含 `session_date`；temporal 输出不能再只返回 `Yesterday/last week`。旧 `--source rewrite` 仅作为修复前诊断保留，不作为主 baseline。

### 5.4 GraphRAG 与 Oracle

```bash
python repro/run_graphrag_baseline.py \
  --data locomo --sample_ids 26 \
  --model deepseek --qa_model v4flash \
  --file graphrag_gate10_qflash \
  --subset_manifest data/subsets/locomo_conv26_10q_core_seed42.json \
  --seed_k 10 --hops 1 --max_context_sentences 30

python repro/run_oracle_evidence_qa.py \
  --data locomo --sample_ids 26 \
  --model deepseek --qa_model v4flash \
  --file oracle_gate10_qflash \
  --subset_manifest data/subsets/locomo_conv26_10q_core_seed42.json
```

预期：两者 context 也必须含日期元数据。Oracle 仍低分时，不能再归因成检索失败，应检查 gold evidence 粒度、答案综合和指标。

### 5.5 A-Mem 与 Mem0

A-Mem adapter 位于 `repro/external_baselines/run_amem_adapter.py`，固定 `WujiangXu/A-mem@0c8039f28fdcc08189a23c07a3437d9d2482f9c2`。它保留官方逐 turn 记忆分析、演化判断、相似度种子检索和邻居扩展，但将默认 MiniLM/OpenAI 调用替换为本实验的 Qwen3-Embedding-4B 与 V4-Flash，并使用统一 QA prompt。

Mem0 adapter 位于 `repro/external_baselines/run_mem0_adapter.py`，固定 `mem0ai/mem0@ccbe5861a138c7583e01bb3a3aa6168e52526a23`。`mem0ai/memory-benchmarks` 当前依赖的 `feat/v3-pipeline` 分支已经删除，无法做 bit-identical checkout；因此本结果必须标为“固定当前 OSS Mem0 的公开可验收工程复现”，不能写成论文时期 Mem0 服务的完全复刻。

两个 adapter 都只读取 manifest 中的题，逐 turn 保留 speaker、绝对 session date、source id 和已有图像 caption；memory cache 可断点续跑。每题输出统一 JSONL、retrieved memories 和独立 trace，且 provenance 会记录源码 commit、数据/manifest 哈希、实际 memory/embedding/QA model 和 top-k。

安装与 10 题命令以 README 的 `External baseline adapters` 为唯一规范。A-Mem 与 Mem0 各完成 10/10 并通过 `repro/validate_baseline_results.py` 后，才进入六方法闸门汇总。

### 5.6 闸门验收

```bash
python repro/summarize_core_validation.py \
  --manifest data/subsets/locomo_conv26_10q_core_seed42.json \
  --methods mragent_full_gate10_qflash,rag_native_gate10_qflash,graphrag_gate10_qflash,oracle_gate10_qflash,amem_gate10_qflash,mem0_gate10_qflash \
  --model deepseek \
  --output reports/gate10_protocol_validation.md
```

报告还必须选择至少一个 Full MRAgent 好例和一个坏例，展示原始问题、gold、主动搜索每步工具与返回节点、最终上下文、预测，以及同题 RAG/A-Mem/Mem0 的检索内容。

停止条件：有任何方法少于 10 题、QA model 不一致、context 不含时间元数据、外部 baseline 未固定版本、或 raw trace 显示 thinking 被打开时，先修复，不扩大到 500。

## 6. 500 题主实验

10 题闸门通过后，在 `data/subsets/locomo10_500q_core_seed42.json` 上运行正式实验。不得覆盖闸门结果。

主对比优先于消融，顺序固定为：Full MRAgent -> native RAG -> GraphRAG -> A-Mem -> Mem0 -> Oracle。Oracle 只诊断“给定 gold evidence 后能否回答”，不属于与 MRAgent 竞争的 baseline。

| 方法 | 关键差异 | 回答的问题 |
| --- | --- | --- |
| Full MRAgent | CTC 图 + 多轮自适应工具调用 | 完整主动图搜索效果 |
| native RAG | 原始 turn 上一次性向量 top-k | 主动图搜索是否优于被动向量检索 |
| GraphRAG | 固定 seed + 固定邻居扩展 | 自适应遍历是否优于预定义图扩展 |
| A-Mem | 图记忆 + 相似度 seed + 邻居扩展 | MRAgent 的主动搜索是否超过另一种图记忆 |
| Mem0 | 紧凑事实记忆 + 被动相似度检索 | 完整图重建是否超过事实压缩记忆 |
| Oracle | 直接提供 gold evidence | 检索失败与答案生成失败的上界诊断 |

正式报告以逐题对齐的 F1、LLM Judge、Evidence Recall 为核心，同时报告 completed/error、平均工具数、平均轮数、输入/输出 token、延迟和检索上下文长度。只有 500 题用于统计性结论；10 题只展示流程案例。

## 7. 消融：图结构与主动搜索分别是否有效

论文 Figure 5 在 LoCoMo multi-hop 问题上沿两条轴消融：

1. 结构轴：CE（Cue-Episode，直接索引）-> CTE（Cue-Tag-Episode）-> CTC（Cue-Tag-Content，包含完整 episodic/semantic/topic 内容层）。
2. 搜索轴：不带 reasoning 的一次性访问 -> 带 reasoning 的多轮主动重建。

因此，“图构建是否有用”应由 CE/CTE/CTC 回答；“迭代扩展是否有用”应由相同 CTC 图上的一次性访问与多轮主动搜索回答。论文还单独比较 reasoning turns 与单轮并行检索预算，结论是增加搜索宽度不能替代增加重建深度。

当前先执行以下实现级消融：

| tag | 设置 | 检验的机制 | 解释边界 |
| --- | --- | --- | --- |
| `mragent_full_core500_qflash` | 8 rounds，CTC 全工具 | 完整方法 | 主结果 |
| `mragent_1round_core500_qflash` | `--max_rounds 1 --max_tool_calls 10` | 主动多步重建 | 仍保留一次 LLM 路由，不等于完全无 reasoning |
| `mragent_cte_view_core500_qflash` | 禁用 semantic 与 topic 工具，只允许 episodic CTE 路径 | CTE/CTC 内容层 | 从完整 cache 派生的运行时视图，不是重新 population |

`CTE runtime view` 示例：

```bash
python run_stratified.py ... \
  --file mragent_cte_view_core500_qflash \
  --disabled_tools query_personal_information,query_personal_aspect,query_topic_events \
  --subset_manifest data/subsets/locomo10_500q_core_seed42.json \
  --max_rounds 8 --max_tool_calls_per_round 10 --max_tool_calls 80
```

`1round` 示例：

```bash
python run_stratified.py ... \
  --file mragent_1round_core500_qflash \
  --subset_manifest data/subsets/locomo10_500q_core_seed42.json \
  --max_rounds 1 --max_tool_calls_per_round 10 --max_tool_calls 10
```

严格 CE 仍需实现“cue 直接索引 episode”的独立 memory view；严格 no-reasoning 仍需实现一次性固定检索而不是 `max_rounds=1`。这两项先在同一个 10 题 manifest 上验证，再决定是否进入 500 题。报告必须把 `CTE runtime view`、`1round approximation` 与论文严格消融分开命名。

## 8. Badcase 归因与人工复核

每个完成的 MRAgent run 都必须生成：

```bash
python repro/attribute_badcases.py \
  --manifest data/subsets/locomo10_500q_core_seed42.json \
  --result_tag mragent_full_core500_qflash \
  --model deepseek \
  --judge_results result_judge_locomo_deepseek_core500.jsonl \
  --manual_review reports/mragent_full_core500_manual_review.csv \
  --output_prefix reports/mragent_full_core500_badcase_attribution
```

输出 CSV 和 Markdown。其中 primary causes 互斥，分母是 F1 小于阈值的坏例总数：

- `execution_error`：API/JSON/runner 在回答前失败。
- `retrieval_miss`：gold evidence 不在 `prediction_context`。
- `temporal_normalization_failure`：命中证据但回答仍保留相对日期。
- `evidence_utilization_failure`：命中证据却回答无信息。
- `adversarial_overanswer`：只用于 allcats 的 cat5。
- `likely_metric_or_format_mismatch`：答案包含关系正确但 token F1 不利，必须人工/LLM judge 复核。
- `semantic_correct_lexical_false_negative`：F1 低，但 LLM Judge 或人工复核确认语义正确。
- `semantic_correct_judge_false_negative`：Judge 判错，但人工复核确认语义正确；必须保留人工说明。
- `answer_synthesis_or_semantic_error`：证据命中但仍答错，必须复核。

最终报告必须同时给出自动归因比例、CSV 中的原始输入输出、gold/predicted evidence、工具数、工具 trace 是否存在，以及人工复核后的最终比例。自动标签不能被写成最终语义事实。

## 9. 与论文其他 baseline 的比较

论文列出的外部 baseline 是 RAG、A-Mem、MemoryOS、LangMem、Mem0。上游 `Ji-shuo/MRAgent` 仓库未包含这些 baseline 的 runner；因此目前唯一可运行的内部比较是 RAG/GraphRAG/Oracle，不能把论文表中的其他数值复制到本项目表格中充当本地结果。

外部 baseline 的有效比较需要按以下顺序进行：

1. 固定一个官方仓库 commit，并写入 provenance 文件：仓库 URL、commit、依赖版本、LLM、embedding、QA prompt、top-k、是否使用 time metadata。
2. 在该方法官方实现中只运行 `locomo10_500q_core_seed42.json` 的 500 个键，排除 cat5。
3. 将输出适配为本项目 JSONL schema：`sample`、`question_index`、`question`、`answer`、`prediction`、`prediction_context`、`_metrics`。
4. 用下列检查阻止不完整或不同题集的输出进入总表：

```bash
python repro/validate_baseline_results.py \
  --manifest data/subsets/locomo10_500q_core_seed42.json \
  --result_glob 'result/external/amem/*.jsonl' \
  --method amem \
  --provenance reports/external_baselines/amem_provenance.md \
  --output reports/external_baselines/amem_validation.md
```

本阶段优先级固定为 native RAG -> GraphRAG -> A-Mem -> Mem0。MemoryOS 与 LangMem 暂不进入本轮主实验。A-Mem 和 Mem0 必须先通过 10 题闸门，再运行 500 题。

## 10. 提交要求

提交 manifest、代码、协议、汇总报告、badcase CSV/Markdown、小型结果 JSONL 与外部 baseline provenance。不要提交 raw cache、embedding、完整 raw API payload、完整 log 或 API key。

每次服务器推送前仍需更新：

```bash
python repro/update_server_directory_manifest.py \
  --root /data/nishome/cuiwenjia/MRAgent-Reproduction
```

并在反馈中给出 commit、manifest、每种方法的 completed/expected、QA/rewrite/embedding model、RUN_ID、日志路径、任何 timeout/parse error，以及是否满足本协议的停止条件。
