# BlockSys 14-Page Paper Outline

This file fixes a writeable, page-budget-aware outline for the final BlockSys submission.

As of `2026-03-24`, the official `BlockSys 2026` call for papers states that submissions must use the `Springer LNCS` one-column format and must not exceed `14` pages. Because the call does not explicitly state that references are excluded from the limit, this outline assumes the full paper, including references, must fit within the same `14`-page cap.

Official source:
- https://blocksys.info/2026/call-for-papers/

## Core Principle

Do not try to turn the paper into a broad benchmark survey. The strongest BlockSys version is still the shortest coherent evidence chain:

1. weak supervision under conditional shift creates deployment-costly benign false positives;
2. CDRO-UG addresses that with uncertainty-guided conditional robustness and asymmetric trust;
3. the strongest supported gain is the `external-J` pooled `FPR` reduction;
4. the system-level translation is frozen-threshold benign alert-burden reduction;
5. the mechanism is supported by non-uniform prioritization, asymmetric trust, and benign FP source decomposition;
6. the boundary is explicit rather than hidden.

## Hard Page Budget

Target about `13.6` pages total content so the final PDF still has a small layout buffer.

| Part | Target pages | Notes |
|---|---:|---|
| Abstract | 0.35 | one compact paragraph |
| 1. Introduction | 1.50 | problem, gap, contribution |
| 2. Related Work and Problem Setting | 0.95 | keep short |
| 3. Method | 2.40 | includes Figure 1 |
| 4. Experimental Setup | 1.15 | only essentials |
| 5. Main Results | 3.05 | includes Table 1, Figure 2, Table 2 |
| 6. Mechanism Analysis | 1.85 | includes Figure 3, Figure 4, and a compact mechanism paragraph |
| 7. Boundary, Limitations, and Discussion | 0.95 | short but necessary |
| 8. Conclusion | 0.35 | two short paragraphs |
| References | 1.00 | keep concise |
| Total | 13.60 | leaves about 0.40 page buffer |

## Recommended Final Outline

### Abstract

The abstract should do only four jobs:

1. define the problem as weak supervision under conditional shift;
2. name the method as `CDRO-UG`;
3. report the strongest supported result on `external-J`;
4. translate that result into frozen-threshold alert-burden reduction with an explicit tradeoff sentence.

### 1. Introduction

#### 1.1 Weak supervision under conditional shift

State that weak labels are structured and unevenly reliable rather than uniform random noise.

#### 1.2 Why pooled F1 is insufficient for trustworthy deployment

Explain that benign false-positive escalation matters as much as pooled accuracy in a deployed security system.

#### 1.3 Our approach and scoped contributions

Keep the contribution list narrow:

1. method contribution;
2. scoped empirical contribution on `external-J`;
3. mechanism contribution;
4. boundary and reproducibility contribution.

### 2. Related Work and Problem Setting

#### 2.1 Weak supervision and noisy-label learning

Use one compact paragraph on classical work plus one short frontier sentence on conditional DRO for noisy labels and learning from weak labelers as constraints.

#### 2.2 Robust learning under conditional shift

Relate the paper to DRO and group-robust learning, then add one short sentence on conformal risk control as a deployment-time complement rather than the main method here.

#### 2.3 Graph-based attack detection and paper positioning

Make the positioning explicit:

1. this is not a new graph architecture paper;
2. it is a weak-label training-stage robustness paper for graph-based attack detection.

### 3. CDRO-UG Method

#### 3.1 Overview

Place `Figure 1` here and explain both the training pipeline and the deployment reading.

#### 3.2 Weak-label aggregation and uncertainty statistics

Define only the necessary notation:
`\tilde{p}_i`, `\tilde{y}_i`, `u_i`, `a_i`, and `\rho_i`.

#### 3.3 Class-asymmetric trust

Emphasize that weak attack and weak benign evidence are not equally trustworthy.

#### 3.4 Uncertainty-guided conditional DRO objective

Keep only the core equations:

1. group construction;
2. group priority score;
3. final objective.

#### 3.5 Final locked variant

