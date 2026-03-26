# Submission Cover Letter Draft

Dear BlockSys Program Chairs and Reviewers,

We are pleased to submit our manuscript, tentatively titled **"Uncertainty-Guided Conditional Robustness for Weakly Supervised Spatiotemporal Graph Attack Detection,"** for consideration at BlockSys. This paper studies weak supervision under conditional shift in graph-based security analytics, with a particular focus on trustworthy deployment behavior: benign false-positive control and alert-burden reduction rather than only pooled average accuracy.

The central contribution of the paper is a mechanism-oriented training objective, CDRO-UG, that combines non-uniform group prioritization with class-asymmetric trust over weak labels. Rather than claiming universal superiority across all noisy-label settings, the paper makes a narrower and more defensible claim: under structured weak supervision, the proposed method can reduce benign false positives in external shifted evaluation, and under frozen source thresholds it also reduces analyst-facing benign alert burden. We support this scoped claim with mechanism analysis, weak-label audit, false-positive source decomposition, and deployment-oriented evaluation. We believe this contribution fits BlockSys because it addresses a concrete AI-driven trustworthy-systems question: how to keep a weakly supervised detector useful when operating conditions shift and benign false alarms become costly.

The empirical section is intentionally comprehensive and transparent. In addition to the main and external-batch results, we report ablations, stronger noisy-label baselines, multiple-testing corrections, calibration and operating-point analyses, hard stress protocols, and weak-label noise/coverage sweeps. These supplemental studies do not always strengthen the main claim, and we explicitly present them as boundary-defining evidence. We regard this transparency as a strength of the paper: it separates the strongest supported result from the settings in which the method is merely competitive or limited.

We believe the submission is relevant to the conference because it addresses a practically important reliability issue in weakly supervised security learning, namely benign false-positive escalation under shift, and proposes a robust training mechanism grounded in both empirical evidence and interpretable design choices. The paper is self-contained, emphasizes operating-boundary transparency rather than overclaiming, and includes a lightweight reproducibility package for the public/reference components.

Thank you for your consideration.

Sincerely,  
[Author Names]
