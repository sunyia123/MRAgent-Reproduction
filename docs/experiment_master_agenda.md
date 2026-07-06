# MRAgent 总体实验纲领

更新时间：2026-07-06

## 1. 总目标

本项目不再把“完整复刻所有论文表格”作为当前唯一目标。当前主线是：

1. 快速复现 MRAgent 的关键机制。
2. 判断原论文核心改进是否可靠。
3. 找出图结构记忆系统在检索、重构、图生成、工具调用中的真实瓶颈。
4. 设计可插拔的 CBR/Q-learning 模块，用于改进图结构记忆的生成、检索、更新和剪枝。
5. 所有结论必须有 GitHub 可追踪的代码、报告、badcase 过程证据。

当前优先级不是追求一次性大规模全量跑完，而是小批量、可复查、可修复、可迭代。

## 2. 快速迭代原则

### 2.1 发现问题后直接修复

如果出现以下问题，不继续扩大实验：

- rewrite 出现 `null` session；
- keyword 与 rewrite 句子数不对齐；
- embedding 缺 question 或 sentence；
- QA 结果大量 `no information available`；
- 单类指标异常低；
- VLM 图片无法访问；
- evaluation 或 judge 与人工判断明显不一致。

处理方式：

1. 先冻结当前小样本结果。
2. 导出 badcase 过程包。
3. 定位是数据、模型、prompt、parser、图构建、检索、工具调用还是评估问题。
4. 直接做最小代码/配置修复。
5. 在同一小样本上复跑验证。
6. 修复有效后再扩大样本。

### 2.2 控制昂贵模型使用

DeepSeek-V4-Pro 推理模式很慢，不应该所有阶段都默认使用。

建议分层：

| 阶段 | 默认策略 | 原因 |
| --- | --- | --- |
| rewrite | 先用稳定便宜模型或低思考配置；失败样本再用 V4-Pro | rewrite 量最大，最耗时 |
| keyword | 优先用便宜模型或规则辅助 | keyword 不需要强推理 |
| embedding | 固定 embedding 模型 | 保持可比性 |
| QA/tool-calling | 小样本用 V4-Pro，扩展实验可对比 Qwen | QA 是核心推理阶段 |
| judge | 先用自动 F1 + 少量人工/LLM judge | judge 不应成为主要成本 |
| diagnostics | 优先便宜模型 | 目标是定位问题 |

需要记录：

- 每个阶段实际模型。
- 是否开启 reasoning。
- `max_tokens`。
- temperature。
- prompt hash 或 prompt 路径。
- 运行时间。

如果某个实验不是验证模型能力，而是验证工程链路，应优先用快模型。

## 3. 当前已知结论

### 3.1 conv-30 小样本端到端已跑通

已验证：

- rewrite、keyword、embedding、图构建、tool-calling QA、evaluation、artifact audit 能完整跑通。
- `max_tokens=4096` 导致 rewrite NULL 的问题已定位为截断问题。
- `max_tokens=16384` 后 conv-30 无 NULL session。

局限：

- 只有 1 个 conversation sample。
- 只有 15 个 QA。
- 不能代表 LoCoMo-10 或论文完整结果。

### 3.2 temporal 表现最好

conv-30 中 cat2 temporal F1 最高，说明当前时间工具和时间提示至少在小样本上有效。

### 3.3 multi-hop 与 single-hop 都需要复查

multi-hop 低分符合预期，因为需要跨证据综合。

single-hop 低分不符合直觉，需要优先诊断。当前可能原因：

1. 指标问题：F1 对 paraphrase 很敏感，judge 对部分 single-hop 判断为正确。
2. 图检索问题：单跳答案可能在图中，但没有进入 `prediction_context`。
3. 工具路径问题：模型调用过多工具，反而错过直接证据。
4. rewrite 问题：原始句子被改写后丢失关键实体或视觉信息。
5. image-related single-hop 问题：问题看似 single-hop，但答案依赖图片。
6. 回答策略问题：模型在证据不足时过早输出 `no information available`。
7. gold answer 表达过短，模型回答较长，导致 token F1 偏低。

因此 single-hop 低分不能直接解释为图结构无效，必须逐题看 badcase。

### 3.4 VLM 链路可运行但图片访问不稳定

VLM-enriched rewrite smoke 已证明：

- VLM evidence collection -> session enrichment -> text rewrite 可以跑通。
- 输出隔离到 `data/locomo/rewrite_deepseek_vlm/`，没有覆盖 baseline。
- 部分 Flickr 图片可访问。
- 多数 Wikimedia/custom/geograph 图片不能被 SiliconFlow 下载。

结论：

- 这是输入图片可访问性问题，不是 Qwen VLM 能力已经被否定。
- 在解决图片可访问性前，不能做大规模 VLM-QA 结论。

## 4. Benchmark 主线

### 4.1 必做基线

| 基线 | 目的 | 当前状态 |
| --- | --- | --- |
| MRAgent 原始图记忆 | 原论文核心系统 | conv-30 小样本通过 |
| Standard RAG | 检验图结构是否优于扁平向量检索 | 脚本已实现，指标未完成 |
| GraphRAG | 检验 MRAgent 是否优于常规图 RAG | 需要新增 |
| No-graph / flat rewrite QA | 检验图结构是否必要 | 待实现 |
| Oracle evidence QA | 判断上限：给定 gold evidence 时模型能否答对 | 待实现 |

GraphRAG 必须加入，因为当前研究问题本质是“图结构记忆是否真的比普通检索强”。仅与 Standard RAG 对比不够。

