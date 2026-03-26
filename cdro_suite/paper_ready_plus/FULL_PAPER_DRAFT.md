# Uncertainty-Guided Conditional Robustness for Weakly Supervised Spatiotemporal Graph Attack Detection

Authors: [Author Names]  
Affiliations: [Affiliations]  
Corresponding Author: [Email]  

## Abstract

Weakly supervised attack detection often relies on heuristic labels whose reliability varies sharply across data regions, especially under conditional shift. We study this problem in spatiotemporal graph-based security analytics and frame it as an AI-driven trustworthy systems problem: the critical failure mode is benign alert escalation under shift, not only pooled accuracy loss. To address this setting, we propose CDRO-UG, an uncertainty-guided conditional distributionally robust objective that combines non-uniform group prioritization with class-asymmetric trust over weak labels. Across four weak-supervision evaluation protocols, the method does not deliver a universal pooled-F1 gain over standard weak-label baselines. Its strongest supported result instead appears on an external shifted batch, where pooled false-positive rate drops from `0.2695` to `0.2259` relative to Noisy-CE (`delta = -0.043630`, `p = 0.0051`) while pooled F1 remains comparable. Under source-locked thresholds, the same model further reduces mean benign false alerts from `63.4` to `36.1` per run, or from `1676` to `958` per `10k` benign nodes, at a measurable F1 / first-alert-delay tradeoff. Mechanism analysis shows that this gain depends on retaining non-uniform prioritization and on assigning higher trust to weak attack labels than to weak benign labels. Public HTTP benchmarking, supervision-budget sweeps, non-graph / clean-label references, deployment-oriented analyses, and a lightweight reproducibility package are used to define the method boundary rather than to inflate the headline. These results position CDRO-UG as a deployment-oriented mechanism for trustworthy graph-based detection under conditional shift, rather than as a universal defense against arbitrary noisy labels.

## 1. Introduction

Weak supervision is increasingly used to train attack detection systems when precise labels are expensive, delayed, or partially unavailable. In practice, however, weak labels are not only noisy but also unevenly reliable across the data: some regions are covered by relatively trustworthy attack indicators, whereas others are dominated by ambiguous benign-side heuristics, abstentions, or partial agreement across weak views. This heterogeneity becomes especially problematic under conditional shift, where a deployed detector trained to fit average weak-label behavior can overreact to uncertain regions and produce deployment-costly benign false positives. For trustworthy security systems, this failure mode matters as much as pooled accuracy, because a detector that over-flags benign traffic under shift can be operationally unusable even when its global F1 remains competitive.

These observations suggest that weak supervision under shift should not be treated only as a generic noisy-label problem. Instead, the training objective should account for where weak supervision is uncertain, how disagreement is distributed across groups, and whether weak attack and weak benign evidence deserve the same level of trust. Motivated by this view, we study weakly supervised spatiotemporal graph attack detection through the lens of conditional robustness. Our goal is not to claim a universal learner that dominates all noisy-label baselines, but to design a trustworthy detection mechanism that focuses training pressure on uncertain groups while controlling benign-side false positives when weak supervision is structured but imperfect.

Most existing weak-supervision and noisy-label methods are optimized primarily for average predictive quality [CITE]. However, attack detection under operational shift introduces a different emphasis: the most expensive failure mode may not be a modest drop in pooled F1, but a surge in benign false positives in precisely those regions where heuristic supervision is weak, ambiguous, or inconsistent. This makes group-aware robustness and trust-aware target construction especially relevant. In this paper, we therefore ask a narrower question than "how can we learn from noisy labels in general?": can conditional robustness be used to suppress benign-side false alarms when weak-label reliability is heterogeneous across a spatiotemporal graph?

Our results support a narrower but stronger story than a generic claim of universal noisy-label robustness. Across the main weak-supervision protocols, the proposed method is usually competitive with standard weak-label learning baselines, but its pooled advantage is modest and not uniformly significant. The clearest and most defensible improvement instead appears under external condition shift, where CDRO-UG reduces benign false positives relative to a hard-label weak-supervision baseline. This effect is not explained by simply replacing hard labels with soft posteriors, nor by prior correction alone; rather, it is tied to the conditional robustness design itself. We therefore position this paper as a mechanism-oriented study of weak supervision under conditional shift: its primary contribution is not universal average-case accuracy gains, but a principled way to prioritize uncertain groups and to treat weak attack and weak benign evidence asymmetrically in order to improve benign-side risk control.

Our main contributions are:

