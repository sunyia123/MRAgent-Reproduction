# MRAgent Benchmark Reproduction Plan

本文档专门记录 MRAgent 论文 benchmark 复现要求。它和当前的 `explore50` 不同：`explore50` 是工程诊断；benchmark 复现必须对齐论文数据集、指标和 baseline。

## 1. 论文使用的 Benchmark

根据论文和当前仓库 README，MRAgent 主要在两个长对话记忆 benchmark 上评测：

| Benchmark | 任务含义 | 当前仓库状态 | 当前风险 |
| --- | --- | --- | --- |
| LoCoMo | 长期多轮对话记忆问答，含多跳、时间、单跳、开放域、对抗/未提及问题 | `data/dataset_locomo.json` 已跟踪 | 当前文件只有 10 个 conversation samples；论文描述的 LoCoMo 规模需要进一步核对 |
| LongMemEval | 长期交互记忆问答，含 multi-session、single-session、temporal 等类别 | `data/dataset_LM.json` 未就绪 | Git LFS 对象缺失，当前不能复现 |

当前本地 LoCoMo 统计：

| 项目 | 数量 |
| --- | ---: |
| conversation samples | 10 |
| total QA | 1986 |
| category 1 | 282 |
| category 2 | 321 |
| category 3 | 96 |
| category 4 | 841 |
| category 5 | 446 |
| non-adversarial QA | 1540 |

结论：当前可以做 LoCoMo-10 的公开可验收复现；不能直接声称完整 LoCoMo paper benchmark，除非确认论文是否也只使用这 10 个公开样本，或补齐论文使用的数据划分。

## 2. 论文 Baseline

论文对比的 baseline 至少包括：

| Baseline | 类型 | 当前仓库是否提供实现 | 复刻要求 |
| --- | --- | --- | --- |
| Standard RAG | 向量检索 baseline | 未看到独立 runner | 需要实现或确认原作者脚本 |
| A-Mem | 关联/演化记忆系统 | 未内置 | 需要使用外部仓库或重新实现可比接口 |
| MemoryOS | agent memory system | 未内置 | 需要使用外部仓库或重新实现可比接口 |
| LangMem | agent memory framework | 未内置 | 需要使用外部框架或重新实现可比接口 |
| Mem0 | memory platform / framework | 未内置 | 需要使用外部框架或重新实现可比接口 |
| MRAgent | 论文方法 | 已有主代码 | 当前只完成单样本 clean run |

严格判断：当前仓库主要提供 MRAgent 方法本身，不等于已经提供所有 baseline 的可运行复现脚本。若要做论文级 baseline，对每个 baseline 至少要做到：

1. 使用同一份 benchmark 数据。
2. 使用同一套问题和 gold answer。
3. 使用同一或明确记录差异的模型后端。
4. 使用同一评估脚本或等价指标。
5. 保存每题 prediction、trace 或 retrieval evidence。
6. 输出 per-category 和 overall 指标。

## 3. 指标复现要求

当前仓库评估脚本支持：

- F1：`eval/evaluation.py`
- LLM judge accuracy：`eval/evaluate_reasoning.py` + `eval/judge.py`
- per-category metrics
- tool calls、runtime、schema retries、forced accepts 等工程指标

benchmark 报告至少要包含：

| 指标 | LoCoMo | LongMemEval |
| --- | --- | --- |
| Overall F1 | required | required if paper reports it |
| Per-category F1 | required | required |
| LLM judge accuracy | required | required if comparable |
| Error count | required | required |
| Runtime | required | required |
| Retrieval/tool trace | required for audit | required for audit |

注意：如果 judge model 从论文配置变成 Qwen/DeepSeek，报告必须明确写为“公开可验收复现”，不能声称绝对数值与论文完全可比。

## 4. 当前进度定位

已完成：

- LoCoMo `conv-30` 单样本 clean run。
- 15 题 stratified QA。
- 图构建、keyword、embedding、QA、metrics、badcase 初步闭环。
- VLM 工具验收脚本已加入，但尚未在服务器完成真实 API 验收。
- Explore-50 runner 控制参数已加入。

未完成：

- LoCoMo-10 全量 MRAgent run。
- LoCoMo baseline 对比。
- LongMemEval 数据恢复。
- LongMemEval MRAgent run。
- LongMemEval baseline 对比。
- 论文 baseline 的 Standard RAG / A-Mem / MemoryOS / LangMem / Mem0 复刻。

## 5. Benchmark 复现阶段划分

### Stage B0：数据一致性审计

目标：确认我们手里的 benchmark 是否等于论文使用的 benchmark。

命令：

```bash
python - <<'PY'
import json
from collections import Counter
data=json.load(open('data/dataset_locomo.json',encoding='utf-8'))
cat=Counter()
for s in data:
    cat.update(q.get('category') for q in s.get('qa',[]))
print('samples', len(data))
print('sample_ids', [s.get('sample_id') for s in data])
print('questions', sum(len(s.get('qa',[])) for s in data))
print('categories', dict(sorted(cat.items(), key=lambda x: str(x[0]))))
PY
```

合格标准：

- 报告记录样本数、sample_id、问题数、类别分布。
- 如果与论文 benchmark 规模不一致，必须明确写入限制。

