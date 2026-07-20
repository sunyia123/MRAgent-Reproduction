# MRAgent 当前实验交接文档

## 1. 基本信息

- 项目名称：MRAgent-Reproduction
- 交接日期：2026-07-20
- 交接人：本地 Codex
- 接手人：服务器 Claude Code
- 文档版本：v3.0
- 当前状态：进行中
- 代码分支：`codex/locomo-main500-interim-audit`
- 代码基线：以本交接文档所在 commit 为准

## 2. 一句话说明

- 当前只处理四件事：定向修复错误行并回填完整结果、统一运行 DeepSeek-V4-Flash Judge、补齐 Mem0/A-Mem、生成五方法主比较与 MRAgent badcase 报告。
- 不重跑已经完成的五组 200 题消融。
- 最先执行：拉取本分支，完成三组错误题定向重跑和完整结果回填。

## 3. 当前进度

### 3.1 已完成并验证

- LoCoMo-10 图缓存：10/10 conversation 完整。
- Full MRAgent：500/500，原结果有 5 个执行 ERROR。
- RAG：500/500。
- GraphRAG：500/500。
- 五组消融：每组 200/200。
- CTE active：原结果有 6 个执行 ERROR。
- CTC active：原结果有 7 个执行 ERROR；另有 18 题发生内容工具参数错误。
- Mem0：297/500，已完成 6 个 conversation。
- A-Mem：96/500，已完成 2 个 conversation。
- structured output、topic/person 参数、active context 记录代码已经修复并有本地测试。

### 3.2 本轮进行中

- 只重跑 Full 的 5 个 ERROR、CTE active 的 6 个 ERROR、CTC active 的 25 个错误题。
- 将重跑结果替换到原完整结果的副本中，形成修正版 500/200 题结果。
- 使用统一 DeepSeek-V4-Flash Judge 对五方法普通题进行完整判断。

### 3.3 本轮待完成

- Mem0 剩余 conversation：`conv-47,48,49,50`。
- A-Mem 剩余 conversation：`conv-41,42,43,44,47,48,49,50`。
- Full/RAG/GraphRAG/A-Mem/Mem0 的统一 Judge。
- 五方法主比较、置信区间、MRAgent 全量判错归因和中期报告。

## 4. 核心产物

### 4.1 代码

- 主运行入口：`run_stratified.py`
- 外部基线：`repro/external_baselines/run_mem0_adapter.py`
- 外部基线：`repro/external_baselines/run_amem_adapter.py`
- Judge：`eval/evaluate_reasoning.py`、`eval/judge.py`
- 定向清单生成：`repro/build_targeted_replay_manifests.py`
- 重跑前后检查：`repro/compare_targeted_replays.py`
- 错误行回填：`repro/merge_targeted_replay_results.py`
- Judge 验收：`repro/validate_judge_results.py`
- 五方法比较：`repro/compare_main_experiment.py`
- MRAgent 判错归因：`repro/audit_mragent_judged_errors.py`

### 4.2 数据与清单

- 主实验：`data/subsets/locomo10_500q_main_seed42.json`
- Full 错误题：`data/subsets/locomo_replay_mragent_main_errors_20260720.json`，5 题。
- CTE active 错误题：`data/subsets/locomo_replay_cte_active_errors_20260720.json`，6 题。
- CTC active 错误题：`data/subsets/locomo_replay_ctc_active_repairs_20260720.json`，25 题。

### 4.3 原始完整结果

- Full：`*_result_deepseek_mragent_500q_main.jsonl`
- RAG：`*_result_deepseek_rag_500q_main.jsonl`
- GraphRAG：`*_result_deepseek_graphrag_500q_main.jsonl`
- CTE active：`*_result_deepseek_ablation_200q_cte_active.jsonl`
- CTC active：`*_result_deepseek_ablation_200q_ctc_active.jsonl`

上述文件是修复前证据，不删除、不覆盖。

### 4.4 本轮最终结果 tag

- 修正版 Full：`mragent_500q_main_repaired_v2`
- 修正版 CTE active：`ablation_200q_cte_active_repaired_v2`
- 修正版 CTC active：`ablation_200q_ctc_active_repaired_v2`
- Mem0：继续使用 `mem0_500q_main`
- A-Mem：继续使用 `amem_500q_main`

