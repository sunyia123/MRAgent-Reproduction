# 中型核心验证阶段交接文档

更新时间：2026-07-06

> 该文档保留 100q 历史执行背景。新的主实验请优先遵循 `docs/locomo_500q_ablation_protocol.md`；所有新命令必须显式传入 `--qa_model`。

## Context

当前小样本诊断已经完成：

- conv-30 的 15 题 MRAgent 小样本跑通。
- graph snapshot 已证明 conv-30 的 gold evidence coverage 是 75/75。
- single-hop 低分主要不是图构建缺失，而是 evaluation mismatch、图像证据缺失、tool path 漂移。
- 现在要进入中型核心验证阶段，目标是判断 MRAgent 的图结构检索是否真的比更简单的检索方法强。
- 但当前 10 个 sample 的对话级 cache 仍大量缺失，所以第一步不是继续评价，而是让所有 sample 的 rewrite / keyword / embedding / graph / result 产物可见、可审计、可续跑。

不要直接全量跑 LoCoMo-10 的 1986 题。当前阶段固定为：

```text
LoCoMo-10 / 100 questions / 同一题集 / 多方法对比
```

方法：

1. MRAgent 原图工具调用。
2. Standard RAG。
3. GraphRAG。
4. Oracle evidence QA。

## 当前阻塞与处理原则

2026-07-07 的中型验证启动时发现：

- conv-30 的 rewrite、keyword、embedding cache 完整。
- conv-26 只有 rewrite cache，缺 keyword 和 embedding。
- conv-42 有不完整 `.tmp` rewrite，不能当作完整 cache。
- conv-41、conv-43、conv-44、conv-47、conv-48、conv-49、conv-50 缺 rewrite、keyword、embedding。
- DeepSeek-V4-Pro 太慢；DeepSeek-V4-Flash 速度更好，但下午高峰仍可能 API 超时。

这不是模型能力问题，而是工程可恢复性问题：旧逻辑只有整批 session 全完成后才会把 rewrite cache 视为有效，中断后容易丢进度。

现在 `run_stratified.py` 已改为可恢复：

- 不删除已有 `.tmp`。
- rewrite 按已完成 session 数续跑。
- keyword 按已完成 jsonl 行数续跑。
- 如果 `.tmp` 最后一行损坏，会截断到最后一个完整有效记录。
- 完整校验通过后才把 `.tmp` 移动为正式 cache。

因此下一步不是继续手工清理目录，而是直接分批补 cache，并保留每批报告。

推荐模型策略：

- rewrite / keyword：优先使用 `deepseek-ai/DeepSeek-V4-Flash`。
- QA 对比：可以继续使用同一模型，保证方法间公平。
- 如果 Flash 在同一个 session 连续超时，停止该 batch，记录 session id、日志路径和 `.tmp` 已完成行数。

注意：2026-07-07 发现过一个模型路由问题：`--re_model` 设置了重写模型，但旧版 `agent.rewrite()` / `agent.extract_keys()` 没有显式传入 `config.RE_MODEL`，因此实际仍可能调用 `MODEL`。新版已修复，rewrite 和 keyword 都应使用 `RE_MODEL`。如果 api_call_log 中 rewrite/keyword 仍显示 V4-Pro，而你期望的是 V4-Flash，先停下来检查环境变量和命令行参数，不要继续跑。

2026-07-07 又发现一个运行命令风险：

```text
/data/nishome/cuiwenjia/MRAgent-Reproduction/.venv/bin/python3 run_stratified.py --sample_ids 26 --model deepseek
```

这条裸命令不能作为中型验证命令，因为它会带来以下风险：

- 没有 `--subset_manifest`，不会使用固定 100q manifest，而是退回本地随机分层抽样。
- 没有 `--file mragent_100q`，结果会写成 `*_result_deepseek_0.jsonl`，容易和正式结果混淆。
- 没有 `--re_model v4flash`，rewrite/keyword 会默认跟随 `MODEL`。
- 如果 `.env` 没有设置 `LLM_BASE_URL` 或 `DEEPSEEK_MODEL_ID`，旧代码可能退到错误 provider 或错误模型。

每次正式运行前必须先使用：

```text
repro/audit_runtime_config.py
```

确认以下字段：

- `MODEL`
- `RE_MODEL`
- `LLM_BASE_URL`
- `SAMPLE_IDS`
- `SUBSET_MANIFEST`
- `ADDITIONAL_RE`
- `result_template`
- `rewrite_template`

中型验证的最低完整参数应包含：

```text
--data locomo
--sample_ids 26
--model deepseek
--re_model v4flash
--file mragent_100q
--subset_manifest data/subsets/locomo10_100q_seed42.json
```