### 4.2 GraphRAG baseline 设计

最低可行版本：

1. 使用 MRAgent 已生成的 rewrite sentence 作为节点。
2. 使用 tag/topic/persona/origin 构边。
3. 问题向量先召回 top-k 节点。
4. 从 top-k 节点做 1-hop/2-hop 邻居扩展。
5. 将扩展子图压缩为 context。
6. 单轮 QA。

对比对象：

- Standard RAG top-k sentence。
- MRAgent tool-calling graph traversal。
- GraphRAG 1-hop。
- GraphRAG 2-hop。

需要记录：

- 初始召回节点。
- 扩展节点。
- 边类型。
- 最终 context。
- gold evidence 是否命中。
- QA 正误。

## 5. Badcase 记录规范

所有关键实验都必须生成 badcase process pack。

新增脚本：

```bash
python repro/export_badcase_pack.py \
  --data locomo \
  --model deepseek \
  --file stratified \
  --sample 30 \
  --output reports/badcase_pack_conv30_stratified_YYYYMMDD.md
```

badcase 报告必须至少包含：

- 原始 question。
- gold answer。
- prediction。
- category。
- token F1。
- gold evidence ids。
- prediction_context ids。
- tool_calls。
- runtime。
- 初步 failure type。

人工复查时继续补充：

- gold evidence 对应原始对话片段。
- rewrite 句子。
- keyword 记录。
- tool-call 完整路径。
- 是否命中 gold evidence。
- 失败原因：检索缺失、图遍历错误、rewrite 丢失、视觉信息缺失、时间计算错误、模型综合失败、评估不匹配。
- 下一步修复方案。

大型日志不提交 GitHub。提交 Markdown 摘要和 manifest，记录服务器绝对路径、文件大小、SHA256。

## 6. CBR/Q-learning 改造主线

### 6.1 研究假设

Memento 的 CBR/Q-learning 思路不应直接硬塞进 MRAgent 的最终回答阶段，而应做成可插拔模块，服务于图结构记忆系统的几个关键决策：

- 图生成前：生成 probe questions，预先探索对话中的典型检索需求。
- 图生成时：根据 probe 结果调整 rewrite/tag/topic/persona 的结构。
- 检索前：根据当前问题检索历史相似案例，选择检索策略。
- 检索中：决定工具调用顺序、扩展深度、是否调用 VLM。
- 检索后：根据成功/失败轨迹更新 case bank。
- 图维护时：剪枝低价值节点、合并重复节点、强化高价值边。

### 6.2 CBR 与 Q-learning 的关系

在本项目中：

- CBR 是案例记忆框架。
- Q-learning 是 CBR 内部可选的价值学习机制。

CBR 不一定需要 Q-learning。先做无学习的 case retrieval，再做 Q-learning value learner。

### 6.3 最小实验顺序

1. Case bank without learning：记录成功/失败轨迹。
2. CBR retrieval only：根据问题检索相似案例，给 tool-calling 提示。
3. CBR strategy selection：用案例选择检索策略。
4. Q-learning value：学习状态-动作价值。
5. Graph update：用案例和价值信号调整图边/节点。

每一步都必须与同一批 QA baseline 对比。

## 7. 下一轮实验顺序

### E1：single-hop badcase audit

目标：

- 解释 cat4 single-hop F1 为什么低。

命令：

```bash
python repro/export_badcase_pack.py \
  --data locomo \
  --model deepseek \
  --file stratified \
  --sample 30 \
  --output reports/badcase_pack_conv30_stratified_20260706.md
```

人工重点看 cat4：

- 是否 gold evidence 在 `prediction_context`。
- 是否回答语义正确但 F1 低。
- 是否图片相关。
- 是否工具调用过多导致漂移。

### E2：Standard RAG smoke

目标：

- 判断图工具链是否至少优于扁平向量检索。

范围：

- 先跑 conv-30 同一批 15 题。
- 再扩展 Explore-50。

### E3：GraphRAG baseline

目标：

- 增加图检索基线，避免只和 Standard RAG 对比。

最小版本：

- top-k embedding seed nodes。
- tag/topic/persona 1-hop 扩展。
- 单轮 QA。

### E4：Oracle evidence QA

目标：

- 判断错误来自检索还是回答。

做法：

- 直接把 gold evidence 对应 rewrite/context 给模型。
- 如果 oracle 仍答错，是模型综合或 rewrite 表达问题。
- 如果 oracle 答对而 MRAgent 答错，是检索/工具路径问题。

### E5：CBR probe case bank

目标：

- 在正式 QA 前，先用生成的 probe questions 探索图结构。
- 建立每个 conversation sample 的案例库。

输出：

```text
result/case_bank/*.jsonl
reports/cbr_probe_case_bank_*.md
```

## 8. GitHub 同步规则

Codex 本机负责：

1. 写代码。
2. 写文档。
3. 推送到 GitHub。

服务器 Claude Code 负责：

1. 拉取 GitHub 最新代码。
2. 运行实验。
3. 生成小型报告、指标摘要、manifest。
4. 推送到 GitHub 实验分支。

Codex 本机再负责：

1. 检查 GitHub 分支。
2. 严格判断报告是否可信。
3. 检查是否缺中间产物。
4. 根据 badcase 写下一轮代码。

不要只写“已完成”。每次实验必须留下：

- commit hash；
- 命令；
- 数据范围；
- 模型配置；
- 结果路径；
- 指标；
- badcase；
- 缺失项；
- 下一步修复。