## 5. 目录结构

```text
MRAgent-Reproduction/
├── agent/                         # MRAgent 检索与工具边界
├── eval/                          # F1 与 Judge
├── data/subsets/                  # 固定题目和定向修复清单
├── data/locomo/                   # 服务器缓存，不提交大文件
├── repro/                         # 重跑、合并、校验、比较脚本
├── result/locomo/                 # 逐题结果，允许提交
├── result/diagnostics/            # 脱敏错误/trace
├── reports/                       # 汇总、逐题审计和实验报告
├── log/                           # 完整运行日志，仅服务器保存
└── docs/handoff.md                # 当前唯一服务器执行交接
```

- 输入：`data/dataset_locomo.json`、`data/subsets/*.json`。
- 中间产物：`data/locomo/`、外部 baseline memory cache、embedding。
- 最终产物：`result/locomo/*.jsonl`、Judge JSONL、`reports/*.md/json/csv`。
- 归档：修复前结果和 Judge 备份；不得删除。

## 6. 数据说明

- 数据来源：LoCoMo 官方数据，仓库文件 `data/dataset_locomo.json`。
- 当前范围：10 个 conversation，固定 500 题；普通题 400，adversarial 题 100。
- 消融范围：固定 200 题，category 1/2 各 100。
- 格式：manifest 为 JSON；逐题结果和 Judge 为 JSONL。
- 可复现性：题目由固定 manifest 和 `question_index` 唯一确定。
- 定向重跑结果不能单独计算总体均值；它们只用于替换完整结果中的同一题。

## 7. 运行说明

### 7.1 同步和静态检查

命令：

```bash
git status --short --branch
git fetch origin
git switch codex/locomo-main500-interim-audit
git pull --ff-only origin codex/locomo-main500-interim-audit
python -m py_compile agent/structured.py agent/tools.py agent/agent.py eval/judge.py eval/evaluate_reasoning.py repro/merge_targeted_replay_results.py
```

预期效果：工作区位于交接分支，代码可以编译，不触发 API。

验证：反馈当前 commit、`git status` 和编译退出码。

失败处理：工作区有未提交结果时先停止，不执行 reset/clean；先把结果提交到独立实验分支。

### 7.2 定向重跑三组错误题

统一环境：沿用原实验的 V4-Flash QA、Qwen3-Embedding-4B、`ENABLE_THINKING=0` 和现有图缓存。不要重建图。

Full 5 题：

```bash
python run_stratified.py --data locomo --model deepseek --re_model v4flash --qa_model v4flash --memory_view ctc --retrieval_mode active --file repair_mragent_main_errors_v2 --subset_manifest data/subsets/locomo_replay_mragent_main_errors_20260720.json
```

CTE active 6 题：

```bash
python run_stratified.py --data locomo --model deepseek --re_model v4flash --qa_model v4flash --memory_view cte --retrieval_mode active --file repair_cte_active_errors_v2 --subset_manifest data/subsets/locomo_replay_cte_active_errors_20260720.json
```

CTC active 25 题：

```bash
python run_stratified.py --data locomo --model deepseek --re_model v4flash --qa_model v4flash --memory_view ctc --retrieval_mode active --file repair_ctc_active_repairs_v2 --subset_manifest data/subsets/locomo_replay_ctc_active_repairs_20260720.json
```

预期效果：分别得到 5、6、25 行；原始完整结果不变。

验证：每组检查题目键与 manifest 完全一致；执行 ERROR 为 0；CTC 内容工具参数错误为 0；每行包含三类 context id、tool trace 和 retry/schema 指标。

失败处理：任一题仍为 ERROR 时停止在该组，上传该题 prompt、raw response、retry、trace 和 traceback，不继续回填。

### 7.3 比较并回填完整结果

先分别运行前后检查：

```bash
python repro/compare_targeted_replays.py --manifest data/subsets/locomo_replay_mragent_main_errors_20260720.json --after_tag repair_mragent_main_errors_v2 --output_prefix reports/repair_compare_mragent_main_v2
python repro/compare_targeted_replays.py --manifest data/subsets/locomo_replay_cte_active_errors_20260720.json --after_tag repair_cte_active_errors_v2 --output_prefix reports/repair_compare_cte_active_v2
python repro/compare_targeted_replays.py --manifest data/subsets/locomo_replay_ctc_active_repairs_20260720.json --after_tag repair_ctc_active_repairs_v2 --output_prefix reports/repair_compare_ctc_active_v2
```

