# Safe Claims And Limitations

## 1. Paper positioning

This paper should now be positioned as:

- a mechanism-oriented weak-supervision paper
- about noisy labels under conditional shift
- with the most reliable gain appearing in benign false-positive control
- not as a universal robust learner for arbitrary noisy-label regimes

The central message should be:

> Under multi-view weak supervision and conditional label shift, an uncertainty-guided conditional DRO objective can reduce benign false positives in external shifted settings, and this gain is tied to non-uniform group prioritization and class-asymmetric trust.


## 2. What the paper can safely claim

### Safe Claim A

CDRO-UG (sw0) shows its strongest evidence on the external-J batch2 evaluation, where pooled FPR is lower than Noisy-CE with statistically significant paired evidence.

Use this wording:

- "The most stable gain appears on the external shifted batch, where CDRO-UG reduces benign false positives relative to Noisy-CE."
- "The improvement is concentrated in false-positive suppression rather than universal pooled F1 gains."

Do not use this wording:

- "CDRO-UG significantly outperforms Noisy-CE across datasets."
- "CDRO-UG consistently improves all metrics."


### Safe Claim B

The mechanism evidence is stronger than the global performance headline.

Use this wording:

- "Ablation results show that non-uniform group prioritization is necessary."
- "Weak-label audit and trust ablation support a class-asymmetric trust design."
- "False-positive decomposition shows that the gain comes mainly from benign abstain / weak-benign regions."

Do not use this wording:

- "Every part of the method is necessary."
- "The full method is uniformly superior because of better calibration."


### Safe Claim C

The method works best in the specific regime it was designed for: covered-only weak supervision, moderate label noise, and benign false-positive suppression under conditional shift.

Use this wording:

- "The method is most effective when weak labels are available but imperfect, rather than adversarially flipped at high rates."
- "The design primarily improves benign-side decision control."


### Safe Claim D

Under the current CPU-only setting, the locked raw sw0 version does not impose a meaningful runtime penalty relative to Noisy-CE, and its frozen-threshold external-J transfer preserves the lowest false-positive rate while also reducing benign alert burden, with an explicit F1 / delay tradeoff.

Use this wording:

- "The supplemental runtime table shows that CDRO-UG remains in the same computational regime as Noisy-CE."
- "Full-graph forward latency differs only slightly from the baseline under CPU-only evaluation."
- "With thresholds frozen from the main batch, CDRO-UG preserves the lowest external-J FPR and lowers benign alert burden, but this comes with lower F1 and slightly slower / less complete first alerts."

Do not use this wording:

- "The method is faster in general."
- "The runtime advantage is significant across hardware settings."
- "Frozen-threshold transfer improves every deployment metric at once."


### Safe Claim E

The supplemental public and reference experiments strengthen paper completeness, but they narrow rather than broaden the headline.

Use this wording:

- "A compact public HTTP benchmark shows that CDRO-UG remains competitive on a reproducible public dataset, but not universally best."
- "Label-budget and non-graph / clean-label reference experiments clarify when the method is usable and how far it remains from the clean-label ceiling."
- "Deployment-oriented checks, family breakdowns, and analyst-facing case studies explain the operating-point tradeoffs and where the method helps most."
- "A lightweight reproducibility package improves artifact transparency even though the full private captures are not released."

Do not use this wording:

- "The public benchmark proves state-of-the-art performance."
- "The public benchmark shows the best calibration."
- "CDRO-UG is the most label-efficient method across supervision budgets."
- "Graph structure is always better on every deployment metric."
- "The analyst-facing cases prove the mechanism by themselves."


## 3. What the paper should explicitly admit

These points should be in the paper, not hidden:

1. Main pooled result vs Noisy-CE is not significant.
2. External-4 pooled result vs Noisy-CE is not significant on F1/FPR, and pooled ECE/Brier are worse.
3. Strong noisy-label baselines show that raw sw0 is not uniformly best on pooled FPR.
4. Calibration is not universally improved.
5. Operating-point analysis does not strengthen the main claim.
6. Hard/camouflaged protocols do not yield a new significant headline result; after corrected merged pairing, the combined pooled delta is near zero.
7. Flip-noise stress shows a clear weakness of raw sw0.
8. Coverage loss is less harmful than wrong-label corruption, but the gain is still limited.
9. The compact public benchmark is competitive, but not a universal win on F1/FPR or calibration.
10. Label-budget sweeps do not show a universal low-budget advantage for CDRO-UG.
11. On external-J, XGBoost(weak) trades lower FPR for noticeably lower F1.
12. The clean-label PI-GNN upper bound remains substantially higher than every weak-label method.
13. Frozen-threshold transfer improves external-J FPR, but it also lowers attack-IP coverage and worsens mean first-alert delay.
14. `Burst` remains the hardest attack family across all compared methods.


## 4. How to convert negative results into boundaries

### Boundary 1: Not a universal noisy-label method

Write:

- "The proposed mechanism is not intended to dominate all noisy-label baselines under all corruption patterns."
- "Its advantage is regime-specific: weak supervision with structured uncertainty and conditional shift."


