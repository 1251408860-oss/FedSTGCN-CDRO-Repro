# Paper Writing Draft

## Title Options

1. Uncertainty-Guided Conditional Robustness for Weakly Supervised Spatiotemporal Graph Attack Detection
2. Conditional Robust Learning from Weak Labels for Spatiotemporal Graph-Based Attack Detection
3. Benign False-Positive Control under Weak Supervision via Uncertainty-Guided Conditional DRO
4. Weak Supervision under Conditional Shift: Uncertainty-Guided Conditional DRO for Spatiotemporal Attack Detection

Recommended title:

- Uncertainty-Guided Conditional Robustness for Weakly Supervised Spatiotemporal Graph Attack Detection

More conservative title:

- Benign False-Positive Control under Weak Supervision via Uncertainty-Guided Conditional DRO

## Abstract

Weakly supervised attack detection often relies on heuristic labels whose reliability varies sharply across data regions, especially under conditional shift. We study this problem in spatiotemporal graph-based security analytics and frame it as an AI-driven trustworthy systems problem: the critical failure mode is benign alert escalation under shift, not only pooled accuracy loss. To address this setting, we propose CDRO-UG, an uncertainty-guided conditional distributionally robust objective that combines non-uniform group prioritization with class-asymmetric trust over weak labels. Across four weak-supervision evaluation protocols, the method does not deliver a universal pooled-F1 gain over standard weak-label baselines. Its strongest supported result instead appears on an external shifted batch, where pooled false-positive rate drops from `0.2695` to `0.2259` relative to Noisy-CE (`delta = -0.043630`, `p = 0.0051`) while pooled F1 remains comparable. Under source-locked thresholds, the same model further reduces mean benign false alerts from `63.4` to `36.1` per run, or from `1676` to `958` per `10k` benign nodes, at a measurable F1 / first-alert-delay tradeoff. Mechanism analysis shows that this gain depends on retaining non-uniform prioritization and on assigning higher trust to weak attack labels than to weak benign labels. Public HTTP benchmarking, supervision-budget sweeps, non-graph / clean-label references, deployment-oriented analyses, and a lightweight reproducibility package are used to define the method boundary rather than to inflate the headline. These results position CDRO-UG as a deployment-oriented mechanism for trustworthy graph-based detection under conditional shift, rather than as a universal defense against arbitrary noisy labels.

## Contributions

1. We formulate weakly supervised attack detection under conditional shift as a trustworthy system security problem, where the main operational risk is benign false-positive escalation and analyst alert burden rather than only pooled accuracy loss.
2. We propose CDRO-UG, an uncertainty-guided conditional DRO pipeline that combines non-uniform group prioritization with class-asymmetric trust over weak labels, while keeping the final locked version free of pseudo-sample expansion.
3. We show that the strongest empirical gain appears on an external shifted batch: CDRO-UG lowers pooled FPR with paired significance and, under frozen source thresholds, further reduces benign alert burden in operator-facing terms.
4. We connect that gain to mechanism evidence rather than to headline-only comparisons: ablations, weak-label audit, and benign-region error decomposition show that the effect depends on uncertainty-aware prioritization and asymmetric trust.
5. We complement the controlled captures with deployment-oriented readouts, a public HTTP benchmark, reference-baseline studies, and a lightweight reproducibility package, so the paper directly addresses comparability, transparency, and operating-boundary questions.
6. We explicitly document the method boundary: the design is most appropriate for covered-only weak supervision with moderate structured noise, and it is less effective under adversarially wrong weak labels.

## Introduction Opening Paragraphs

### Introduction Paragraph 1

Weak supervision is increasingly used to train attack detection systems when precise labels are expensive, delayed, or partially unavailable. In practice, however, weak labels are not only noisy but also unevenly reliable across the data: some regions are covered by relatively trustworthy attack indicators, whereas others are dominated by ambiguous benign-side heuristics, abstentions, or partial agreement across weak views. This heterogeneity becomes especially problematic under conditional shift, where a deployed detector trained to fit average weak-label behavior can overreact to uncertain regions and produce deployment-costly benign false positives. For trustworthy security systems, this failure mode matters as much as pooled accuracy, because a detector that over-flags benign traffic under shift can be operationally unusable even when its global F1 remains competitive.

### Introduction Paragraph 2

These observations suggest that weak supervision under shift should not be treated only as a generic noisy-label problem. Instead, the training objective should account for where weak supervision is uncertain, how disagreement is distributed across groups, and whether weak attack and weak benign evidence deserve the same level of trust. Motivated by this view, we study weakly supervised spatiotemporal graph attack detection through the lens of conditional robustness. Our goal is not to claim a universal learner that dominates all noisy-label baselines, but to design a trustworthy detection mechanism that focuses training pressure on uncertain groups while controlling benign-side false positives when weak supervision is structured but imperfect.

## Related Work

### Weak Supervision and Noisy Labels

Weak supervision has become a practical alternative to fully supervised labeling in domains where annotation is expensive or delayed [CITE]. Existing methods often aggregate multiple heuristic signals into pseudo-labels, posterior targets, or confidence-weighted supervision. A large body of work on noisy-label learning then focuses on robust losses, sample selection, correction matrices, or consistency regularization [CITE]. However, most of these methods are designed to improve average predictive quality under label corruption, rather than to explicitly control which regions of the weakly supervised data should dominate training. In our setting, this distinction matters because weak-label reliability is highly uneven: some regions carry relatively trustworthy attack evidence, whereas others contain ambiguous benign-side heuristics that are precisely where false positives accumulate under shift.

If one short frontier sentence is added here, use this version: recent work has extended imperfect-supervision learning through conditional DRO for noisy labels [Guo et al., NeurIPS 2024] and constraint-based denoising from weak labelers with explicit error bounds [Agrawal et al., ICLR 2025], but those methods do not directly address benign alert escalation in weakly supervised spatiotemporal graph deployment.

### Distributional Robustness under Shift

Distributionally robust optimization and group-robust learning aim to improve performance under subpopulation or shift-sensitive failure modes by emphasizing high-risk groups rather than average loss [CITE]. Prior work has shown that group-aware objectives can be useful when the worst-case or minority-group error is more important than pooled accuracy. Our work is related to this line of research, but differs in two ways. First, our groups are not predefined semantic attributes; they are induced from weak-supervision uncertainty and shift-related proxies. Second, we are not optimizing for generic worst-group classification alone. Instead, we use conditional robustness as a mechanism to regulate benign-side overprediction under uncertain weak supervision.