1. We formulate weakly supervised attack detection under conditional shift as a trustworthy system security problem, where the main operational risk is benign false-positive escalation and analyst alert burden rather than only pooled accuracy loss.
2. We propose CDRO-UG, an uncertainty-guided conditional DRO pipeline that combines non-uniform group prioritization with class-asymmetric trust over weak labels, while keeping the final locked version free of pseudo-sample expansion.
3. We show that the strongest empirical gain appears on an external shifted batch: CDRO-UG lowers pooled FPR with paired significance and, under frozen source thresholds, further reduces benign alert burden in operator-facing terms.
4. We connect that gain to mechanism evidence rather than to headline-only comparisons: ablations, weak-label audit, and benign-region error decomposition show that the effect depends on uncertainty-aware prioritization and asymmetric trust.
5. We complement the controlled captures with deployment-oriented readouts, a public HTTP benchmark, reference-baseline studies, and a lightweight reproducibility package, so the paper directly addresses comparability, transparency, and operating-boundary questions.
6. We explicitly document the method boundary: the design is most appropriate for covered-only weak supervision with moderate structured noise, and it is less effective under adversarially wrong weak labels.

## 2. Related Work

### 2.1 Weak Supervision and Noisy Labels

Weak supervision has become a practical alternative to fully supervised labeling in domains where annotation is expensive or delayed [CITE]. Existing methods often aggregate multiple heuristic signals into pseudo-labels, posterior targets, or confidence-weighted supervision. A large body of work on noisy-label learning then focuses on robust losses, sample selection, correction matrices, and consistency regularization [CITE]. These approaches are valuable for improving average predictive quality under corruption, but they usually treat label noise as a global phenomenon rather than as a conditionally heterogeneous one.

Our setting differs in an important way. Weak-label quality is not uniformly bad across the graph. Instead, the supervision is structured: some regions are associated with relatively precise weak attack evidence, while others are dominated by noisy or abstaining benign-side heuristics. This means that the central question is not only how to fit noisy supervision, but how to allocate learning pressure when weak-label reliability and deployment cost vary across groups. Recent work has started to move in related directions through conditional DRO for noisy labels [Guo et al., NeurIPS 2024] and constraint-based learning from weak labelers with explicit error bounds [Agrawal et al., ICLR 2025], but these methods do not target the deployment-costly benign alert escalation problem in weakly supervised spatiotemporal graph detection.

### 2.2 Robust Learning under Distribution Shift

Distributionally robust optimization and group-robust learning aim to improve worst-group or minority-group performance under shift-sensitive settings [CITE]. Prior work shows that group-aware training can outperform purely average-risk objectives when errors are concentrated on certain subpopulations. Our method is related to this literature, but differs in both its group construction and its objective. We do not assume semantic demographic groups; instead, groups are induced from uncertainty and shift-related proxies derived from weak supervision. Moreover, our aim is not generic worst-group accuracy, but operational benign false-positive control under conditional shift.

Recent conformal risk control methods [Angelopoulos et al., ICLR 2024; Farinhas et al., ICLR 2024] are also relevant from a deployment perspective because they provide post-hoc ways to control task-specific risk under shift. Our paper is complementary rather than redundant: we change the training objective so that the learned detector produces a better benign-side error profile before any later threshold-control layer is applied.

### 2.3 Graph-Based Attack Detection

Graph neural networks and spatiotemporal graph models have been widely used for intrusion detection, traffic analysis, and network anomaly detection because they capture dependencies across communicating entities and temporal windows [CITE]. Most prior graph-based systems, however, assume standard supervised labels or focus on model architecture. Much less attention has been paid to how such models should be trained when supervision is weak, view-dependent, and unevenly reliable under shift. This paper contributes to that gap by combining weak-label uncertainty statistics with a conditional robustness objective tailored to the deployment cost of benign false positives.

This positioning is also distinct from recent reliability-focused graph work such as intrinsic GNN uncertainty estimation [Trivedi et al., ICLR 2024] and graph test-time adaptation under structure shift [Bao et al., ICLR 2025]. Those directions are important, but they operate after or around the predictor; our contribution is to reshape training itself when the supervision source is weak, asymmetric, and conditionally shifted.

### 2.4 Positioning

The most appropriate way to position this paper is at the intersection of weak supervision, robust learning under shift, and spatiotemporal graph attack detection. We do not claim a new universal noisy-label defense, nor a new graph architecture. Instead, we contribute a mechanism for deciding where robustness pressure should be placed and how weak labels should be trusted asymmetrically when the dominant deployment risk is false-positive escalation under conditional shift.

## 3. Problem Setup

We consider a spatiotemporal graph

\[
\mathcal{G} = (\mathcal{V}, \mathcal{E}, X),
\]

where each flow-window node \(i \in \mathcal{V}\) has feature vector \(x_i\), latent clean label \(y_i \in \{0,1\}\), and graph connectivity defined over spatial and temporal relations. The task is binary attack detection, where \(y_i = 1\) denotes attack and \(y_i = 0\) denotes benign traffic.

