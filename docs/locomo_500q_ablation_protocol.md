# LoCoMo 500 题主实验与消融协议

更新时间：2026-07-14

## 1. 目标与边界

本轮目标是验证 MRAgent 的两个核心主张是否成立：

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
| `data/subsets/locomo10_100q_core_seed42.json` | 修复后 pilot | 100 | cat1-4 | 论文主表口径 |
| `data/subsets/locomo10_500q_core_seed42.json` | 正式 500 题主实验 | 500 | cat1-4 | 主报告唯一口径 |
| `data/subsets/locomo10_500q_allcats_seed42.json` | 附录鲁棒性 | 500 | cat1-5 | 完整包含历史 100 题 |

`500q_core` 的类别分布为 cat1=125、cat2=130、cat3=91、cat4=154，cat3 在这 10 个 conversation 中可用题较少；报告必须展示真实计数而不是把类别平均化。`500q_allcats` 完整包含旧 100 题，但不得用于论文主表比较。

## 4. 公平运行条件

所有新的 core 实验必须满足：

- 图构建 cache namespace 保持 `--model deepseek --re_model v4flash`，复用现有 `rewrite_deepseek`、`keyword_deepseek`、`embedding/gpt_deepseek` cache。
- QA 必须显式传 `--qa_model v4flash`，让 MRAgent 与所有内部 baseline 使用相同问答模型；`ENABLE_THINKING=0`。
- MRAgent 使用 `--max_rounds 8 --max_tool_calls_per_round 10 --max_tool_calls 80`。
- 被动 baseline 使用相同 Qwen3-Embedding-4B 向量模型；native RAG 以原始 dialogue turn（含 session 时间与已有 BLIP caption）作为 unit，不使用 MRAgent 的 rewrite 内容。
- 所有方法严格读取同一个 manifest。结果 JSONL 必须保留 `sample`、`question_index`、`prediction_context`、`_metrics`。
- core 主实验只包括 cat1-4。cat5 只运行 `allcats` 附录，并单独报告 “Not mentioned” 判定。

## 5. 先做 100 题修复后 Pilot

先在 `locomo10_100q_core_seed42.json` 运行四种方法。只有每种方法都完成 100/100，才进入 500 题。

### 5.1 构建 native RAG cache

```bash
python repro/build_native_rag_cache.py \
  --sample_ids 26,30,41,42,43,44,47,48,49,50
```

预期：每个 sample 在 `data/locomo/rag_native/` 产生一个 `*_raw_turn.pkl`。该文件可断点续写，不能提交 Git。

### 5.2 Full MRAgent

```bash
export RUN_ID=core100_full_$(date +%Y%m%d_%H%M%S)
export ENABLE_THINKING=0
python run_stratified.py \
  --data locomo --sample_ids 26,30,41,42,43,44,47,48,49,50 \
  --model deepseek --re_model v4flash --qa_model v4flash \
  --file mragent_full_core100_qflash \
  --subset_manifest data/subsets/locomo10_100q_core_seed42.json \
  --max_rounds 8 --max_tool_calls_per_round 10 --max_tool_calls 80
```

预期：每个结果文件 10 行；每题 `_metrics.tool_trace` 有实际工具名、参数和结果摘要；`raw_api_calls_${RUN_ID}.jsonl` 显示 `enable_thinking:false`。

### 5.3 Native RAG

```bash
export RUN_ID=core100_rag_native_$(date +%Y%m%d_%H%M%S)
export ENABLE_THINKING=0
python repro/run_standard_rag_baseline.py \
  --data locomo --sample_ids 26,30,41,42,43,44,47,48,49,50 \
  --model deepseek --qa_model v4flash \
  --file rag_native_core100_qflash --source raw --top_k 20 \
  --subset_manifest data/subsets/locomo10_100q_core_seed42.json
```

预期：context 每行均含 `session_date`；temporal 输出不能再只返回 `Yesterday/last week`。旧 `--source rewrite` 仅作为修复前诊断保留，不作为主 baseline。

### 5.4 GraphRAG 与 Oracle

```bash
python repro/run_graphrag_baseline.py \
  --data locomo --sample_ids 26,30,41,42,43,44,47,48,49,50 \
  --model deepseek --qa_model v4flash \
  --file graphrag_core100_qflash \
  --subset_manifest data/subsets/locomo10_100q_core_seed42.json \
  --seed_k 10 --hops 1 --max_context_sentences 30

python repro/run_oracle_evidence_qa.py \
  --data locomo --sample_ids 26,30,41,42,43,44,47,48,49,50 \
  --model deepseek --qa_model v4flash \
  --file oracle_core100_qflash \
  --subset_manifest data/subsets/locomo10_100q_core_seed42.json
```