确认重跑行通过后再运行：

```bash
python repro/merge_targeted_replay_results.py --manifest data/subsets/locomo_replay_mragent_main_errors_20260720.json --replay_tag repair_mragent_main_errors_v2 --output_tag mragent_500q_main_repaired_v2 --report_prefix reports/repair_merge_mragent_main_v2

python repro/merge_targeted_replay_results.py --manifest data/subsets/locomo_replay_cte_active_errors_20260720.json --replay_tag repair_cte_active_errors_v2 --output_tag ablation_200q_cte_active_repaired_v2 --report_prefix reports/repair_merge_cte_active_v2

python repro/merge_targeted_replay_results.py --manifest data/subsets/locomo_replay_ctc_active_repairs_20260720.json --replay_tag repair_ctc_active_repairs_v2 --output_tag ablation_200q_ctc_active_repaired_v2 --report_prefix reports/repair_merge_ctc_active_v2
```

预期效果：生成完整修正版 500/200/200 题结果；只替换 5/6/25 行。

验证：合并报告必须显示 `source_rows == output_rows`、`replaced_rows` 正确、修复后执行 ERROR 为 0；输出 tag 与源 tag 不同。

随后用修正版 active tag 和未改动的 passive tag 重新计算 200 题消融：

```bash
python repro/compare_main_experiment.py --manifest data/subsets/locomo10_200q_ablation_seed42.json --methods 'CTE-active-v2=ablation_200q_cte_active_repaired_v2,CTE-passive=ablation_200q_cte_passive' --output_prefix reports/ablation_200q_cte_repaired_v2

python repro/compare_main_experiment.py --manifest data/subsets/locomo10_200q_ablation_seed42.json --methods 'CTC-active-v2=ablation_200q_ctc_active_repaired_v2,CTC-passive=ablation_200q_ctc_passive,CTE-active-v2=ablation_200q_cte_active_repaired_v2' --output_prefix reports/ablation_200q_ctc_repaired_v2
```

这两份报告才是修复后 200 题消融结果；临时 replay 结果不单独进入表格。

失败处理：禁止手工复制粘贴 JSONL。键不一致、输出已存在或行数变化时停止并反馈脚本输出。

### 7.4 统一 Judge

事实边界：

- 上游公开代码通过 OpenRouter 使用 `openai/gpt-4o-mini`。
- 当前仓库已有旧 Judge 文件只有 `llm_score/question/prediction/reference/category/sample`，没有模型和 prompt provenance。根据服务器运行者确认，旧三组 Judge 实际设置为 SiliconFlow `deepseek-ai/DeepSeek-V4-Flash`；但仅凭已提交 JSONL 无法独立复核该配置。
- 本轮继续使用 SiliconFlow 的 `deepseek-ai/DeepSeek-V4-Flash`，关闭 thinking，并由新版 runner 逐行记录 provenance。这属于公开复现的替代 Judge，不得描述为论文原始 Judge。

运行前环境：

```bash
export JUDGE_BASE_URL=https://api.siliconflow.cn/v1
export JUDGE_MODEL=deepseek-ai/DeepSeek-V4-Flash
export JUDGE_ENABLE_THINKING=0
export JUDGE_MAX_TOKENS=256
export JUDGE_CLIENT_MAX_RETRIES=0
export JUDGE_CALL_MAX_ATTEMPTS=2
```

API key 只写入服务器 `.env` 的 `JUDGE_API_KEY`，禁止出现在命令、日志或 Git。

先对修正版 Full、RAG、GraphRAG 使用同一批题做闸门：

```bash
for TAG in mragent_500q_main_repaired_v2 rag_500q_main graphrag_500q_main; do
  python eval/evaluate_reasoning.py --data locomo --model deepseek --file "$TAG" --allfile --judge_overwrite --judge_manifest data/subsets/locomo10_500q_main_seed42.json --judge_max_new 20
  python repro/validate_judge_results.py --manifest data/subsets/locomo10_500q_main_seed42.json --judge_path "result_judge_locomo_deepseek_${TAG}.jsonl" --expected_count 20 --expected_model deepseek-ai/DeepSeek-V4-Flash --expected_thinking false
done
```

