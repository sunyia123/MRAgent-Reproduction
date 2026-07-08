# Core Validation 100q — Evaluation Report
Generated: 2026-07-08

## Methods

| Method | Rows | ERRORs | Overall F1 | Evidence Hit Rate |
|---|---:|---:|---:|---:|
| MRAgent | 100 | 2 | 0.629 | 0.670 |
| RAG | 100 | 0 | 0.441 | 0.612 |
| GraphRAG | 100 | 0 | 0.353 | 0.596 |
| Oracle | 100 | 77 | 0.090 | 0.990 |

## Per-Category F1

| Category | MRAgent F1 | RAG F1 | GraphRAG F1 | Oracle F1 |
|---|---:||---:||---:||---:|
| 1 | 0.555 (n=20) | 0.413 (n=20) | 0.295 (n=20) | 0.118 (n=20) |
| 2 | 0.600 (n=20) | 0.177 (n=20) | 0.154 (n=20) | 0.029 (n=20) |
| 3 | 0.345 (n=18) | 0.147 (n=18) | 0.061 (n=18) | 0.031 (n=18) |
| 4 | 0.752 (n=22) | 0.530 (n=22) | 0.463 (n=22) | 0.159 (n=22) |
| 5 | 0.850 (n=20) | 0.900 (n=20) | 0.750 (n=20) | 0.100 (n=20) |

## Evidence Hit Rate

| Category | MRAgent | RAG | GraphRAG | Oracle |
|---|---:||---:||---:||---:|
| 1 | 43.33% | 53.33% | 45.21% | 100.00% |
| 2 | 80.00% | 87.50% | 95.00% | 100.00% |
| 3 | 25.00% | 33.33% | 30.21% | 93.75% |
| 4 | 100.00% | 77.27% | 72.73% | 100.00% |
| 5 | 75.00% | 47.50% | 47.50% | 100.00% |

## Oracle ERROR Examples
Total Oracle ERRORs: 77/100

### Oracle Error #1
- **Question**: When did Caroline go to the LGBTQ support group?
- **Gold Answer**: 7 May 2023
- **Category**: 2
- **Evidence**: ['D1:3']
- **Sample**: conv-26

### Oracle Error #2
- **Question**: Where did Caroline move from 4 years ago?
- **Gold Answer**: Sweden
- **Category**: 1
- **Evidence**: ['D3:13', 'D4:3']
- **Sample**: conv-26

### Oracle Error #3
- **Question**: Would Melanie be considered a member of the LGBTQ community?
- **Gold Answer**: Likely no, she does not refer to herself as part of it
- **Category**: 3
- **Evidence**: []
- **Sample**: conv-26

### Oracle Error #4
- **Question**: What are Melanie's pets' names?
- **Gold Answer**: Oliver, Luna, Bailey
- **Category**: 1
- **Evidence**: ['D13:4', 'D7:18']
- **Sample**: conv-26

### Oracle Error #5
- **Question**: Would Melanie likely enjoy the song "The Four Seasons" by Vivaldi?
- **Gold Answer**: Yes; it's classical music
- **Category**: 3
- **Evidence**: ['D15:28']
- **Sample**: conv-26

### Oracle Error #6
- **Question**: How long has Melanie been practicing art?
- **Gold Answer**: Since 2016
- **Category**: 2
- **Evidence**: ['D16:8']
- **Sample**: conv-26

### Oracle Error #7
- **Question**: What did the charity race raise awareness for?
- **Gold Answer**: mental health
- **Category**: 4
- **Evidence**: ['D2:2']
- **Sample**: conv-26

### Oracle Error #8
- **Question**: What was Melanie's reaction to her children enjoying the Grand Canyon?
- **Gold Answer**: She was happy and thankful
- **Category**: 4
- **Evidence**: ['D18:5']
- **Sample**: conv-26

### Oracle Error #9
- **Question**: What did Melanie make for a local church?
- **Gold Answer**: None
- **Category**: 5
- **Evidence**: ['D14:17']
- **Sample**: conv-26

### Oracle Error #10
- **Question**: What type of instrument does Caroline play?
- **Gold Answer**: None
- **Category**: 5
- **Evidence**: ['D15:26']
- **Sample**: conv-26


## Key Findings

- **RAG cat2 (temporal) F1**: 0.177 — improved
- **GraphRAG cat2 (temporal) F1**: 0.154 — improved
- **MRAgent cat4 (single-hop) F1**: 0.752
- **RAG cat4 (single-hop) F1**: 0.530
- **GraphRAG cat4 (single-hop) F1**: 0.463
- **Oracle cat4 (single-hop) F1**: 0.159