Under weak supervision, the training split does not observe all clean labels directly. Instead, each node is associated with a collection of weak-label views

\[
\{p_i^{(1)}, p_i^{(2)}, \ldots, p_i^{(M)}\},
\]

where \(p_i^{(m)} \in [0,1]^2\) is the posterior suggested by the \(m\)-th weak supervision view. These views are aggregated into:

1. a weak posterior \(\tilde{p}_i\),
2. a weak hard label \(\tilde{y}_i\),
3. a weak-label uncertainty score \(u_i\),
4. an agreement score \(a_i\),
5. additional shift-sensitive proxies such as \(\rho_i\).

We are interested in the conditional-shift regime in which the relationship between weak-label evidence and clean labels varies across groups and across evaluation batches. In particular, weak attack evidence and weak benign evidence need not have the same precision. This motivates two design goals:

1. training should emphasize groups that are more uncertain or shift-sensitive;
2. weak attack and weak benign signals should not necessarily be trusted equally.

The evaluation objective is also scoped. We report pooled predictive quality through F1, but we explicitly treat benign false-positive rate as a first-class deployment metric because a detector that over-flags benign traffic under shift can be operationally unacceptable even when pooled F1 remains competitive.

## 4. Method

### 4.1 Overview

Our method, CDRO-UG, combines three components:

1. weak-label posterior aggregation from multiple heuristic views;
2. class-asymmetric trust that converts weak posteriors into training targets;
3. uncertainty-guided conditional DRO over groups constructed from uncertainty and shift-related proxies.

Figure 1 gives the end-to-end view used by the paper. The upper half is the training pipeline: multiple weak supervision views are aggregated into posteriors, uncertainty, agreement, and shift-sensitive proxies; class-asymmetric trust converts these signals into soft targets; and conditional group construction determines where robustness pressure should be applied. The lower half is the deployment reading: the locked detector is transferred with source-tuned thresholds to an external shifted batch, and the paper evaluates the result not only through pooled F1 but also through alert burden, attack-IP coverage, and first-alert delay. This system-level framing is important because the contribution of CDRO-UG is not only a training objective, but also a trustworthy deployment strategy for weakly supervised graph-based detection under shift.

The final locked variant used in the main results is `CDRO-UG (sw0)`, which uses covered-only weak supervision, does not perform pseudo-sample expansion, and sets sample-weight amplification to zero. We choose this version because it yields the cleanest and most stable interpretation of the underlying mechanism.

### 4.2 Weak-Label Aggregation

For each training node \(i\), the weak-label views are aggregated into posterior \(\tilde{p}_i\), and the hard weak label is defined as

\[
\tilde{y}_i = \arg\max_c \tilde{p}_{i,c}.
\tag{1}
\]

We further compute weak-label uncertainty \(u_i \in [0,1]\), agreement \(a_i \in [0,1]\), disagreement \(d_i = 1 - a_i\), and a shift-sensitive proxy \(\rho_i\). These quantities summarize how uncertain, stable, and conditionally risky the weak supervision is for node \(i\).

### 4.3 Conditional Group Construction

Training nodes are partitioned into conditional groups according to uncertainty and shift sensitivity. In the final implementation, nodes are grouped by thresholding \(u_i\) and \(\rho_i\) at training-set medians, producing four groups:

\[
g_i \in \{0,1,2,3\}.
\]

These groups correspond to low/high uncertainty and low/high shift sensitivity. The grouping is not meant to be semantic; it is meant to expose heterogeneity in weak-label quality and deployment risk.

### 4.4 Class-Asymmetric Trust

The key trust observation is that weak attack labels and weak benign labels may have systematically different quality. Let \(c_i\) denote a posterior-confidence statistic. The trust score is defined asymmetrically:

\[
t_i =
\begin{cases}
\alpha_{\mathrm{atk}} \, f_{\mathrm{atk}}(a_i, c_i), & \tilde{y}_i = 1, \\
\alpha_{\mathrm{ben}} \, f_{\mathrm{ben}}(a_i, c_i, u_i), & \tilde{y}_i = 0,
\end{cases}
\tag{2}
\]

where \(\alpha_{\mathrm{atk}}\) and \(\alpha_{\mathrm{ben}}\) are global trust coefficients and \(f_{\mathrm{atk}}, f_{\mathrm{ben}}\) are monotone scaling functions. In practice, benign trust is intentionally lower and is further discounted when uncertainty is high.

The final soft target used for training is then

\[
q_i = t_i \cdot \mathrm{onehot}(\tilde{y}_i) + (1-t_i)\tilde{p}_i.
\tag{3}
\]

