# LoCoMo 500 题主实验与严格消融协议

更新时间：2026-07-15

## 1. 研究问题

本阶段只回答一个主命题：

> 在相同问答模型、相同题目、相同时间信息和可审计运行条件下，MRAgent 的多轮主动图搜索是否稳定优于被动向量检索与固定图扩展？

主命题拆成三项可证伪问题：

1. **主效果**：Full MRAgent 是否优于 native RAG、GraphRAG、A-Mem 和 Mem0。
2. **图层效果**：Cue-Episode（CE）、Cue-Tag-Episode（CTE）和 Cue-Tag-Content（CTC）逐层增加时，证据命中和回答正确率是否提高。
3. **主动搜索效果**：在同一个图视图上，多轮工具调用是否优于一次性读取。

Memento 的 CBR/soft-Q 路径学习不进入本轮主效果。必须先证明原始 MRAgent 的主动图搜索有效，再在固定基线上增加路径学习，避免同时改变记忆、检索和评估而无法归因。

## 2. 当前事实与解释边界

- 10 个 LoCoMo conversation 的 rewrite、keyword、Qwen3-Embedding-4B 和 MRAgent 图 cache 已构建完成。
- A-Mem 与 Mem0 已在 conv-26 的 10 题闸门完成 10/10；闸门只证明 adapter、模型路由、缓存、输出与 trace 可运行，不提供统计结论。
- 旧 100 题结果保留为 `pre-protocol diagnostic`。其模型路由、时间字段、工具预算和题类口径不完全一致，不能进入新主表。
- 当前只覆盖 LoCoMo-10，而论文完整设置使用更多 conversation 和不同模型。因此可验证机制趋势，不能把本地绝对分数写成论文 Table 1 的完全复现。

## 3. 固定题集

题集由 `repro/build_main_experiment_manifests.py` 从原始 `data/dataset_locomo.json` 确定性生成。

| Manifest | 题数 | 分布 | 用途 |
|---|---:|---|---|
| `data/subsets/locomo_conv26_10q_core_seed42.json` | 10 | cat1-4 | 新 runner/adapter 的接口闸门，不做统计 |
| `data/subsets/locomo10_500q_main_seed42.json` | 500 | cat1=102, cat2=101, cat3=96, cat4=101, cat5=100 | 五方法主实验 |
| `data/subsets/locomo10_200q_ablation_seed42.json` | 200 | cat1=100, cat2=100 | 图层与主动搜索消融 |

主实验的普通题共 400 道，类别尽可能均衡。cat3 在这 10 个 conversation 中只有 96 道，因此短缺的 4 道被确定性分配给其他普通类别。cat5 固定 100 道并单独报告，不与论文排除 adversarial 的主指标混算。

消融 200 题全部属于主实验 500 题，避免 Full MRAgent 为消融额外选择一批更有利的问题。

重新生成并验证：

```bash
python repro/build_main_experiment_manifests.py
```

预期输出必须严格为 `500: 102/101/96/101/100` 和 `200: 100/100`。生成后不得人工改题。

## 4. 公平条件

所有方法必须满足：

- QA：`deepseek-ai/DeepSeek-V4-Flash`，显式传 `--qa_model v4flash`。
- 记忆构建/抽取：V4-Flash；embedding：`Qwen/Qwen3-Embedding-4B`。
- `ENABLE_THINKING=0`，并在 raw request 中验证 `enable_thinking=false`。
- 同一题目必须保留相同 `sample_id + question_index`、原始 session date、speaker、已有图像 caption。
- 不允许从 gold answer 或 gold evidence 构造检索 query、记忆或 case。
- 每题保存 prediction、prediction_context、模型路由、token、耗时、错误、重试和完整 trace。
- MRAgent 上限为 8 轮、每轮 10 次工具调用、总计 80 次。
- 结果按题对齐；缺题和 ERROR 单列，不能从分母静默删除。

## 5. 五方法主实验

| 方法 | 固定设置 | 主要回答的问题 |
|---|---|---|
| Full MRAgent | CTC + 8 轮主动工具调用 | 完整主动图重建是否有效 |
| Native RAG | 原始 turn 上一次性向量 top-k，保留日期 | 主动图搜索是否优于被动向量检索 |
| GraphRAG | 固定 seed、hop 和上下文上限 | 自适应遍历是否优于预定义图扩展 |
| A-Mem | 官方图记忆演化 + 被动检索 adapter | MRAgent 是否优于另一种演化图记忆 |
| Mem0 | 官方事实压缩记忆 + 被动检索 adapter | 图重建是否优于紧凑事实记忆 |

