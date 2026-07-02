# Claude Code Full Experiment Instructions

This is the master server-side instruction sheet for MRAgent reproduction and extension.

Read order:

```bash
cat docs/handoff.md
cat docs/benchmark_reproduction_plan.md
cat docs/claude_code_full_experiment_instructions.md
```

Do not treat any diagnostic subset as paper-level benchmark reproduction.

## 0. Common Setup

If another server process is still running, do not update code in that same checkout until the process finishes. First inspect whether the server has local commits that are not visible on GitHub:

```bash
cd /data/nishome/cuiwenjia/MRAgent-Reproduction
git status --short --branch
git log --oneline --decorate -5
git branch -vv
git remote -v
```

If `git status` is dirty or `git branch -vv` shows local commits ahead of `origin/main`, commit/push those files first or create a separate clone for the next experiment. Do not run `git pull`, `git reset --hard`, or `git clean` in a checkout that is still producing results.

```bash
cd /data/nishome/cuiwenjia/MRAgent-Reproduction
git pull --ff-only origin main
git status --short --branch
conda activate mragent-repro
python -c "import openai, dotenv, numpy, torch; print('env ok')"
```

If imports fail:

```bash
pip install -r requirements.txt
```

Create `.env` manually:

```bash
cp .env.example .env
nano .env
```

Required:

```text
LLM_BASE_URL=https://api.siliconflow.cn/v1
OPENAI_API_KEY=<new key here>
DEEPSEEK_MODEL_ID=deepseek-ai/DeepSeek-V4-Pro
VLM_MODEL=Qwen/Qwen3.5-397B-A17B
VLM_MAX_TOKENS=1024
EMBED_MODEL=Qwen/Qwen3-Embedding-8B
```

Never commit `.env`, raw API keys, `result/`, `log/`, embedding `.pkl`, or large data files.

## 1. Immediate Experiments

These can run with current code after `.env` is configured.

### 1.1 VLM Tool Validation

Purpose:

- Verify Qwen VLM can read real LoCoMo image URLs.
- This does not modify MRAgent QA.

Dry run:

```bash
python repro/validate_vlm_tool.py \
  --data locomo \
  --sample 30 \
  --limit 5 \
  --file stage1_vlm \
  --dry_run
```

Real run:

```bash
python repro/validate_vlm_tool.py \
  --data locomo \
  --sample 30 \
  --limit 5 \
  --file stage1_vlm
```

Acceptance:

- At least 3/5 real image turns return non-empty visual evidence.
- JSONL exists under `result/diagnostics/`.
- Markdown report exists under `reports/`.
- Failures are explained as API, URL, empty response, or model issue.

Commit only:

- The Markdown report if small.
- A small manifest if raw JSONL is not committed.

### 1.1.5 VLM-Enriched Rewrite Smoke

Purpose:

- Test whether visual evidence can be injected before MRAgent's rewrite stage.
- Keep this separate from the baseline rewrite cache.
- This is a prerequisite for later image-aware QA, but it is not the final VLM-QA experiment.

Why this matters:

- The original rewrite code only uses existing text and `blip_caption`.
- It does not call a VLM during rewrite.
- For image-related LoCoMo questions, missing visual facts can already damage the graph before retrieval starts.

Dry run, no API calls:

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

Real VLM evidence collection, but no text rewrite call:

```bash
python repro/run_vlm_enriched_rewrite.py \
  --data locomo \
  --model deepseek \
  --sample 30 \
  --file vlmrewrite_smoke \
  --limit_image_turns 10 \
  --max_sessions 3
```

Full smoke: collect VLM evidence and run text rewrite:

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

Expected outputs:

```text
data/locomo/rewrite_deepseek_vlm/conv-30_rewrite.json
result/diagnostics/vlm_enriched_rewrite_visual_vlmrewrite_smoke_*.jsonl
result/diagnostics/vlm_enriched_rewrite_sessions_vlmrewrite_smoke_*.jsonl
reports/vlm_enriched_rewrite_vlmrewrite_smoke_*.md
```