不要为了提速临时改变 prompt、抽样题集或评价脚本，否则 100 题对比会失去可解释性。

## Request

请完成中型核心验证实验的准备和第一轮运行。重点不是追求最大规模，而是保证所有方法在同一批 100 题上比较。

### 任务 0：每次推送前更新服务器目录清单

当前最主要的问题之一是服务器上 sample cache、graph snapshot、result、log 的位置不透明。每次服务器运行和推送前，必须先更新目录清单。

使用代码：

```text
repro/update_server_directory_manifest.py
```

扫描根目录固定为：

```text
/data/nishome/cuiwenjia/MRAgent-Reproduction
```

默认输出：

```text
reports/server_directory_manifest.md
reports/server_directory_manifest.jsonl
```

清单必须提交到 GitHub。它用于回答：

- 哪些 sample 已有 rewrite / keyword / embedding cache。
- 哪些 result JSONL 已经生成。
- graph snapshot 节点/边文件在哪里。
- 每次运行的 run log、sample log、API call log 在哪里。
- 是否存在脏 `.tmp`、`.bak_before_truncate_*`、skip marker 相关文件。

默认跳过 `.git`、`.venv`、`__pycache__` 等非实验产物目录；如果确实需要全量本地排查，可以临时加 `--include_venv`，但不要提交巨大的 venv manifest。

每次反馈必须包含：

- `reports/server_directory_manifest.md` 是否更新。
- `reports/server_directory_manifest.jsonl` 文件数。
- 当前 `data/locomo/rewrite_deepseek/`、`data/locomo/keyword_deepseek/`、`data/locomo/embedding/gpt_deepseek/`、`result/locomo/`、`result/graph_snapshot/`、`log/locomo/runs/` 的文件摘要。
- 新 commit hash。

### 任务 1：构建固定 100 题 subset manifest

使用代码：

```text
repro/build_stratified_subset.py
```

数据大约长这样：

- `data/dataset_locomo.json`
- 10 个 conversation samples。
- 1986 个 QA。
- 每个 QA 包含 question、answer、category、evidence。

要做什么：

- 生成固定 manifest。
- 每个 sample 抽 10 题。
- 总计 100 题。
- 尽量覆盖 cat1/cat2/cat3/cat4/cat5。

输出：

```text
data/subsets/locomo10_100q_seed42.json
```

这个 manifest 可以提交 GitHub，因为它是小型可复现实验配置。

### 任务 2：运行 MRAgent on 100q subset

使用代码：

```text
run_stratified.py
```

当前 `run_stratified.py` 已支持 `--subset_manifest`。它会读取 manifest 中的 `sample_id` 和 `question_index`，确保 MRAgent 与其他 baseline 使用同一批题。

输出：

```text
result/locomo/<sample>_result_deepseek_mragent_100q.jsonl
```

要点：

- 可以复用已有 rewrite/keyword/embedding cache。
- 如果某个 sample 缺 cache，使用可恢复逻辑分批补齐，不要删除 `.tmp`。
- 每个 sample 只跑 manifest 指定的 10 题。

分批推进顺序：

1. Batch 1：conv-26、conv-42。
   - conv-26 需要 keyword + embedding + MRAgent 10 题。
   - conv-42 需要从 `.tmp` rewrite 续跑或重建完整 rewrite，然后 keyword + embedding + MRAgent 10 题。
   - 输出 `reports/cache_batch1_conv26_conv42_20260707.md`。
2. Batch 2：conv-41、conv-43、conv-44。
   - 每个 sample 需要 rewrite + keyword + embedding + MRAgent 10 题。
   - 输出 `reports/cache_batch2_conv41_conv43_conv44_20260707.md`。
3. Batch 3：conv-47、conv-48、conv-49、conv-50。
   - 每个 sample 需要 rewrite + keyword + embedding + MRAgent 10 题。
   - 输出 `reports/cache_batch3_conv47_conv48_conv49_conv50_20260707.md`。

每个 batch 报告必须写清楚：

- 使用的模型 id。
- 每个 sample 的 rewrite session 完成数。
- keyword 行数是否等于 rewrite session 数。
- embedding 文件是否生成。
- MRAgent result JSONL 是否为 10 行。
- 是否存在 API timeout、retry、坏 JSON、schema error。
- 如果中断，`.tmp` 文件路径和已完成行数。

### 单个 session 连续超时的检查方法

如果某个 rewrite session 连续超时，不要先假设是“对话太长”。先用静态诊断脚本检查：

```text
repro/diagnose_rewrite_session.py
```

