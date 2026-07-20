# MRAgent-Reproduction Agent Rules

本文件约束后续 Codex 在本仓库中生成实验计划、修改代码、编写服务器交接和验收结果的方式。开始工作前同时阅读：

1. `.agents/codex_experience_review.md`
2. `README.md`
3. `docs/handoff.md`（仅代表当前服务器任务）
4. `.local/mragent_long_term_experiment_plan.md`（仅本地 Codex 和用户使用，不上传 GitHub）

当轮用户指令优先于本文件；发现冲突时必须指出，不能静默选择一种解释。

## 1. 研究目标优先

1. 每轮实验先写清楚要检验的核心命题、对照变量、成功标准和不能证明什么，再决定代码和样本量。
2. 当前复现的核心不是“把流程跑完”，而是判断论文的核心改进是否可靠。优先保证同模型、同题目、同时间信息、同缓存与可比预算下的公平比较。
3. 对原论文机制、仓库实现和我们的工程改造必须分栏说明。不得把修复、简化或新设计描述成论文原方法。
4. 对用户提出的方案保持批判性：同时说明可行性、前提、潜在泄漏、替代解释和可能的负结果，不迎合式下结论。

## 2. 计划生成

1. 重大新阶段开始前，先用少量启发式问题澄清：最想证明的命题、主要 baseline、关键消融、样本选择、预算、停止条件和期望产物。已有明确答案时直接复述并推进，不重复提问。
2. 计划必须从仓库当前真实状态出发。先检查最新分支、完整 commit、结果文件、行数、manifest、日志和 cache，再写“已完成/未完成”。远端人员的文字汇报只能作为线索，不能作为已验证事实。
3. 清楚区分三个规模：
   - 极小样本仅验证代码、模型路由、日志和结果格式是否贯通。
   - 中型样本用于发现稳定失败模式和估算成本。
   - 正式样本用于统计比较和论文结论。
4. `10 题 gate` 不能被描述为有统计意义的结果；一旦工程闸门通过，应及时进入 200/500 题等主实验，不得长期停留在低价值 smoke 或重复审计。
5. 审计的目标是解除阻塞和验证证据。已经定位并修复的问题应转入执行；不要以反复审计代替图构建、baseline、消融或主实验。
6. 每项任务写明输入、输出、预期效果、验收方法、失败处理和 checkpoint。Checkpoint 只用于真实阻塞、数据破坏风险或实验定义歧义。
7. 先估算 API 调用次数、token、时间和可恢复性。可用非思考/低成本模型完成的预处理，不默认使用昂贵推理模型。

## 3. 文档边界

1. `.local/mragent_long_term_experiment_plan.md` 保存全部历史、未来路线、暂停设想和关键路径；它只在本地维护，禁止提交。
2. `docs/handoff.md` 是服务器唯一当前任务源，只保留本阶段要执行和验收的内容。不要写入 Q-learning、CBR、LongMemEval 等本阶段未执行方向。
3. `reports/` 记录已经完成的实验、证据、限制和结论。不得把计划中的结果写成已经完成。
4. README 只说明项目入口、当前交接入口和稳定操作规范，不堆叠每轮临时命令。
5. 服务器话术采用 `Context / Request / Output Format / Constraints / Checkpoint`。它应要求 Claude 阅读哪些文档、使用哪些已提交代码、完成什么、反馈什么；避免重复抄写与 handoff 冲突的实验定义。
6. 不规定服务器 Python 绝对路径。命令必须符合 Linux shell，但环境选择由服务器实际状态决定。

## 4. 代码与实验执行