Acceptance:

- The baseline `data/locomo/rewrite_deepseek/` cache is not overwritten.
- The report shows how many image turns were found, how many VLM calls succeeded, and where the enriched sessions were written.
- If image URLs are unreachable, the report must say so and the run should be treated as network/tool failure, not as proof that VLM is useless.
- If `--rewrite` is used, verify that `data/locomo/rewrite_deepseek_vlm/conv-30_rewrite.json` exists and has non-empty rewritten sessions.

Failure handling:

- If every VLM call fails, first check URL reachability and SiliconFlow VLM model support.
- If the full rewrite fails after VLM evidence collection, keep the visual JSONL/report and debug text rewrite separately.
- Do not delete or replace the baseline rewrite cache.

### 1.2 Explore-50 Diagnostic Subset

Purpose:

- Expand from 15 QA to 50 QA.
- Collect badcases before full benchmark runs.
- This is not benchmark reproduction.
- This does not yet inject VLM into MRAgent QA.

Run:

```bash
python run_stratified.py \
  --data locomo \
  --model deepseek \
  --file explore50_vlmready \
  --sample_ids 30,42,44,48,50 \
  --per_category 2 \
  --total 10 \
  --seed 42
```

Evaluate:

```bash
python eval/evaluate_reasoning.py \
  --data locomo \
  --model deepseek \
  --file explore50_vlmready \
  --allfile
```

Report:

```text
reports/explore50_vlmready_YYYYMMDD.md
```

Required report contents:

- Exact commit.
- Exact command.
- Exact sample ids.
- Per-sample question counts.
- Per-category counts.
- Completed answer count.
- Error count.
- F1 and judge results.
- Runtime and tool calls.
- Badcases: image-related, multi-hop, temporal, no-information despite evidence.
- Whether caches were reused or regenerated.

Do not claim:

- full paper reproduction,
- benchmark reproduction,
- VLM-enhanced QA,
- CBR/Q-learning effect.

## 2. Benchmark Reproduction Experiments

These are required for paper-level reproduction.

### 2.1 Data Consistency Audit

Run before benchmark claims:

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

Report:

```text
reports/benchmark_data_audit_YYYYMMDD.md
```

Must state:

- Current private repo has LoCoMo-10.
- It must not be called full paper LoCoMo unless paper data scale is verified.
- LongMemEval is unavailable until recovered.

### 2.2 LoCoMo-10 Full MRAgent

Run only after Explore-50 is stable:

```bash
python run.py \
  --data locomo \
  --model deepseek \
  --file locomo10_full
```

Evaluate:

```bash
python eval/evaluate_reasoning.py \
  --data locomo \
  --model deepseek \
  --file locomo10_full \
  --allfile
```

Report:

```text
reports/locomo10_full_mragent_YYYYMMDD.md
```

Acceptance:

- All 10 samples have result JSONL.
- Metrics summary exists.
- Per-category metrics are reported.
- Rewrite, keyword, embedding, memory audit, result, judge, and logs are auditable.
- The report explicitly says `LoCoMo-10`, not full paper LoCoMo unless proven.

### 2.3 LongMemEval Recovery

Do not use the broken Git LFS pointer. Download the cleaned official dataset and inspect schema first.

```bash
mkdir -p data/external
curl -L --fail \
  -o data/external/longmemeval_s_cleaned.json \
  https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_s_cleaned.json

ls -lh data/external/longmemeval_s_cleaned.json
head -c 200 data/external/longmemeval_s_cleaned.json
sha256sum data/external/longmemeval_s_cleaned.json
```

Schema audit:

