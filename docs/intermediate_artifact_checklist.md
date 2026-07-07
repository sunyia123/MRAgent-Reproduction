# MRAgent 中间产物检查清单

## 1. 使用场景

如果远端实验只提交了最终 `result/*.jsonl`、metrics 或 Markdown 报告，但缺少 rewrite、keyword、embedding、memory graph、tool trace 等中间证据，本清单必须先执行。

结论规则：

```text
缺少中间产物或中间产物审计摘要时，只能认定为“结果文件存在”，不能认定为“论文机制已复现”。
```

## 2. 必须检查的文件

每个实验至少需要能定位以下产物。大文件不一定提交 GitHub，但必须提交可审计摘要、远端绝对路径、文件大小和生成命令。

| 阶段 | 必查内容 | 可提交到 GitHub | 不建议提交 |
| --- | --- | --- | --- |
| 数据 | dataset 名称、sample id、question id、category、gold answer | 小型 manifest / CSV | 大型原始数据副本 |
| Rewrite | `data/locomo/rewrite_<model>/<sample>_rewrite.json` | 结构摘要、缺失字段统计 | 全量大缓存 |
| Keyword | `data/locomo/keyword_<model>/<sample>_keyword.json` | 结构摘要、关键词统计 | 全量大缓存 |
| Embedding | `data/locomo/embedding/.../<sample>_embedding.pkl` | 维度、数量、checksum、路径 | pkl 大文件 |
| Memory graph | node/edge/topic/persona 数量 | `memory_audit_*.json` | 运行时内存对象 dump |
| QA result | 每题 gold、prediction、category、evidence、prediction_context | `result/*.jsonl` | 无 |
| Tool trace | 每题工具调用、参数、返回 event id、最终 supports | 精简 log / trace JSON | 未清洗完整长日志 |
| Metrics | F1、LLM judge、per-category、runtime、tool calls | `metrics_summary_*.json` | 无 |
| Failure audit | error、traceback、失败 run 是否混入最终 log | Markdown 报告 | 无 |

## 3. 服务器检查命令

在实验目录执行：

```bash
git status --short --branch
git log --oneline --decorate -5
find data/locomo -maxdepth 4 -type f | sort
find result -maxdepth 4 -type f | sort
find log -maxdepth 4 -type f | sort
find reports -maxdepth 2 -type f | sort
```

检查某个 sample 的核心文件：

```bash
SAMPLE=conv-30
MODEL=deepseek
FILE=stratified

ls -lh data/locomo/rewrite_${MODEL}/${SAMPLE}_rewrite.json
ls -lh data/locomo/keyword_${MODEL}/${SAMPLE}_keyword.json
ls -lh data/locomo/embedding/*/${SAMPLE}_embedding.pkl
ls -lh result/locomo/${SAMPLE}_result_${MODEL}_${FILE}.jsonl
ls -lh result/locomo/metrics_summary_${MODEL}_${FILE}.json
ls -lh result/locomo/memory_audit_${MODEL}_${FILE}.json
ls -lh log/locomo/${SAMPLE}_${MODEL}_${FILE}.log
```

如果某个文件缺失，报告必须说明：

1. 是否确实没有生成。
2. 是否生成在其他路径。
3. 是否因为 `.gitignore` 没提交。
4. 是否可以通过命令复现。
5. 远端绝对路径、文件大小和 checksum。

## 4. Rewrite 检查

必须确认：

- session 数等于该 conversation 的真实 session 数。
- `sessions_without_sentences` 必须为 0，除非原始数据本身为空，并在报告中逐条解释。
- `sentences_without_id/text/tag/origin` 必须为 0。
- conversation time 覆盖范围必须合理。
- 不能存在静默 `null` session。

建议命令：

```bash
python eval/memory_audit.py --data locomo --model deepseek --sample 30 --file stratified
```

最低验收：

```text
sessions_without_sentences = 0
sentences_without_id = 0
sentences_without_text = 0
sentences_without_tag = 0
```

如果 rewrite 有 null session，必须先修复并重跑，不允许继续扩大实验。

## 5. Keyword 检查

必须确认：

- keyword 里的 sentence 数与 rewrite 可用 sentence 数一致或差异有解释。
- `sentences_without_keywords` 应接近 0；如果不是 0，必须列出 sentence id。
- unique keywords、keyword instances、keywords per sentence 要写入 audit。
- schema retry 和 forced accept 要记录。

最低验收：

```text
keyword_total_sentences == rewrite_total_sentences
sentences_without_keywords = 0
forced_accepts_total = 0，或逐条解释
```

## 6. Embedding 检查

Embedding pkl 不要求提交 GitHub，但必须提交摘要。

必须检查：

- embedding 文件存在。
- sentence embedding 数量与 sentence id 数量一致。
- question embedding 数量不少于本次选择题目的最大原始 index + 1。
- embedding 维度与模型一致。
- topic embedding 和 topic id 数量一致。

必须在报告或 manifest 中记录：

```json
{
  "embedding_path": "",
  "file_size_bytes": 0,
  "sha256": "",
  "sentence_embedding_count": 0,
  "sentence_id_count": 0,
  "question_embedding_count": 0,
  "topic_embedding_count": 0,
  "embedding_dim": 0
}
```

如果 question embedding 数量不足，会导致分层抽样按原始 index 取 embedding 时失败。这类问题必须先修复，不能用空 embedding 或错误 index 掩盖。

## 7. Memory Graph 检查

必须提交 `memory_audit_*.json`，至少包含：