### Boundary 2: Robust to missing labels more than wrong labels

Write:

- "The method is relatively stable under weak-label coverage loss, but it degrades under aggressive flip-noise corruption."
- "This suggests that the current design is better suited to incomplete weak supervision than to adversarially wrong weak labels."


### Boundary 3: Mechanism-first, headline-second

Write:

- "The strongest contribution of the paper is the mechanism: uncertainty-guided prioritization plus asymmetric trust."
- "The strongest empirical headline is a scoped external FPR result rather than broad universal superiority."


### Boundary 4: Benign-side control, not calibration

Write:

- "The primary deployment-oriented value lies in benign false-positive suppression."
- "Calibration results are reported for completeness, but they are not the main source of improvement."


### Boundary 5: Useful public/reference evidence, but not new headline evidence

Write:

- "The public HTTP benchmark and label-budget analyses are primarily for reproducibility and scope clarification."
- "The non-graph baseline and clean-label upper bound are reference points, not replacement headline claims."


## 5. Recommended contribution bullets

Use contribution bullets like these:

1. We formulate weakly supervised attack detection under conditional shift as a conditional robustness problem, where the main deployment risk is benign false-positive escalation.
2. We propose an uncertainty-guided conditional DRO objective that combines non-uniform group prioritization with class-asymmetric trust over weak labels.
3. We show that the strongest empirical benefit appears in external shifted evaluation through benign false-positive suppression, while ablations and weak-label audits explain when this gain appears.
4. We supplement the controlled captures with a public HTTP sanity benchmark, supervision-budget sweeps, and non-graph / clean-label reference points to clarify reproducibility, label efficiency, and remaining supervision headroom.
5. We add deployment-oriented frozen-threshold checks, pooled attack-family breakdowns, analyst-facing case studies, and a lightweight reproducibility package so the paper addresses operating-point tradeoffs, family-specific behavior, and artifact transparency directly.
6. We document the method boundary: the current design is more tolerant to weak-label coverage loss than to severe flip-noise corruption.


## 6. Recommended abstract-safe wording

Below is a safe English abstract-style paragraph:

> Weakly supervised attack detection often relies on imperfect heuristic labels whose reliability varies across regions of the data, especially under conditional shift. We study this setting in spatiotemporal graph-based attack detection and propose an uncertainty-guided conditional DRO objective that combines non-uniform group prioritization with class-asymmetric trust over weak labels. Across four weak-supervision protocols, the proposed method is most effective in reducing benign false positives on an external shifted batch, while pooled F1 remains broadly comparable to standard weak-label baselines. A compact public HTTP benchmark shows competitive public-data performance with improved calibration, and additional label-budget plus non-graph / clean-label reference experiments clarify both usability under sparse supervision and the remaining gap to full supervision. We further report boundary conditions: the current design is more stable under weak-label coverage loss than under heavy flip-noise corruption.


## 7. Recommended result-section wording

Use wording of this kind:

- "We first emphasize that the pooled main-batch improvement is small and not statistically significant."
- "The most reliable positive result appears on the external shifted batch, where CDRO-UG reduces benign false positives."
- "The evidence is therefore stronger for scoped deployment risk control than for broad universal accuracy gains."
- "Mechanism analysis is essential here because the aggregate performance headline alone would understate why the method helps."
- "The public benchmark, budget sweep, and reference baselines should be read as scope-defining evidence rather than as broader replacement headlines."
- "The frozen-threshold deployment readout should be presented as a tradeoff: lower external-J FPR in exchange for slightly worse attack-IP coverage / delay."


## 8. Recommended limitations section

Use a limitations paragraph like this:

> Our results indicate that the current CDRO-UG design is regime-specific rather than universally dominant. While it can reduce benign false positives under external conditional shift, it does not consistently outperform stronger noisy-label baselines on pooled metrics; the pooled external-4 validation is non-significant on F1/FPR and shows worse ECE/Brier, the compact public benchmark is competitive but not a universal win, the label-budget sweep does not reveal universal low-budget dominance, the frozen-threshold deployment transfer trades lower external-J FPR for weaker attack-IP coverage / delay, and the hard/camouflaged combined suite is effectively near-tied after corrected merged pairing. The method is therefore better viewed as a mechanism for structured weak-supervision settings with uncertainty heterogeneity than as a general-purpose defense against arbitrary label noise. Future work should redesign the trust mechanism for adversarially wrong weak labels rather than only incomplete or moderately noisy supervision.


## 9. Claims to ban during writing

Never write any of the following:

- "significantly better across all settings"
- "universally improves weak-label learning"
- "robust to noisy labels in general"
- "stronger calibration across datasets"
- "best among all robust noisy-label baselines"
- "validated across all external batches with significant gains"


## 10. Practical writing order

The safest paper structure now is:

1. Lead with the scoped problem: weak supervision + conditional shift + benign false-positive risk.
2. Present the external-J FPR result as the strongest positive evidence.
3. Immediately follow with mechanism evidence.
4. Put external-4, strong baselines, hard suite, and operating-point analysis into appendix-facing support.
5. Move noise sweep into limitations, not into the positive-results narrative.