```bash
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

Report:

```text
reports/longmemeval_schema_audit_YYYYMMDD.md
```

If schema does not match `data/get_data.py`, implement:

```text
repro/convert_longmemeval_to_mragent.py
```

Converter output:

```text
data/dataset_LM.json
```

Loader validation:

```bash
python - <<'PY'
from data.get_data import get_data
c, q, _, _ = get_data("LM", "data/dataset_LM.json")
print("samples", len(c))
print("questions", sum(len(v or []) for v in q.values()))
print("first_sample", next(iter(c)))
PY
```

Commit only:

- converter script,
- schema audit report,
- small manifest with URL, file size, SHA256, conversion command, output sample count, output question count.

Do not commit:

- `data/external/`,
- `data/dataset_LM.json`.

### 2.4 LongMemEval MRAgent Smoke And Full Runs

Only after loader validation passes.

Smoke:

```bash
python run.py \
  --data LM \
  --model deepseek \
  --file lm_smoke_ca0 \
  --ca 0 \
  --lm_batch 1 \
  --max_samples 1
```

Full category runs:

```bash
python run.py --data LM --model deepseek --file lm_ca0 --ca 0 --lm_batch 1
python run.py --data LM --model deepseek --file lm_ca1 --ca 1 --lm_batch 1
python run.py --data LM --model deepseek --file lm_ca2 --ca 2 --lm_batch 1
```

Evaluate:

```bash
python eval/evaluate_reasoning.py --data LM --model deepseek --file lm_ca0 --allfile
python eval/evaluate_reasoning.py --data LM --model deepseek --file lm_ca1 --allfile
python eval/evaluate_reasoning.py --data LM --model deepseek --file lm_ca2 --allfile
```

Reports:

```text
reports/longmemeval_ca0_mragent_YYYYMMDD.md
reports/longmemeval_ca1_mragent_YYYYMMDD.md
reports/longmemeval_ca2_mragent_YYYYMMDD.md
```

## 3. Baseline Experiments

These are required for benchmark comparison. Some are not implemented yet.

### 3.1 Standard RAG Baseline

Current status:

- Not implemented as a runner in this repo.
- This is the highest-priority baseline to implement.

Implementation task:

```text
Implement repro/run_standard_rag_baseline.py.
```

Minimum design:

1. Reuse MRAgent rewrite events as the text corpus.
2. Reuse the same embedding model and question embeddings.
3. Retrieve top-k events by embedding similarity.
4. Send top-k event texts plus question to the same QA model.
5. Write prediction JSONL in the same shape expected by `eval/evaluate_reasoning.py`.
6. Support `--data`, `--model`, `--file`, `--sample_ids`, `--top_k`, `--max_samples`.

After implementation, smoke:

```bash
python repro/run_standard_rag_baseline.py \
  --data locomo \
  --model deepseek \
  --file rag_smoke \
  --sample_ids 30 \
  --top_k 20
```

Explore-50 baseline:

```bash
python repro/run_standard_rag_baseline.py \
  --data locomo \
  --model deepseek \
  --file rag_explore50 \
  --sample_ids 30,42,44,48,50 \
  --top_k 20

python eval/evaluate_reasoning.py \
  --data locomo \
  --model deepseek \
  --file rag_explore50 \
  --allfile
```

Full LoCoMo-10 baseline:

```bash
python repro/run_standard_rag_baseline.py \
  --data locomo \
  --model deepseek \
  --file rag_locomo10 \
  --top_k 20

python eval/evaluate_reasoning.py \
  --data locomo \
  --model deepseek \
  --file rag_locomo10 \
  --allfile
