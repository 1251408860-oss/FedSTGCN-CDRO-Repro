# CDRO Paper-Ready Plus

## Locked safe claim
- This paper should be presented as a scoped weak-supervision / noisy-label / conditional-shift result, not as a universal noisy-label learner.
- The safest positive evidence is the external-J (`batch2` high-load) pooled false-positive reduction of CDRO-UG (sw0) against Noisy-CE: delta FPR = -0.043630, p = 0.0051.
- The safest wording is that the rewritten UG can reduce benign false alarms under specific external condition shift, while pooled F1 usually stays close to the baseline.

## Mechanism readout
- Main probe: replacing non-uniform weighting with uniform weighting hurts pooled F1 (delta = -0.004083, p = 0.0149).
- Batch2 probe: lowering benign trust to 0.35 hurts pooled FPR (delta = +0.011855, p = 7.32e-04).
- FP-source analysis: the robust gain comes mainly from benign `abstain` and `weak_benign` regions, especially in `weak_attack_strategy_ood`.
- Weak-label audit supports asymmetric trust: weak_attack precision is consistently much higher than weak_benign precision.

## Practicality readout
- CPU-only runtime benchmarking shows no meaningful efficiency penalty for the locked raw sw0 version.
- Main: CDRO-UG full-graph forward latency is 72.58 ms versus 72.30 ms for Noisy-CE, with lower end-to-end wall time (2.27 s versus 2.52 s).
- Batch2: CDRO-UG full-graph forward latency is 53.17 ms versus 51.58 ms for Noisy-CE, again with slightly lower end-to-end wall time (2.19 s versus 2.27 s).
- Deployment-oriented frozen-threshold transfer on external-J keeps the lowest mean FPR for CDRO-UG (0.096 versus 0.168 for Noisy-CE) and also the lowest benign alert burden (36.1 versus 63.4 false alerts per run; 958 versus 1676 per 10k benign nodes), but this comes with lower mean F1 (0.860 versus 0.874) and slightly worse attack-IP detection coverage / delay; this tradeoff should be reported directly rather than hidden.

## Completeness readout
- Scenario-wise external consistency is now explicit: under tuned thresholds, `CDRO-UG(sw0)` lowers `FPR` in `3/4` external scenarios (`J/K/L`), with the strongest support still on `J`; `K` is smaller paired support, `L` is directional only, and `I` reverses.
- Public HTTP benchmark on `Biblio-US17` is now completed: train weak-label coverage is `94.6%`, both train-covered weak attack / weak benign precision are `1.000`, and the final artifact chain is populated under `public_http_biblio_us17_s3_v1`.
- This new public benchmark should still be read as a sanity check rather than as a headline result: `Noisy-CE` has the highest mean F1 (`0.842`), while `CDRO-UG(sw0)` is only directionally lower on mean FPR (`0.023` versus `0.025`, `p = 1.0`) and is slightly worse on mean ECE / Brier.
- Label-budget sweeps on main + external-J show CDRO-UG remains viable at 5-10% weak-label budget, but do not support a universal low-budget dominance claim.
- Non-graph / clean-label reference experiments show that XGBoost(weak) trails the weak-label graph family on pooled F1, while PI-GNN(clean) remains far above all weak-label methods and therefore defines a clear supervision ceiling.
- Per-attack-family breakdown pooled over all four protocols shows that `burst` remains the hardest family, while on external-J CDRO-UG achieves the lowest pooled FPR for `slowburn` and `mimic`.
- Analyst-facing case studies make the mechanism concrete with one benign false positive suppressed, one slowburn true positive recovered, and one mimic true positive preserved despite a misleading weak-benign label.
- A lightweight reproducibility package now names the released schema files, protocol split manifests, replay wrappers, and sanitized sample slice explicitly for artifact release.

## Boundaries that must stay explicit
- Main pooled result against Noisy-CE is not significant.
- Pooled external-4 validation is not significant against Noisy-CE on F1/FPR, and its pooled ECE/Brier are worse after corrected merged pairing.
- The new scenario-wise external consistency evidence is only partial: `3/4` FPR directions align, but `External-I` reverses and pooled external remains non-significant.
- Strong noisy-label baselines show that raw sw0 is not uniformly best on pooled FPR.
- Calibration and operating-point analysis do not provide a stronger headline than the external-J FPR result.
- Hard/camouflaged protocols are stress-test supplements; after corrected merged pairing, the combined pooled delta is near zero rather than a meaningful advantage.
- Flip-noise stress hurts raw sw0; this is a real limitation, not something to hide.
- The completed `Biblio-US17` public benchmark is not a positive headline for CDRO-UG: `Noisy-CE` is stronger on mean F1 and slightly better on mean ECE / Brier, while the mean FPR gap is tiny and non-significant.
- Label-budget curves do not show a universal label-efficiency advantage for CDRO-UG.
- On external-J, XGBoost(weak) attains lower pooled FPR than CDRO-UG only by accepting a materially lower pooled F1; this tradeoff should be stated explicitly.
- The clean-label PI-GNN upper bound remains substantially better than every weak-label method, so current weak supervision is still far from the clean-label ceiling.
- Frozen-threshold deployment transfer lowers external-J FPR for CDRO-UG, but it also reduces F1 and slightly worsens attack-IP coverage / first-alert delay.
- `Burst` remains the hardest attack family across all compared methods, so the family breakdown should be discussed as a boundary, not as uniform family-wise improvement.

## Recommended paper usage
- Main text: Fig. 1 (`fig_method_overview.svg`), Table 1 (`table_maintext_core_results.csv`), Fig. 2 (`fig1_pooled_results.png`), Table 2 (`table_maintext_deployment_transfer.csv`), Fig. 3 (`fig2_mechanism_probe.png`), and Fig. 4 (`fig3_fp_sources.png`).
- Appendix / reviewer-facing robustness: full protocol tables, significance sheets, supplemental baselines, runtime, calibration, operating points, hard-suite stress tables, public benchmark, label budget, non-graph references, family breakdown, analyst case studies, and `reproducibility_package.md`.
- Numbering rule: do not expose asset numbering such as `Table 18` or `Fig. 10` in the main paper.
- Reviewer alignment guide: `CONTRIBUTION_EVIDENCE_MAP.md`.
- Claim-shrinking guide: `SAFE_CLAIMS_AND_LIMITATIONS.md`.