### Stage B1：MRAgent LoCoMo-10 全量

目标：先复刻当前仓库可用的 LoCoMo-10。

命令：

```bash
python run.py --data locomo --model deepseek --file locomo10_full
python eval/evaluate_reasoning.py --data locomo --model deepseek --file locomo10_full --allfile
```

合格标准：

- 10 个 sample 全部有 result JSONL。
- rewrite/keyword/embedding 缓存完整。
- metrics summary 存在。
- per-category 指标完整。
- 报告明确这是 LoCoMo-10，不是未经核对的 LoCoMo paper full。

### Stage B2：Standard RAG baseline

目标：实现最小可比 baseline。

设计：

1. 使用同一份 rewrite 事件作为文本库。
2. 使用同一 embedding 模型。
3. 对每个问题 top-k 检索事件。
4. 把 top-k 事件交给同一 QA 模型生成答案。
5. 用同一评估脚本计算 F1 和 judge。

这是最优先 baseline，因为它最容易实现，也最能证明 MRAgent 的图遍历相对普通检索是否有收益。

### Stage B3：外部记忆系统 baseline

目标：复刻论文中除 Standard RAG 之外的 baseline。

优先级：

1. A-Mem：和当前研究方向最相关。
2. Mem0 / LangMem：工程框架类 baseline。
3. MemoryOS：如果代码和环境可用再做。

要求：

- 每个 baseline 都必须产生同格式 prediction JSONL。
- 不能只引用论文数字作为我们的实验结果。
- 如果无法运行，只能列为“论文引用 baseline”，不能列为“本仓库复现实验”。

### Stage B4：LongMemEval

当前阻塞：`data/dataset_LM.json` 真实文件缺失。

恢复要求：

- 文件不是 Git LFS pointer。
- 文件大小、SHA256、来源记录在报告中。
- 能按 `--ca 0/1/2` 至少跑论文涉及类别。

推荐恢复路径：

1. 从 HuggingFace `xiaowu0162/longmemeval-cleaned` 下载 `longmemeval_s_cleaned.json` 到 `data/external/`。
2. 审计第一条样本的字段结构。
3. 若字段不匹配 MRAgent loader，则新增转换脚本 `repro/convert_longmemeval_to_mragent.py`。
4. 生成 `data/dataset_LM.json`。
5. 用 `data.get_data("LM", "data/dataset_LM.json")` 验证 loader 可读。
6. 先跑 `--max_samples 1` smoke，再跑 `--ca 0/1/2`。

下载与 schema 审计命令：

```bash
mkdir -p data/external
curl -L --fail \
  -o data/external/longmemeval_s_cleaned.json \
  https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_s_cleaned.json

ls -lh data/external/longmemeval_s_cleaned.json
sha256sum data/external/longmemeval_s_cleaned.json

python - <<'PY'
import json
from pathlib import Path
p = Path("data/external/longmemeval_s_cleaned.json")
data = json.loads(p.read_text(encoding="utf-8"))
print(type(data), len(data) if hasattr(data, "__len__") else "NA")
first = data[0] if isinstance(data, list) else next(iter(data.values()))
print(first.keys())
for k, v in first.items():
    print(k, type(v), (str(v)[:300]).replace("\n", " "))
PY
```

转换后的验收命令：

```bash
python - <<'PY'
from data.get_data import get_data
c, q, _, _ = get_data("LM", "data/dataset_LM.json")
print("samples", len(c))
print("questions", sum(len(v or []) for v in q.values()))
print("first_sample", next(iter(c)))
PY
```

注意：

- 不要把 downloaded raw dataset 直接重命名为 `data/dataset_LM.json` 后运行。
- 不要提交 `data/external/` 或 `data/dataset_LM.json`。
- 必须提交 schema audit report 和 conversion manifest。

命令：

```bash
python run.py --data LM --model deepseek --file lm_ca0 --ca 0 --lm_batch 1
python run.py --data LM --model deepseek --file lm_ca1 --ca 1 --lm_batch 1
python run.py --data LM --model deepseek --file lm_ca2 --ca 2 --lm_batch 1
python eval/evaluate_reasoning.py --data LM --model deepseek --file lm_ca0 --allfile
python eval/evaluate_reasoning.py --data LM --model deepseek --file lm_ca1 --allfile
python eval/evaluate_reasoning.py --data LM --model deepseek --file lm_ca2 --allfile
```

## 6. 对当前 Explore-50 的定位修正

`explore50_vlmready` 不是 benchmark 复现。它的作用是：

- 在全量 benchmark 前发现 API、token、runtime、tool trace、image-related badcase 问题。
- 为后续 VLM QA 和 CBR case bank 收集失败样本。
- 估计 LoCoMo-10 全量运行成本。

因此报告中必须写：

```text
Explore-50 is a diagnostic subset, not a benchmark reproduction.
```

## 7. 给服务器实验员的硬性要求

在任何 benchmark 报告中必须写清：

- benchmark 名称。
- 数据文件路径。
- 样本数。
- 问题数。
- 类别分布。
- baseline 名称。
- 模型配置。
- 运行命令。
- result 文件路径。
- evaluation 文件路径。
- 是否与论文 benchmark 数据规模一致。
- 若不一致，不能声称论文完整复现。