If page budget allows one more sentence, use this version: recent conformal risk control methods [Angelopoulos et al., ICLR 2024; Farinhas et al., ICLR 2024] suggest a post-hoc path to bounded deployment risk under shift, whereas our paper focuses on changing the training objective so the detector enters deployment with a better benign-side error profile.

### Graph-Based Attack Detection

Graph neural networks and spatiotemporal graph models have been widely used for intrusion detection, anomaly detection, and traffic analysis because they can capture dependencies across communicating entities and temporal windows [CITE]. Most prior graph-based attack detection systems, however, assume standard supervised labels or focus on architectural improvements. Less attention has been paid to how graph-based detectors should be trained when supervisory signals are weak, view-dependent, and conditionally shifted. Our paper contributes to this gap by combining weak-label uncertainty signals with a conditional robustness objective tailored to the operational cost of benign false positives.

Keep the graph frontier mention to one sentence only: recent graph reliability work on intrinsic uncertainty estimation [Trivedi et al., ICLR 2024] and graph structure-shift adaptation [Bao et al., ICLR 2025] is complementary, but our contribution stays upstream at the weak-label training stage.

### Positioning Relative to Prior Work

The most appropriate way to position this paper is therefore at the intersection of three areas: weak supervision, robust learning under shift, and spatiotemporal graph attack detection. We do not claim a new universal noisy-label defense, nor a new graph architecture. Instead, we contribute a mechanism for deciding where robustness pressure should be placed and how weak labels should be trusted asymmetrically when the dominant deployment risk is false-positive escalation under conditional shift.

## Problem Setup

We consider a spatiotemporal graph

\[
\mathcal{G} = (\mathcal{V}, \mathcal{E}, X),
\]

where each flow-window node \(i \in \mathcal{V}\) has feature vector \(x_i\), latent clean label \(y_i \in \{0,1\}\), and graph connectivity defined over spatial and temporal relations. The task is binary attack detection, where \(y_i = 1\) denotes attack and \(y_i = 0\) denotes benign traffic.

Under weak supervision, the training set does not observe \(y_i\) directly for all nodes. Instead, each node is associated with a collection of weak-label views

\[
\{p_i^{(1)}, p_i^{(2)}, \ldots, p_i^{(M)}\},
\]

where \(p_i^{(m)} \in [0,1]^2\) is the class posterior suggested by the \(m\)-th weak-label view. These views are aggregated into a weak posterior \(\tilde{p}_i\), a weak hard label \(\tilde{y}_i\), an uncertainty score \(u_i\), and an agreement score \(a_i\). In our implementation, \(u_i\) increases when the aggregated weak evidence is uncertain, while \(a_i\) increases when the views agree.

We are interested in the conditional-shift regime in which the relationship between weak-label evidence and clean attack/benign labels varies across groups and across evaluation batches. In particular, weak attack evidence and weak benign evidence need not have the same precision. This motivates two design goals:

1. training should emphasize groups that are more uncertain or shift-sensitive;
2. weak attack and weak benign signals should not necessarily be trusted equally.

The evaluation objective is also scoped. We report pooled predictive quality through F1, but we explicitly treat benign false-positive rate as a first-class deployment metric because a detector that over-flags benign traffic under shift can be operationally unacceptable even when pooled F1 remains competitive.

## Method

### Overview

Our method, CDRO-UG, combines three components:

1. weak-label posterior aggregation from multiple heuristic views;
2. class-asymmetric trust that converts weak posteriors into training targets;
3. uncertainty-guided conditional DRO over groups constructed from uncertainty and shift-related proxies.

Figure 1 should present the full system and deployment view used by the paper. The upper half is the training pipeline: multiple weak supervision views are aggregated into posteriors, uncertainty, agreement, and shift-sensitive proxies; class-asymmetric trust converts these signals into soft targets; and conditional group construction determines where robustness pressure should be applied. The lower half is the deployment reading: the locked detector is transferred with source-tuned thresholds to an external shifted batch, and the paper evaluates the result not only through pooled F1 but also through alert burden, attack-IP coverage, and first-alert delay.

The final locked variant used in the main results is `CDRO-UG (sw0)`, which uses covered-only weak supervision, does not perform pseudo-sample expansion, and sets sample-weight amplification to zero. This locked version was chosen because it provides the cleanest and most stable interpretation of the mechanism.

### Weak-Label Aggregation

For each training node \(i\), the weak-label views are aggregated into a posterior \(\tilde{p}_i\) and hard weak label

\[
\tilde{y}_i = \arg\max_c \tilde{p}_{i,c}.
\]

We further compute:

\[
u_i \in [0,1], \quad a_i \in [0,1], \quad d_i = 1 - a_i,
\]

where \(u_i\) is weak-label uncertainty, \(a_i\) is inter-view agreement, and \(d_i\) is disagreement. We also maintain a shift-sensitive proxy \(\rho_i\), derived from scenario-dependent weak-supervision statistics, to capture how likely a node is to lie in a more difficult conditional region.

### Conditional Group Construction

The training nodes are partitioned into conditional groups based on uncertainty and the shift proxy. In the simplest version used here, each node is assigned to one of four groups by thresholding \(u_i\) and \(\rho_i\) at their training-set medians:

\[
g_i \in \{0,1,2,3\}.
\]

This construction yields groups corresponding to low/high uncertainty and low/high shift sensitivity. The point of the grouping is not to create a semantic taxonomy, but to expose structured variation in weak-label reliability and downstream risk.

### Class-Asymmetric Trust

The central observation behind the trust mechanism is that weak attack labels and weak benign labels need not have the same quality. Let \(c_i\) denote a confidence statistic derived from the weak posterior. We define a trust score \(t_i \in [0,1)\) differently depending on whether the weak label is attack or benign:

\[
t_i =
\begin{cases}
\alpha_{\text{atk}} \cdot f_{\text{atk}}(a_i, c_i), & \text{if } \tilde{y}_i = 1, \\
\alpha_{\text{ben}} \cdot f_{\text{ben}}(a_i, c_i, u_i), & \text{if } \tilde{y}_i = 0,
\end{cases}
\]

where \(\alpha_{\text{atk}}\) and \(\alpha_{\text{ben}}\) are global trust coefficients and \(f_{\text{atk}}, f_{\text{ben}}\) are monotone scaling functions. In practice, benign trust is intentionally lower and is further discounted when uncertainty is high.

The final soft training target is then

\[
q_i = t_i \cdot \text{onehot}(\tilde{y}_i) + (1 - t_i)\tilde{p}_i.
\]

