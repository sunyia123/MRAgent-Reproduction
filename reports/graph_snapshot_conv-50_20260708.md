# Graph Snapshot - conv-50

## Source Caches

- rewrite: `data/locomo/rewrite_deepseek/conv-50_rewrite.json`
- keyword: `data/locomo/keyword_deepseek/conv-50_keyword.json`
- embedding: `data/locomo/embedding/gpt_deepseek/conv-50_embedding.pkl`
- embedding sentence count: 1453
- topic id source: `topic_list`
- topic id count: 264
- topic embedding count: 264
- question embedding count: 204

## Outputs

- nodes: `result/graph_snapshot/conv-50_nodes.jsonl`
- edges: `result/graph_snapshot/conv-50_edges.jsonl`

## Node Counts

| type | count |
| --- | ---: |
| episode_event | 1453 |
| keyword | 1622 |
| persona | 3 |
| personal_event | 353 |
| topic | 264 |

## Edge Counts

| type | count |
| --- | ---: |
| keyword_event | 5855 |
| persona_fact | 353 |
| topic_event | 1561 |

## Gold Evidence Coverage

- unique gold evidence ids: 134
- gold evidence turns with at least one sentence node: 133 / 134
- matched sentence-level evidence nodes: 392
- matching rule: exact event id or sentence-level prefix match, e.g. `D1:25` matches `D1:25-1`
- missing from episode graph after prefix matching: 1
- missing ids: D30:05

## Manual Badcase Use

- For a failed question, locate its gold evidence id in the nodes file.
- Check the event text, tag, keys, and topics.
- If the evidence exists but was not retrieved, diagnose retrieval/tool path.
- If the evidence is missing or malformed, diagnose rewrite/keyword/graph construction.
- If the evidence is retrieved and the answer is still wrong, diagnose synthesis or evaluation.