1. 原则上由本地 Codex 先实现代码、测试并推送；服务器 Claude 负责拉取、运行和必要的最小修复。服务器修改后必须推送独立分支和完整 commit 供复核。
2. 修改必须小而可验证。不要顺手重构，不覆盖服务器或用户已有结果，不用新 tag 冒充新实验组。
3. 修复 ERROR 时先用 manifest 定向重跑，再以新完整 tag 合并回原规模结果；保留原始文件、替换清单、源/目标哈希和每行修复来源。
4. 禁止 force-push 已汇报分支、直接覆盖完整结果、删除原始 cache、无备份截断临时文件或在 dirty worktree 强行 pull。
5. 每次运行必须支持断点续跑，并在每个最小可恢复单元后落盘。长 API 请求不能等全部会话完成后才写 cache。
6. 模型路由必须显式记录每一阶段实际模型、服务端点、thinking 开关、temperature、max_tokens、timeout 和 retry。不能根据命令行参数名推断实际生效模型。
7. Embedding、rewrite、keyword、QA、VLM 和 Judge 是不同阶段，分别验证。图像存在时先审计其是否进入 rewrite/图构建证据链；需要视觉信息时使用明确验证过的 VLM 工具，而不是让纯文本模型静默忽略。
8. 结构化输出在 API 边界验证根类型、字段、schema 和截断状态。`response_format=json_object` 不能代替类型检查；错误不得退化成无标记的普通答案。

## 5. 公平比较与消融

1. baseline 必须尽量共享题目 manifest、模型、prompt 信息、rewrite/embedding cache、时间信息和评估器。任何不共享项都要在报告中列为混杂变量。
2. 每个 baseline 和消融写清楚“唯一改变了什么”。缩写首次出现必须给出中文全称和实际数据流，不能只列 CE/CTE/CTC、active/passive 等标签。
3. 主表至少同时报告问题数、完成数、ERROR、F1、语义 Judge、证据命中、运行时间和调用成本；F1、Judge、Evidence Hit 不能互相替代。
4. Judge 模型、prompt 版本和原始响应必须留痕。回答模型与 Judge 相同时，报告自评偏差。旧 prompt 与新 prompt 的 Judge 结果不可静默混合。
5. 外部 baseline 很慢时先拆分 memory 构建和 QA 时间，确认 thinking、缓存复用和每题调用数，再估算扩到 500 题的成本。

## 6. 证据与 Badcase

1. 每题至少可追溯：原始问题、gold、prediction、gold evidence、实际检索内容、图节点/边或向量结果、工具调用序列、最终上下文和评分结果。
2. API 诊断保留 raw prompt、raw response、`content`、`reasoning_content`、`finish_reason`、usage、request id、每次 retry、temperature、max_tokens、timeout 和 parse/schema 原文。
3. 失败归因必须区分：传输超时、模型未响应、JSON 解析耗尽、根类型错误、schema 错误、输出截断、工具参数错误、检索遗漏、图构建遗漏、答案生成错误和评估误判。
4. “模型能力不足”“内容安全过滤”“搜索质量差”都只能在有对照证据后提出，不能用作默认解释。
5. Badcase 报告既要有自动分类占比，也要展示代表性完整过程。尤其保留语义正确但字符串/F1/Judge 判错的案例，避免把评估错误算成系统错误。
6. 报告中的示例必须来自实际结果文件。需要说明 30/100/200/500 题如何选择、覆盖哪些类别以及为什么该规模足以或不足以支持结论。

## 7. GitHub 验收

1. 开始检查时先 `git fetch`，记录远端分支和完整 commit；用文件内容、行数、哈希和 manifest 验证远端汇报。
2. 每轮交接结束后逐项核对 `docs/handoff.md`，输出“通过 / 不通过 / 缺证据”，不能只复述 Claude 的总结。
3. 若 Git 忽略规则导致必要的小型结果、trace manifest 或报告未上传，应精确修改 `.gitignore`；不要为此开放密钥、完整大日志、embedding 或 checkpoint。
4. 每次推送前维护服务器目录 manifest，至少列出关键 cache、result、report、trace 和 log 的路径、大小、样本覆盖与生成 commit。
5. 最终结论分成：仓库已证实、远端声称但未证实、合理推测、仍缺证据。数字必须能定位到具体文件。

## 8. 安全

1. SSH 密码、API key 和 `.env` 不进入代码、文档、命令参数、日志或 Git。聊天中暴露的密钥应视为需要轮换。
2. GitHub 只同步代码、文档、配置模板、manifest、必要 trace 和小型结果摘要；大 cache、embedding、checkpoint 和完整原始日志留在服务器并记录路径与校验信息。