This interpolation keeps weak supervision probabilistic while allowing the method to rely more strongly on higher-quality attack-side evidence than on lower-quality benign-side evidence.

### Uncertainty-Guided Conditional DRO

Let \(\ell_i\) denote the per-sample soft cross-entropy loss against target \(q_i\). The base loss over covered training nodes is

\[
\mathcal{L}_{\text{base}}
=
\frac{1}{|\mathcal{I}|}\sum_{i \in \mathcal{I}} \ell_i.
\]

For each group \(g\), we compute a group loss

\[
\mathcal{L}_g = \frac{1}{|\mathcal{I}_g|} \sum_{i \in \mathcal{I}_g} \ell_i.
\]

Unlike a fixed worst-group objective, CDRO-UG assigns each group a priority score based on both loss and uncertainty-related signals:

\[
\pi_g
=
\lambda_{\text{loss}} \mathcal{L}_g
 \lambda_u \bar{u}_g
 \lambda_d \bar{d}_g,
\]

where \(\bar{u}_g\) and \(\bar{d}_g\) are the mean uncertainty and disagreement of group \(g\). Group weights are then obtained through a softmax with temperature \(\tau\):

\[
w_g = \frac{\exp(\pi_g / \tau)}{\sum_{g'} \exp(\pi_{g'} / \tau)}.
\]

The final training objective is

\[
\mathcal{L}
=
(1-\lambda)\mathcal{L}_{\text{base}}
 \lambda \sum_g w_g \mathcal{L}_g.
\]

This objective is the core of the method: it does not merely fit weak labels, but reallocates training pressure toward conditionally risky groups defined by structured uncertainty.

### Final Locked Variant: CDRO-UG (sw0)

Several design variants were explored during development, including prior correction and stronger sample-level weighting. The final locked version used in the main paper is intentionally simpler. It uses:

1. covered-only weak supervision;
2. asymmetric trust over weak attack and weak benign labels;
3. non-uniform group prioritization;
4. no pseudo-sample expansion;
5. no additional sample-weight scaling (`sw0`).

This locked version is the one we recommend for the paper because it yields the clearest mechanism interpretation and avoids mixing the core idea with auxiliary heuristics.

### Method Formula Version with Equation References

For manuscript formatting, the core method can be rewritten in equation-number form as follows.

Let \(\tilde{p}_i \in [0,1]^2\) denote the aggregated weak posterior for node \(i\), and let

\[
\tilde{y}_i = \arg\max_c \tilde{p}_{i,c}
\tag{1}
\]

be its hard weak label. We also compute weak-label uncertainty \(u_i\), agreement \(a_i\), disagreement \(d_i = 1-a_i\), and a shift-sensitive proxy \(\rho_i\).

The trust score is defined asymmetrically:

\[
t_i =
\begin{cases}
\alpha_{\mathrm{atk}} \, f_{\mathrm{atk}}(a_i, c_i), & \tilde{y}_i = 1,\\
\alpha_{\mathrm{ben}} \, f_{\mathrm{ben}}(a_i, c_i, u_i), & \tilde{y}_i = 0,
\end{cases}
\tag{2}
\]

where \(c_i\) is a posterior-confidence statistic and \(\alpha_{\mathrm{atk}} > \alpha_{\mathrm{ben}}\) in the final locked variant. The soft target used for training is

\[
q_i = t_i \cdot \mathrm{onehot}(\tilde{y}_i) + (1-t_i)\tilde{p}_i.
\tag{3}
\]

Training nodes are partitioned into conditional groups \(g_i\) using thresholds on \(u_i\) and \(\rho_i\). If \(\mathcal{I}_g\) denotes the covered nodes in group \(g\), the group loss is

\[
\mathcal{L}_g = \frac{1}{|\mathcal{I}_g|}\sum_{i \in \mathcal{I}_g}\ell\!\left(f_\theta(x_i), q_i\right),
\tag{4}
\]

and the group priority score is

\[
\pi_g = \lambda_{\mathrm{loss}}\mathcal{L}_g + \lambda_u \bar{u}_g + \lambda_d \bar{d}_g.
\tag{5}
\]

The uncertainty-guided group weights are then

\[
w_g = \frac{\exp(\pi_g / \tau)}{\sum_{g'} \exp(\pi_{g'} / \tau)},
\tag{6}
\]

which yields the final conditional DRO objective

\[
\mathcal{L}_{\mathrm{CDRO\text{-}UG}}
=
(1-\lambda)\mathcal{L}_{\mathrm{base}}
\;+\;
\lambda \sum_g w_g \mathcal{L}_g.
\tag{7}
\]

In the paper text, Eq. (2) should be referenced when motivating class-asymmetric trust, Eq. (5) when motivating non-uniform group prioritization, and Eq. (7) when introducing the full training objective.

## Experimental Setup

### Data and Evaluation Batches

We evaluate the method on spatiotemporal graphs built from controlled capture batches. The primary batch is used for the main four-protocol benchmark, and an external shifted batch is used to assess whether the same weak-supervision mechanism transfers under changed operating conditions. We further include additional external batches as supplemental validation rather than as the main source of the paper's headline claim. To improve public reproducibility, we also build a compact public HTTP sanity benchmark from Biblio-US17 and use it only for a narrow four-method public comparison.

### Protocols

The main evaluation uses four weak-supervision protocols:

1. weak temporal OOD;
2. weak topology OOD;
3. weak attack-strategy OOD;
4. label-prior shift OOD.

These protocols are designed to expose different forms of mismatch between the training split and the test split while preserving the practical structure of the weak-supervision problem.

### Baselines

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

These baselines serve different purposes. Noisy-CE is the simplest hard-label weak-supervision baseline, Posterior-CE tests whether soft labels alone explain the gain, CDRO-Fixed tests whether any group-robust objective is sufficient, and the stronger noisy-label baselines test whether the method remains meaningful once more sophisticated noise-robust losses are introduced.

### Metrics and Statistical Testing

The main reported metrics are F1, recall, false-positive rate, expected calibration error, and Brier score. We prioritize false-positive rate in the main text because the method is explicitly motivated by benign-side deployment risk.

For statistical testing, we use paired sign-flip tests across matched protocol-seed runs. We report raw paired significance in the core comparison tables and also include Holm and Benjamini-Hochberg corrections in supplemental material. The intended reading order is family-wise first and global correction second.

### Supplemental Robustness Analyses

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

