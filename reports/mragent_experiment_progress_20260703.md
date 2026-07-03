# MRAgent 复现与改造实验进度报告 - 2026-07-03

## 1. 当前仓库状态

本报告基于 2026-07-03 本地执行 `git fetch origin --prune` 后的 GitHub 可见状态。

| 分支 | 最新提交 | 状态 |
| --- | --- | --- |
| `origin/main` | `8d478e3 feat: add VLM-enriched rewrite smoke runner` | 主线已包含 VLM-rewrite 脚本与最新交接文档 |
| `origin/exp/20260701-stage-b-eval-audit` | `21f5a90 C8: Standard RAG baseline implementation + gitignore data/external/` | 服务器实验分支，包含 A1/A3/B4/C8 报告与脚本，但尚未合入 `main` |

需要注意：

- 服务器提到的 A1/A3/B4/C8 已经同步到实验分支，不在 `main`。
- `main` 上新增的 `repro/run_vlm_enriched_rewrite.py` 不在实验分支的末端提交中。后续服务器需要把 `origin/main` 合入当前实验分支，或新建干净分支继续。
- 当前没有看到 Explore-50 的完整结果进入 GitHub。若服务器仍在运行，该结果目前不能写入“已验证完成”。

## 2. 已完成并可引用的结果

### 2.1 单样本 conv-30 干净端到端复现

来源：

- `reports/stage_b_clean_conv30_20260702.md`
- `result/locomo/metrics_summary_deepseek_stratified.json`
- `result/locomo/memory_audit_deepseek_stratified.json`

实验范围：

- 数据：LoCoMo `conv-30`
- 问题数：15
- 类别：cat1=4, cat2=4, cat4=4, cat5=3
- 模型：DeepSeek-V4-Pro via SiliconFlow
- QA 实际使用 `max_tokens=16384`

主要结果：

| 指标 | 结果 |
| --- | --- |
| QA questions | 15 |
| errors | 0 |
| overall F1 | 0.5118 |
| cat1 multi-hop F1 | 0.2665 |
| cat2 temporal F1 | 0.7857 |
| cat4 single-hop F1 | 0.1170 |
| cat5 adversarial | 3/3 |
| LLM judge non-adversarial | 9/12 = 0.75 |
| tool calls per question | avg 9.47 |
| total runtime | 6661.78s QA runtime sum |

图构建质量：

| 项目 | 结果 |
| --- | --- |
| rewrite sessions | 19/19 |
| null sessions | 0 |
| rewritten sentences | 1094 |
| topics | 213 |
| personal events | 344 |
| unique tags | 465 |
| unique persons | 4 |
| keyword sentences | 1094 |
| keyword instances | 4408 |
| sentences without keywords | 9 |

结论：

- 当前工程链路已经能完整跑通：rewrite、keyword、embedding、graph construction、tool-calling QA、evaluation、artifact audit。
- `max_tokens=4096` 导致 rewrite NULL 的问题已经定位为输出截断；`16384` 后 conv-30 无 NULL session。
- temporal 类问题表现最好，multi-hop 和 image-related 问题是主要薄弱点。
- 这仍然只是单样本、小规模诊断，不是论文级完整复现。

### 2.2 LoCoMo 数据审计

来源：

- `origin/exp/20260701-stage-b-eval-audit:reports/benchmark_data_audit_20260702.md`

当前私有仓库中的 LoCoMo 数据：

| 项目 | 数量 |
| --- | --- |
| conversation samples | 10 |
| QA questions | 1986 |

类别分布：

| 类别 | 含义 | 数量 |
| --- | --- | --- |
| 1 | multi-hop | 282 |
| 2 | temporal | 321 |
| 3 | open-domain | 96 |
| 4 | single-hop | 841 |
| 5 | adversarial | 446 |

结论：

- 当前数据应称为 LoCoMo-10。
- 不能直接称为论文完整 LoCoMo，除非进一步核对论文使用的数据规模和官方划分。

### 2.3 LongMemEval 恢复

来源：

- `origin/exp/20260701-stage-b-eval-audit:reports/longmemeval_schema_audit_20260702.md`
- `origin/exp/20260701-stage-b-eval-audit:repro/convert_longmemeval_to_mragent.py`

已完成：