This interpolation preserves probabilistic supervision while allowing the model to rely more strongly on relatively trustworthy attack-side evidence than on more ambiguous benign-side evidence.

### 4.5 Uncertainty-Guided Conditional DRO

Let \(\ell_i\) denote the per-sample soft cross-entropy loss against target \(q_i\). The base loss over covered training nodes is

\[
\mathcal{L}_{\mathrm{base}}
=
\frac{1}{|\mathcal{I}|}\sum_{i \in \mathcal{I}} \ell_i.
\tag{4}
\]

For each group \(g\), we define

\[
\mathcal{L}_g = \frac{1}{|\mathcal{I}_g|}\sum_{i \in \mathcal{I}_g}\ell_i.
\tag{5}
\]

Unlike a fixed worst-group objective, CDRO-UG assigns each group a priority score based on both loss and uncertainty signals:

\[
\pi_g
=
\lambda_{\mathrm{loss}}\mathcal{L}_g
\;+\;
\lambda_u \bar{u}_g
\;+\;
\lambda_d \bar{d}_g,
\tag{6}
\]

where \(\bar{u}_g\) and \(\bar{d}_g\) are the group-wise mean uncertainty and disagreement. Group weights are then computed via a temperature-controlled softmax:

\[
w_g = \frac{\exp(\pi_g / \tau)}{\sum_{g'} \exp(\pi_{g'} / \tau)}.
\tag{7}
\]

The final training objective is

\[
\mathcal{L}_{\mathrm{CDRO\text{-}UG}}
=
(1-\lambda)\mathcal{L}_{\mathrm{base}}
\;+\;
\lambda \sum_g w_g \mathcal{L}_g.
\tag{8}
\]

The role of Eq. (8) is central: the method does not simply learn from weak labels, but reallocates robustness pressure toward conditionally risky groups defined by structured uncertainty.

### 4.6 Final Locked Variant: CDRO-UG (sw0)

Several variants were explored during development, including prior correction and stronger sample-level weighting. The final locked version used in the main paper is intentionally simpler. It uses:

1. covered-only weak supervision;
2. asymmetric trust over weak attack and weak benign labels;
3. non-uniform group prioritization;
4. no pseudo-sample expansion;
5. no additional sample-weight scaling (`sw0`).

We recommend this locked version for the paper because it yields the clearest mechanism interpretation and avoids conflating the core idea with auxiliary heuristics.

## 5. Experimental Setup

### 5.1 Data and Evaluation Batches

We evaluate the method on spatiotemporal graphs built from controlled capture batches. The primary batch is used for the main four-protocol benchmark, and an external shifted batch is used to assess whether the same weak-supervision mechanism transfers under changed operating conditions. We further include additional external batches as supplemental validation rather than as the primary headline source. To improve public reproducibility, we also build a compact public HTTP sanity benchmark from Biblio-US17 and use it only for a narrow four-method public comparison.

### 5.2 Protocols

The main evaluation uses four weak-supervision protocols:

1. weak temporal OOD;
2. weak topology OOD;
3. weak attack-strategy OOD;
4. label-prior shift OOD.

These protocols are designed to expose different forms of mismatch between the training split and the test split while preserving the practical structure of the weak-supervision problem.

### 5.3 Baselines

We compare CDRO-UG against three groups of baselines.

First, the core baselines are:

1. Noisy-CE;
2. Posterior-CE;
3. CDRO-Fixed;
4. CDRO-UG + PriorCorr.

Second, we add stronger noisy-label baselines in supplemental comparisons:

1. GCE;
2. SCE;
3. Bootstrap-CE;
4. ELR.

These baselines serve different purposes. Noisy-CE is the simplest hard-label weak-supervision baseline, Posterior-CE tests whether soft-label training alone explains the gain, CDRO-Fixed tests whether any group-robust objective is sufficient, and the stronger noisy-label baselines test whether the method remains meaningful once more sophisticated noise-robust losses are introduced.

### 5.4 Metrics and Statistical Testing

The main reported metrics are F1, recall, false-positive rate, expected calibration error, and Brier score. We prioritize false-positive rate in the main text because the method is explicitly motivated by benign-side deployment risk.

For statistical testing, we use paired sign-flip tests across matched protocol-seed runs. We report raw paired significance in the core comparison tables and include Holm and Benjamini-Hochberg corrections in supplemental material. The intended reading order is family-wise first and global correction second.

### 5.5 Supplemental Robustness Analyses

In addition to the main protocol benchmark, we report:

