# Paper Positioning (2026-03-10)

## Recommended Main Claims

### Claim 1: Federated robust aggregation is the primary contribution
- In poisoned federated settings, robust aggregation methods outperform FedAvg with stable effect size.
- The strongest current evidence is the pooled cross-protocol result and the 9-seed temporal extension.
- This should be the first headline claim in the title, abstract, and introduction.

### Claim 2: Physics-informed learning is a conditional, not universal, gain
- The traditional anti-leakage family (`temporal_ood`, `topology_ood`, `attack_strategy_ood`) remains non-significant.
- The congestion-centric family shows significant gains, and the mechanism ablation indicates that the physics-loss term is the main source of improvement.
- This should be framed as a scoped second claim, not as a universal uplift.

## Claims To Avoid
- Do not claim that physics regularization consistently improves all OOD protocols.
- Do not describe batch2 as a fully independent data-generation batch unless payloads are regenerated.
- Do not describe the protocol-family policy as formal preregistration without an earlier timestamped record.

## Paper Structure Recommendation

1. Introduction
- Position the work as federated attack detection under poisoning, with congestion-aware inductive bias as a secondary mechanism.

2. Threat Model and Problem Setup
- Distinguish between centralized OOD evaluation and federated poisoned aggregation.

3. Data Collection and Protocol Families
- Keep both protocol families in the paper.
- Treat the traditional family as a required negative-result boundary condition.
- Treat the congestion family as the mechanism-sensitive setting.

4. Main Results
- Lead with federated robust aggregation.
- Then present the congestion-family physics result.
- Move the traditional-family non-significant central results earlier than the appendix, but keep them concise.

5. Ablation and Runtime
- Use the congestion-family ablation to argue why the gain is due to the physics loss rather than context-only features.
- Include runtime overhead and robustness-cost tradeoffs.

6. Limitations
- State that current results come from a controlled Mininet-style environment.
- State that batch2 is an independent capture batch reusing the same payload pool unless that is changed.

## Supplemental Federated Baselines To Add

The repository now has support for the following classic robust aggregation baselines in `fed_pignn.py`:
- `krum`
- `multi_krum`
- `bulyan`
- `rfa`

Why these baselines matter:
- `Krum` is the canonical Byzantine-robust aggregation baseline for distributed learning.
- `Bulyan` is a stronger follow-up that explicitly addresses hidden vulnerability in Byzantine-resilient aggregation.
- `RFA` (geometric median / robust aggregation for FL) is a widely used federated robust baseline.

Primary sources:
- Blanchard et al., "Machine Learning with Adversaries: Byzantine Tolerant Gradient Descent", NeurIPS 2017.
  https://arxiv.org/abs/1703.02757
- Mhamdi et al., "The Hidden Vulnerability of Distributed Learning in Byzantium", ICML 2018.
  https://arxiv.org/abs/1802.07927
- Pillutla et al., "Robust Aggregation for Federated Learning", TMLR 2022.
  https://arxiv.org/abs/1912.13445

## Important Experimental Note

Classic Byzantine baselines should not be forced into the current `3-client` main suite:
- `Krum` requires `n > 2f + 2`.
- `Bulyan` requires `n >= 4f + 3`.

Therefore:
- Keep the existing `3-client` suite as the main historical result path.
- Run classic robust baselines as a supplemental suite with more clients, using `run_fed_classic_robust_baselines.py`.

## Writing Deliverable

The recommended paper wording has now been materialized in:
- `/home/user/FedSTGCN/top_conf_suite_recharge/paper_ready_plus/PAPER_WRITING_DRAFT.md`

That draft contains:
- title candidates
- an abstract draft
- contribution bullets
- introduction/result-section wording
- safe vs unsafe claim language

Use that file as the direct writing baseline rather than treating this note as the final manuscript text.