Oracle 不进入主表。它只保留为历史答案生成诊断，因为直接读取 gold evidence，不是可部署 baseline。

### 5.1 两个 250 题检查点

- Batch A：`26,30,41,42,43`，固定共 250 题。
- Batch B：`44,47,48,49,50`，固定共 250 题。

每批完成后先验证行数、模型路由和错误，再继续下一批。每个 sample 独立结果文件，因此两批使用同一个 file tag 不会互相覆盖。

### 5.2 Full MRAgent

```bash
export ENABLE_THINKING=0 RAW_API_LOG=1 RAW_API_LOG_MAX_CHARS=0
export RUN_ID=main500_mragent_A_$(date +%Y%m%d_%H%M%S)
python run_stratified.py \
  --data locomo --sample_ids 26,30,41,42,43 \
  --model deepseek --re_model v4flash --qa_model v4flash \
  --file mragent_full_main500_qflash \
  --subset_manifest data/subsets/locomo10_500q_main_seed42.json \
  --memory_view ctc --retrieval_mode active \
  --max_rounds 8 --max_tool_calls_per_round 10 --max_tool_calls 80
```

Batch B 只替换 `RUN_ID` 和 `--sample_ids 44,47,48,49,50`。

### 5.3 Native RAG 与 GraphRAG

先为 10 个 sample 补齐 native raw-turn embedding cache：

```bash
python repro/build_native_rag_cache.py --sample_ids 26,30,41,42,43,44,47,48,49,50
```

按两个 batch 分别运行：

```bash
python repro/run_standard_rag_baseline.py \
  --data locomo --sample_ids 26,30,41,42,43 \
  --model deepseek --qa_model v4flash \
  --file rag_native_main500_qflash --source raw --top_k 20 \
  --subset_manifest data/subsets/locomo10_500q_main_seed42.json

python repro/run_graphrag_baseline.py \
  --data locomo --sample_ids 26,30,41,42,43 \
  --model deepseek --qa_model v4flash \
  --file graphrag_main500_qflash \
  --subset_manifest data/subsets/locomo10_500q_main_seed42.json \
  --seed_k 10 --hops 1 --max_context_sentences 30
```

随后对 Batch B 使用相同 tag 运行。

### 5.4 A-Mem 与 Mem0

两个 adapter 必须逐个运行，避免同时压 SiliconFlow API。它们按 turn 构建记忆，500 题增加的是 QA 数，不会为同一 conversation 重建已经完成的 cache。

```bash
python repro/external_baselines/run_amem_adapter.py \
  --external_repo external/A-mem \
  --data locomo --sample_ids 26,30,41,42,43 --model deepseek \
  --re_model v4flash --qa_model v4flash \
  --file amem_main500_qflash --retrieve_k 10 --max_context_memories 30 \
  --subset_manifest data/subsets/locomo10_500q_main_seed42.json

python repro/external_baselines/run_mem0_adapter.py \
  --external_repo external/mem0 \
  --data locomo --sample_ids 26,30,41,42,43 --model deepseek \
  --re_model v4flash --qa_model v4flash \
  --file mem0_main500_qflash --retrieve_k 10 \
  --subset_manifest data/subsets/locomo10_500q_main_seed42.json
```

conv-26 的 gate cache 可复用，但必须由 provenance 证明 namespace、模型与数据哈希一致。若不一致，应创建新 namespace，不能把不同设置混在一个 cache 中。

## 6. 严格消融

`--max_rounds 1` 仍包含一次 LLM 路由，不等于“无主动推理”。本仓库新增两个正交开关：

- `--memory_view ce|cte|ctc`：控制可见图层和工具。
- `--retrieval_mode passive|active`：一次性确定读取或多轮工具搜索。

运行五组 200 题消融：

| Tag | 图视图 | 检索 | 作用 |
|---|---|---|---|
| `ab200_ce_passive` | CE | 单次 | cue 直接到 episode 的最低结构 |
| `ab200_cte_passive` | CTE | 单次 | 检验 tag 层的增益 |
| `ab200_ctc_passive` | CTC | 单次 | 检验 topic/person content 层的增益 |
| `ab200_cte_active` | CTE | 多轮 | 在相同 CTE 上检验主动搜索 |
| `ab200_ctc_active` | CTC | 多轮 | 完整方法在同题子集上的结果 |

被动组仍执行一次问题 key 提取，但不会进入 agent tool loop。CTC 被动组会一次性展开命中的 topic/person content；结果 `_metrics` 记录 `memory_view`、`retrieval_mode` 和 `initial_context_units`，避免把少给上下文误称为主动搜索增益。