1. mechanism ablations;
2. weak-label quality audit;
3. false-positive source decomposition;
4. calibration and operating-point analysis;
5. runtime and efficiency benchmarking;
6. deployment-oriented frozen-threshold and first-alert checks;
7. pooled per-attack-family breakdown;
8. analyst-facing case studies;
9. hard/camouflaged protocol stress tests;
10. weak-label flip-noise and coverage-drop sweeps;
11. a compact public HTTP benchmark;
12. explicit supervision-budget curves;
13. a simple non-graph baseline and a clean-label PI-GNN upper bound.

These analyses are included to define the method boundary and to answer predictable reviewer questions, not to inflate the headline claim. Because the controlled captures cannot be fully released, we also prepare a lightweight reproducibility package that exposes the graph / weak-label interface and the replay hooks for the public or reference analyses. Concretely, the package includes `schema/graph_schema.json`, `schema/weak_label_sidecar_schema.json`, `protocol_split_manifests/main_protocol_splits.json`, `protocol_split_manifests/external_j_protocol_splits.json`, wrapper scripts for the public HTTP benchmark, label-budget sweep, non-graph / clean-label references, deployment checks, attack-family breakdown, analyst case studies, and package regeneration, plus `sample/sanitized_node_slice.json`. These artifacts support transparency and appendix replay without overstating the private-data release boundary.

### 5.6 Main-Text Display Plan

For the BlockSys submission, the paper should use a compact system-first display chain rather than the artifact-oriented numbering used in the raw result package. Figure 1 should introduce the end-to-end method and deployment pipeline. Table 1 should then be the pooled-only core results summary assembled from the primary-batch and external-J pooled rows, and Fig. 2 should visualize the same source-vs-shift comparison. Table 2 should report frozen-threshold deployment transfer on external-J so the main empirical gain is immediately translated into operator-facing burden. Fig. 3 should then summarize the two decisive mechanism probes, and Fig. 4 should show where the benign false-positive reduction actually comes from. Weak-label audit visuals, full per-protocol tables, significance sheets, the scenario-wise external consistency table, stronger-baseline tables, runtime and calibration tables, hard-suite stress tables, public benchmark checks, label-budget sweeps, non-graph references, family breakdowns, and analyst-facing case studies should be moved to the appendix.

## 6. Main Results

### 6.1 Primary-Batch Results

Table 1 summarizes the pooled primary-batch benchmark, while the full per-protocol breakdown is moved to Appendix Tables A1-A2. As shown in Table 1 and Fig. 2, CDRO-UG (sw0) remains competitive with Noisy-CE and CDRO-Fixed on pooled F1, but its pooled advantage over Noisy-CE is modest and not statistically significant. For the BlockSys-style reading of the paper, this source-batch block is best treated as a competitiveness control rather than as the main claim table. It shows that the method does not collapse on the source batch, while also making clear that the paper should not be framed as a universal pooled-accuracy improvement.

### 6.2 External Shifted-Batch Results

The clearest positive result appears in the external-J block of Table 1. From a trustworthy-systems perspective, the relevant question is not whether the method dominates pooled F1 everywhere, but whether it reduces deployment-costly benign false alarms when operating conditions change. In that shifted setting, CDRO-UG reduces pooled false-positive rate from `0.2695` to `0.2259` relative to Noisy-CE, corresponding to a delta of `-0.043630` with paired significance (`p = 0.0051`), while keeping pooled F1 broadly comparable. Fig. 2 visualizes the same pattern: the most reliable difference between the methods is not a large pooled-F1 gap, but a reduction in benign false positives under shift. This is the strongest empirical result in the paper because it directly matches the intended system objective.

### 6.3 Deployment-Oriented Frozen-Threshold Transfer

Table 2 reports deployment-style checks that do not re-tune thresholds on the target batch; the full deployment sheet is kept in the appendix. When thresholds are frozen from the matched main-batch run, CDRO-UG still achieves the lowest mean external-J FPR (`0.096` versus `0.168` for Noisy-CE and `0.239` for CDRO-Fixed). More importantly for an operator-facing reading, the same frozen-threshold view yields the lowest benign alert burden: mean false alerts per run fall from `63.4` for Noisy-CE to `36.1` for CDRO-UG, or from `1676` to `958` per `10k` benign nodes, with paired significance against Noisy-CE on both absolute FP count and FP-per-10k-benign. The corresponding pooled mean F1 drops to `0.860`, and attack-IP detection rate / mean first-alert delay become `0.978` / `0.88` windows, compared with `0.990` / `0.58` for Noisy-CE. This is the right operational reading: the method can preserve a conservative false-positive advantage and materially reduce analyst-facing alert load under source-locked thresholds, but not without a coverage / delay cost.

### 6.4 Multi-External Reading

