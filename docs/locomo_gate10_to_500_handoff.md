# LoCoMo 10 题闸门到 500 题主实验交接

更新时间：2026-07-14

## Context

本阶段要验证的核心命题是：在相同 QA 模型、相同题目、相同时间信息、相同 embedding 和可比检索预算下，MRAgent 的主动图搜索是否显著优于被动向量检索。

旧 100 题实验已完成并保留，但由于模型路由、时间字段、题目类别和工具预算不一致，只能作为 `pre-protocol diagnostic`。新的结论必须来自固定 10 题闸门和固定 500 题主实验。

现有 10 个 conversation 的 MRAgent rewrite、keyword、embedding 和完整 CTC 图 cache 已构建完成。500 题主实验不重建这些图。A-Mem 与 Mem0 使用各自独立记忆结构，仍需为同一批 conversation 建立自己的 memory cache。

## 当前能力与缺口

| 内容 | 状态 | 说明 |
| --- | --- | --- |
| Full MRAgent runner | 已有 | 支持独立 QA/rewrite model、8 轮 x 10 tools、工具 trace |
| native RAG runner | 已有 | 原始 dialogue turn、日期、speaker、已有图像 caption |
| GraphRAG runner | 已有 | 固定 seed 与固定 hop 扩展 |
| Oracle runner | 已有 | 直接提供 gold evidence，诊断答案生成上界 |
| 固定 10 题 manifest | 已有 | `conv-26`，cat1/2/3/4=3/2/2/3 |
| 固定 500 题 manifest | 已有 | LoCoMo-10，cat1-4=125/130/91/154 |
| badcase 自动归因 | 已有 | 支持 F1、judge、人工语义复核三种证据 |
| A-Mem adapter | 已实现，待服务器 gate10 | 固定 A-Mem commit，逐 turn 演化 + Qwen embedding |
| Mem0 adapter | 已实现，待服务器 gate10 | 固定当前 OSS Mem0 commit；旧 benchmark 分支已删除 |
| 严格 CE memory view | 待 Codex 实现 | cue 直接索引 episode |
| 严格 no-reasoning CTC | 待 Codex 实现 | 一次性固定检索，不等于 `max_rounds=1` |

## Request

### 阶段 0：同步与运行前审计

读取：

- `README.md`
- `docs/locomo_500q_ablation_protocol.md`
- 本文档
- `data/subsets/locomo_conv26_10q_core_seed42.json`
- `data/subsets/locomo10_500q_core_seed42.json`

检查：

- 当前 commit 必须包含本次协议和 10 题 manifest。
- 10 个 MRAgent 图 cache 仍完整，不重新生成。
- `ENABLE_THINKING=0`。
- QA 统一使用 V4-Flash，embedding 统一使用 Qwen3-Embedding-4B。
- 每个 run 使用唯一 `RUN_ID`、file tag 和日志文件，禁止覆盖历史结果。

达成效果：运行配置可以从日志反查，且不会误用 V4-Pro、默认题集或旧结果 tag。

### 阶段 1：完成 A-Mem 与 Mem0 adapter

代码阶段已完成。服务器执行者只负责安装固定依赖、运行、验证和反馈，不自行发明新的数据转换或评测口径。规范命令见 README 的 `External baseline adapters`。

A-Mem adapter 以 `WujiangXu/A-mem@0c8039f...` 为源；Mem0 adapter 以 `mem0ai/mem0@ccbe586...` 为源。旧 `memory-benchmarks` 指向的 `feat/v3-pipeline` 已删除，所以 Mem0 只能声明为固定当前 OSS 实现的公开工程复现。每个 adapter 必须：

1. 记录官方仓库 URL、固定 commit、依赖版本和 license。
2. 读取本项目 manifest，只处理指定 `sample_id + question_index`。
3. 将 conversation 时间、speaker、text 和已有图像 caption 传给 memory ingestion。
4. 记忆抽取/更新使用 V4-Flash，embedding 使用 Qwen3-Embedding-4B，最终 QA 使用同一个 V4-Flash。
5. 保存每题 retrieved memories、prediction、token、runtime 和错误。
6. 输出统一 JSONL schema：`sample`、`question_index`、`category`、`question`、`answer`、`evidence`、`prediction`、`prediction_context`、`_metrics`。
7. memory cache 可复用但不提交 Git；provenance、结果摘要和小型 10 题结果提交 Git。

达成效果：A-Mem 与 Mem0 均能在固定 10 题上输出 10 行，并通过 `repro/validate_baseline_results.py`。

执行顺序固定为：先运行 `prepare_sources.py` 并安装 `requirements-external-baselines.txt`，再分别运行 A-Mem 和 Mem0 adapter。不要先重跑四个已有方法；外部 adapter 的 10/10、provenance、模型路由、时间字段和 trace 均通过后，再运行阶段 2 的其余方法并汇总六方法结果。

注意：`gate10` 只表示 QA 数量为 10。`conv-26` 实际有 419 个 dialogue turns，A-Mem 与 Mem0 都必须先完整摄取 419 条输入，不能为了缩短时间只建立与 10 道题相关的局部 memory。两种 adapter 都逐 turn checkpoint，发生 timeout 后应从 cache 恢复；二者应串行运行，避免同时压迫 SiliconFlow API。

### 阶段 2：运行固定 10 题全方法闸门

manifest：`data/subsets/locomo_conv26_10q_core_seed42.json`。

依次运行：

