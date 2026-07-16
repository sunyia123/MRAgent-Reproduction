# LoCoMo 500 题主实验服务器交接

更新时间：2026-07-15

## 0. 2026-07-16 中期状态

远端实验分支 `exp/20260716-gate10-500q-main-results` 已完成 Full MRAgent、RAG、GraphRAG 各 500/500，以及 CE/CTE/CTC 三组 passive 消融各 200/200。不要重跑这些已完成结果。

当前仍未完成：

- A-Mem：54/500；Mem0：145/500；
- CTE active：40/200；CTC active：60/200；
- 三个主方法的 Judge 文件均为 0 字节；
- 主实验逐题 CSV、非空 Judge 和全量判错归因；5 个执行 ERROR 已有摘要 trace，但仍缺 request-linked 原始 prompt/response/retry。

严格审计与已算出的中期指标见 `reports/locomo_main500_interim_audit_20260716.md`。后续从现有 checkpoint 续跑，不删除已有结果、不重建已完成 cache。新增逐题结果、Judge 和脱敏 trace 已由 `.gitignore` 精确放行；完整 raw API 日志和运行日志继续只保存在服务器。当前 trace 中名为 `raw_prompts/raw_responses` 的文件仍是日志摘要，不得把它们报告为完整原始调用。

## 1. 交接目标

服务器接收本分支代码后，完成：

1. 新增严格消融的 10 题接口验证。
2. 五方法 500 题主实验，分两个 250 题检查点。
3. 五组 200 题图层/主动搜索消融。
4. 统一 F1/Judge/证据命中与配对置信区间。
5. 对 Full MRAgent 的全部判错和执行失败做可追溯归因。

唯一实验协议是 `docs/locomo_500q_ablation_protocol.md`。本文件只描述执行顺序和每步交付物，不重新定义参数。

## 2. 接收代码

```bash
cd /data/nishome/cuiwenjia/MRAgent-Reproduction
git status --short --branch
git fetch origin
git switch codex/locomo-500q-ablation-v2
git pull --ff-only origin codex/locomo-500q-ablation-v2
```

预期：工作区位于该分支且无未说明修改。若有本地结果或代码改动，先提交到单独 `exp/...` 分支；不要 force-push、reset 或删除 cache。

## 3. 静态与数据验收

```bash
python -m py_compile \
  agent/ablation.py agent/agent.py common/config.py llm/controller.py run_stratified.py \
  repro/build_main_experiment_manifests.py \
  repro/audit_mragent_judged_errors.py \
  repro/compare_main_experiment.py
python repro/build_main_experiment_manifests.py
```

必须反馈：

- main manifest：500，类别 `102/101/96/101/100`；
- ablation manifest：200，类别 `100/100`；
- 200 题键是 500 题键的子集；
- 当前 commit、Python、模型路由和 cache 完整度。

任何数量不一致都停止，不运行 API。

## 4. 严格消融 10 题闸门

使用现有 `data/subsets/locomo_conv26_10q_core_seed42.json`，依次运行：

1. CE + passive
2. CTE + passive
3. CTC + passive
4. CTE + active
5. CTC + active

每组使用协议中的 `--memory_view` 和 `--retrieval_mode`，file tag 必须独立，不能覆盖旧 gate10。

预期：每组 10/10；passive 的 `tool_calls=0`；active 保存完整 tool trace；每行 `_metrics` 含 memory view、retrieval mode、initial context units。选择同一道题展示五组实际输入上下文和路径差异。

Checkpoint：任一组缺行、passive 调用了工具、active 无 trace，或 CTC passive 没有 content 展开时停止并反馈代码、日志和原始结果。

## 5. 500 题主实验

顺序固定：Full MRAgent、Native RAG、GraphRAG、A-Mem、Mem0。Oracle 不运行。

- Batch A：`26,30,41,42,43`，250 题。
- Batch B：`44,47,48,49,50`，250 题。

每种方法先跑 Batch A，完成下列检查后再跑 Batch B：

- completed=250、无重复键；
- V4-Flash QA、Qwen3-Embedding-4B、thinking=false；
- 时间字段仍在 context；
- ERROR、timeout、parse/schema retry 数量；
- RUN_ID、主日志、raw API 和 trace 路径。

Full MRAgent 优先完成，因为它决定核心机制是否值得继续。RAG/GraphRAG 使用已有或新建的 raw-turn embedding cache。A-Mem/Mem0 逐个运行并断点续跑，不并发压 API。

## 6. 200 题消融

在主实验 Full MRAgent 完成后，使用 `locomo10_200q_ablation_seed42.json` 运行五组严格消融。CTC active 可以复用主实验中同一 200 题的逐题结果做统计，但仍要验证其运行配置确实为完整 CTC active；若 tag 或配置不同，不得复制冒充。

输出必须包含每组 200 行、逐题对齐表，以及四个核心差值：tag 层、content 层、CTE 主动搜索、CTC 主动搜索。

## 7. 评估和归因

对五个主实验 tag 分别运行 `eval/evaluate_reasoning.py --allfile`。随后使用：

- `repro/compare_main_experiment.py`：生成五方法总表、逐题 CSV、conversation-clustered bootstrap 95% CI。
- `repro/audit_mragent_judged_errors.py`：纳入所有 Judge 错、cat5 错和执行失败。

自动归因后必须人工复核 `manual_review_needed=true`。每类至少给一个完整案例，包含 raw prompt、raw response、工具序列、返回节点、最终 context、retry/error 和图中 gold evidence 是否存在。

## 8. 每次推送前

```bash
python repro/update_server_directory_manifest.py \
  --root /data/nishome/cuiwenjia/MRAgent-Reproduction
git status --short
```

只提交代码、文档、manifest、provenance、指标摘要、逐题结果、逐题对比、Judge 文件和脱敏 badcase trace。raw cache、embedding、全量 raw API、checkpoint、完整运行日志和 API key 留在服务器。

允许直接提交的实验路径是：

- `result/locomo/*_result_*.jsonl`
- `result_judge_locomo_deepseek_*_500q_main.jsonl`
- `result_judge_locomo_deepseek_ablation_200q_*.jsonl`
- `result/diagnostics/mragent_main500_traces/`

不要对这些路径使用 `git add -f`；正常 `git status` 应能看到新增内容。若仍不可见，先运行 `git check-ignore -v <path>` 并反馈匹配规则，不要继续扩大 `.gitignore` 放行范围。

推送实验分支，不直接覆盖主分支：

```bash
git switch -c exp/$(date +%Y%m%d)-locomo-main500
git add <本轮允许提交的文件>
git commit -m "exp: add LoCoMo 500q validation results"
git push -u origin HEAD
```

## 9. 反馈格式

反馈必须包含：

1. branch、commit、manifest SHA256；
2. 每个方法 completed/expected/error；
3. 实际 QA/memory/embedding model 和 thinking 状态；
4. F1、Judge、cat5、Evidence hit、工具/耗时；
5. Full MRAgent 对四个 baseline 的配对差值与 95% CI；
6. 每个消融组的设置与结果；
7. MRAgent 错例主因数量、比例和人工复核进度；
8. RUN_ID、日志、trace、结果和报告路径；
9. 任何偏离协议的地方，不得用“已完成”掩盖。

## 10. 何时停下来询问

- 需要删除、覆盖或重建现有 cache；
- git 合并会覆盖未提交实验结果；
- 模型、embedding 或 thinking 路由不符合协议；
- 结果缺行、重复、无 trace 或 Judge 大量缺失；
- A-Mem/Mem0 cache provenance 与当前设置不一致；
- API 连续三次同类错误且 checkpoint 无法前进。