它不会调用模型 API，只读取原始 LoCoMo 数据和已有 `.tmp`。

需要检查：

- 该 session 的 turn 数、字符数、估算 prompt token。
- 它在同一个 sample 内是否真的是最长 session。
- 是否含有图片 caption、image url、特殊敏感主题或异常空字段。
- `.tmp` 已经保存了多少个完整 session。
- 是否最后一行损坏；如果损坏，新版 `run_stratified.py` 会截断到最后一个有效 JSONL 记录再续跑。

conv-26 session 9 的本地静态诊断结论：

- D9 只有 17 turns。
- session 文本约 2651 字符。
- rewrite prompt 约 4950 字符，估算约 1414 tokens。
- D9 不是 conv-26 最长 session；D14、D8、D3 等都更长。
- 因此“session 9 特别长导致超时”这个解释不成立。
- 更可能是供应商侧超时、内容安全审核、结构化 JSON 生成卡住，或当前时段服务不稳定。
- 但在确认 `RE_MODEL` 路由前，不能断言 V4-Flash 也失败；必须先用修复后的代码真实重试。

诊断坏 session 时可以临时缩短 API 等待时间：

```text
API_TIMEOUT_SECONDS=120
API_CLIENT_MAX_RETRIES=0
API_CALL_MAX_RETRIES=1
CHAT_TEXT_PARSE_MAX_ATTEMPTS=1
```

这组变量只用于定位问题。正式 batch 可以恢复默认值，或保留较短 timeout 以避免单个 session 阻塞全局。

跳过机制只允许作为最后手段：

- 不允许直接跳过 D9 并生成正式 cache。
- 如果 V4-Flash、Qwen 替代模型都失败，才允许生成一条人工审计报告，说明该 session 无法由当前 API 完成。
- 若临时跳过，只能进入 `diagnostic` 标记结果，不能进入正式 100q 对比。
- 正式实验必须保证 graph construction 没有人为缺口，否则后续 RAG/MRAgent/Oracle 对比都不可信。

2026-07-07 额外风险：

- `smart_retry_batch.py` 一类自动跳过脚本不允许用于正式实验。
- 该类脚本可能向 rewrite `.tmp` 写入 `conversation_time: skipped-api-timeout` 和空 `sentence: []`。
- 新版 `run_stratified.py` 会拒绝这种 skip marker，不再把它当作有效 rewrite cache。
- 如果服务器上已经产生过 skip marker，必须先用 `repro/audit_rewrite_cache.py` 审计，再只保留连续有效前缀。
- 新版 `run_stratified.py` 在截断 JSONL 前会自动写 `.bak_before_truncate_*` 备份；如果误截断，先找备份，不要直接重跑已完成 session。

审计命令使用的代码：

```text
repro/audit_rewrite_cache.py
```

需要报告：

- `.tmp` 总行数。
- `valid_prefix_count`。
- 是否有 `skip marker`。
- 是否有空 sentence list。
- 是否有 JSON parse error。
- 最后一个有效 session id。

如果 `.tmp` 已经从 8 行误截断成 1 行：

1. 先查找备份文件：

```text
data/locomo/rewrite_deepseek/conv-26_rewrite.json.tmp.bak_before_truncate_*
```

2. 对每个备份运行 `repro/audit_rewrite_cache.py`。
3. 选择 `valid_prefix_count` 最大、且无 skip marker 的备份恢复为 `.tmp`。
4. 如果没有可用备份，才从当前 `.tmp` 继续重跑。
5. 为避免 SDK 内部静默重试吞掉日志，诊断阶段必须设置：

```text
API_CLIENT_MAX_RETRIES=0
API_CALL_MAX_RETRIES=1
CHAT_TEXT_PARSE_MAX_ATTEMPTS=1
```

这样 timeout 会进入应用层日志，并带有 `stage=rewrite`。

### 任务 3：运行 Standard RAG on 100q subset

使用代码：

```text
repro/run_standard_rag_baseline.py
```

输入：

- subset manifest：`data/subsets/locomo10_100q_seed42.json`
- 每个 sample 的 rewrite cache。
- 每个 sample 的 embedding cache。

输出：

```text
result/locomo/<sample>_result_deepseek_rag_100q.jsonl
```

要点：

- 只跑 manifest 指定的 100 题。
- 不要跑全量 1986 题。
- 不重跑 rewrite、keyword、embedding。

### 任务 4：运行 GraphRAG on 100q subset

使用代码：

```text
repro/run_graphrag_baseline.py
```

GraphRAG 数据大约长这样：

- rewrite sentence 是图节点。
- keyword、topic、origin turn 是边或邻接关系。
- 先用 embedding 找 seed nodes。
- 再扩展 keyword/topic/origin 邻居。
- 将扩展子图转成 context，单轮 QA。

