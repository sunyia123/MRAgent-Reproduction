# Graph Snapshot - conv-48

## Source Caches

- rewrite: `data/locomo/rewrite_deepseek/conv-48_rewrite.json`
- keyword: `data/locomo/keyword_deepseek/conv-48_keyword.json`
- embedding: `data/locomo/embedding/gpt_deepseek/conv-48_embedding.pkl`
- embedding sentence count: 1289
- topic id source: `topic_list`
- topic id count: 290
- topic embedding count: 290
- question embedding count: 239

## Outputs

- nodes: `result/graph_snapshot/conv-48_nodes.jsonl`
- edges: `result/graph_snapshot/conv-48_edges.jsonl`

## Node Counts

| type | count |
| --- | ---: |
| episode_event | 1289 |
| keyword | 2275 |
| persona | 9 |
| personal_event | 376 |
| topic | 290 |

## Edge Counts

| type | count |
| --- | ---: |
| keyword_event | 6628 |
| persona_fact | 376 |
| topic_event | 1415 |

## Gold Evidence Coverage

- unique gold evidence ids: 168
- gold evidence turns with at least one sentence node: 168 / 168
- matched sentence-level evidence nodes: 403
- matching rule: exact event id or sentence-level prefix match, e.g. `D1:25` matches `D1:25-1`
- missing from episode graph after prefix matching: 0
- missing ids: none

## Manual Badcase Use

- For a failed question, locate its gold evidence id in the nodes file.
- Check the event text, tag, keys, and topics.
- If the evidence exists but was not retrieved, diagnose retrieval/tool path.
- If the evidence is missing or malformed, diagnose rewrite/keyword/graph construction.
- If the evidence is retrieved and the answer is still wrong, diagnose synthesis or evaluation.
