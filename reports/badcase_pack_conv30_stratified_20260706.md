# Badcase Process Pack - 20260706

## Source

- result: `result\locomo\conv-30_result_deepseek_stratified.jsonl`
- rows: 15
- selected badcases: 5
- f1_threshold: 0.2

## Category Summary

| category | count | avg report score |
| --- | ---: | ---: |
| 1 | 4 | 0.2865 |
| 2 | 4 | 0.7500 |
| 4 | 4 | 0.1064 |
| 5 | 3 | 1.0000 |

## Badcase Table

| # | cat | f1 | type | tools | question | gold | prediction | gold evidence | retrieved context |
| ---: | --- | ---: | --- | ---: | --- | --- | --- | --- | --- |
| 1 | 4 | 0.0000 | no_information_answer | 31 | What do the dancers in the photo represent? | They are performing at the festival | no information available | D1:25 |  |
| 2 | 1 | 0.0000 | no_information_answer | 24 | What do Jon and Gina both have in common? | They lost their jobs and decided to start their own businesses. | no information available | D1:2, D1:3, D1:4, D2:1 |  |
| 3 | 4 | 0.0563 | low_f1_possible_paraphrase_or_wrong_answer | 8 | What made Gina choose the furniture and decor for her store? | personal style and customer comfort | She wanted to make the place look like her own style and make her customers feel cozy. She chose furniture that looks great and is comfy, and the chandelier ... | D3:6 | D3:6, D3:8 |
| 4 | 4 | 0.1053 | low_f1_possible_paraphrase_or_wrong_answer | 7 | What is Jon's attitude towards being part of the dance festival? | Glad | Excited, glad, and passionate — he finds it awesome, brings him joy, and reminds him why he loves dance. | D1:28 | D1:14, D1:24, D1:28, D5:2 |
| 5 | 2 | 1.0000 | retrieval_miss_or_context_mismatch | 6 | When did Jon and Gina decide to collaborate to create dance content? | 21 July 2023 | 21 July 2023 | D18:18 | D18:13, D18:14, D18:15 |

## Manual Review Checklist

For each important badcase, add:

- original conversation snippets for gold evidence ids;
- rewrite sentences and keyword records for those ids;
- full tool-call path from log files;
- whether the error is retrieval miss, graph traversal issue, rewrite loss, image evidence loss, temporal calculation, model synthesis, or metric mismatch;
- concrete code/prompt change to test next.

This report is intentionally small enough to commit to GitHub. Large logs should be referenced by manifest path, size, and checksum.
