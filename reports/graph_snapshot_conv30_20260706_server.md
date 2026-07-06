# Graph Snapshot - conv-30

## Source Caches

- rewrite: `data/locomo/rewrite_deepseek/conv-30_rewrite.json`
- keyword: `data/locomo/keyword_deepseek/conv-30_keyword.json`
- embedding: `data/locomo/embedding/gpt_deepseek/conv-30_embedding.pkl`
- embedding sentence count: 1094
- topic id source: `topic_list`
- topic id count: 213
- topic embedding count: 213
- question embedding count: 105

## Outputs

- nodes: `result/graph_snapshot/conv-30_nodes.jsonl`
- edges: `result/graph_snapshot/conv-30_edges.jsonl`

## Node Counts

| type | count |
| --- | ---: |
| episode_event | 1094 |
| keyword | 1779 |
| persona | 4 |
| personal_event | 344 |
| topic | 213 |

## Edge Counts

| type | count |
| --- | ---: |
| keyword_event | 5103 |
| persona_fact | 344 |
| topic_event | 1321 |

## Gold Evidence Coverage

- unique gold evidence ids: 75
- gold evidence turns with ≥1 sentence in graph: **75 / 75 (100%)**
- format: gold evidence IDs are turn-level (`D1:25`), graph stores sentence-level (`D1:25-1`, `D1:25-2`, `D1:25-3`). Prefix matching confirms all 75 gold evidence turns map to ≥1 sentence node.

### Gold evidence per session (turn count → sentence count)

| session | gold turns | total sentences |
| --- | ---: | ---: |
| D1 | 14 | 43 |
| D2 | 4 | 21 |
| D3 | 7 | 35 |
| D4 | 1 | 3 |
| D5 | 3 | 11 |
| D6 | 7 | 23 |
| D7 | 1 | 5 |
| D8 | 5 | 17 |
| D9 | 2 | 9 |
| D10 | 2 | 12 |
| D11 | 1 | 5 |
| D12 | 3 | 8 |
| D13 | 3 | 8 |
| D14 | 3 | 9 |
| D15 | 9 | 27 |
| D16 | 2 | 7 |
| D17 | 3 | 14 |
| D18 | 5 | 18 |
| D19 | 2 | 7 |
| **Total** | **75** | **279** |

### Known false negative in raw script

The raw `export_graph_snapshot.py` reports "75 missing" because it checks `eid in memory.episode_events` with exact string match. Gold evidence IDs (`D1:25`) are turn-level; episode event IDs (`D1:25-1`) are sentence-level. This report corrects the check by prefix-matching turn IDs against sentence IDs. All 75 gold evidence turns are present.

## Manual Badcase Use

- For a failed question, locate its gold evidence id in the nodes file.
- Check the event text, tag, keys, and topics.
- If the evidence exists but was not retrieved, diagnose retrieval/tool path.
- If the evidence is missing or malformed, diagnose rewrite/keyword/graph construction.
- If the evidence is retrieved and the answer is still wrong, diagnose synthesis or evaluation.

## Badcase Graph Analysis

See `reports/badcase_pack_conv30_stratified_20260706_server_review.md` Section 8 for detailed Q9-Q12 graph-layer evidence.