```

Report:

```text
reports/standard_rag_baseline_YYYYMMDD.md
```

### 3.2 External Memory Baselines

Targets:

- A-Mem
- MemoryOS
- LangMem
- Mem0

Current status:

- Not implemented inside this repo.
- Do not claim reproduced results until each baseline produces local prediction JSONL.

For each baseline:

1. Inspect upstream repository or package.
2. Record commit/version.
3. Build a dataset adapter from MRAgent/LoCoMo sample to that baseline input.
4. Run the same question set.
5. Convert output to the same prediction JSONL schema.
6. Evaluate with the same script.
7. Report failure if the baseline cannot be run.

Required report pattern:

```text
reports/baseline_<name>_audit_YYYYMMDD.md
reports/baseline_<name>_results_YYYYMMDD.md
```

Do not use paper numbers as our reproduced results.

## 4. VLM-Enhanced QA Experiments

Current status:

- VLM validation script exists.
- VLM is not yet wired into MRAgent QA.

Implementation task after VLM tool passes:

1. Add a `query_visual_evidence` tool.
2. Map event id to original `img_url`, `blip_caption`, dialogue text, and session.
3. Call Qwen VLM only when a selected event has image evidence or the question is image-related.
4. Record VLM tool calls in QA trace.
5. Do not overwrite non-VLM baseline results.

Smoke target:

```text
conv-30 Q9 or another known image-related badcase.
```

Suggested file tag:

```text
vlmqa_smoke
```

Then run a small image-focused subset before Explore-50 VLM:

```text
reports/vlmqa_smoke_YYYYMMDD.md
reports/vlmqa_image_subset_YYYYMMDD.md
```

## 5. CBR And Q-Learning Extension Experiments

These are research extensions, not original MRAgent benchmark reproduction.

### 5.1 CBR Probe Case Bank

Current design:

- Before benchmark QA, generate synthetic probe questions from a conversation sample.
- Run these probe questions over the graph.
- Store trajectories in a sample-level case memory bank.
- Do not inject gold answers.

Implementation task:

```text
Implement a probe generator and case-bank writer.
```

Suggested outputs:

```text
result/case_bank/graph_cases_YYYYMMDD.jsonl
reports/cbr_probe_case_bank_YYYYMMDD.md
```

Required fields:

```json
{
  "source": "synthetic_probe|benchmark_question",
  "sample_id": "",
  "question": "",
  "question_type": "",
  "tool_trace": [],
  "retrieved_event_ids": [],
  "reward": null,
  "failure_type": "",
  "lesson": ""
}
```

### 5.2 CBR Retrieval/Update Ablations

Only after case bank exists.

Experiment groups:

- baseline MRAgent
- CBR-probe only
- CBR-retrieval
- CBR-update
- CBR-full

Report:

```text
reports/cbr_ablation_YYYYMMDD.md
```

Required:

- Same question set across groups.
- Same model/backend.
- Same evaluation script.
- Trace whether CBR changed tool choices or graph updates.

### 5.3 Q-Learning As CBR Value Learner

Q-learning is not "CBR itself"; it is an optional value learner inside the CBR module.

Do not claim Q-learning unless all exist:

- state,
- action,
- reward,
- next state,
- update rule,
- replay/update log.

Initial Q-learning target:

- learn value for tool choice,
- learn value for calling VLM,
- learn value for keeping/pruning graph nodes,
- learn value for writing a probe trajectory into case bank.

Report:

```text
reports/qlearning_cbr_value_YYYYMMDD.md
```

## 6. Required Final Reports

At minimum, the server should eventually produce:

```text
reports/vlm_tool_validation_*.md
reports/explore50_vlmready_*.md
reports/benchmark_data_audit_*.md
reports/locomo10_full_mragent_*.md
reports/standard_rag_baseline_*.md
reports/longmemeval_schema_audit_*.md
reports/longmemeval_ca*_mragent_*.md
reports/baseline_<name>_*.md
reports/cbr_probe_case_bank_*.md
reports/cbr_ablation_*.md
reports/qlearning_cbr_value_*.md
```

Every report must include:

- command,
- commit hash,
- data file path,
- sample count,
- question count,
- category distribution,
- model/backend,
- result path,
- evaluation path,
- runtime,
- error count,
- badcase examples,
- whether this is diagnostic, benchmark reproduction, or research extension.

## 7. Git Rules

Before each experiment:

```bash
git pull --ff-only origin main
git status --short --branch
```

After each report:

```bash
git status --short
git add <small-code-or-report-files-only>
git commit -m "<type>: <short description>"
git push origin main
```

Never commit:

- `.env`
- API keys
- passwords
- full `result/`
- full `log/`
- `data/external/`
- `data/dataset_LM.json`
- embedding `.pkl`
- checkpoint files

If large artifacts are needed for audit, write a manifest with absolute server path, size, SHA256, and generation command.