三组都通过后从 20 条断点续跑至 400 条普通题：

```bash
for TAG in mragent_500q_main_repaired_v2 rag_500q_main graphrag_500q_main; do
  python eval/evaluate_reasoning.py --data locomo --model deepseek --file "$TAG" --allfile --judge_manifest data/subsets/locomo10_500q_main_seed42.json
  python repro/validate_judge_results.py --manifest data/subsets/locomo10_500q_main_seed42.json --judge_path "result_judge_locomo_deepseek_${TAG}.jsonl" --expected_count 400 --expected_model deepseek-ai/DeepSeek-V4-Flash --expected_thinking false
done
```

外部 baseline 达到 500/500 后，以相同 Judge 配置运行 A-Mem、Mem0 至各 400 条普通题。

```bash
for TAG in amem_500q_main mem0_500q_main; do
  python eval/evaluate_reasoning.py --data locomo --model deepseek --file "$TAG" --allfile --judge_overwrite --judge_manifest data/subsets/locomo10_500q_main_seed42.json --judge_max_new 20
  python repro/validate_judge_results.py --manifest data/subsets/locomo10_500q_main_seed42.json --judge_path "result_judge_locomo_deepseek_${TAG}.jsonl" --expected_count 20 --expected_model deepseek-ai/DeepSeek-V4-Flash --expected_thinking false
  python eval/evaluate_reasoning.py --data locomo --model deepseek --file "$TAG" --allfile --judge_manifest data/subsets/locomo10_500q_main_seed42.json
  python repro/validate_judge_results.py --manifest data/subsets/locomo10_500q_main_seed42.json --judge_path "result_judge_locomo_deepseek_${TAG}.jsonl" --expected_count 400 --expected_model deepseek-ai/DeepSeek-V4-Flash --expected_thinking false
done
```

预期效果：五个 Judge 文件各 400 行，模型、prompt version、thinking 和字段统一。

验证：validator 显示无重复键、无 manifest 外题目、`judge_model=deepseek-ai/DeepSeek-V4-Flash`、`thinking=false`；每行保留 prompt、raw response、attempt、finish reason 和 usage。

失败处理：不得把旧 Judge 行追加到新结果。闸门出现混合 provenance、JSON parse error 或缺字段时停止并上传 `judge_errors_*.jsonl`。

### 7.5 补齐 Mem0 和 A-Mem

Mem0：只运行 `conv-47,48,49,50`，继续使用 `mem0_500q_main`。

A-Mem：只运行 `conv-41,42,43,44,47,48,49,50`，继续使用 `amem_500q_main`。

两个 adapter 均使用 `data/subsets/locomo10_500q_main_seed42.json`、V4-Flash QA、Qwen3-Embedding-4B、thinking=false，并从 `data/locomo/external_cache/` 恢复。

```bash
export ENABLE_THINKING=0
export EMBED_MODEL=Qwen/Qwen3-Embedding-4B

python repro/external_baselines/run_mem0_adapter.py --external_repo external/mem0 --data locomo --sample_ids 47,48,49,50 --model deepseek --re_model v4flash --qa_model v4flash --file mem0_500q_main --retrieve_k 10 --subset_manifest data/subsets/locomo10_500q_main_seed42.json

python repro/external_baselines/run_amem_adapter.py --external_repo external/A-mem --data locomo --sample_ids 41,42,43,44,47,48,49,50 --model deepseek --re_model v4flash --qa_model v4flash --file amem_500q_main --retrieve_k 10 --max_context_memories 30 --subset_manifest data/subsets/locomo10_500q_main_seed42.json
```

预期效果：Mem0 和 A-Mem 各达到 500/500，无重复题。

验证：分别反馈每个 conversation 的结果行数、cache hit、memory build wall-clock、QA wall-clock、API 次数和 ERROR 数。

失败处理：cache provenance 与当前模型配置不一致时停止，不删除缓存；提交审计报告后等待确认。

### 7.6 五方法比较和 badcase

五方法固定为：修正版 Full MRAgent、RAG、GraphRAG、A-Mem、Mem0。Oracle 不进入主比较。