When all four external batches are pooled together, CDRO-UG is essentially tied with Noisy-CE on pooled F1 and only directionally lower on pooled FPR without significance, while pooled ECE and Brier are worse. This broader result is still useful because it shows that the external-J gain is not contradicted by the other batches. A companion appendix table sharpens that reading by showing partial scenario-wise consistency rather than only the pooled external average: under tuned thresholds, `FPR` direction aligns in `3/4` external scenarios (`J/K/L`), with the strongest support on `J`, smaller paired support on `K`, directional-only support on `L`, and a reversal on `I`. However, both the pooled external row and the reversed `I` case mean that this evidence should remain appendix-facing rather than part of the main display chain. The correct interpretation is therefore that the method has a clearly positive signal in one external shifted condition and a statistically weaker, boundary-defining pattern when external scenarios are aggregated.

### 6.5 Strong Baseline Reading

The stronger noisy-label baselines further narrow the claim. On the primary batch, GCE achieves lower pooled FPR than raw sw0; on the external shifted batch, Posterior-CE is slightly lower on pooled FPR than raw sw0. These comparisons do not invalidate the paper, but they do mean that the method should not be advertised as the uniformly strongest noisy-label learner. They should therefore remain appendix-facing boundary evidence. The method's value lies instead in a specific operating regime where benign false-positive control under structured uncertainty matters more than broad pooled dominance.

## 7. Ablation and Analysis

### 7.1 Non-Uniform Group Prioritization

Fig. 3 begins with the first key ablation: whether uncertainty-guided non-uniform group prioritization is necessary. Replacing the learned prioritization with uniform weighting hurts pooled F1 on the primary batch (`delta = -0.004083`, `p = 0.0149`), while the full ablation sheet is kept in Appendix Table A4. This result matters because it shows that the method's gain is not simply due to using a DRO-shaped objective in name only. What matters is the ability to assign more robustness pressure to groups that appear uncertain and shift-sensitive.

### 7.2 Asymmetric Trust

The second key ablation, summarized alongside Fig. 3, tests the trust mechanism. Lowering benign trust too aggressively hurts pooled false-positive behavior on the external shifted batch (`delta = +0.011855`, `p = 7.32e-04`). This is the kind of mechanism result the paper needs: it ties the empirical gain to a specific design choice rather than to an unstructured hyperparameter search. Together with the group-prioritization ablation, it shows that the final method works because it jointly decides where to focus and how strongly to trust different weak-label types.

### 7.3 Weak-Label Audit

Appendix Fig. A1, backed by Appendix Table A6, provides an independent explanation for the trust asymmetry. Across the evaluated settings, weak attack labels are consistently more precise than weak benign labels. This means that a symmetric treatment of attack and benign weak labels would ignore a key property of the supervision itself. The audit therefore converts a modeling choice into a data-supported design decision.

### 7.4 False-Positive Source Decomposition

Fig. 4, backed by Appendix Table A5, shows that the gain is concentrated in benign abstain and weak-benign regions, with especially clear protocol-level evidence in weak attack-strategy OOD. This matters because it confirms that the method is operating on the intended failure mode. The paper should emphasize this analysis because it is substantially more informative than simply stating that one pooled metric is higher or lower.

### 7.5 Runtime and Efficiency

Runtime results are supplementary, but they matter for paper completeness because the proposed method adds grouping and trust logic on top of a standard weak-label learner. The appendix runtime table shows that this added structure does not create a meaningful practical penalty under the current CPU-only single-thread setting. On the primary batch, CDRO-UG records `2.27 s` mean end-to-end wall time versus `2.52 s` for Noisy-CE, while full-graph forward latency is nearly unchanged (`72.58 ms` versus `72.30 ms`). On batch2, CDRO-UG records `2.19 s` versus `2.27 s` wall time and `53.17 ms` versus `51.58 ms` forward latency. The corresponding forward cost is about `0.39 ms` per temporal window on the primary batch and `0.35 ms` per temporal window on batch2. One-time suite setup is also modest: `9.79 s` on the primary batch and `8.86 s` on batch2. The correct reading is therefore not that the method is faster in general, but that the rewritten UG remains in the same computational regime as the baseline family; Table 2 should be read alongside the appendix runtime table when discussing the separate frozen-threshold FPR-versus-delay tradeoff.

### 7.6 Attack-Family and Analyst-Facing Reading

The pooled attack-family breakdown and analyst-facing case studies should be kept in the appendix rather than in the main display chain. When pooled over all four protocols, `burst` is the hardest family across all methods on both the main batch and external-J. On external-J, however, CDRO-UG achieves the lowest pooled FPR for `slowburn` (`0.236` versus `0.294` for Noisy-CE) and `mimic` (`0.226` versus `0.270`). The three case studies show complementary behaviors: a benign false alert suppressed, a slowburn true positive recovered under the lower UG threshold, and a mimic true positive preserved despite a misleading weak-benign label. These cases should not be read as standalone proof, but they help explain why the method's benefit is concentrated in benign-side decision control rather than universal pooled gains.

