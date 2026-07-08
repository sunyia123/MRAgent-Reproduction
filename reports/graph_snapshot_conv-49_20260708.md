# Graph Snapshot - conv-49

## Source Caches

- rewrite: `data/locomo/rewrite_deepseek/conv-49_rewrite.json`
- keyword: `data/locomo/keyword_deepseek/conv-49_keyword.json`
- embedding: `data/locomo/embedding/gpt_deepseek/conv-49_embedding.pkl`
- embedding sentence count: 950
- topic id source: `topic_list`
- topic id count: 245
- topic embedding count: 245
- question embedding count: 196

## Outputs

- nodes: `result/graph_snapshot/conv-49_nodes.jsonl`
- edges: `result/graph_snapshot/conv-49_edges.jsonl`

## Node Counts

| type | count |
| --- | ---: |
| episode_event | 950 |
| keyword | 1294 |
| persona | 3 |
| personal_event | 316 |
| topic | 245 |

## Edge Counts

| type | count |
| --- | ---: |
| keyword_event | 4068 |
| persona_fact | 316 |
| topic_event | 1069 |

## Gold Evidence Coverage

- unique gold evidence ids: 185
- gold evidence turns with at least one sentence node: 181 / 185
- matched sentence-level evidence nodes: 397
- matching rule: exact event id or sentence-level prefix match, e.g. `D1:25` matches `D1:25-1`
- missing from episode graph after prefix matching: 4
- missing ids: D1:15, D21:18 D21:22 D11:15 D11:19, D22:1 D22:2 D9:10 D9:11, D9:1 D4:4 D4:6

## Manual Badcase Use

- For a failed question, locate its gold evidence id in the nodes file.
- Check the event text, tag, keys, and topics.
- If the evidence exists but was not retrieved, diagnose retrieval/tool path.
- If the evidence is missing or malformed, diagnose rewrite/keyword/graph construction.
- If the evidence is retrieved and the answer is still wrong, diagnose synthesis or evaluation.