These analyses are included to define the method boundary and to answer predictable reviewer questions, not to inflate the headline claim. Because the controlled captures cannot be fully released, we also prepare a lightweight reproducibility package that names the released graph / weak-label schemas, main and external-J split manifests, replay wrappers, and a sanitized node slice explicitly. The appendix text should mention `schema/graph_schema.json`, `schema/weak_label_sidecar_schema.json`, the two protocol-split manifests, the wrapper scripts for the public benchmark and reference analyses, and `sample/sanitized_node_slice.json`, so the artifact story is concrete rather than generic.

## Main Results

### Primary-Batch Results

On the primary batch, Table 1 should present CDRO-UG (sw0) as broadly competitive with the standard weak-label baselines, while making clear that the pooled improvement over Noisy-CE is modest and not statistically significant. For the BlockSys-style reading of the paper, this source-batch block is best treated as a competitiveness control rather than as the main claim table. It shows that the method does not collapse on the source batch, while also clarifying that the paper should not be framed as a universal pooled-accuracy improvement.

### External Shifted-Batch Results

The clearest positive result appears in the external-J block of Table 1. From a trustworthy-systems perspective, the relevant question is not whether the method dominates pooled F1 everywhere, but whether it reduces deployment-costly benign false alarms when operating conditions change. In this setting, CDRO-UG (sw0) achieves pooled F1 comparable to Noisy-CE while reducing pooled false-positive rate from `0.2695` to `0.2259`, corresponding to a delta of `-0.043630` with paired significance (`p = 0.0051`). This is the strongest empirical result in the paper because it matches the intended system objective.

### Deployment-Oriented Frozen-Threshold Transfer

Table 2 should report deployment-style checks that do not re-tune thresholds on the target batch. When thresholds are frozen from the matched main-batch run, CDRO-UG still achieves the lowest mean external-J FPR (`0.096` versus `0.168` for Noisy-CE and `0.239` for CDRO-Fixed). More importantly for an operator-facing reading, the same frozen-threshold view yields the lowest benign alert burden: mean false alerts per run fall from `63.4` for Noisy-CE to `36.1` for CDRO-UG, or from `1676` to `958` per `10k` benign nodes, with paired significance against Noisy-CE on both absolute FP count and FP-per-10k-benign. The corresponding pooled mean F1 drops to `0.860`, and attack-IP detection rate / mean first-alert delay become `0.978` / `0.88` windows, compared with `0.990` / `0.58` for Noisy-CE. This is the right operational reading: the method can preserve a conservative false-positive advantage and materially reduce analyst-facing alert load under source-locked thresholds, but not without a coverage / delay cost.

### Multi-External Reading

When all four external batches are pooled together, CDRO-UG is essentially tied with Noisy-CE on pooled F1 and only directionally lower on pooled FPR without significance, while pooled ECE and Brier are worse. This broader result is still useful because it shows that the external-J gain is not contradicted by the other batches, but it should be kept in an appendix-facing table rather than in the main display chain. The new scenario-wise appendix table should sharpen this reading: under tuned thresholds, `FPR` direction aligns in `3/4` external scenarios (`J/K/L`), with strongest support on `J`, smaller support on `K`, directional-only support on `L`, and a reversal on `I`. The correct interpretation is therefore partial external consistency rather than a universal transfer claim.

### Strong Baseline Reading

The stronger noisy-label baselines further narrow the claim. On the primary batch, GCE achieves lower pooled FPR than raw sw0; on the external-J batch, Posterior-CE is slightly lower on pooled FPR than raw sw0. These comparisons do not invalidate the paper, but they do mean that the method should not be advertised as the uniformly strongest noisy-label learner. They should remain appendix-facing boundary evidence. Its value lies instead in a specific operating regime where benign false-positive control under structured uncertainty matters more than broad pooled dominance.

### Runtime and Efficiency Reading

Runtime should be written as a practicality check, not as a main result. Under CPU-only single-thread benchmarking, CDRO-UG stays in the same runtime regime as Noisy-CE: on the main setting, end-to-end wall time is `2.27s` versus `2.52s`, and full-graph forward latency is `72.58 ms` versus `72.30 ms`; on batch2, wall time is `2.19s` versus `2.27s`, and full-graph forward latency is `53.17 ms` versus `51.58 ms`. The one-time suite setup cost is also small (`9.79s` on main and `8.86s` on batch2). The safe wording is therefore that the rewritten UG does not introduce a meaningful runtime penalty under the current CPU setting, while Table 2 separately reports the frozen-threshold FPR-versus-delay tradeoff.

### Public HTTP Benchmark Reading

The compact public Biblio-US17 benchmark should be framed as a reproducible sanity check rather than as a new graph-level leaderboard result. In that setting, Noisy-CE has the highest mean F1 (`0.842`), while CDRO-UG reaches mean F1 `0.736` with a slightly lower mean FPR (`0.023` versus `0.025`) but slightly worse mean ECE / Brier (`0.089` / `0.068` versus `0.084` / `0.066`). With only three seeds, none of these pairwise gaps are significant, so the public benchmark closes the public-data gap without strengthening the main claim hierarchy.

### Label-Budget And Reference-Baseline Reading

The new label-budget curves show that CDRO-UG remains usable even when only `5-10%` of the original weak-label coverage is retained, but they do not support a universal label-efficiency claim over Noisy-CE or CDRO-Fixed. The most defensible use of these curves is therefore to show viability under sparse supervision and to reinforce the broader conclusion that missing labels are easier to tolerate than wrong labels. The new reference baselines are more decisive: `XGBoost(weak)` trails the weak-label graph family on pooled F1 on both main and external-J, while `PI-GNN(clean)` reaches near-ceiling performance (`0.995` main pooled F1; `0.993` external-J pooled F1). The combined interpretation is that graph structure remains useful under weak supervision, but the main ceiling is still imposed by supervision quality rather than by the graph backbone.

### Attack-Family And Analyst-Facing Reading

The pooled family breakdown and analyst-facing case studies should remain appendix-facing. When pooled over all four protocols, `burst` is the hardest family across all methods on both the main batch and external-J. On external-J, however, CDRO-UG achieves the lowest pooled FPR for `slowburn` (`0.236` versus `0.294` for Noisy-CE) and `mimic` (`0.226` versus `0.270`). The three case studies show complementary behaviors: a benign false alert suppressed, a slowburn true positive recovered under the lower UG threshold, and a mimic true positive preserved despite a misleading weak-benign label. These cases should not be read as standalone proof, but they help explain why the method's benefit is concentrated in benign-side decision control rather than universal pooled gains.