使用 `repro/compare_main_experiment.py` 输出 Markdown、JSON 和逐题 CSV；使用 `repro/audit_mragent_judged_errors.py` 审计修正版 Full 的所有 Judge=0、cat5 错误和执行错误。

```bash
python repro/compare_main_experiment.py --manifest data/subsets/locomo10_500q_main_seed42.json --methods 'FullMRAgent=mragent_500q_main_repaired_v2,RAG=rag_500q_main,GraphRAG=graphrag_500q_main,A-Mem=amem_500q_main,Mem0=mem0_500q_main' --output_prefix reports/comparison_500q_repaired_v2

python repro/audit_mragent_judged_errors.py --manifest data/subsets/locomo10_500q_main_seed42.json --result_glob 'result/locomo/*_result_deepseek_mragent_500q_main_repaired_v2.jsonl' --judge_glob 'result_judge_locomo_deepseek_mragent_500q_main_repaired_v2.jsonl' --trace_dir result/diagnostics/mragent_main500_traces --output_prefix reports/mragent_500q_repaired_v2_badcase_audit
```

预期效果：五方法均为 500 题，普通题 Judge 均为 400；报告包含配对差值和 conversation-clustered 95% CI。

验证：每个 MRAgent badcase 必须能关联 question、gold、prediction、初始上下文、工具轨迹、最终上下文、raw response、Judge 和人工结论。

失败处理：任何方法不是完整同题 500/400 时，不生成最终排名，只报告缺失项。

## 8. 结果说明

- 当前已验证：Full MRAgent 相对 RAG/GraphRAG 的 500 题 F1 主效果存在；active 在 CTE/CTC 两种视图中均优于 passive。
- 当前未闭环：统一语义 Judge、A-Mem/Mem0 全量、修复后的完整结果、全量 badcase 归因。
- 本轮修复行合并后，后续所有报告必须使用 `*_repaired_v2` 的 Full/CTE/CTC 结果，不得把临时 replay tag 当作独立实验方法。

## 9. 风险与坑

- `deepseek` 出现在结果文件名中只表示答案实验的模型短名，不证明 Judge 使用 DeepSeek。
- 旧 Judge 没有逐行 provenance，且使用旧 prompt，不能与新版 V4-Flash Judge 混合。
- V4-Flash 同时作为答案模型和 Judge 可能产生自评偏差；五方法必须使用同一 Judge，并在报告中标注该限制。
- 定向重跑是错误修复，不是新的小样本实验；不能用 5/6/25 题计算总体结论。
- 禁止覆盖修复前完整结果；合并器只允许生成新 output tag。
- 禁止重建已完整的 LoCoMo 图缓存。
- 禁止 force-push、`git reset --hard`、`git clean -fdx` 和提交 API key。
- 完整 raw API 日志留在服务器；Git 只提交脱敏逐题 trace、结果、Judge 和报告。

## 10. 下一步与查收清单

服务器按顺序完成后，Codex 将逐项查收：

- [ ] 三份 replay 行数为 5/6/25，键与 manifest 完全一致。
- [ ] 三份 repair compare 报告存在，错误归零。
- [ ] 修正版完整结果为 500/200/200，替换行数为 5/6/25。
- [ ] Full/RAG/GraphRAG Judge 20 题闸门通过。
- [ ] 五方法结果均为 500，Judge 均为 400。
- [ ] Mem0/A-Mem 构建和 QA 耗时分开记录。
- [ ] 五方法主比较和置信区间完成。
- [ ] MRAgent 全量 badcase 自动归因与人工复核完成。
- [ ] 服务器目录 manifest 更新。
- [ ] 实验分支、commit、日志/结果/报告路径完整反馈。

## 11. 推送交付

每次推送前运行服务器目录扫描脚本，提交代码、manifest、逐题结果、Judge、脱敏错误记录和报告。不要提交 cache、embedding、checkpoint、`.env` 或完整 raw API 日志。

反馈必须包含：分支、commit、每项 completed/expected、实际模型与 thinking、ERROR 数、Judge provenance、输出路径、任何偏离本交接文档的操作。

## 12. 更新日志

- 2026-07-20 v3.0：交接范围收窄到错误行回填、统一 Judge、外部 baseline 和最终审计；移除后续研究设想。
