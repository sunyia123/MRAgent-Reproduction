# MRAgent 第一轮复现审查报告 - 2026-07-01

## 1. 总体判断

当前 GitHub 仓库最新提交为 `85b3ef2`，提交信息为：

```text
Stage A: LoCoMo smoke test - DeepSeek-V4-Pro via SiliconFlow provider adaptation
```

严格判断：这轮工作是一次有效的工程 smoke test，但不是论文级复现。

它证明了三件事：

1. 官方 MRAgent 代码可以被最小改造为 OpenAI-compatible provider。
2. SiliconFlow / DeepSeek-V4-Pro 能跑通 LoCoMo 的单个样本、少量问题。
3. 日志中确实出现了图记忆排序、工具调用、上下文查询和最终回答。

它还没有证明三件事：

1. 没有证明论文表格中的 LoCoMo 整体指标可复现。
2. 没有证明 LongMemEval 可复现，因为 `data/dataset_LM.json` 仍缺失。
3. 没有证明 MRAgent 的核心优势来自主动图记忆重构，而不是样本过少、问题过易、人工选择或模型先验。

因此，当前状态应标记为：

```text
Stage A 通过：工程链路跑通。
Stage B 未完成：小规模可评测复现。
Stage C 未开始：论文级 LoCoMo 复现。
Stage D 阻塞：LongMemEval 数据不可用。
```

## 2. 本轮实际做了什么

### 2.1 代码改造

本轮改造了以下模块：

- `common/config.py`：增加 `LLM_BASE_URL`、`EMBED_BASE_URL`、`deepseek` 模型短名和 `--max_questions`。
- `llm/controller.py`：将 chat client 改为动态 base URL，timeout 从 120s 改为 600s，并补 `max_tokens=4096`。
- `llm/embeddings.py`：embedding provider 改成可通过环境变量配置。
- `run.py`：增加 `--max_questions`，用于 smoke test 限制问题数量。
- `agent/agent.py`、`data/embed_rewrite.py`、`memory/system.py`：增加若干 `None` 保护，避免 LLM 输出结构不完整时崩溃。

这些改动总体方向合理，但还不是完整 provider 抽象。尤其是 evaluation judge 仍然硬编码 OpenRouter 和 `openai/gpt-4o-mini`。

### 2.2 实验命令

报告记录的命令是：

```bash
.venv/bin/python run.py --data locomo --model deepseek --file smoke \
    --sample 30 --max_questions 3
```

这意味着只跑了：

- 数据集：LoCoMo
- 样本：`conv-30`
- 问题数：前 3 题
- 模型：DeepSeek-V4-Pro
- 运行类型：smoke，不是完整评测

### 2.3 GitHub 中可验证产物

GitHub 当前包含：

- `reports/locomo_smoke_20260701.md`
- `log/locomo/conv-30_deepseek_smoke.log`
- `result/locomo/conv-30_result_deepseek_smoke.jsonl`

GitHub 当前不包含：

- `data/locomo/rewrite_deepseek/conv-30_rewrite.json`
- `data/locomo/keyword_deepseek/conv-30_keyword.json`
- `data/locomo/embedding/gpt_deepseek/conv-30_embedding.pkl`
- `log/run_locomo_deepseek_deepseek_smoke.log`

这意味着仓库可以验证最终答案和部分 trace，但不能完整复核 memory construction 的中间结构质量。

## 3. 当前结果

结果文件 `result/locomo/conv-30_result_deepseek_smoke.jsonl` 共 3 行：

| # | 问题 | 标准答案 | 预测 | 类别 | 严格判断 |
|---|---|---|---|---|---|
| 1 | When Jon has lost his job as a banker? | 19 January, 2023 | 19 January 2023 | temporal | 正确，格式差异 |
| 2 | When Gina has lost her job at Door Dash? | January, 2023 | January 2023 | temporal | 正确，格式差异 |
| 3 | How do Jon and Gina both like to destress? | by dancing | dance | single-hop | 语义正确，非 exact match |

人工判断可以认为 3/3 语义正确，但严格报告中只能说：

```text
2 个 exact/near-exact 正确，1 个语义正确但未经过 LLM judge。
```

当前没有正式评测输出：

- 没有 F1 汇总文件。
- 没有 LLM-judge 输出文件。
- 没有按 category 的指标。
- 没有和论文表格对齐的指标。

## 4. 严格问题清单

### 问题 1：样本量过小，不能支持论文复现结论

LoCoMo 当前数据规模为：

```text
10 个样本，共 1986 个问题。
```

本轮只跑了：

```text
1 个样本 conv-30 的前 3 个问题。
```

覆盖比例约为：

