# Graph Snapshot - conv-44

## Source Caches

- rewrite: `data/locomo/rewrite_deepseek/conv-44_rewrite.json`
- keyword: `data/locomo/keyword_deepseek/conv-44_keyword.json`
- embedding: `data/locomo/embedding/gpt_deepseek/conv-44_embedding.pkl`
- embedding sentence count: 1270
- topic id source: `topic_list`
- topic id count: 277
- topic embedding count: 277
- question embedding count: 158

## Outputs

- nodes: `result/graph_snapshot/conv-44_nodes.jsonl`
- edges: `result/graph_snapshot/conv-44_edges.jsonl`

## Node Counts

| type | count |
| --- | ---: |
| episode_event | 1270 |
| keyword | 1439 |
| persona | 8 |
| personal_event | 344 |
| topic | 277 |

## Edge Counts

| type | count |
| --- | ---: |
| keyword_event | 5099 |
| persona_fact | 344 |
| topic_event | 1513 |

## Gold Evidence Coverage

- unique gold evidence ids: 126
- gold evidence turns with at least one sentence node: 126 / 126
- matched sentence-level evidence nodes: 331
- matching rule: exact event id or sentence-level prefix match, e.g. `D1:25` matches `D1:25-1`
- missing from episode graph after prefix matching: 0
- missing ids: none

## Manual Badcase Use

- For a failed question, locate its gold evidence id in the nodes file.
- Check the event text, tag, keys, and topics.
- If the evidence exists but was not retrieved, diagnose retrieval/tool path.
- If the evidence is missing or malformed, diagnose rewrite/keyword/graph construction.
- If the evidence is retrieved and the answer is still wrong, diagnose synthesis or evaluation.