- 不再依赖损坏的 Git LFS 指针文件。
- 从 HuggingFace `xiaowu0162/longmemeval-cleaned` 获取真实 JSON。
- 下载文件大小：277,496,593 bytes。
- 原始数据：500 samples。
- 转换后 `data/dataset_LM.json`：500 samples, 500 questions。
- `data.get_data("LM", "data/dataset_LM.json")` loader 验证通过。

类别分布：

| LongMemEval 类别 | 数量 |
| --- | ---: |
| multi-session | 133 |
| single-session-user | 70 |
| temporal-reasoning | 133 |
| single-session-preference | 30 |
| knowledge-update | 78 |
| single-session-assistant | 56 |

结论：

- LongMemEval 的数据阻塞已经从“缺真实文件”推进到“转换器与 loader 已验证”。
- 还没有看到 LongMemEval smoke/full 实验结果进入 GitHub。
- `data/external/longmemeval_s_cleaned.json` 和 `data/dataset_LM.json` 都是大文件，不应提交，只提交转换脚本、校验和与报告。

### 2.4 VLM 工具验证

来源：

- `origin/exp/20260701-stage-b-eval-audit:reports/vlm_tool_validation_stage1_vlm_conv-30_20260702_112850.md`

实验：

- 模型：`Qwen/Qwen3.5-397B-A17B`
- 输入：conv-30 的 5 个 image turns
- 结果：0/5 成功
- 错误：SiliconFlow 返回 20040，提示 image URL must be a valid and downloadable URL。

结论：

- 当前失败不是 Qwen VLM 一定不能理解图像，而是 SiliconFlow 服务端无法下载这些外部图片 URL。
- VLM-QA 和 VLM-rewrite 的正式实验前，必须先解决图片可访问性。
- 可选路径：下载图片并转为可访问 URL、转 base64/data URL 如接口支持、建立临时对象存储、或先使用 `blip_caption` fallback。

### 2.5 标准 RAG baseline

来源：

- `origin/exp/20260701-stage-b-eval-audit:reports/standard_rag_baseline_20260702.md`
- `origin/exp/20260701-stage-b-eval-audit:repro/run_standard_rag_baseline.py`

已完成：

- 标准 RAG baseline 脚本实现。
- 设计为复用 MRAgent rewrite 句子和 embedding。
- 按 top-k embedding similarity 检索句子，再单轮 QA。
- 输出格式兼容 `eval/evaluate_reasoning.py`。

尚未完成：

- RAG smoke run pending。
- Explore-50 baseline pending。
- LoCoMo-10 baseline pending。

结论：

- baseline 代码已具备，但还没有可引用的 RAG 指标。

### 2.6 VLM-enriched rewrite 新增代码

来源：

- `origin/main:repro/run_vlm_enriched_rewrite.py`
- `origin/main:docs/claude_code_next_steps.md`
- `origin/main:docs/handoff.md`

新增目的：

- 在 MRAgent rewrite 阶段之前调用 VLM，为 image turns 注入视觉证据。
- 输出到独立缓存 `data/locomo/rewrite_deepseek_vlm/`。
- 不覆盖 baseline 缓存 `data/locomo/rewrite_deepseek/`。

已本地验证：

- `python -m py_compile repro/run_vlm_enriched_rewrite.py`
- `python repro/run_vlm_enriched_rewrite.py --help`
- dry-run 路径检查通过。

尚未完成：

- 服务器真实 VLM evidence collection。
- 服务器 full VLM-enriched rewrite smoke。
- 与 baseline rewrite 的人工对比。

## 3. 当前主要问题

### 3.1 分支未合并

实验分支有 A1/A3/B4/C8，`main` 有 VLM-rewrite 新代码。两边各自有新增内容。

建议：

- 不要在服务器长任务运行时强行切换或 reset。
- 当前任务结束后，在实验分支执行：

```bash
git fetch origin
git merge --no-edit origin/main
```

然后再运行 VLM-rewrite smoke。

### 3.2 Explore-50 尚未进入 GitHub

目前没有看到以下文件进入 GitHub：

```text
reports/explore50_vlmready_*.md
result/locomo/*explore50*.jsonl
result/locomo/*explore50*metrics*.json
```

因此：

- 不能把 Explore-50 写为已完成。
- 只能写为服务器正在运行或待同步。

### 3.3 图像链路仍未打通

现有 VLM 工具验证 0/5 成功，原因是远端图片 URL 不可下载。

后续必须先完成其中一种方案：