### 7.7 Hard Protocols and Stress Sweeps

The hard/camouflaged protocol suite and weak-label stress sweeps are useful for boundary discovery and should remain appendix-facing. They do not create a stronger headline result, but they show what the method can and cannot tolerate. In particular, the method remains relatively more stable under weak-label coverage loss than under severe weak-label flip corruption. This asymmetry is not a nuisance result; it is one of the most important conclusions of the broader study because it precisely defines the weak-supervision regime for which the method is best suited.

## 8. Discussion

Our experiments support a narrower but more defensible story than a generic claim of universal noisy-label robustness. On the primary batch, CDRO-UG (sw0) remains broadly comparable to standard weak-label learning methods, but its pooled advantage over Noisy-CE is not statistically significant. The strongest positive result appears on the external shifted batch, where CDRO-UG achieves a pooled false-positive-rate reduction of `-0.043630` against Noisy-CE with paired significance (`p = 0.0051`). This indicates that the method is most useful as a trustworthy deployment mechanism for benign-side risk control under external condition shift, rather than as a universal F1-maximizing learner.

The mechanism experiments explain why this gain appears. Replacing non-uniform group prioritization with uniform weighting hurts pooled F1 on the main batch, and lowering benign trust to `0.35` hurts pooled FPR on the external batch. Weak-label audit shows that weak attack labels are consistently more reliable than weak benign labels, and false-positive source analysis shows that the observed gain is concentrated in benign abstain and weak-benign regions. Taken together, these results support the central design logic of the method: conditional robustness should focus more heavily on uncertain groups while treating weak attack and weak benign evidence asymmetrically. Supplemental runtime benchmarking also shows that this mechanism stays within the same computational regime as Noisy-CE under CPU-only execution, so the method boundary is empirical rather than computational. Deployment-style frozen-threshold analysis sharpens the interpretation: the same mechanism keeps the lowest external-J FPR when the operating point is locked on the source batch, but it does so by sacrificing some F1 and first-alert coverage / delay. That is a real systems tradeoff, not a free improvement.

At the same time, the broader robustness picture is intentionally limited. When all four external batches are pooled together, CDRO-UG is essentially tied with Noisy-CE on F1, only directionally lower on FPR without significance, and worse on pooled ECE/Brier. The new scenario-wise appendix table strengthens this broader reading only partially: under tuned thresholds, `FPR` direction is lower in `3/4` external scenarios, but one scenario reverses and the pooled external comparison remains non-significant. Stronger noisy-label baselines such as GCE, SCE, Bootstrap-CE, ELR, and Posterior-CE show that raw sw0 is not uniformly optimal on pooled FPR. The compact public benchmark is helpful for reproducibility and public comparability, but it should still be read as a sanity check: on Biblio-US17, Noisy-CE has the highest mean F1 (`0.842`), while CDRO-UG reaches mean F1 `0.736` with only a tiny directional FPR reduction (`0.023` versus `0.025`) and slightly worse ECE / Brier. The new label-budget curves likewise show viability under `5-10%` retained weak-label coverage without establishing universal label-efficiency superiority. The additional reference baselines are more diagnostic: `XGBoost(weak)` trails the weak-label graph family on pooled F1, while `PI-GNN(clean)` remains substantially stronger than every weak-label method and therefore exposes a large supervision gap. The pooled family breakdown also shows that `burst` remains the hardest family across all methods, while the analyst-facing cases indicate that the gain is more about suppressing benign alarms and preserving selected true positives than about uniform family-wise dominance. Because the raw captures are private, we therefore pair these analyses with a lightweight reproducibility package that names the released schema files, split manifests, replay wrappers, and sanitized node slice explicitly in the appendix. Calibration, operating-point, and hard/camouflaged stress suites provide completeness and reviewer-facing robustness evidence, but they do not produce a stronger headline than the external shifted-batch result; after corrected merged pairing, the combined hard/camouflaged pooled delta is also near zero. Most importantly, heavy flip-noise stress reveals a clear weakness: the current method degrades under aggressively wrong weak labels, even though it is relatively more stable under weak-label coverage loss.

## 9. Limitations

