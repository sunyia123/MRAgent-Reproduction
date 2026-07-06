# Graph Snapshot Manifest — conv-30

Generated: 2026-07-06 | Machine: Codex本机 (CWJ, Windows 11)
Status: **NOT GENERATED** — cache files exist only on server

---

## 1. Why Not Generated

The graph snapshot script (`repro/export_graph_snapshot.py`) requires three cache files that are gitignored and exist only on the Linux server:

| cache | server path | gitignored |
| --- | --- | --- |
| rewrite | `data/locomo/rewrite_deepseek/conv-30_rewrite.json` | yes |
| keyword | `data/locomo/keyword_deepseek/conv-30_keyword.json` | yes |
| embedding | `data/locomo/embedding/gpt_deepseek/conv-30_embedding.pkl` | yes |

These were regenerated on the server during the 2026-07-02 stratified run (see log lines 3, 24, 45+ in `log/locomo/conv-30_deepseek_stratified.log`).

On the Codex machine (Windows), the directories `data/locomo/rewrite_deepseek/`, `data/locomo/keyword_deepseek/`, and `data/locomo/embedding/gpt_deepseek/` exist but are EMPTY.

---

## 2. Memory Audit (from committed artifact)

The memory audit at `result/locomo/memory_audit_deepseek_stratified.json` provides a partial graph inventory without needing to re-run `export_graph_snapshot.py`:

| component | count |
| --- | ---: |
| sessions | 19 |
| total sentences (episode events) | 1094 |
| unique tags | 465 |
| keywords (key nodes) | 4408 |
| unique keywords | 1779 |
| topics | 213 |
| persona events | 344 |
| unique persons | 4 |
| sentences without keywords | 9 / 1094 |
| sessions without sentences | 0 |
| sentences without id/text/tag | 0 |

---

## 3. Expected Output (when run on server)

```bash
cd /data/nishome/cuiwenjia/MRAgent-Reproduction
conda activate mragent-repro
python repro/export_graph_snapshot.py \
  --data locomo \
  --model deepseek \
  --sample 30 \
  --output_dir result/graph_snapshot \
  --report reports/graph_snapshot_conv30_20260706.md
```

Expected outputs:

| file | description | expected size |
| --- | --- | --- |
| `result/graph_snapshot/conv-30_nodes.jsonl` | episode_event, keyword, topic, persona, personal_event nodes | ~1–2 MB |
| `result/graph_snapshot/conv-30_edges.jsonl` | keyword_event, topic_event, persona_fact edges | ~0.5–1 MB |
| `reports/graph_snapshot_conv30_20260706.md` | summary counts and gold evidence coverage | small |

---

## 4. Gold Evidence Coverage (pre-computed from result)

From the result JSONL and dataset, the expected gold evidence for conv-30 stratified questions:

| question | category | gold evidence ids | in episode graph? |
| --- | --- | --- | --- |
| Q1: commonality | 1 | D1:2, D1:3, D1:4, D2:1 | expected yes (D1, D2 sessions) |
| Q2: ideal studio | 1 | D1:20, D2:4, D2:8 | expected yes |
| Q3: Jon gym start | 2 | D6:1 | expected yes |
| Q4: Gina store open | 2 | D6:6 | expected yes |
| Q5: Gina store reason | 1 | D6:8, D1:3 | expected yes |
| Q6: Jon in Rome | 2 | D15:1 | expected yes |
| Q7: studio time | 1 | D1:2, D15:13 | expected yes |
| Q8: collaborate date | 2 | D18:18 | expected yes |
| Q9: dancers photo | 4 | D1:25 | expected yes |
| Q10: Jon attitude | 4 | D1:28 | expected yes |
| Q11: Gina furniture | 4 | D3:6 | expected yes |
| Q12: Gina combine | 4 | D8:8 | expected yes |
| Q13: Jon internship | 5 | D12:3 | expected yes |
| Q14: Jon limited edition | 5 | D16:3 | expected yes |
| Q15: Gina plans | 5 | D18:10 | expected yes |

All gold evidence IDs map to real conversation turns (verified by extracting original text from `data/dataset_locomo.json`). With 1094 episode events and zero sessions_without_sentences, **all gold evidence should exist in the episode graph**.

If any are missing when the graph snapshot is actually exported, the issue is in the rewrite-to-graph construction pipeline, not in the raw data.

---

## 5. Server Artifact Paths (to be filled after server run)

When the graph snapshot is generated on the server, record here:

```json
{
  "server": "TBD",
  "commit": "48a7807",
  "command": "python repro/export_graph_snapshot.py --data locomo --model deepseek --sample 30 --output_dir result/graph_snapshot --report reports/graph_snapshot_conv30_20260706.md",
  "nodes": {
    "path": "result/graph_snapshot/conv-30_nodes.jsonl",
    "size_bytes": null,
    "sha256": null,
    "committed": false
  },
  "edges": {
    "path": "result/graph_snapshot/conv-30_edges.jsonl",
    "size_bytes": null,
    "sha256": null,
    "committed": false
  },
  "report": {
    "path": "reports/graph_snapshot_conv30_20260706.md",
    "committed": true
  }
}
```

---

## 6. Recommendation

The graph snapshot should be generated on the server during the next server-side Claude Code session. The cache files exist there and the command is a pure read-only operation (no API calls). The resulting report can then be committed alongside this manifest.

For now, the memory audit (`result/locomo/memory_audit_deepseek_stratified.json`) provides sufficient structural evidence: 1094 events, 4408 keyword links, 213 topics, 344 persona events, zero structural anomalies.