1. 将 LoCoMo 图片下载到服务器，再上传到 SiliconFlow 可访问的公开/内网对象存储。
2. 验证 SiliconFlow 是否支持 base64 image input。
3. 建立一个临时 HTTP 静态文件服务，并确认 SiliconFlow 服务端可访问。
4. 若短期无法解决，则将 VLM 实验标为 blocked，先用 `blip_caption` 做 fallback-only ablation。

### 3.4 benchmark baseline 还未形成指标

目前已有 MRAgent 单样本指标，但缺少：

- Standard RAG 指标。
- LoCoMo-10 MRAgent full 指标。
- LongMemEval smoke/full 指标。
- 外部 baseline，如 A-Mem、MemoryOS、LangMem、Mem0。

因此目前仍是工程复现与诊断阶段，不是完整 benchmark 复现阶段。

## 4. 下一步计划

### P0：同步分支并保护正在运行的实验

服务器当前任务完成后，先检查：

```bash
git status --short --branch
git log --oneline --decorate -5
git branch -vv
```

如果在实验分支：

```bash
git fetch origin
git merge --no-edit origin/main
```

如果在 `main`：

```bash
git pull --ff-only origin main
```

### P1：把 Explore-50 结果同步上来

需要提交小报告：

```text
reports/explore50_vlmready_YYYYMMDD.md
```

报告必须包含：

- 实际完成的 sample ids。
- 每个 sample 完成多少 QA。
- 是否复用了 rewrite/keyword/embedding cache。
- 总问题数、错误数、runtime、tool calls。
- per-category F1/judge。
- 至少 5 个 badcase，包含原始问题、gold、prediction、检索路径、失败原因。

### P2：运行 VLM-enriched rewrite smoke

在合并 `origin/main` 后执行：

```bash
python repro/run_vlm_enriched_rewrite.py \
  --data locomo \
  --model deepseek \
  --sample 30 \
  --file vlmrewrite_smoke \
  --limit_image_turns 10 \
  --max_sessions 3 \
  --dry_run
```

然后：

```bash
python repro/run_vlm_enriched_rewrite.py \
  --data locomo \
  --model deepseek \
  --sample 30 \
  --file vlmrewrite_smoke \
  --limit_image_turns 10 \
  --max_sessions 3
```

如果 VLM evidence collection 成功，再执行：

```bash
python repro/run_vlm_enriched_rewrite.py \
  --data locomo \
  --model deepseek \
  --sample 30 \
  --file vlmrewrite_smoke \
  --limit_image_turns 10 \
  --max_sessions 3 \
  --rewrite
```

### P3：RAG baseline smoke

前提：目标 sample 已有 rewrite 和 embedding cache。

```bash
python repro/run_standard_rag_baseline.py \
  --data locomo \
  --model deepseek \
  --file rag_smoke \
  --sample_ids 30 \
  --top_k 20
```

然后评估：

```bash
python eval/evaluate_reasoning.py \
  --data locomo \
  --model deepseek \
  --file rag_smoke \
  --allfile
```

### P4：LongMemEval smoke

前提：服务器上已生成真实 `data/dataset_LM.json`。

优先只跑小样本，不直接 full：

```bash
python run.py \
  --data LM \
  --model deepseek \
  --file lm_smoke \
  --ca 0 \
  --lm_batch 1 \
  --max_samples 3 \
  --max_questions 3
```

## 5. 当前可写入周报的判断

可以写：

- MRAgent 单样本端到端复现已经跑通，且中间产物完整可审计。
- token 截断是此前 rewrite NULL 的主要原因，不是 DeepSeek-V4-Pro 能力不足的直接证据。
- LoCoMo-10 数据规模已经审计完成。
- LongMemEval 的 Git LFS 阻塞已经通过 HuggingFace cleaned 数据与转换器缓解，loader 验证通过。
- VLM 工具验证暴露了图片 URL 可访问性问题，当前 VLM 不是模型能力失败，而是输入图片无法被 API 下载。
- 标准 RAG baseline 代码已经实现，但指标还没跑。
- VLM-enriched rewrite 代码已经进入 `main`，但服务器真实实验未完成。

不能写：

- 不能说已经完成论文完整复现。
- 不能说 Explore-50 已完成，除非服务器把报告和指标同步到 GitHub。
- 不能说 VLM 增强有效或无效，因为目前 VLM 输入链路未打通。
- 不能说 CBR/Q-learning 已经带来提升，目前还处于架构设计和后续实验规划阶段。