```text
3 / 1986 = 0.15%
```

这只能证明链路能跑，不能证明方法有效。

### 问题 2：`--max_questions 3` 只取前 3 题，存在顺序偏差

`run.py` 当前实现是：

```python
qa_list = qa_list[: config.MAX_QUESTIONS]
```

这不是随机抽样，也不是分层抽样。`conv-30` 的前 3 题正好是 2 个 temporal 和 1 个相对简单的 single-hop，没有覆盖：

- adversarial / not mentioned
- 多证据组合
- 更长跨度的问题
- 失败场景
- category 1 / 3 / 5

下一轮不能继续使用“前 N 题”作为实验依据。

### 问题 3：模型设置与论文不一致

本轮使用：

- Chat：`deepseek-ai/DeepSeek-V4-Pro`
- Embedding：`Qwen/Qwen3-Embedding-8B`

论文原始设置不是这个组合。该结果可以作为公开可复跑工程复现，但不能直接声称复现论文分数。

下一轮必须明确区分：

```text
论文设置复现：尽量靠近论文模型、prompt、judge。
工程替代复现：使用 SiliconFlow / DeepSeek，只验证机制与趋势。
```

### 问题 4：评测脚本没有真正跑通

报告建议运行：

```bash
python eval/evaluate_reasoning.py --data locomo --model deepseek --file smoke --allfile
```

但 `eval/judge.py` 仍然硬编码：

```python
API_KEY = os.getenv("OPENROUTER_API_KEY")
client = OpenAI(api_key=API_KEY, base_url="https://openrouter.ai/api/v1")
model="openai/gpt-4o-mini"
```

这说明 evaluation provider 还没有同步到 SiliconFlow 配置。如果服务器只配置了 SiliconFlow key，LLM judge 很可能不能跑。

### 问题 5：报告存在至少一处事实不一致

报告写了：

```text
.env.example - Deleted File
```

但 Git diff 显示 `.env.example` 实际是被修改，不是删除。

这不是严重问题，但说明报告需要被审计，不能直接当作实验事实。

### 问题 6：memory construction 中间产物没有提交，难以审查质量

报告声称生成了 rewrite、keyword、embedding：

- rewrite：100 KB
- keyword：45 KB
- embedding：8.6 MB

但这些文件没有进入 GitHub。当前只能通过日志间接相信它们存在，不能检查：

- rewrite 是否丢信息；
- keyword 是否抽取错误；
- topic / personal memory 是否质量足够；
- embedding 是否维度、数量、字段对齐；
- graph memory 是否和论文设计一致。

如果下一步要判断“主动图记忆重构是否真的有效”，必须提交小型可审查摘要，而不是只提交最终答案。

### 问题 7：修复方式可能掩盖 LLM 输出错误

`agent/agent.py` 中 keyword extraction 最后一次失败后直接：

```python
flag = True
err = ""
```

这能避免崩溃，但风险是把格式不合格的 LLM 输出当作可用结果继续处理。下一轮必须记录：

- 每个 sample 的 schema validation 失败次数；
- 最后是否发生 forced accept；
- forced accept 是否影响 memory quality。

否则后续准确率下降时，很难定位是模型能力问题、prompt 问题还是 memory 构建污染。

## 5. 对远端实验人员工作的评价

这轮远端工作有价值，但只能打“工程通过”，不能打“复现通过”。

合格点：

1. 成功把代码跑起来。
2. 没有把 `.env` 或真实 API key 提交到仓库。
3. 日志里能看到工具调用，不是纯 LLM 直接回答。
4. 发现并修复了多个 upstream 对 `None` 处理不足的问题。
5. 结果、日志和报告都有提交，具备最低限度可审查性。

不合格点：

1. 直接推到 `main`，没有 PR 审查流程。
2. 只跑 3 个问题却在 checklist 中写出较强的成功表述。
3. 没有运行正式评测脚本。
4. 没有分层抽样，没有覆盖失败场景。
5. 没有提交 memory construction 的可审查摘要。
6. 没有把 evaluation judge 一并改造成 provider-configurable。
7. 没有对“是否符合论文设置”给出清晰边界。

## 6. 下一步计划

### Stage B1：修正评测和审计基础设施

目标：先让指标可信，再扩大样本。

必须完成：

1. 将 `eval/judge.py` 改成可配置：
   - `JUDGE_BASE_URL`
   - `JUDGE_API_KEY`
   - `JUDGE_MODEL`
2. 增加一个纯本地 F1-only 模式，避免 LLM judge 阻塞基础评测。
3. 每次 run 输出一个 machine-readable summary：
   - sample id
   - question count
   - category count
   - exact/F1/LLM-judge
   - tool call count
   - forced accept 次数
   - schema retry 次数
   - runtime
