# Graph Snapshot - conv-26

## Source Caches

- rewrite: `data/locomo/rewrite_deepseek/conv-26_rewrite.json`
- keyword: `data/locomo/keyword_deepseek/conv-26_keyword.json`
- embedding: `data/locomo/embedding/gpt_deepseek/conv-26_embedding.pkl`
- embedding sentence count: 1122
- topic id source: `topic_list`
- topic id count: 191
- topic embedding count: 191
- question embedding count: 199

## Outputs

- nodes: `result/graph_snapshot/conv-26_nodes.jsonl`
- edges: `result/graph_snapshot/conv-26_edges.jsonl`

## Node Counts

| type | count |
| --- | ---: |
| episode_event | 1122 |
| keyword | 1468 |
| persona | 5 |
| personal_event | 242 |
| topic | 191 |

## Edge Counts

| type | count |
| --- | ---: |
| keyword_event | 4828 |
| persona_fact | 242 |
| topic_event | 1226 |

## Gold Evidence Coverage

- unique gold evidence ids: 134
- gold evidence turns with at least one sentence node: 133 / 134
- matched sentence-level evidence nodes: 401
- matching rule: exact event id or sentence-level prefix match, e.g. `D1:25` matches `D1:25-1`
- missing from episode graph after prefix matching: 1
- missing ids: D8:6; D9:17

## Manual Badcase Use

- For a failed question, locate its gold evidence id in the nodes file.
- Check the event text, tag, keys, and topics.
- If the evidence exists but was not retrieved, diagnose retrieval/tool path.
- If the evidence is missing or malformed, diagnose rewrite/keyword/graph construction.
- If the evidence is retrieved and the answer is still wrong, diagnose synthesis or evaluation.
