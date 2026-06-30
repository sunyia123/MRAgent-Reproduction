# MRAgent Reproduction Goal

## Objective

Reproduce the public MRAgent results at a verifiable small-to-full scale, then extend MRAgent with Memento-inspired case-based reasoning and Q-learning-style memory utility selection.

## Current Main Paper

- Title: `Memory is Reconstructed, Not Retrieved: Graph Memory for LLM Agents`
- arXiv: https://arxiv.org/abs/2606.06036
- Upstream repository: https://github.com/Ji-shuo/MRAgent
- Local deep-reading note: `D:\Obsidian\ObsidianResearch\20_Research\22-精读\MRAgent Memory is Reconstructed, Not Retrieved Graph Memory for LLM Agents.md`

## Fixed Baseline

- Upstream commit: `7441506db984b7c4da32e8dbeb2527f2e351270a`
- Private repository: `sunyia123/MRAgent-Reproduction`
- Local path: `D:\Desktop\Study\0-Project\MRAgent-Reproduction`

## Success Criteria

1. Local code checkout and dependency installation succeed.
2. LoCoMo single-sample smoke run completes.
3. LoCoMo small subset run produces answer JSONL and evaluation summary.
4. LongMemEval data availability is resolved or documented as blocked by Git LFS quota.
5. Full LoCoMo reproduction runs on the server with cached intermediate artifacts.
6. Reports compare reproduced metrics with paper Table 1/2/3 and identify model/backend differences.
7. Extension experiments record graph traversal traces, fixed/broken cases, and utility-scored memory decisions.

