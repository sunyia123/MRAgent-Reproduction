# MRAgent Reproduction Plan

## 1. Reading Summary

The paper argues that long-dialogue memory should not be accessed through one-shot top-k retrieval. Instead, useful memory is reconstructed through a state-dependent graph traversal process.

Core mechanism:

1. Rewrite dialogue turns into self-contained events.
2. Extract cues, tags, topics, personal facts, and temporal anchors.
3. Build a graph-structured memory.
4. During answering, let the LLM choose graph traversal tools based on the current evidence state.
5. Route and prune retrieved evidence before producing the final answer.

Main claim:

> Active memory reconstruction outperforms passive retrieval because later retrieval steps can depend on evidence discovered earlier.

Relevance to the thesis:

- Direction B: Case-Based Reasoning for LLM Agents.
- Direction D: Reward-aware / utility-aware retrieval.
- Direction E: Adaptive RAG / Agentic Search.
- Direction I: Long-horizon Agent Memory evaluation.

Critical limitation:

- MRAgent has active query-time memory access, but does not learn long-term memory utility from historical success/failure.
- Selection, routing, and stopping are prompt/tool-use decisions, not learned policies.

## 2. Reproduction Scope

### Stage A: Engineering Smoke

Goal: verify the official code runs.

Commands:

```bash
python run.py --data locomo --model gemini --file smoke --sample 0
python eval/evaluate_reasoning.py --data locomo --model gemini --file smoke --allfile
```

Expected:

- Single LoCoMo sample completes.
- Rewrite, keyword, embedding, result, and log files are produced.
- Evaluation script runs.

Acceptance:

- No unhandled exception.
- At least one prediction JSONL exists.
- The report records all generated files.

### Stage B: LoCoMo Small Subset

Goal: reproduce a stable subset before full runs.

Plan:

- Select 3-5 LoCoMo samples.
- Run `gemini` first, then optionally `claude`.
- Save summary only, not raw generated artifacts.

Metrics:

- LLM-judge accuracy.
- F1/EM from evaluation script.
- Per-category result if available.
- Average turns, tool calls, runtime.

Required report:

```text
reports/locomo_subset_reproduction_YYYYMMDD.md
reports/locomo_subset_reproduction_YYYYMMDD.csv
```

### Stage C: Full LoCoMo Reproduction

Goal: compare against paper Table 1 under available model/backend constraints.

Plan:

```bash
python run.py --data locomo --model gemini --file full_locomo
python eval/evaluate_reasoning.py --data locomo --model gemini --file full_locomo --allfile
```

Expected:

- All LoCoMo samples complete.
- Result JSONL files exist under `result/locomo/`.
- Evaluation summary is produced.

Risks:

- API cost and rate limit.
- Long runtime due to tool-calling.
- Judge dependency.
- Prompt/model differences from the paper.

### Stage D: LongMemEval Reproduction

Current blocker:

- Upstream `data/dataset_LM.json` failed to download because GitHub LFS quota is exceeded.
- The local file may exist but still be only a Git LFS pointer. A pointer file is not usable benchmark data.
- This blocker is external data availability, not an implementation failure.

Plan:

1. Confirm whether server clone has the full file.
2. If not, locate the official LongMemEval source and document provenance.
3. Do not fabricate or silently replace the dataset.
4. Once available, run each category:

```bash
python run.py --data LM --model gemini --file lm_ca0 --ca 0 --lm_batch 1
python run.py --data LM --model gemini --file lm_ca1 --ca 1 --lm_batch 1
python run.py --data LM --model gemini --file lm_ca2 --ca 2 --lm_batch 1
```

Expected:

- Category-specific result files.
- Evaluation report comparable to paper Table 2.

Dataset readiness criteria:

- `data/dataset_LM.json` must be hundreds of MB, not around 100-200 bytes.
- The first lines must be JSON data, not `version https://git-lfs.github.com/spec/v1`.
- The experiment report must record file size, checksum, and source URL or transfer path.

## 3. Trace Requirements

Every reproduced answer must be auditable at the graph traversal level.

Required fields:

```json
{
  "sample_id": "",
  "question_id": "",
  "question": "",
  "gold_answer": "",
  "prediction": "",
  "judge_correct": true,
  "category": "",
  "tool_calls": [
    {
      "turn": 1,
      "tool": "query_event_context",
      "arguments": {},
      "returned_event_ids": [],
      "returned_text_preview": ""
    }
  ],
  "evidence_support": [],
  "support_origin": [],
  "failure_type": "none|rewrite|keyword|embedding|tool|routing|answer|judge|unknown"
}
```

If traces are not available from upstream logs, add minimal instrumentation before large runs.

## 4. Memento-Inspired Extension Plan

Memento is a reference, not the main codebase. The extension should target MRAgent's active graph traversal.

### Extension 1: Graph Case Bank

Store historical successful and failed graph traversal trajectories:

```json
{
  "question": "",
  "category": "",
  "question_keys": [],
  "tool_trace": [],
  "event_ids": [],
  "topic_ids": [],
  "answer": "",
  "reward": 1,
  "failure_type": ""
}
```

### Extension 2: CBR Strategy Retrieval

Before answering a new question:

1. Retrieve similar historical cases by question type and graph-action pattern.
2. Inject only strategy-level guidance.
3. Do not inject answer facts.
4. Record whether the strategy changed tool choices.

### Extension 3: Q-learning-style Utility Scoring

Initial approximation:

- State: question keys, category, current evidence state, candidate tool/node.
- Action: choose graph tool, tag, event, topic, or context expansion.
- Reward: final correctness plus evidence support, minus tool-cost penalty.
- Output: utility score for candidate actions.

Do not claim full paper-style Q-learning unless a real temporal-difference target and replay buffer are implemented.

### Extension 4: Gating

Only apply CBR/Q-score guidance when confidence is high. Otherwise fall back to original MRAgent.

Required comparison:

| Config | Meaning |
| --- | --- |
| A | Original MRAgent |
| B | MRAgent + CBR strategy retrieval |
| C | MRAgent + supervised utility scorer |
| D | MRAgent + Q-learning-style scorer |
| E | MRAgent + gated utility scorer |

Report fixed/broken cases against A.

## 5. Evaluation Risks

1. LLM judge bias can inflate gains.
2. Graph construction quality depends on the LLM rewrite/extraction stage.
3. Training and evaluation must be split by conversation/sample to avoid leakage.
4. More tool calls can improve recall but increase latency and noise.
5. LongMemEval is blocked until the LFS dataset issue is resolved.

## 6. Immediate Next Steps

1. Push this project to private GitHub.
2. Verify local environment with LoCoMo sample 0.
3. Add trace instrumentation if upstream logs are insufficient.
4. Run a 3-sample LoCoMo subset.
5. Write first reproduction report.
6. Resolve LongMemEval data availability.