```json
{
  "rewrite": {
    "total_sessions": 0,
    "total_sentences": 0,
    "sessions_without_sentences": 0
  },
  "keyword": {
    "total_sentences": 0,
    "total_keywords": 0,
    "sentences_without_keywords": 0
  },
  "graph": {
    "key_nodes": 0,
    "episode_events": 0,
    "links_estimated": 0,
    "topics": 0,
    "persona_events": 0
  }
}
```

审查重点：

- `episode_events` 是否明显小于原始对话规模。
- `topics/persona_events` 是否异常为 0。
- `key_nodes` 是否只是 keyword instances，而不是 unique nodes；报告必须写清定义。

## 8. QA Trace 检查

每题必须能追溯：

- 题目原始 index。
- category。
- gold answer。
- prediction。
- evidence labels。
- prediction_context。
- tool calls 数量。
- 最终 supports。
- failure type。

如果 `prediction_context` 为空但模型给出答案，必须标记为高风险。
如果模型大量输出 `no information available`，必须优先检查 memory construction，而不是直接扩大样本。

## 9. Metrics 检查

必须防止重复追加污染：

- `result_judge_*.jsonl` 每次评测前要删除旧文件，或使用 run id 去重。
- metrics summary 必须记录输入 result 文件列表。
- `errors=0` 只能表示最终 result 中没有 `ERROR` 行，不能表示日志中没有失败试跑。

必须检查日志：

```bash
grep -R "Traceback\\|ERROR\\|IndexError\\|ValueError\\|APITimeout" log/locomo/*.log
```

如果最终 log 混入失败试跑，必须重新生成干净日志，或在报告中明确分段说明哪些 run 失败、哪些 run 有效。

## 10. 缺失时处理规则

如果缺少任一关键中间产物或审计摘要：

1. 停止扩大实验。
2. 不合并到 `main`。
3. 不写“复现成功”。
4. 先补 `artifact_manifest_*.json`。
5. 能重跑则重跑；不能重跑则记录原因、远端路径、文件大小、checksum。

最低可合并条件：

```text
result JSONL + metrics summary + memory audit + artifact manifest + clean report 同时存在。
```

## 11. Git 推送与数据保留检查

每次远端推送前必须确认：

```bash
git status --short --branch
git log --oneline --decorate -5
git diff --name-status origin/main..HEAD
```

禁止把以下情况伪装成正常更新：

- force-push 覆盖已经汇报过的实验提交。
- 删除已有报告、metrics、manifest，却没有在新报告中说明原因。
- 只保留结论报告，删除能支撑结论的 result/log/audit。
- 重新 clone 或 `reset --hard` 后丢失服务器上唯一存在的中间缓存。

如果发生 force-push，必须在报告中写明：

```text
old_commit:
new_commit:
rewritten_branch:
removed_files:
preserved_remote_artifacts:
backup_tag:
reason:
```

正常 push 不会删除 GitHub 历史中的旧 commit，但 force-push 会让旧 commit 从分支历史中消失。服务器上被 `.gitignore` 忽略的 rewrite/keyword/embedding 缓存通常不会因为 push 本身消失；真正危险的是 `git reset --hard`、`git clean -fdx`、删除重 clone、或手动删除实验目录。

## 12. 模型诊断检查

如果要把失败归因于模型能力，必须先提交模型诊断证据。最低要求：

- 每个失败 session 的 raw prompt。
- 每个失败 session 的 raw API response。
- `content`、`reasoning_content`、`finish_reason`、usage tokens。
- JSON parse error 原文。
- schema validation error 原文。
- 是否触发或疑似触发 `max_tokens` 截断。
- 每次 retry 的 temperature、输出长度、错误类型。
- DeepSeek 在 `response_format=json_object` 下是否仍失败。
- DeepSeek 在 `max_tokens=16384/32768` 下是否仍失败。
- 同一批 session 用 Gemini-2.5-Flash 或 Claude-Sonnet-4.5 是否通过。
- 同一批 session 用 Qwen3-235B 是否通过。

没有这些证据时，只能写：

```text
当前模型/Provider/解析链路未通过结构化抽取诊断。
```

不能写：

```text
模型能力不行。
```

## 13. Artifact Manifest 模板

每轮实验必须提交一个小型 JSON manifest，例如：

```json
{
  "run_id": "20260701-stage-b-stratified-conv30",
  "branch": "exp/20260701-stage-b-eval-audit",
  "commit": "",
  "command": "",
  "dataset": "locomo",
  "sample_ids": ["conv-30"],
  "model": "deepseek-ai/DeepSeek-V4-Pro",
  "embedding_model": "Qwen/Qwen3-Embedding-4B",
  "judge_model": "",
  "artifacts": {
    "rewrite": {
      "path": "",
      "exists": true,
      "size_bytes": 0,
      "sha256": ""
    },
    "keyword": {
      "path": "",
      "exists": true,
      "size_bytes": 0,
      "sha256": ""
    },
    "embedding": {
      "path": "",
      "exists": true,
      "size_bytes": 0,
      "sha256": "",
      "committed": false
    },
    "result": {
      "path": "",
      "exists": true,
      "size_bytes": 0,
      "sha256": ""
    },
    "log": {
      "path": "",
      "exists": true,
      "size_bytes": 0,
      "sha256": ""
    },
    "metrics": {
      "path": "",
      "exists": true,
      "size_bytes": 0,
      "sha256": ""
    },
    "memory_audit": {
      "path": "",
      "exists": true,
      "size_bytes": 0,
      "sha256": ""
    }
  },
  "known_missing": [],
  "merge_status": "blocked|reviewable|approved"
}
```