### Figure and Table Referenced Main-Text Version

The following paragraphs are intended for direct use in the paper with figure and table references.

#### Main Results with Figure/Table References

Figure 1 should first give the reader the end-to-end method and deployment pipeline: weak supervision views are aggregated into uncertainty-aware signals, trust converts them into soft targets, conditional groups guide robustness pressure, and the locked detector is finally read under source-frozen transfer with operator-facing metrics. This figure is worth main-text space because it makes the paper look like a trustworthy systems paper rather than a disconnected set of result tables.

Table 1 summarizes the pooled primary-batch benchmark, while the full protocol rows should be moved to the appendix. As shown in Table 1 and Fig. 2, CDRO-UG (sw0) remains competitive with Noisy-CE and CDRO-Fixed on pooled F1, but its main-batch pooled advantage over Noisy-CE is modest and not statistically significant. We therefore do not interpret the primary batch as evidence of universal pooled superiority. Instead, we use it to establish that the proposed method is competitive enough to justify a closer analysis of where its intended benefit should appear.

That benefit appears most clearly in the external-J block of Table 1. There, CDRO-UG reduces pooled false-positive rate from `0.2695` to `0.2259` relative to Noisy-CE, while keeping pooled F1 broadly comparable. Fig. 2 visualizes the same pattern: the most reliable difference between the methods is not a large pooled-F1 gap, but a reduction in benign false positives under external shift. This is the strongest empirical result in the paper and the one we treat as the main deployment-oriented headline.

#### Mechanism Paragraph with Figure/Table References

Table 2 should follow immediately after the main result block, because frozen-threshold deployment transfer converts the external-J gain into a system-facing readout: lower external-J FPR, fewer false alerts per run, and lower false alerts per `10k` benign nodes, but with an explicit coverage / delay tradeoff.

The ablation results summarized around Fig. 3 explain why the external-batch gain appears. When uncertainty-guided non-uniform prioritization is replaced with uniform weighting, pooled F1 on the primary batch decreases significantly. When benign trust is reduced too aggressively, pooled false-positive behavior on the external batch worsens. These results show that the final design depends on both components: it must decide where to apply robustness pressure, and it must treat weak attack and weak benign evidence asymmetrically.

#### Audit and Error Decomposition Paragraph with Figure/Table References

The weak-label audit in Appendix Fig. A1, backed by an appendix table, provides an independent explanation for the trust asymmetry. Across the evaluated settings, weak attack labels are consistently more precise than weak benign labels, which makes a symmetric trust rule difficult to justify. The false-positive decomposition in Fig. 4 further shows that the gain is concentrated in benign abstain and weak-benign regions. Together, these analyses indicate that the method is operating on the intended failure mode rather than improving predictions uniformly across all regions.

#### Supplemental Boundary Paragraph with Figure/Table References

The appendix tables clarify the boundary of the method. The pooled external-4 result is essentially tied with Noisy-CE on F1 and only directionally lower on FPR without statistical support, while pooled ECE and Brier are worse. The new scenario-wise external table strengthens the discussion only modestly: it shows `FPR` direction aligned in `3/4` external scenarios, but one scenario reverses and the pooled external row stays non-significant. Stronger noisy-label baselines can outperform raw sw0 on pooled FPR in some settings. Calibration and operating-point analysis do not create a stronger headline than the external-J FPR result. The public HTTP benchmark is competitive but not a universal win on F1/FPR or calibration. The label-budget curve shows that the method remains usable under sparse weak-label budgets without establishing universal label-efficiency superiority. The non-graph and clean-label reference table shows that XGBoost(weak) is not enough to close the pooled F1 gap, while PI-GNN(clean) remains far above all weak-label methods. The full deployment table, family breakdown, and analyst case studies should remain appendix-facing, and the hard/camouflaged plus stress-sweep suite is better read as near-tied boundary evidence than as a new positive result. We therefore treat these supplemental results as boundary-defining evidence rather than as additional positive headline claims.

## Ablation and Analysis

### Non-Uniform Group Prioritization

Fig. 3 starts with the first key ablation: whether uncertainty-guided non-uniform group prioritization is necessary. Replacing the learned prioritization with uniform weighting hurts pooled F1 on the primary batch (`delta = -0.004083`, `p = 0.0149`). This result is important because it shows that the method's gain is not just coming from using a DRO-shaped objective in name only. What matters is the ability to assign more robustness pressure to groups that appear uncertain and shift-sensitive.

### Asymmetric Trust

The second key ablation tests the trust mechanism. Lowering benign trust too aggressively hurts pooled false-positive behavior on the external shifted batch (`delta = +0.011855`, `p = 7.32e-04`). This is exactly the type of result the paper needs: it ties the empirical gain to a specific design choice rather than to an unstructured hyperparameter search. Together with the group-prioritization ablation, it shows that the final method works because it jointly decides where to focus and how strongly to trust different weak-label types.

### Weak-Label Audit

Appendix Fig. A1, backed by an appendix table, provides an independent explanation for the trust asymmetry. Across the evaluated settings, weak attack labels are consistently more precise than weak benign labels. This means that a symmetric treatment of attack and benign weak labels would ignore an important property of the supervision itself. The audit therefore converts a modeling choice into a data-supported design decision.

### False-Positive Source Decomposition

Fig. 4, backed by Appendix Table A5, shows that the gain is concentrated in benign abstain and weak-benign regions, with especially clear protocol-level evidence in weak attack-strategy OOD. This matters because it confirms that the method is acting on the intended operational failure mode. The paper should emphasize this analysis heavily: it is much more informative than simply stating that one pooled number is higher or lower.

### Hard Protocols and Stress Sweeps

The hard/camouflaged protocol suite and weak-label stress sweeps are useful for boundary discovery, but they should remain appendix-facing. They do not create a stronger headline result, and after corrected merged pairing the combined hard-suite pooled delta is effectively near zero. Their value is therefore to show that the method does not catastrophically collapse under overlap hardening and camouflage, while also clarifying what kinds of weak-supervision degradation it cannot tolerate. In particular, the method remains relatively more stable under weak-label coverage loss than under severe weak-label flip corruption. This asymmetry is not a nuisance finding; it is one of the most important conclusions of the broader study because it tells the reader exactly which weak-supervision regime the method is suited for.

## Experimental Conclusion

