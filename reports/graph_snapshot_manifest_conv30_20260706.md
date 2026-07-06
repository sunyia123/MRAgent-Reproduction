# Graph Snapshot Manifest — conv-30

Generated: 2026-07-06 | Machine: Server (Linux)
Status: **GENERATED** ✅

---

## 1. Server Execution

| field | value |
| --- | --- |
| server | Linux server (`/data/nishome/cuiwenjia/MRAgent-Reproduction`) |
| commit | Merged `origin/main` (aac5117) into `exp/20260701-stage-b-eval-audit` |
| command | `python repro/export_graph_snapshot.py --data locomo --model deepseek --sample 30 --output_dir result/graph_snapshot --report reports/graph_snapshot_conv30_20260706_server.md` |
| cache rewrite | `data/locomo/rewrite_deepseek/conv-30_rewrite.json` (231K) |
| cache keyword | `data/locomo/keyword_deepseek/conv-30_keyword.json` (98K) |
| cache embedding | `data/locomo/embedding/gpt_deepseek/conv-30_embedding.pkl` (23M) |

## 2. Output Artifacts

| file | size | committed | notes |
| --- | --- | :---: | --- |
| `result/graph_snapshot/conv-30_nodes.jsonl` | 755K | ❌ | Too large; not committed |
| `result/graph_snapshot/conv-30_edges.jsonl` | 453K | ❌ | Too large; not committed |
| `reports/graph_snapshot_conv30_20260706_server.md` | — | ✅ | Committed |

## 3. Graph Statistics

| component | count |
| --- | ---: |
| episode events | 1094 |
| keywords | 1779 |
| topics | 213 |
| persona | 4 |
| personal events | 344 |
| keyword→event edges | 5103 |
| topic→event edges | 1321 |
| persona→fact edges | 344 |
| embedding sentence count | 1094 |
| topic id source | `topic_list` |
| topic id count | 213 |
| topic embedding count | 213 |
| question embedding count | 105 |

## 4. Gold Evidence Coverage

- unique gold evidence IDs: **75**
- in episode graph: **75 / 75 (100%)** ✅
- format: gold evidence IDs are turn-level (`D1:25`), graph stores sentence-level (`D1:25-1`)
- correction: raw script reported "75 missing" due to exact string match bug — prefix matching confirms all 75 present

## 5. Bug Fix

The original `export_graph_snapshot.py` (commit 48a7807) had a `topic_id` → `topic_list` field name mismatch causing a `D1:t1 not in list` assertion error. Fixed in commit aac5117 on `origin/main`.

## 6. Badcase Graph Analysis

Graph-layer evidence for Q9-Q12 was added to `reports/badcase_pack_conv30_stratified_20260706_server_review.md` Section 8. Key finding: 0/4 cat4 single-hop questions have graph construction issues. All gold evidence exists with adequate keyword/topic connections. Q9's failure is a retrieval/tool-path miss (31 tools, empty context), not a graph problem.
