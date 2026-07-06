# RAG vs MRAgent Subset Comparison - 2026-07-06

## Source

- MRAgent subset: `result/locomo/conv-30_result_deepseek_stratified.jsonl` (15 rows)
- RAG full result: `result/locomo/conv-30_result_deepseek_rag_smoke.jsonl` (105 rows)
- matched questions: 15 / 15
- missing questions: 0
- duplicate RAG questions: 1

## Score Summary

| category | n | MRAgent score | RAG score | RAG - MRAgent | MRAgent evidence hit | RAG evidence hit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 4 | 0.2665 | 0.2791 | 0.0125 | 0.7500 | 0.5000 |
| 2 | 4 | 0.7857 | 0.0000 | -0.7857 | 0.7500 | 1.0000 |
| 4 | 4 | 0.1170 | 0.1534 | 0.0364 | 0.7500 | 0.7500 |
| 5 | 3 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |
| OVERALL | 15 | 0.5118 | 0.3153 | -0.1965 | 0.8000 | 0.8000 |

## Per-Question Comparison

| # | cat | MR score | RAG score | MR hit | RAG hit | question | gold | MRAgent prediction | RAG prediction |
| ---: | --- | ---: | ---: | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 0.0000 | 0.1333 | N | N | What do Jon and Gina both have in common? | They lost their jobs and decided to start their own businesses. | no information available | They both support each other. |
| 2 | 1 | 0.2745 | 0.4444 | Y | Y | What Jon thinks the ideal dance studio should look like? | By the water, with natural light and Marley flooring | By the water with a view of the ocean, downtown (easy to get to), natural light, good size, a good dance floor with e... | By the water |
| 3 | 2 | 0.5714 | 0.0000 | Y | Y | When did Jon start to go to the gym? | March, 2023 | the week before 16 March 2023 | no information available |
| 4 | 2 | 1.0000 | 0.0000 | Y | Y | When did Gina open her online clothing store? | 16 March, 2023 | 16 March 2023 | no information available |
| 5 | 1 | 0.2917 | 0.5385 | Y | Y | Why did Gina decide to start her own clothing store? | She always loved fashion trends and finding unique pieces and she lost her job so decided it was time to start her ow... | After losing her job at Door Dash, she wanted to take control of her own destiny, be her own boss, and combine her pa... | Gina decided to start her own clothing store because she is passionate about fashion trends and finding unique pieces... |
| 6 | 2 | 0.5714 | 0.0000 | Y | Y | When was Jon in Rome? | June 2023 | the week before 19 June 2023 | no information available |
| 7 | 1 | 0.5000 | 0.0000 | Y | N | How long did it take for Jon to open his studio? | six months | 5 months | no information available |
| 8 | 2 | 1.0000 | 0.0000 | N | Y | When did Jon and Gina decide to collaborate to create dance content? | 21 July 2023 | 21 July 2023 | no information available |
| 9 | 4 | 0.0000 | 0.0000 | N | Y | What do the dancers in the photo represent? | They are performing at the festival | no information available | no information available |
| 10 | 4 | 0.1111 | 0.0000 | Y | N | What is Jon's attitude towards being part of the dance festival? | Glad | Excited, glad, and passionate — he finds it awesome, brings him joy, and reminds him why he loves dance. | He feels joyful and passionate about it. |
| 11 | 4 | 0.1017 | 0.2500 | Y | Y | What made Gina choose the furniture and decor for her store? | personal style and customer comfort | She wanted to make the place look like her own style and make her customers feel cozy. She chose furniture that looks... | Gina wanted the store to reflect her own style and make customers feel cozy. |
| 12 | 4 | 0.2553 | 0.3636 | Y | Y | Why did Gina combine her clothing business with dance? | she is passionate about dance and fashion | She is passionate about both dance and fashion, so combining them lets her show her creativity, share her love with o... | Gina combined her clothing business with dance because she is passionate about both dance and fashion, and blending t... |
| 13 | 5 | 1.0000 | 1.0000 | Y | Y | Where is Jon's fashion internship? |  | Not mentioned in the conversation | Not mentioned in the conversation. |
| 14 | 5 | 1.0000 | 1.0000 | Y | Y | What did Jon make a limited edition line of? |  | Not mentioned in the conversation | Not mentioned in the conversation |
| 15 | 5 | 1.0000 | 1.0000 | Y | Y | What plans does Gina have after receiving advice at the networking event? |  | Not mentioned in the conversation. | Not mentioned in the conversation. |

## Interpretation Rules

- If RAG hits evidence and MRAgent misses it, diagnose tool-path or graph traversal.
- If both hit evidence but answer differs, diagnose answer synthesis or evaluation.
- If both miss evidence, diagnose rewrite/embedding/query formulation or image missingness.
- This comparison is fair only for matched questions; do not compare 105-question RAG aggregate to 15-question MRAgent aggregate directly.
