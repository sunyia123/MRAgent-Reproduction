# Graph Snapshot - conv-43

## Source Caches

- rewrite: `data/locomo/rewrite_deepseek/conv-43_rewrite.json`
- keyword: `data/locomo/keyword_deepseek/conv-43_keyword.json`
- embedding: `data/locomo/embedding/gpt_deepseek/conv-43_embedding.pkl`
- embedding sentence count: 1444
- topic id source: `topic_list`
- topic id count: 223
- topic embedding count: 223
- question embedding count: 242

## Outputs

- nodes: `result/graph_snapshot/conv-43_nodes.jsonl`
- edges: `result/graph_snapshot/conv-43_edges.jsonl`

## Node Counts

| type | count |
| --- | ---: |
| episode_event | 1444 |
| keyword | 2305 |
| persona | 2 |
| personal_event | 369 |
| topic | 223 |

## Edge Counts

| type | count |
| --- | ---: |
| keyword_event | 6843 |
| persona_fact | 369 |
| topic_event | 1505 |

## Gold Evidence Coverage

- unique gold evidence ids: 169
- gold evidence turns with at least one sentence node: 168 / 169
- matched sentence-level evidence nodes: 414
- matching rule: exact event id or sentence-level prefix match, e.g. `D1:25` matches `D1:25-1`
- missing from episode graph after prefix matching: 1
- missing ids: D:11:26

## Manual Badcase Use

- For a failed question, locate its gold evidence id in the nodes file.
- Check the event text, tag, keys, and topics.
- If the evidence exists but was not retrieved, diagnose retrieval/tool path.
- If the evidence is missing or malformed, diagnose rewrite/keyword/graph construction.
- If the evidence is retrieved and the answer is still wrong, diagnose synthesis or evaluation.
