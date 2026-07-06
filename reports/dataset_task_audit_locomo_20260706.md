# Dataset And Task Audit - 2026-07-06

## Summary

- dataset path: `data\dataset_locomo.json`
- samples: 10
- questions: 1986
- sessions: 272
- turns: 5882
- image turns: 910

## Category Distribution

| category | count |
| --- | ---: |
| 1 | 282 |
| 2 | 321 |
| 3 | 96 |
| 4 | 841 |
| 5 | 446 |

## Per-Sample Tasks

| sample | sessions | turns | image turns | questions | categories | speakers |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `conv-26` | 19 | 419 | 77 | 199 | 1:32, 2:37, 3:13, 4:70, 5:47 | Caroline:211, Melanie:208 |
| `conv-30` | 19 | 369 | 30 | 105 | 1:11, 2:26, 4:44, 5:24 | Jon:185, Gina:184 |
| `conv-41` | 32 | 663 | 77 | 193 | 1:31, 2:27, 3:8, 4:86, 5:41 | John:335, Maria:328 |
| `conv-42` | 29 | 629 | 80 | 260 | 1:37, 2:40, 3:11, 4:111, 5:61 | Nate:316, Joanna:313 |
| `conv-43` | 29 | 680 | 123 | 242 | 1:31, 2:26, 3:14, 4:107, 5:64 | Tim:344, John:336 |
| `conv-44` | 28 | 675 | 149 | 158 | 1:30, 2:24, 3:7, 4:62, 5:35 | Audrey:338, Andrew:337 |
| `conv-47` | 31 | 689 | 81 | 190 | 1:20, 2:34, 3:13, 4:83, 5:40 | John:346, James:343 |
| `conv-48` | 30 | 681 | 108 | 239 | 1:21, 2:42, 3:10, 4:118, 5:48 | Deborah:341, Jolene:340 |
| `conv-49` | 25 | 509 | 86 | 196 | 1:37, 2:33, 3:13, 4:73, 5:40 | Evan:256, Sam:253 |
| `conv-50` | 30 | 568 | 99 | 204 | 1:32, 2:32, 3:7, 4:87, 5:46 | Calvin:285, Dave:283 |

## How To Use This Audit

- Use small, stratified subsets before full runs.
- Include image-heavy samples only when the image access path is validated.
- Keep category counts fixed across MRAgent, Standard RAG, GraphRAG, Oracle, and CBR ablations.
- Do not interpret a diagnostic subset as a paper-level benchmark.