Our experiments support a narrower but more defensible story than a generic claim of universal noisy-label robustness. On the main batch, CDRO-UG (sw0) remains broadly comparable to standard weak-label learning methods, but its pooled advantage over Noisy-CE is not statistically significant. The strongest positive result appears on the external-J shifted batch, where CDRO-UG achieves a pooled false-positive-rate reduction of `-0.043630` against Noisy-CE with paired significance (`p = 0.0051`). This indicates that the method is most useful as a trustworthy deployment mechanism for benign-side risk control under external condition shift, rather than as a universal F1-maximizing learner.

The mechanism experiments explain why this gain appears. Replacing non-uniform group prioritization with uniform weighting hurts pooled F1 on the main batch (`delta = -0.004083`, `p = 0.0149`), and lowering benign trust to `0.35` hurts pooled FPR on the external batch (`delta = +0.011855`, `p = 7.32e-04`). Weak-label audit shows that weak attack labels are consistently more reliable than weak benign labels, and false-positive source analysis shows that the observed gain is concentrated in benign abstain and weak-benign regions. Taken together, these results support the central design logic of the method: conditional robustness should focus more heavily on uncertain groups while treating weak attack and weak benign evidence asymmetrically. The deployment-oriented frozen-threshold analysis sharpens this interpretation: the same mechanism preserves the lowest external-J FPR when the operating point is locked on the source batch, but it does so by sacrificing some F1 and first-alert coverage / delay. In other words, the gain is best read as lower operator-facing alert burden with an explicit systems tradeoff, not as a free improvement.

At the same time, the broader robustness picture is intentionally limited. When all four external batches are pooled together, CDRO-UG is essentially tied with Noisy-CE on F1, only directionally lower on FPR without significance, and worse on pooled ECE/Brier. The scenario-wise appendix table makes the same point more precisely: `FPR` direction is favorable in `3/4` external scenarios, but one scenario reverses and the pooled external comparison remains non-significant. Stronger noisy-label baselines such as GCE, SCE, Bootstrap-CE, ELR, and Posterior-CE show that raw sw0 is not uniformly optimal on pooled FPR. The pooled family breakdown also shows that `burst` remains the hardest family across all methods, while the analyst-facing cases indicate that the gain is more about suppressing benign alarms and preserving selected true positives than about uniform family-wise dominance. Calibration, operating-point, and hard/camouflaged stress suites provide completeness and reviewer-facing robustness evidence, but they do not produce a stronger headline than the external-J result; after corrected merged pairing, the combined hard/camouflaged pooled delta is also near zero. Most importantly, heavy flip-noise stress reveals a clear weakness: the current method degrades under aggressively wrong weak labels, even though it is relatively more stable under weak-label coverage loss. Because the raw captures are private, we pair these analyses with a lightweight reproducibility package that explicitly documents the schema files, split manifests, replay wrappers, and sanitized sample slice. The correct conclusion is therefore that CDRO-UG is a mechanism-oriented method for structured weak supervision under conditional shift, with its most reliable value lying in scoped benign false-positive suppression rather than in universal noisy-label dominance.

## Short Conclusion Variant

We conclude that the final CDRO-UG design is best understood as a scoped trustworthy-systems mechanism rather than a universal noisy-label learner. Its strongest evidence lies in reducing benign false positives on an external shifted batch, and this benefit is tied to non-uniform group prioritization plus class-asymmetric trust over weak labels. Deployment-oriented frozen-threshold transfer preserves this benefit only with a measurable alert-delay tradeoff, and the pooled family breakdown shows that `burst` remains the hardest family. The method remains competitive, but not uniformly superior, under broader pooled comparisons, and it is notably weaker under severe weak-label flip corruption. These findings define both the contribution and the boundary of the method.

## Introduction Final Paragraph

Our results support a narrower but stronger story than a generic claim of universal noisy-label robustness. Across the main weak-supervision protocols, the proposed method is usually competitive with standard weak-label learning baselines, but its pooled advantage is modest and not uniformly significant. The clearest and most defensible improvement instead appears under external condition shift, where CDRO-UG reduces benign false positives relative to a hard-label weak-supervision baseline. This effect is not explained by simply replacing hard labels with soft posteriors, nor by prior correction alone; rather, it is tied to the conditional robustness design itself. We therefore position this paper as a mechanism-oriented study of weak supervision under conditional shift: its primary contribution is not universal average-case accuracy gains, but a principled way to prioritize uncertain groups and to treat weak attack and weak benign evidence asymmetrically in order to improve benign-side risk control.

## Method Section Overview

### Method Overview Paragraph

The method section should be written around a simple progression. We first define the weak-supervision setting on a spatiotemporal graph, where each node is associated with a latent clean label, an observed weak-label posterior, and uncertainty signals derived from multiple weak views. We then describe how training nodes are partitioned into conditional groups using uncertainty- and shift-related proxies, and how these groups are used inside a conditional DRO objective. Finally, we explain the uncertainty-guided weighting rule and the class-asymmetric trust mechanism that convert weak posteriors into training targets. This ordering is important because it makes clear that the final method is not just another soft-label baseline: it is a conditional robustness scheme whose main degrees of freedom are group prioritization and trust calibration.

### Suggested Method Subsections

1. Problem Setup: Weak Supervision under Conditional Shift
2. Spatiotemporal Graph Representation and Weak-Label Views
3. Conditional Group Construction from Uncertainty and Shift Proxies
4. Uncertainty-Guided Conditional DRO Objective
5. Class-Asymmetric Trust over Weak Attack and Weak Benign Labels
6. Final Locked Variant: CDRO-UG (sw0)

### Method Transition Paragraph

For readability, the method section should repeatedly emphasize the distinction between three objects: weak-label evidence, trust assigned to that evidence, and robustness pressure applied across groups. Weak-label evidence answers what provisional supervisory signal is available; asymmetric trust answers how strongly that signal should be believed; and the conditional DRO layer answers where the model should focus under structured uncertainty. Framing the method this way will make the later ablation results feel natural rather than post hoc.

## Experimental Section Overview

### Experiment Overview Paragraph

Our evaluation is designed to separate positive evidence from boundary conditions. We first report the main four-protocol weak-supervision benchmark on the primary batch, using pooled and per-protocol comparisons against standard weak-label baselines. We then evaluate the same methods on an external shifted batch, where the strongest empirical gain appears in false-positive suppression. To explain when this gain arises, we follow the main comparison with mechanism-oriented analyses: ablation of non-uniform group prioritization, trust-parameter probing, weak-label quality auditing, and false-positive source decomposition. We further include supplemental baselines, stronger noisy-label competitors, calibration and operating-point analyses, hard/camouflaged stress protocols, and explicit weak-label noise and coverage sweeps. The intent of this section is therefore not to suggest universal superiority, but to identify the regime in which the proposed mechanism helps, the mechanism by which it helps, and the settings in which it does not.

