# BlockSys Pre-Submission Checklist

Use this file for the last pass before converting the draft into the final BlockSys submission.

## 1. Core positioning

- Frame the paper as a trustworthy deployment / benign false-positive control paper, not as a universal noisy-label learner.
- Keep the main positive claim anchored to `external-J` plus the frozen-threshold deployment readout.
- Keep the mechanism story stronger than the broad performance story.

## 2. Abstract checks

- Mention `conditional shift`, `benign false positives`, and `trustworthy deployment` or `alert burden`.
- Report the strongest supported result:
  `external-J` pooled FPR `0.2695 -> 0.2259`, `delta = -0.043630`, `p = 0.0051`.
- Mention the frozen-threshold alert-burden reduction:
  `63.4 -> 36.1` false alerts per run, or `1676 -> 958` per `10k` benign nodes.
- Include the tradeoff sentence:
  lower alert burden / FPR is not free; there is an F1 / delay / coverage tradeoff.

## 3. Contribution checks

- Include at least one deployment-oriented contribution, not only an algorithm bullet.
- Include at least one scoped empirical contribution tied to `external-J`.
- Include at least one mechanism contribution:
  non-uniform prioritization, asymmetric trust, or benign-region error decomposition.
- Include at least one scope / boundary / reproducibility contribution.

## 4. Main-results checks

- Describe the primary-batch table as a competitiveness control, not as the headline win.
- Describe the external-J table as the strongest result because it reduces benign false alarms under changed conditions.
- Translate the deployment table into analyst-facing burden:
  false alerts per run, false alerts per `10k` benign nodes, and frozen-threshold tradeoff.
- If the appendix discusses all four external scenarios, write the safe sentence:
  tuned-threshold `FPR` direction aligns in `3/4` scenarios, strongest on `J`, smaller on `K`, directional on `L`, reversed on `I`, and pooled external remains non-significant.
- Describe external-4, strong-baseline, hard-suite, and stress-sweep sections as boundaries or reviewer-facing evidence.
- Use only `Table 1-2` and `Figure 1-4` in the main paper; move all asset-style numbering to the appendix package.
- Do not leave `Table 18`, `Table 19`, or `Fig. 10` in the body text.
- Put a method/deployment overview figure in the main paper before the result figures.

## 5. Artifact and appendix checks

- Name the released reproducibility items concretely:
  `schema/graph_schema.json`, `schema/weak_label_sidecar_schema.json`, `protocol_split_manifests/main_protocol_splits.json`, `protocol_split_manifests/external_j_protocol_splits.json`, the wrapper scripts, and `sample/sanitized_node_slice.json`.
- Describe the reproducibility package as transparency and replay support, not as a full raw-data release.
- Keep the artifact paragraph appendix-facing if page pressure is high, but make sure the main paper still states that the package contains schemas, split manifests, replay wrappers, and a sanitized sample.

## 6. Must-keep numbers

- `external-J` pooled FPR:
  `Noisy-CE = 0.2695`, `CDRO-UG = 0.2259`, `delta = -0.043630`, `p = 0.0051`.
- Frozen-threshold `external-J`:
  `FPR = 0.168 -> 0.096`,
  `mean false alerts per run = 63.4 -> 36.1`,
  `alerts per 10k benign = 1676 -> 958`.
- Frozen-threshold tradeoff:
  `F1 = 0.874 -> 0.860`,
  `attack-IP detect rate = 0.990 -> 0.978`,
  `mean delay = 0.58 -> 0.88`.
- Scenario-wise external appendix:
  `External-I` reverses,
  `External-J` is the strongest supported FPR drop,
  `External-K` has smaller paired support,
  `External-L` is directional only,
  pooled external remains non-significant.
- Public benchmark boundary:
  `Noisy-CE` has higher mean F1 than `CDRO-UG`; do not invert this.

## 7. Hard bans

Do not write any of the following unless the sentence is rewritten first:

- `state-of-the-art`
- `SOTA`
- `universal`
- `consistently outperforms`
- `across datasets`
- `improves all metrics`
- `deployment-ready`
- `best calibration`
- `robust to arbitrary noisy labels`
- `general-purpose noisy-label defense`

## 8. Safe replacements

- Replace `better overall performance` with `lower benign false-positive rate under external shift`.
- Replace `real-world robustness` with `scoped deployment-oriented benefit under conditional shift`.
- Replace `better practical utility` with `lower analyst-facing benign alert burden under frozen thresholds`.
- Replace `superior method` with `mechanism-oriented method with a clear operating regime`.
- Replace `generalizes across external settings` with `shows partial scenario-wise external consistency, while pooled external remains non-significant`.

## 9. Consistency grep pass

Before submission, search the final draft and cover letter for:

- `state-of-the-art`
- `universal`
- `consistently`
- `all metrics`
- `best calibration`
- `deployment-ready`

Every match should be deleted or rewritten into a scoped claim.

## 10. Final narrative order

- Lead with the problem:
  weak supervision under conditional shift can create deployment-costly benign false alarms.
- Then state the mechanism:
  uncertainty-guided conditional robustness plus asymmetric trust.
- Then state the strongest result:
  external-J pooled FPR reduction.
- Then convert it into an operator-facing readout:
  lower frozen-threshold alert burden.
- Then state the boundary:
  not universal, not uniformly strongest, and weaker under heavy flip noise.
- Final display order:
  `Figure 1`, then `Table 1` + `Figure 2`, then `Table 2`, then `Figure 3` + `Figure 4`, with the compact mechanism numbers still kept in prose rather than in a standalone mechanism table.

## 11. Page-budget frontier rule

- Do not add a new experiment block, table, or figure just to show awareness of frontier literature.
- If page pressure is high, keep frontier positioning to:
  one sentence on recent imperfect-supervision methods,
  one sentence on conformal deployment risk control,
  and one sentence on future low-cost extensions.
- Preferred minimal citation set under page pressure:
  Guo et al. (NeurIPS 2024),
  Agrawal et al. (ICLR 2025),
  Angelopoulos et al. (ICLR 2024),
  Farinhas et al. (ICLR 2024),
  Trivedi et al. (ICLR 2024),
  Bao et al. (ICLR 2025).
