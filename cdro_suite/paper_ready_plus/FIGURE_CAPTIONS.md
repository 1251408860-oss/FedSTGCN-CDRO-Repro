# Figure Captions

## Main-Text Figures

### Figure 1. End-to-end method and deployment overview
Source asset: `fig_method_overview.svg`  
Placement: main text, Sec. 4.

This figure should appear before the result figures. It shows the full system view: weak supervision is aggregated into uncertainty- and shift-aware signals, class-asymmetric trust and conditional group prioritization feed the CDRO-UG objective, and the locked detector is then read through source-frozen deployment transfer and operator-facing alert metrics.

### Figure 2. Pooled results overview
Source asset: `fig1_pooled_results.png`  
Placement: main text, Sec. 6.1-6.2.

CDRO-UG (sw0) is compared with Noisy-CE and CDRO-Fixed on the primary batch and on the external-J shifted batch. The intended reading is restrained: the clearest supported gain is not a universal pooled-F1 increase, but lower benign false-positive rate under external shift while source-batch pooled F1 stays competitive.

### Figure 3. Mechanism probe for non-uniform prioritization and asymmetric trust
Source asset: `fig2_mechanism_probe.png`  
Placement: main text, Sec. 7.1-7.2.

Ablations isolate whether the observed benefit comes from non-uniform group prioritization or from the trust design. The two main manuscript sentences should be stated directly around this figure: removing non-uniform weighting hurts primary-batch pooled F1, and setting benign trust too low hurts external-J pooled FPR.

### Figure 4. False-positive source decomposition
Source asset: `fig3_fp_sources.png`  
Placement: main text, Sec. 7.3-7.4.

Delta FPR is shown as CDRO-UG minus Noisy-CE. Negative bars indicate fewer benign false alarms. This figure should be treated as the main-text failure-mode explanation: the gain is concentrated in benign `abstain` and `weak_benign` regions rather than uniformly across all buckets.

## Appendix Figures

### Figure A1. Weak-label quality and effective trust
Source asset: `fig4_weak_label_quality.png`

Weak attack labels are consistently more precise than weak benign labels across the main evaluated settings, and the effective trust values follow the same split. This is the cleanest visual justification for class-asymmetric trust, but it can move to the appendix when the main paper needs a stronger system-first figure.

### Figure A2. Calibration and risk-coverage
Source asset: `fig5_calibration_risk.png`

This figure is completeness evidence only. It should not be used to claim universal calibration or selective-risk improvement.

### Figure A3. Operating-point analysis
Source asset: `fig6_operating_points.png`

Use this figure only in the appendix or rebuttal to support low-FPR operating-point discussion. It does not create a stronger headline than external-J pooled FPR plus frozen-threshold transfer.

### Figure A4. Stress sweep F1 curves
Source asset: `fig7_stress_f1.png`

Use this figure to show how pooled F1 changes under weak-label flip corruption and coverage loss. The intended reading is boundary discovery, not a new win.

### Figure A5. Stress sweep FPR curves
Source asset: `fig8_stress_fpr.png`

This figure makes the negative result visible: the method is relatively more stable under coverage loss than under severe wrong-label corruption.

### Figure A6. Label-budget curves
Source asset: `fig9_label_budget.png`

Use this figure as sparse-supervision availability evidence. Do not present it as universal label-efficiency superiority.

### Figure A7. Analyst-facing case studies
Source asset: `fig10_analyst_case_studies.png`

These cases translate the mechanism into analyst-readable behavior, but they should remain appendix-facing because they are explanatory examples rather than aggregate evidence.