### Experiment Subsection Opening

We organize the experiments around three questions. First, does CDRO-UG improve weakly supervised attack detection under protocol shift, and if so, on which metric is the gain most reliable? Second, which parts of the method are actually responsible for that gain? Third, how broad is the validity range of the method once stronger baselines and harsher weak-label perturbations are considered? The answers to these questions lead to a deliberately scoped conclusion: the method is most compelling as a benign false-positive control mechanism under structured weak supervision and conditional shift.

### Main Results Transition Paragraph

We begin with the main and external-batch protocol benchmarks. These results should be read with an emphasis on pooled false-positive behavior rather than only pooled F1, because the practical failure mode motivating the method is benign-side overprediction under uncertain weak supervision. In this sense, the external shifted batch is particularly important: it is the setting in which CDRO-UG shows its clearest advantage, while the main batch should be interpreted as evidence of competitiveness rather than dominance.

## Experimental Section Structure

### Recommended Experiment Subsection Titles

1. Experimental Setup and Evaluation Protocols
2. Main Weak-Supervision Results on the Primary Batch
3. External Shifted-Batch Evaluation
4. Mechanism Analysis: Group Prioritization and Asymmetric Trust
5. Weak-Label Audit and False-Positive Source Decomposition
6. Supplemental Baselines and Multiple-Testing Corrections
7. Calibration, Operating Points, and Runtime
8. Hard Protocols and Weak-Label Stress Tests

### Recommended Order Rationale

The experimental section should move from strongest positive evidence to broader boundary conditions. Start with the primary batch only to establish competitiveness, then move quickly to the external shifted batch because that is the strongest positive result. Once the reader has seen that result, explain it mechanistically through ablations, weak-label audit, and false-positive decomposition. Only after the main mechanism story is clear should the paper report stronger noisy-label baselines, correction tables, calibration, runtime, hard protocols, and noise/coverage stress tests. This order prevents weaker or negative supplemental evidence from obscuring the paper's core contribution.

### Appendix Placement Guidance

Keep the following in the main paper:

1. Figure 1: method and deployment overview
2. Table 1: compact pooled core results on the primary batch and external-J
3. Figure 2: pooled source-vs-shift overview
4. Table 2: frozen-threshold deployment transfer
5. Figure 3: decisive mechanism evidence
6. Figure 4: false-positive source decomposition

Move the following to appendix or supplement:

1. Full per-protocol result tables from the primary batch and external-J
2. Significance and multiple-testing correction tables
3. External-4 pooled table and strong noisy-label baseline tables
4. Calibration, operating-point, and runtime tables
5. Hard/camouflaged protocol table and noise/coverage stress sweeps
6. Public benchmark, label-budget, non-graph reference, family breakdown, and analyst case studies

### Main-Text Figure And Table Assembly

The clean BlockSys version should renumber the display chain so that the body of the paper contains only `Table 1-2` and `Figure 1-4`. `Figure 1` should be the method and deployment overview, `Table 1` should be a pooled-only summary assembled from the current main and batch2 pooled rows, and `Table 2` should be the frozen-threshold deployment summary assembled from the current deployment sheet. `Figure 2` should remain the pooled results overview, `Figure 3` the mechanism probe, and `Figure 4` the false-positive decomposition. The two decisive ablation rows should still be written directly into the mechanism paragraph, rather than restored as a standalone table. All raw asset numbering such as `Table 18` or `Fig. 10` should disappear from the main paper and be reserved for the appendix artifact package.

## Limitations

### Limitations Subsection

This work has several important limitations. First, the current CDRO-UG design is regime-specific rather than universally dominant: while it can reduce benign false positives under external conditional shift, it does not consistently outperform stronger noisy-label baselines on pooled metrics. Second, the method is more tolerant to weak-label coverage loss than to aggressively wrong weak labels. Our stress sweeps show that heavy flip-noise corruption can substantially degrade the false-positive behavior of the method, which means that the present trust mechanism is better suited to incomplete or moderately noisy weak supervision than to adversarial weak-label corruption. Third, calibration and operating-point analyses do not provide a stronger headline than the main external-batch false-positive result, so the method should not be presented as a general calibration improvement. Fourth, the hard/camouflaged protocol suite is useful as a stress test, but it does not produce a new statistically strong primary claim. Overall, these limitations suggest that future work should focus less on extending the current result rhetorically and more on redesigning the trust mechanism for settings where weak labels are directionally wrong rather than merely sparse or uncertain. If one short forward-looking sentence is kept, prefer: a compact next step is to combine the current training mechanism with post-hoc non-exchangeable conformal risk control or lightweight graph test-time adaptation, not to turn this submission into a second large algorithm paper.

## Page-Budget Frontier Insertions

Use this rule for the BlockSys version: add at most three short sentences in the main paper and do not add any new main-text figure, table, or experiment subsection for frontier positioning.

Recommended insertion order:

1. one sentence in related work on recent imperfect-supervision methods;
2. one sentence in related work on conformal deployment risk control;
3. one sentence in limitations or conclusion on a compact next-step extension.

Recommended minimal citation set:

1. Guo et al., `Learning from Noisy Labels via Conditional Distributionally Robust Optimization`, NeurIPS 2024.
2. Agrawal et al., `Learning from weak labelers as constraints`, ICLR 2025.
3. Angelopoulos et al., `Conformal Risk Control`, ICLR 2024.
4. Farinhas et al., `Non-Exchangeable Conformal Risk Control`, ICLR 2024.
5. Trivedi et al., `Accurate and Scalable Estimation of Epistemic Uncertainty for Graph Neural Networks`, ICLR 2024.
6. Bao et al., `Matcha: Mitigating Graph Structure Shifts with Test-Time Adaptation`, ICLR 2025.

### Shorter Limitations Variant

The main limitation of this work is that CDRO-UG is not a universal noisy-label learner. Its strongest benefit is a scoped reduction of benign false positives under external condition shift, whereas pooled gains against stronger noisy-label baselines are limited and heavy flip-noise corruption remains challenging. The method should therefore be interpreted as a structured weak-supervision mechanism with a clear operating regime, not as a general defense against arbitrary label noise.

## Rebuttal Notes

### Reviewer Question 1: "Your improvements are not consistent across all settings."

Recommended response:

That observation is correct, and the paper is intentionally written to avoid a universal superiority claim. Our main empirical claim is scoped to benign false-positive suppression under external conditional shift, where the pooled FPR reduction on the external-J batch is statistically supported. We treat the main-batch pooled result, the external-4 pooled result, and the hard-stress suites as important boundary conditions rather than hiding them. This is why the paper emphasizes mechanism evidence and deployment-relevant error control instead of claiming uniform gains on every aggregate metric.

### Reviewer Question 2: "Is the gain simply due to using soft labels instead of hard weak labels?"

Recommended response:

Our supplemental baselines were designed to test exactly that alternative explanation. Posterior-CE isolates the effect of replacing hard weak labels with soft posteriors, while PriorCorr isolates prior correction. Neither baseline provides a stable replacement for the full mechanism across the reported settings. The evidence therefore suggests that the gain is not explained by soft-label training alone, but by the interaction between conditional robustness, non-uniform prioritization, and asymmetric trust.

### Reviewer Question 3: "Why should the asymmetric trust design be believed?"

Recommended response:

We support the asymmetric trust design with two independent pieces of evidence. First, weak-label audit shows that weak attack labels are consistently much more precise than weak benign labels. Second, trust ablation on the external batch shows that lowering benign trust harms pooled false-positive behavior. These analyses jointly support the decision to treat weak attack and weak benign evidence differently rather than symmetrically.

### Reviewer Question 4: "Do stronger noisy-label baselines overturn your conclusion?"

Recommended response:

They narrow the conclusion, but they do not overturn it. We agree that raw sw0 is not uniformly best on pooled FPR once stronger baselines such as GCE, SCE, Bootstrap-CE, ELR, and Posterior-CE are included. For that reason, the paper no longer claims universal noisy-label dominance. Instead, the conclusion is that CDRO-UG provides a mechanism-grounded and externally validated false-positive-control benefit in a specific structured weak-supervision regime.

### Reviewer Question 5: "Your method appears weak under severe flip noise."

Recommended response:

Yes. We include that result deliberately because it identifies the true operating boundary of the method. The current design is relatively more stable under weak-label coverage loss than under adversarially wrong weak labels. We regard this as an important negative result: it clarifies that the proposed trust mechanism is better suited to incomplete or moderately noisy supervision than to severe flip-noise corruption. We would rather state that limitation explicitly than overclaim robustness.

### Reviewer Question 6: "Why should this paper still be accepted if the gains are scoped?"

Recommended response:

Because the paper contributes a defensible mechanism with a clearly identified operating regime, rather than a broad but weakly supported claim. The external shifted-batch result, the ablation evidence, the weak-label audit, and the false-positive source decomposition all point to the same conclusion: uncertainty-guided conditional robustness can improve benign-side error control when weak supervision is structured but imperfect. We believe that clearly separating positive evidence from boundary conditions makes the paper stronger, not weaker.

### One-Paragraph Rebuttal Summary

Our revised framing intentionally narrows the claim of the paper. We do not argue that CDRO-UG is uniformly superior across all noisy-label settings. Instead, we show that it provides a mechanism-grounded reduction of benign false positives under external conditional shift, and that this benefit is tied to non-uniform group prioritization plus class-asymmetric trust. We also explicitly report the boundary conditions under which the gain weakens, including stronger noisy-label baselines, hard stress suites, and severe flip-noise corruption. We believe this scoped but well-supported contribution is the most accurate interpretation of the full experimental evidence.

## Final Conclusion Version

Weak supervision under conditional shift is not only a problem of average noisy labels, but also a problem of uneven trust and uneven risk across data regions. In this paper, we studied that setting through a spatiotemporal graph formulation and proposed CDRO-UG, an uncertainty-guided conditional DRO objective with non-uniform group prioritization and class-asymmetric trust over weak labels. The experimental evidence does not support a universal superiority claim over all noisy-label baselines. Instead, it supports a narrower and more defensible conclusion: the method is most valuable as a benign false-positive control mechanism under structured weak supervision, with its clearest positive result appearing on an external shifted batch.

The ablation and audit results are central to that conclusion. They show that the method works not because any soft-label training is sufficient, but because it combines targeted robustness pressure on uncertain groups with asymmetric treatment of weak attack and weak benign evidence. The corresponding gain is concentrated in benign abstain and weak-benign regions, which matches the intended design goal of suppressing costly benign-side overprediction. At the same time, the paper also identifies the boundary of the method. Its advantage weakens under broader pooled comparisons, it is not uniformly strongest against all noisy-label baselines, and it degrades under severe weak-label flip corruption. We therefore conclude that CDRO-UG should be viewed as a scoped mechanism for structured weak supervision under conditional shift, not as a universal solution to arbitrary label noise.

## Short Final Conclusion Variant

The main takeaway of this paper is not that CDRO-UG dominates all noisy-label baselines, but that it offers a principled and externally validated way to reduce benign false positives under structured weak supervision and conditional shift. Its strongest support comes from external shifted-batch evaluation and mechanism analysis, while its limitations under stronger baselines and heavy flip noise define a clear operating boundary. This scoped interpretation is the most faithful reading of the full experimental evidence.

## Formal Conclusion Section

### Conclusion

This paper studied weakly supervised spatiotemporal graph attack detection under conditional shift, with a focus on the practical risk of benign false positives rather than only pooled average accuracy. We proposed CDRO-UG, an uncertainty-guided conditional DRO objective that combines non-uniform group prioritization with class-asymmetric trust over weak labels. The final locked version avoids pseudo-sample expansion and isolates the mechanism we regard as central to the method.

The empirical evidence supports a scoped rather than universal conclusion. CDRO-UG does not consistently dominate standard weak-label baselines on pooled metrics across all settings. However, it does achieve its clearest and most practically meaningful gain on the external shifted batch, where it significantly reduces benign false positives relative to a hard-label weak-supervision baseline. Mechanism analysis, weak-label audit, and false-positive source decomposition all point to the same interpretation: the observed benefit arises because the method focuses robustness pressure on uncertain groups and treats weak attack and weak benign evidence asymmetrically.

Just as importantly, the full experimental study clarifies the boundary of the method. The pooled external-4 result is not significant, stronger noisy-label baselines can be competitive or better on pooled FPR, and severe weak-label flip corruption remains challenging. These findings should not be treated as weaknesses to hide, but as evidence that the method has a specific operating regime. We therefore conclude that CDRO-UG is best viewed as a mechanism for structured weak supervision under conditional shift, particularly when benign-side false-positive control is more important than claiming broad universal superiority over all noisy-label baselines.