State briefly why `CDRO-UG (sw0)` is the main version:

1. no pseudo-sample expansion;
2. cleaner interpretation;
3. main result version is fixed.

### 4. Experimental Setup

#### 4.1 Data and evaluation batches

Explain:

1. the primary batch for the four core protocols;
2. `external-J` as the main shifted-batch test;
3. the other external batches as boundary evidence rather than the headline.

#### 4.2 Weak-supervision protocols

List the four protocols compactly.

#### 4.3 Baselines, metrics, and significance

Keep the main-text baseline family short and focus the metrics on `F1`, `FPR`, and deployment-transfer readouts.

#### 4.4 Implementation and reproducibility note

Use a short paragraph on schemas, split manifests, wrappers, and sanitized sample support.

### 5. Main Results

#### 5.1 Primary batch as competitiveness control

Use the source-batch part of `Table 1` and explicitly say it is not the paper headline.

#### 5.2 External-J as the strongest supported result

Use the external-J part of `Table 1` plus `Figure 2` and make the strongest supported claim here.

#### 5.3 Frozen-threshold deployment transfer

Place `Table 2` immediately after the external-J result so the paper converts the statistical gain into operator-facing benign alert-burden reduction.

### 6. Mechanism Analysis

#### 6.1 Ablation: non-uniform prioritization and asymmetric trust

Use `Figure 3` and write the two decisive mechanism rows directly into the paragraph.

#### 6.2 Weak-label audit

Use a short paragraph to justify the asymmetric trust design.

#### 6.3 False-positive source decomposition

Place `Figure 4` here and tie the gain directly to benign abstain, weak-benign, and high shift-risk regions.

### 7. Boundary, Limitations, and Discussion

#### 7.1 Multi-external and stronger-baseline boundary

One short paragraph is enough:

1. pooled external remains non-significant;
2. direction aligns only partially across scenarios;
3. stronger baselines can be competitive.

#### 7.2 Public benchmark and stress-test boundary

Use this as scope clarification, not as a second result section.

#### 7.3 Low-cost next step

Keep one sentence only:
post-hoc conformal risk control or lightweight graph shift adaptation is a credible extension, but not part of the present submission.

### 8. Conclusion

The conclusion should restate:

1. the deployment problem;
2. the mechanism;
3. the strongest supported result;
4. the operating boundary.

## Main-Text Figure/Table Placement

Keep only these `4` figures and `2` tables:

1. `Figure 1`: method and deployment overview
2. `Table 1`: core pooled results
3. `Figure 2`: source-vs-shift pooled overview
4. `Table 2`: frozen-threshold deployment transfer
5. `Figure 3`: mechanism probe
6. `Figure 4`: false-positive source decomposition

Compression note:

1. write the two decisive mechanism rows directly into `Section 6.1`;
2. restore only `Figure 4`, not a standalone mechanism table.

Recommended placement:

1. `Figure 1` in `Section 3.1`
2. `Table 1` and `Figure 2` in `Section 5.1-5.2`
3. `Table 2` in `Section 5.3`
4. `Figure 3` in `Section 6.1`
5. `Figure 4` in `Section 6.3`

## Keep Out of the Main Paper

Do not promote the following into the 14-page main paper:

1. full per-protocol tables;
2. detailed pooled external-4 expansion;
3. calibration and operating-point detail;
4. runtime tables;
5. hard/camouflaged suite detail;
6. stress-sweep detail;
7. public benchmark detail;
8. label-budget detail;
9. attack-family full breakdown;
10. analyst case-study visuals.

## Trimming Order If Over Page Limit

If the draft goes beyond `14` pages, cut in this order:

1. shorten Section 2 first;
2. compress Section 7 into two short subsections;
3. reduce the weak-label audit paragraph;
4. compress Section 6.3 into half a paragraph before touching `Table 2`;
5. never cut the `external-J` headline or the frozen-threshold deployment reading.

## One-Sentence Read

If written according to this outline, the paper will read like a mature BlockSys submission: system-motivated, method-focused, evidence-disciplined, and explicit about its operating boundary.