先在固定 10 题上运行五组接口闸门。确认每组 10/10、被动组 `tool_calls=0`、主动组有 trace、输出标记正确后，再把 manifest 换成 200 题。统一命令模板：

```bash
python run_stratified.py \
  --data locomo --sample_ids 26,30,41,42,43,44,47,48,49,50 \
  --model deepseek --re_model v4flash --qa_model v4flash \
  --file <tag> \
  --subset_manifest data/subsets/locomo10_200q_ablation_seed42.json \
  --memory_view <ce|cte|ctc> --retrieval_mode <passive|active> \
  --max_rounds 8 --max_tool_calls_per_round 10 --max_tool_calls 80
```

主要配对：

- CTE passive - CE passive：tag 层效果。
- CTC passive - CTE passive：content 层效果。
- CTE active - CTE passive：CTE 上主动搜索效果。
- CTC active - CTC passive：完整图上主动搜索效果。

## 7. 评估与统计

每种方法先运行官方评估入口，生成 F1 与 Judge：

```bash
python eval/evaluate_reasoning.py \
  --data locomo --model deepseek --file <tag> --allfile
```

主表使用：

- cat1-4：逐题 F1、LLM Judge、Evidence hit。
- cat5：`Not mentioned` accuracy，单列。
- 工程指标：completed/error、平均工具数、轮数、token、耗时、上下文条数。

五方法对比和 conversation-clustered bootstrap 95% CI：

```bash
python repro/compare_main_experiment.py \
  --manifest data/subsets/locomo10_500q_main_seed42.json \
  --methods 'FullMRAgent=mragent_full_main500_qflash,RAG=rag_native_main500_qflash,GraphRAG=graphrag_main500_qflash,A-Mem=amem_main500_qflash,Mem0=mem0_main500_qflash' \
  --output_prefix reports/locomo_main500_comparison_20260715
```

Full MRAgent 相对 baseline 的 95% CI 不跨 0，才称为当前 LoCoMo-10 上的稳定优势。还必须同时检查 Evidence hit：若答案分数提高但证据命中不提高，结论更可能来自回答模型差异或格式，而不是检索机制。

## 8. MRAgent 全量判错归因

归因范围不是“F1 低于阈值”，而是：

- cat1-4 中 LLM Judge 判错的全部题；
- cat5 判定错误的全部题；
- 任意类别的缺行、API、JSON、schema 或 runner ERROR。

```bash
python repro/audit_mragent_judged_errors.py \
  --manifest data/subsets/locomo10_500q_main_seed42.json \
  --result_glob 'result/locomo/*_result_deepseek_mragent_full_main500_qflash.jsonl' \
  --judge_glob 'result_judge_locomo_deepseek_mragent_full_main500_qflash.jsonl' \
  --trace_dir result/diagnostics/mragent_main500_traces \
  --output_prefix reports/mragent_main500_judged_errors
```

第一遍自动标签只是假设，`manual_review_needed=true` 必须逐题看原始输入输出。主因互斥：执行/schema、图构建缺失、初始 key、工具/路径、过早停止、命中未利用、时间推理、多跳组合、视觉缺失、答案综合、Judge 假阴性、gold/evidence 标注问题。secondary tags 可以多选。

每个错例必须能定位：原始 question/gold/prediction、gold/prediction evidence、图中证据是否存在、每步 tool call 和返回、最终 prompt/response、retry/error、日志路径。最终报告同时给出主因占全部错例比例、占 500 题比例、分类别比例和代表性案例。

## 9. 停止条件

出现以下任一情况时停止扩大实验并修复：

- manifest 行数、哈希或题目键不一致；
- QA/embedding/memory model 路由不一致或 thinking 被打开；
- 任一方法缺题、重复题或覆盖旧结果；
- passive 组出现 agent tool calls，或 active 组没有 trace；
- native RAG context 丢失 session date；
- raw request/response/retry 日志缺失；
- Judge 缺失却被当作正确，或低 F1 被自动当作语义错误。

## 10. 下一阶段：CBR 与 soft-Q

只有主实验与消融完成后才进入路径学习。下一阶段以独立模块读取“问题状态 + 图状态”，输出一个不含答案事实的检索策略 case；MRAgent 原始工具接口不改。具体设计见 `docs/mragent_cbr_qlearning_module_plan.md`。

## 11. 提交范围

提交代码、manifest、协议、provenance、指标摘要、逐题对比 CSV、badcase 包和服务器目录清单。不要提交 API key、raw cache、embedding、完整 checkpoint 和包含敏感请求的全量日志。全量日志留服务器，报告记录绝对路径、RUN_ID、大小和校验信息。
