# Graph Snapshot - conv-42

## Source Caches

- rewrite: `data/locomo/rewrite_deepseek/conv-42_rewrite.json`
- keyword: `data/locomo/keyword_deepseek/conv-42_keyword.json`
- embedding: `data/locomo/embedding/gpt_deepseek/conv-42_embedding.pkl`
- embedding sentence count: 1128
- topic id source: `topic_list`
- topic id count: 265
- topic embedding count: 265
- question embedding count: 260

## Outputs

- nodes: `result/graph_snapshot/conv-42_nodes.jsonl`
- edges: `result/graph_snapshot/conv-42_edges.jsonl`

## Node Counts

| type | count |
| --- | ---: |
| episode_event | 1128 |
| keyword | 2124 |
| persona | 3 |
| personal_event | 356 |
| topic | 265 |

## Edge Counts

| type | count |
| --- | ---: |
| keyword_event | 5947 |
| persona_fact | 356 |
| topic_event | 1223 |

## Gold Evidence Coverage

- unique gold evidence ids: 182
- gold evidence turns with at least one sentence node: 180 / 182
- matched sentence-level evidence nodes: 367
- matching rule: exact event id or sentence-level prefix match, e.g. `D1:25` matches `D1:25-1`
- missing from episode graph after prefix matching: 2
- missing ids: D, D10:19

## Manual Badcase Use

- For a failed question, locate its gold evidence id in the nodes file.
- Check the event text, tag, keys, and topics.
- If the evidence exists but was not retrieved, diagnose retrieval/tool path.
- If the evidence is missing or malformed, diagnose rewrite/keyword/graph construction.
- If the evidence is retrieved and the answer is still wrong, diagnose synthesis or evaluation.
