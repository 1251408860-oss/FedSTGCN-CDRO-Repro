# Contribution To Evidence Map

This file translates the current contribution list into reviewer-facing evidence anchors. Use it to keep the BlockSys submission concrete and to prevent contribution bullets from drifting into unsupported claims.

| Contribution claim | Core evidence in main paper | Supporting appendix evidence | Safe reading |
|---|---|---|---|
| Weak supervision under conditional shift should be read as a trustworthy system security problem, not only as pooled classification. | `fig_method_overview.svg` as Figure 1, `table_maintext_deployment_transfer.csv` as Table 2 | `deployment_checks.md`, `runtime_costs.md` | The key deployment failure mode is benign alert escalation under shift. |
| CDRO-UG combines conditional robustness with class-asymmetric trust over weak labels. | Figure 1, `fig2_mechanism_probe.png` as Figure 3 | `table_maintext_mechanism_summary.csv`, `table4_mechanism_probe.csv`, `table6_weak_label_quality.csv` | The method contribution is the interaction of group prioritization and asymmetric trust. |
| The strongest empirical gain is a scoped external-shift FPR reduction. | `table_maintext_core_results.csv` as Table 1, `fig1_pooled_results.png` as Figure 2 | `table2_batch2_results.csv`, `table3_significance.csv`, `table20_external_direction_consistency.csv`, `external_direction_consistency.md`, `multiple_testing_corrections.csv` | External-J is the headline scenario; the new scenario-wise table only supports partial external consistency, not general transfer. |
| The result matters operationally because it reduces analyst-facing benign alert burden under frozen thresholds. | `table_maintext_deployment_transfer.csv` as Table 2 | `table18_deployment_checks.csv`, `deployment_checks.md` | Lower alert burden is the strongest BlockSys-facing systems readout. |
| The gain is mechanism-grounded rather than a generic soft-label effect. | `fig2_mechanism_probe.png` as Figure 3, `fig3_fp_sources.png` as Figure 4, plus the mechanism paragraph in the main text | `table_maintext_mechanism_summary.csv`, `table5_fp_sources.csv`, `table7_supplemental_baselines.csv` | The method helps by acting on benign-side failure regions. |
| The paper is transparent about boundary conditions and reproducibility limits. | Boundary paragraph in the main discussion and limitations | `table10_external4_validation.csv`, `table11_strong_baselines.csv`, `table15_public_http_benchmark.csv`, `reproducibility_package.md`, `APPENDIX_REPRODUCIBILITY_TEXT.md` | Public benchmark, strong baselines, external-consistency limits, and artifact details narrow the claim rather than expand it. |

## Reviewer-Facing Use

- Every contribution bullet in the abstract or introduction should map to at least one row in this table.
- If a contribution does not have a main-paper anchor, rewrite it as a scope or transparency statement rather than a headline contribution.
- During rebuttal, answer with the evidence chain first and the interpretation second.
