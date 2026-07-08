# Graph Snapshot - conv-47

## Source Caches

- rewrite: `data/locomo/rewrite_deepseek/conv-47_rewrite.json`
- keyword: `data/locomo/keyword_deepseek/conv-47_keyword.json`
- embedding: `data/locomo/embedding/gpt_deepseek/conv-47_embedding.pkl`
- embedding sentence count: 1408
- topic id source: `topic_list`
- topic id count: 284
- topic embedding count: 284
- question embedding count: 190

## Outputs

- nodes: `result/graph_snapshot/conv-47_nodes.jsonl`
- edges: `result/graph_snapshot/conv-47_edges.jsonl`

## Node Counts

| type | count |
| --- | ---: |
| episode_event | 1408 |
| keyword | 1918 |
| persona | 7 |
| personal_event | 387 |
| topic | 284 |

## Edge Counts

| type | count |
| --- | ---: |
| keyword_event | 5898 |
| persona_fact | 387 |
| topic_event | 1455 |

## Gold Evidence Coverage

- unique gold evidence ids: 133
- gold evidence turns with at least one sentence node: 132 / 133
- matched sentence-level evidence nodes: 340
- matching rule: exact event id or sentence-level prefix match, e.g. `D1:25` matches `D1:25-1`
- missing from episode graph after prefix matching: 1
- missing ids: D4:36

## Manual Badcase Use

- For a failed question, locate its gold evidence id in the nodes file.
- Check the event text, tag, keys, and topics.
- If the evidence exists but was not retrieved, diagnose retrieval/tool path.
- If the evidence is missing or malformed, diagnose rewrite/keyword/graph construction.
- If the evidence is retrieved and the answer is still wrong, diagnose synthesis or evaluation.
