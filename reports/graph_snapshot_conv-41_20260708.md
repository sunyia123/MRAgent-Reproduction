# Graph Snapshot - conv-41

## Source Caches

- rewrite: `data/locomo/rewrite_deepseek/conv-41_rewrite.json`
- keyword: `data/locomo/keyword_deepseek/conv-41_keyword.json`
- embedding: `data/locomo/embedding/gpt_deepseek/conv-41_embedding.pkl`
- embedding sentence count: 1488
- topic id source: `topic_list`
- topic id count: 316
- topic embedding count: 316
- question embedding count: 193

## Outputs

- nodes: `result/graph_snapshot/conv-41_nodes.jsonl`
- edges: `result/graph_snapshot/conv-41_edges.jsonl`

## Node Counts

| type | count |
| --- | ---: |
| episode_event | 1488 |
| keyword | 2019 |
| persona | 8 |
| personal_event | 381 |
| topic | 316 |

## Edge Counts

| type | count |
| --- | ---: |
| keyword_event | 7070 |
| persona_fact | 381 |
| topic_event | 1789 |

## Gold Evidence Coverage

- unique gold evidence ids: 128
- gold evidence turns with at least one sentence node: 128 / 128
- matched sentence-level evidence nodes: 350
- matching rule: exact event id or sentence-level prefix match, e.g. `D1:25` matches `D1:25-1`
- missing from episode graph after prefix matching: 0
- missing ids: none

## Manual Badcase Use

- For a failed question, locate its gold evidence id in the nodes file.
- Check the event text, tag, keys, and topics.
- If the evidence exists but was not retrieved, diagnose retrieval/tool path.
- If the evidence is missing or malformed, diagnose rewrite/keyword/graph construction.
- If the evidence is retrieved and the answer is still wrong, diagnose synthesis or evaluation.
