# Table Notes

## Main-Text Tables

### Table 1. Core pooled results on the primary batch and external-J
Source asset: `table_maintext_core_results.csv`  
Built from: pooled rows of `table1_main_results.csv` and `table2_batch2_results.csv`.

This should be the only main results table in the body of the paper. The primary-batch block should be read as a competitiveness control, while the external-J block should be read as the main empirical claim because the pooled FPR reduction against Noisy-CE is the strongest supported result.

### Table 2. Frozen-threshold deployment transfer on external-J
Source asset: `table_maintext_deployment_transfer.csv`  
Built from: `table18_deployment_checks.csv`.

This table converts the external-shift result into deployment terms: frozen FPR, analyst-facing false alert burden, attack-IP detect rate, and first-alert delay. It belongs in the main paper because it is the most BlockSys-aligned practical readout.

### Optional compact appendix mechanism summary
Source asset: `table_maintext_mechanism_summary.csv`  
Built from: decisive rows in `table4_mechanism_probe.csv`.

This table no longer needs to occupy main-text space. If appendix space permits, keep only the two rows that directly support the manuscript story: non-uniform weighting matters on the primary batch, and overly low benign trust worsens external-J pooled FPR.

## Appendix Tables

### Table A1. Full primary-batch per-protocol results
Source asset: `table1_main_results.csv`

Keep all protocol rows here. Do not place the full table in the main paper.

### Table A2. Full external-J per-protocol results
Source asset: `table2_batch2_results.csv`

This table supports the pooled block in Table 1 and gives reviewers the full protocol-level view.

### Table A3. Raw paired significance summary
Source asset: `table3_significance.csv`

Use this table for reviewer verification of the pooled-significance claims.

### Table A4. Full mechanism probe
Source asset: `table4_mechanism_probe.csv`

This is the complete ablation sheet behind Figure 3 and the compressed mechanism paragraph.

### Table A5. Full false-positive source decomposition
Source asset: `table5_fp_sources.csv`

Use this appendix table to back the false-positive decomposition paragraph and protocol-specific decomposition statements.

### Table A6. Full weak-label quality audit
Source asset: `table6_weak_label_quality.csv`

Use this table to back Appendix Figure A1 and the asymmetric-trust argument.

### Table A7. External scenario-wise tuned-threshold consistency
Source assets: `table20_external_direction_consistency.csv`, `external_direction_consistency.md`

Use this table to show that the external-J FPR reduction is not completely isolated to one shifted batch: `FPR` direction aligns in `3/4` external scenarios, strongest on `J`, smaller on `K`, directional only on `L`, and reversed on `I`. Keep it appendix-facing because pooled external remains non-significant and because this is a tuned-threshold scenario readout rather than a frozen-threshold deployment transfer table.

### Table A8. Supplemental baseline family
Source asset: `table7_supplemental_baselines.csv`

This table rules out the explanation that soft labels or prior correction alone are sufficient.

### Table A9. Multiple-testing corrections and runtime costs
Source assets: `multiple_testing_corrections.csv`, `table8_runtime_costs.csv`

These are reviewer-facing support tables rather than headline tables.

### Table A10. External-4 validation and strong noisy-label baselines
Source assets: `table10_external4_validation.csv`, `table11_strong_baselines.csv`

These tables define the boundary of the claim and should remain appendix-facing.

### Table A11. Calibration and operating points
Source assets: `table9_calibration_risk.csv`, `table12_operating_points.csv`

Use these only as completeness evidence.

### Table A12. Hard protocols and stress sweeps
Source assets: `table13_hard_protocols.csv`, `table14_stress_sweeps.csv`

These tables belong in the appendix because they are stress-test boundaries rather than part of the central evidence chain.

### Table A13. Public benchmark, label budget, non-graph reference, deployment supplement, and family breakdown
Source assets: `table15_public_http_benchmark.csv`, `table16_label_budget.csv`, `table17_non_graph_clean_upper.csv`, `table18_deployment_checks.csv`, `table19_attack_family_breakdown.csv`

These tables are important for rebuttal, transparency, and scope control, but they should not interrupt the main-text narrative.