This work has several important limitations. First, the current CDRO-UG design is regime-specific rather than universally dominant: while it can reduce benign false positives under external conditional shift, it does not consistently outperform stronger noisy-label baselines on pooled metrics; the pooled external-4 result is non-significant on F1/FPR and worse on ECE/Brier. The new scenario-wise appendix table refines this point rather than overturning it: `FPR` direction aligns in `3/4` external scenarios, but one scenario reverses and the pooled external summary remains non-significant. Second, the completed Biblio-US17 public benchmark closes the public-data gap but does not become a new positive headline: Noisy-CE is stronger on mean F1 and slightly better on mean ECE / Brier, while CDRO-UG is only directionally lower on mean FPR without significance. Third, the deployment-oriented frozen-threshold transfer improves external-J FPR only by accepting weaker attack-IP coverage and slightly slower first alerts, so the operating-point advantage is not free. Fourth, the pooled family breakdown shows that `burst` remains hard for every compared method. Fifth, the non-graph reference baseline reveals a real tradeoff: on external-J, `XGBoost(weak)` achieves lower pooled FPR than CDRO-UG only by accepting a materially lower pooled F1. Sixth, the clean-label PI-GNN upper bound remains substantially stronger than every weak-label method, which means the main bottleneck is still supervision quality rather than merely the training objective. Seventh, the method is more tolerant to weak-label coverage loss than to aggressively wrong weak labels. Our stress sweeps show that heavy flip-noise corruption can substantially degrade the false-positive behavior of the method, which means that the present trust mechanism is better suited to incomplete or moderately noisy weak supervision than to adversarial weak-label corruption. Eighth, calibration and operating-point analyses do not provide a stronger headline than the main external-batch false-positive result, so the method should not be presented as a general calibration improvement. Ninth, the hard/camouflaged protocol suite is useful as a stress test, but after corrected merged pairing its combined pooled delta is effectively near zero rather than a new statistically strong primary claim. Overall, these limitations suggest that future work should focus less on extending the current result rhetorically and more on redesigning the trust mechanism for settings where weak labels are directionally wrong rather than merely sparse or uncertain. A compact next step, without enlarging the current submission, is to pair the present training mechanism with post-hoc non-exchangeable conformal risk control or lightweight graph shift adaptation rather than adding a second major learning algorithm into the main paper.

## 10. Conclusion

Weak supervision under conditional shift is not only a problem of average noisy labels, but also a problem of uneven trust and uneven risk across data regions in a deployed detection system. In this paper, we studied that setting through a spatiotemporal graph formulation and proposed CDRO-UG, an uncertainty-guided conditional DRO objective with non-uniform group prioritization and class-asymmetric trust over weak labels. The experimental evidence does not support a universal superiority claim over all noisy-label baselines. Instead, it supports a narrower and more defensible conclusion: the method is most valuable as a benign false-positive control mechanism for trustworthy graph-based detection under structured weak supervision, with its clearest positive result appearing on an external shifted batch.

The ablation and audit results are central to that conclusion. They show that the method works not because any soft-label training is sufficient, but because it combines targeted robustness pressure on uncertain groups with asymmetric treatment of weak attack and weak benign evidence. The corresponding gain is concentrated in benign abstain and weak-benign regions, which matches the intended design goal of suppressing costly benign-side overprediction. The deployment-oriented and analyst-facing supplements sharpen that conclusion rather than broaden it: source-locked thresholds preserve lower external-J FPR with a measurable alert-delay tradeoff, `burst` remains the hardest family, and a lightweight reproducibility package documents the artifacts needed to rerun the public/reference analyses. At the same time, the paper also identifies the boundary of the method. Its advantage weakens under broader pooled comparisons, it is not uniformly strongest against all noisy-label baselines, and it degrades under severe weak-label flip corruption. We therefore conclude that CDRO-UG should be viewed as a scoped mechanism for structured weak supervision under conditional shift, not as a universal solution to arbitrary label noise.

## References Placeholder

- Replace each `[CITE]` token with the appropriate citation entry.
- Recommended citation groups to fill:
  1. weak supervision and data programming;
  2. noisy-label learning and robust losses;
  3. distributionally robust optimization and group robustness;
  4. spatiotemporal graph learning for attack detection;
  5. graph-based intrusion detection under weak or imperfect supervision, if available;
  6. minimal frontier citations for scoped positioning:
     `Learning from Noisy Labels via Conditional Distributionally Robust Optimization` (Guo et al., NeurIPS 2024),
     `Learning from weak labelers as constraints` (Agrawal et al., ICLR 2025),
     `Conformal Risk Control` (Angelopoulos et al., ICLR 2024),
     `Non-Exchangeable Conformal Risk Control` (Farinhas et al., ICLR 2024),
     `Accurate and Scalable Estimation of Epistemic Uncertainty for Graph Neural Networks` (Trivedi et al., ICLR 2024),
     and `Matcha: Mitigating Graph Structure Shifts with Test-Time Adaptation` (Bao et al., ICLR 2025).