4. 生成小型 memory audit 文件：
   - 每个样本保留 rewrite / keyword 的结构摘要；
   - 不提交大 embedding pkl；
   - 记录 memory node 数、edge 数、topic 数、persona 数。

验收标准：

```text
同一个 3 题 smoke 能产生 result + log + metrics + memory audit 四类产物。
```

### Stage B2：分层小样本复现

目标：避免前 3 题偏差。

不要再使用 `qa_list[:N]` 作为实验依据。改为固定分层题集：

```text
每个 category 至少 3 题；
至少 15 题；
覆盖 temporal、single-hop、多证据、adversarial/not-mentioned。
```

建议样本：

```text
conv-30：保留，因为已有缓存和日志。
conv-26：作为第二个样本，检查不同人物和时间线。
conv-42 或 conv-48：作为长样本，检查规模扩大后的稳定性。
```

验收标准：

```text
至少 3 个 conversation；
至少 45 个问题；
每类 category 都有结果；
报告必须列出 badcase 和 goodcase 原始输入、预测、gold、证据路径、工具调用路径。
```

### Stage B3：论文机制验证，而不是只看准确率

目标：证明 MRAgent 的主动图记忆重构机制真的被使用。

需要增加 ablation：

1. Full MRAgent：当前图记忆 + 工具调用。
2. No traversal：只给初始 top-k 证据，不允许多轮工具调用。
3. No semantic/persona：关闭 semantic/persona memory，只用 episodic events。
4. Direct LLM：把问题和有限检索结果直接给模型，不走图遍历。

验收标准：

```text
同一批 45 题，四组设置输出对比表。
至少 5 个 badcase 做逐题分析。
```

### Stage C：LoCoMo 全量公开复现

目标：接近论文表格，但明确模型差异。

前置条件：

- Stage B2/B3 完成；
- DeepSeek-V4-Pro 速度问题有替代策略；
- 评测脚本可信；
- 日志和结果目录规范稳定。

建议策略：

```text
优先使用更快模型跑全量机制验证；
保留 DeepSeek-V4-Pro 只跑代表性子集；
不要为了“看起来高级”用一个慢到不可复跑的模型拖垮实验。
```

验收标准：

```text
10 个 LoCoMo conversations；
1986 个问题；
按 category 输出 F1 / LLM-judge；
和论文 LoCoMo 表格逐项对齐；
明确模型、embedding、judge 与论文不同之处。
```

### Stage D：LongMemEval

当前仍阻塞。

要求：

1. 先解决真实 `data/dataset_LM.json` 来源。
2. 记录来源、大小、checksum。
3. 不允许用 LFS 指针或来历不明的替代文件冒充。

## 7. 给远端 Claude Code 的下一步指令

请直接复制以下内容给远端 Claude Code：

```text
请先阅读 reports/reproduction_audit_20260701.md。当前 85b3ef2 只算 Stage A 工程 smoke，不算论文复现。下一步不要继续扩大运行规模，先修评测与审计基础设施：

1. 将 eval/judge.py 改成 provider-configurable，支持 JUDGE_BASE_URL、JUDGE_API_KEY、JUDGE_MODEL，并保留 OpenRouter 默认值。
2. 给 eval/evaluate_reasoning.py 增加 --no_llm_judge 或 --f1_only 模式，先输出本地 F1，不依赖 judge API。
3. 增加每次运行的 metrics summary，至少包含 sample、question_count、category_count、F1、LLM judge、tool_call_count、schema_retry_count、forced_accept_count、runtime。
4. 增加 memory audit summary，不提交 embedding pkl，但提交每个样本的 node/edge/topic/persona 数量、rewrite/keyword 缺失字段统计。
5. 不要继续用 --max_questions 3 的前 3 题当实验结论。实现固定分层抽样配置，至少每类 category 3 题。
6. 完成后只跑 conv-30 的 15 题分层小样本，提交 result、log、metrics、memory audit、报告。不要跑全量。
7. 所有改动必须走新分支 exp/20260701-stage-b-eval-audit，不要直接推 main。
```

## 8. 当前结论

当前复现进度不应写成“第一轮复现成功”，应写成：

```text
完成第一轮工程 smoke：MRAgent 可在 SiliconFlow / DeepSeek-V4-Pro 上跑通 LoCoMo 单样本 3 问题，并产生可审查的工具调用日志。尚未完成论文级复现；当前主要缺口是样本规模、正式评测、分层抽样、memory construction 审计、LongMemEval 数据可用性，以及与论文模型设置的差异控制。
```