1. Full MRAgent。
2. native RAG，raw turn top-k=20。
3. GraphRAG，seed-k=10、1 hop、最多 30 句 context。
4. Oracle evidence QA。
5. A-Mem。
6. Mem0。

所有方法必须读取同一个 manifest 和同一个 QA model。10 题不是用来判断谁更强，而是检查：

- 是否完成 10/10。
- question index 是否逐题一致。
- temporal context 是否包含绝对日期。
- retrieved context 是否可见。
- raw prompt/response、工具轨迹和错误是否可追踪。
- A-Mem/Mem0 是否真正使用指定模型，而不是官方默认 OpenAI 配置。

达成效果：生成 `reports/gate10_protocol_validation.md`，并包含至少一个 Full MRAgent 好例和一个坏例。每个案例都展示问题、gold、逐步搜索轨迹、检索内容、预测，以及 RAG/A-Mem/Mem0 在同题上的检索差异。

### 阶段 3：进入固定 500 题主实验

manifest：`data/subsets/locomo10_500q_core_seed42.json`，只包含 cat1-4。

运行顺序：

1. Full MRAgent。
2. native RAG。
3. GraphRAG。
4. A-Mem。
5. Mem0。
6. Oracle，作为诊断上界。

每种方法先完成一次完整 500 题运行。首轮不追求三次重复，先确认主效应、错误率和资源消耗；主效应稳定后，再对 Full MRAgent、最强 baseline 和关键消融执行三次独立运行。

主报告必须给出：

- overall 与 cat1-4 的 F1、LLM Judge、Evidence Recall。
- Full MRAgent 相对每个 baseline 的绝对差值和相对差值。
- paired per-question win/tie/loss。
- completed、ERROR、timeout、parse failure。
- 平均/中位工具调用数、推理轮数、token、runtime、context 长度。
- bootstrap 95% confidence interval 或 paired permutation test；没有区间或显著性检验时，不使用“显著优于”措辞。

达成效果：可以回答主动图搜索是否超过被动向量检索，以及优势主要来自 multi-hop、temporal、open-domain 还是 single-hop。

### 阶段 4：图结构与主动搜索消融

论文原始消融包含两个轴：

- 图结构：CE 直接索引 episode、CTE 通过 tag 访问 episode、CTC 使用完整 episodic/semantic/topic 内容层。
- 搜索过程：一次性无 reasoning 检索与多轮主动重建。

当前可先运行：

- Full CTC + 8 轮主动搜索。
- CTC + 1 round，作为多轮搜索的近似消融。
- CTE runtime view：禁止 semantic 与 topic 工具，只保留 episodic Cue-Tag-Episode 路径。

严格 CE 与严格 no-reasoning 由 Codex 补齐实现后，先跑固定 10 题，再决定是否扩展到 500。不得把 `1round` 直接写成论文的 `without reasoning`，也不得把 runtime CTE view 写成重新构建的 CTE graph。

达成效果：分别回答“中间证据驱动的迭代扩展是否有用”和“tag/semantic/topic 等图结构是否有用”。

### 阶段 5：badcase 自动归因与人工复核

badcase 候选定义为 `lexical F1 < 0.8`、prediction=ERROR，或人工确认 Judge 误判。自动 primary cause 保持互斥：

- execution/API/schema failure
- retrieval miss
- temporal normalization failure
- evidence utilization failure
- answer synthesis/semantic failure
- no annotated evidence
- lexical F1 false negative
- LLM Judge false negative confirmed by human review

人工复核 CSV 至少包含：`sample_id`、`question_index`、`semantic_correct`、`note`。Judge 误判只能在人工记录存在时归入 `semantic_correct_judge_false_negative`。

达成效果：报告每类 badcase 的数量、占全部题目的比例、占 badcase 的比例和按 question category 的分布；每类至少展示一个完整案例。自动归因与人工修正前后的比例必须同时保留。

## Output Format

每次服务器反馈必须包含：

1. branch 与 commit hash。
2. RUN_ID、方法、manifest、completed/expected。
3. ingestion/rewrite、embedding、QA、judge 的实际模型。
4. 结果、日志、raw trace、cache、provenance 和报告路径。
5. 按类别的核心指标与 ERROR 数。
6. 至少一个逐步检索案例。
7. 是否达到当前阶段的达成效果。
8. 新 commit 与推送分支。

小型结果、摘要、badcase CSV/Markdown 和 provenance 提交 Git。完整 cache、embedding、大型 raw payload 和完整日志保留服务器，并通过目录 manifest 记录路径与大小。

## Constraints

- 不覆盖旧 100 题结果。
- 不将论文表格数值伪装成本地运行结果。
- 不混用 V4-Pro 与 V4-Flash 后进行公平比较。
- 不允许某个 baseline 丢弃时间字段或使用不同问题集合。
- 不提交 API key、`.env`、embedding cache 或大型 memory database。
- 不在 dirty worktree 中强制 pull，不使用 `git reset --hard` 或 force-push。
- 不因 10 题分数高低提前得出机制结论。

## Checkpoint

遇到以下任一情况立即停止扩大实验并反馈证据：

- A-Mem/Mem0 无法替换默认 LLM 或 embedding。
- 任一方法没有完成固定 10 题或 question index 不一致。
- temporal context 缺少绝对日期。
- output schema 无法通过统一校验。
- raw log 显示 thinking 被开启、模型路由错误或结果被覆盖。
- 500 题 ERROR 超过 5%，或同一错误连续出现 3 次。
- 工具轨迹、retrieved context 或 raw response 缺失，无法完成 badcase 归因。