预期：两者 context 也必须含日期元数据。Oracle 仍低分时，不能再归因成检索失败，应检查 gold evidence 粒度、答案综合和指标。

### 5.5 Pilot 验收

```bash
python repro/summarize_core_validation.py \
  --manifest data/subsets/locomo10_100q_core_seed42.json \
  --methods mragent_full_core100_qflash,rag_native_core100_qflash,graphrag_core100_qflash,oracle_core100_qflash \
  --model deepseek \
  --output reports/core100_protocol_validation.md
```

停止条件：有任何方法少于 100 题、QA model 不一致、context 不含时间元数据、或 raw trace 显示 thinking 被打开时，先修复，不扩大到 500。

## 6. 500 题主实验

Pilot 通过后，将 `core100` 的四个 file tag 替换为 `core500`，并将 manifest 替换为 `data/subsets/locomo10_500q_core_seed42.json`。不得覆盖 pilot 结果。

主方法与三种最低限度的组件消融：

| tag | 设置 | 检验的机制 | 解释边界 |
| --- | --- | --- | --- |
| `mragent_full_core500_qflash` | 8 rounds，CTC 全工具 | 完整方法 | 主结果 |
| `mragent_1round_core500_qflash` | `--max_rounds 1 --max_tool_calls 10` | 主动多步重建 | 仍保留一次 LLM 路由，不等于完全无 reasoning |
| `mragent_no_semantic_core500_qflash` | 禁用 `query_personal_information,query_personal_aspect` | semantic content layer | 是 CTE/CTC 差异的实现级近似 |
| `mragent_no_tag_edge_core500_qflash` | 禁用 `edges_by_tag` | cue-tag 定向访问 | 是强消融，不等于论文 CE 的精确复刻 |
| `rag_native_core500_qflash` | 原始 turn + 向量 top-k + 单轮 QA | 被动文本检索 | 内部强 RAG baseline |

`no_semantic` 示例：

```bash
python run_stratified.py ... \
  --file mragent_no_semantic_core500_qflash \
  --disabled_tools query_personal_information,query_personal_aspect \
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

上述是**实现级组件消融**，不能直接称为论文 Figure 5 的 CE/CTE/CTC 严格重现。论文的结构消融还要求改变 memory population 与直接索引策略；在本轮结论稳定后，才应单独实现该结构变体。

## 7. Badcase 归因与人工复核

每个完成的 MRAgent run 都必须生成：

```bash
python repro/attribute_badcases.py \
  --manifest data/subsets/locomo10_500q_core_seed42.json \
  --result_tag mragent_full_core500_qflash \
  --model deepseek \
  --output_prefix reports/mragent_full_core500_badcase_attribution
```

输出 CSV 和 Markdown。其中 primary causes 互斥，分母是 F1 小于阈值的坏例总数：

- `execution_error`：API/JSON/runner 在回答前失败。
- `retrieval_miss`：gold evidence 不在 `prediction_context`。
- `temporal_normalization_failure`：命中证据但回答仍保留相对日期。
- `evidence_utilization_failure`：命中证据却回答无信息。
- `adversarial_overanswer`：只用于 allcats 的 cat5。
- `likely_metric_or_format_mismatch`：答案包含关系正确但 token F1 不利，必须人工/LLM judge 复核。
- `answer_synthesis_or_semantic_error`：证据命中但仍答错，必须复核。

最终报告必须同时给出自动归因比例、CSV 中的原始输入输出、gold/predicted evidence、工具数、工具 trace 是否存在，以及人工复核后的最终比例。自动标签不能被写成最终语义事实。

## 8. 与论文其他 baseline 的比较

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

优先级是 native RAG -> A-Mem -> Mem0 -> MemoryOS -> LangMem。前两者直接对应“被动文本检索”和“图结构但非 MRAgent 重建”的关键反事实；后三者用于补全论文主表，但不应为了数量而使用未记录版本或不同题集。

## 9. 提交要求

提交 manifest、代码、协议、汇总报告、badcase CSV/Markdown、小型结果 JSONL 与外部 baseline provenance。不要提交 raw cache、embedding、完整 raw API payload、完整 log 或 API key。

每次服务器推送前仍需更新：

```bash
python repro/update_server_directory_manifest.py \
  --root /data/nishome/cuiwenjia/MRAgent-Reproduction
```

并在反馈中给出 commit、manifest、每种方法的 completed/expected、QA/rewrite/embedding model、RUN_ID、日志路径、任何 timeout/parse error，以及是否满足本协议的停止条件。
