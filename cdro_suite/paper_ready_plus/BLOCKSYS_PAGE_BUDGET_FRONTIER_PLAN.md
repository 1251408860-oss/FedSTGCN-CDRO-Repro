# BlockSys Page-Budget Frontier Plan

This note records the lowest-cost way to absorb recent frontier literature into the BlockSys manuscript without expanding the paper structure.

## Core Rule

Do not add a new experiment section, extra main-text table, or extra main-text figure for frontier positioning.

The recommended ceiling is:

1. one short sentence in related work on recent imperfect-supervision methods;
2. one short sentence in related work on deployment-time risk control;
3. one short sentence in limitations or conclusion on the most credible next-step extension.

## Why This Is the Right Tradeoff

The current paper is already near its strongest readable form:

1. the main positive claim is still `external-J` pooled `FPR` reduction plus frozen-threshold alert-burden reduction;
2. the main mechanism is still non-uniform prioritization plus asymmetric trust;
3. the main weakness is still lack of universal pooled significance.

Adding a large frontier block would consume page budget without fixing the central evidence problem. A short positioning layer is better because it shows awareness of the field while keeping the paper honest and focused.

## Recommended Insertions

### 1. Imperfect-supervision sentence

Recent work has extended imperfect-supervision learning through conditional DRO for noisy labels and constraint-based denoising from weak labelers, but those methods do not directly target benign alert escalation in weakly supervised spatiotemporal graph deployment.

Recommended citations:

1. Hui Guo, Grace Y. Yi, Boyu Wang. `Learning from Noisy Labels via Conditional Distributionally Robust Optimization`. NeurIPS 2024.
2. Vishwajeet Agrawal, Rattana Pukdee, Nina Balcan, Pradeep K Ravikumar. `Learning from weak labelers as constraints`. ICLR 2025.

### 2. Deployment-risk sentence

Recent conformal risk control methods suggest a post-hoc path to bounded deployment risk under shift, whereas our paper focuses on changing the training objective so the detector enters deployment with a better benign-side error profile.

Recommended citations:

1. Anastasios Angelopoulos, Stephen Bates, Adam Fisch, Lihua Lei, Tal Schuster. `Conformal Risk Control`. ICLR 2024.
2. Antonio Farinhas, Chrysoula Zerva, Dennis Ulmer, Andre Martins. `Non-Exchangeable Conformal Risk Control`. ICLR 2024.

### 3. Graph-reliability sentence

Recent graph reliability work on intrinsic uncertainty estimation and graph structure-shift adaptation is complementary, but our contribution stays upstream at the weak-label training stage.

Recommended citations:

1. Puja Trivedi, Mark Heimann, Rushil Anirudh, Danai Koutra, Jayaraman J. Thiagarajan. `Accurate and Scalable Estimation of Epistemic Uncertainty for Graph Neural Networks`. ICLR 2024.
2. Wenxuan Bao, Zhichen Zeng, Zhining Liu, Hanghang Tong, Jingrui He. `Matcha: Mitigating Graph Structure Shifts with Test-Time Adaptation`. ICLR 2025.

### 4. One-sentence future-work addition

A compact next step is to combine the current training mechanism with post-hoc non-exchangeable conformal risk control or lightweight graph test-time adaptation, not to turn this submission into a second large algorithm paper.

## What Not To Add

Do not add any of the following unless a later revision creates clear space:

1. a new theorem or guarantee subsection on conformal methods;
2. a new experiment suite for test-time adaptation;
3. a large comparison table of frontier papers;
4. a survey-style related work expansion;
5. claims that the current paper already provides conformal guarantees or graph adaptation.

## Safe Reading

The role of these citations is positioning, not headline inflation. They should help reviewers read the paper as a well-scoped systems/security contribution that is aware of current learning trends, while keeping the empirical center of gravity on the existing `external-J` and deployment-transfer evidence.