输出：

```text
result/locomo/<sample>_result_deepseek_graphrag_100q.jsonl
```

本轮默认：

- seed_k = 10
- hops = 1
- max_context_sentences = 30

### 任务 5：运行 Oracle evidence QA on 100q subset

使用代码：

```text
repro/run_oracle_evidence_qa.py
```

Oracle 数据大约长这样：

- 直接使用 QA 的 gold evidence id。
- 从 rewrite cache 中找到对应 sentence-level evidence。
- 把 gold evidence context 直接给模型回答。

目的：

- 判断模型拿到证据后能不能答对。
- 如果 Oracle 答对而 RAG/MRAgent 答错，问题在检索。
- 如果 Oracle 也错，问题在模型综合、rewrite 表达或评估。

输出：

```text
result/locomo/<sample>_result_deepseek_oracle_100q.jsonl
```

### 任务 6：生成对比报告

使用代码：

```text
repro/compare_rag_to_mragent_subset.py
repro/summarize_core_validation.py
```

当前它可以比较任意 baseline 与 MRAgent subset，只是参数名 `--rag_result` 保留了历史名称。

生成：

```text
reports/medium_core_validation_100q_YYYYMMDD.md
```

报告必须包含：

- subset manifest 路径。
- 每个方法实际完成题数。
- 每类题数量。
- overall / cat1 / cat2 / cat3 / cat4 / cat5 分数。
- evidence hit rate。
- Q9 类型 image/tool-path 案例在更大集合中是否普遍。
- 哪些错误是 retrieval，哪些是 synthesis，哪些是 metric mismatch。

当四种方法都跑完同一 manifest 后，使用 `repro/summarize_core_validation.py` 生成总表。它读取 manifest 和各方法 JSONL，输出每个方法的完成题数、overall/category score 和 evidence hit rate。

## Output Format

最终反馈：

1. 当前 commit hash。
2. subset manifest 是否生成，路径是什么，包含多少题。
3. 每个方法是否运行：
   - MRAgent 100q：完成/未完成/阻塞原因。
   - Standard RAG 100q：完成/未完成。
   - GraphRAG 100q：完成/未完成。
   - Oracle 100q：完成/未完成。
4. 每个方法输出路径。
5. 每个方法完成题数。
6. 是否有任何方法不是同一批题。
7. 初步指标。
8. 是否有任何 runner 未按 manifest 运行。
9. 新提交的报告路径和 commit hash。

## 运行日志要求

每次服务器运行都必须保留完整日志，不要只依赖终端输出。

当前代码会自动生成：

```text
log/<dataset>/runs/<RUN_ID>_<model>_<file>.log
log/<dataset>/<sample>_<model>_<file>_<RUN_ID>.log
result/diagnostics/api_call_log_<RUN_ID>.jsonl
result/diagnostics/api_call_log.jsonl
```

如果启用 embedding 诊断：

```text
DIAGNOSTIC_LOG=1
result/diagnostics/raw_embedding_calls_<RUN_ID>.jsonl
result/diagnostics/raw_embedding_calls.jsonl
```

每次反馈必须写明：

- `RUN_ID`
- run-level log 路径
- sample-level log 路径
- API call log 路径
- result JSONL 路径
- 当前停在哪个 stage：rewrite / keyword / embedding / store / qa
- 最后一个已完成 session 或 question

正式运行建议显式设置 `RUN_ID`，例如：

```text
RUN_ID=conv26_mragent_100q_20260707_01
```

这样所有日志和诊断文件会使用同一个可追踪前缀。

## Constraints

1. 不要全量跑 1986 题。
2. 允许补齐缺失 cache，但必须使用可恢复逻辑，禁止删除 `.tmp` 后从零开始。
3. 不要把不同题集的结果当作公平对比。
4. 不要提交大型 cache、embedding、rewrite、keyword、log。
5. result JSONL 如果较小可以提交；如果过大，写 manifest。
6. 如果 API 成本或时间明显超预期，先停下来反馈，不要继续扩大。
7. 不要临时改实验设计；需要代码改动时交给 Codex。

## Checkpoint

遇到以下情况必须停下来：

1. 同一个 session 连续超时，导致 batch 无法继续。
2. Standard RAG、GraphRAG、Oracle 使用的题集不一致。
3. MRAgent 无法保证与 manifest 同题。
4. GraphRAG 报错或输出空 context。
5. Oracle evidence 找不到 gold evidence。
6. 100 题运行时间超过预期。
7. 需要修改核心代码而不是实验脚本。
