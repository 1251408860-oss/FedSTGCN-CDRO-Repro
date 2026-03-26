# Manuscript Figure And Table Plan

This file converts the current artifact-oriented asset set into the final BlockSys manuscript display plan. The main paper should show only Tables 1-2 and Figures 1-4. All full protocol tables and reviewer-facing robustness suites should move to the appendix. The figure set is intentionally system-first: a method/deployment overview is more valuable for BlockSys reviewers than keeping every diagnostic plot in the main paper.

## Main-Text Display Set

| Manuscript id | Source asset(s) | Section | Question answered | Why it stays in the main paper |
|---|---|---|---|---|
| Figure 1 | `fig_method_overview.svg` | Sec. 4 | What is the end-to-end system and deployment pipeline? | This makes the paper look like a trustworthy systems paper instead of a bare metric sheet. |
| Table 1 | `table_maintext_core_results.csv` assembled from `table1_main_results.csv` + `table2_batch2_results.csv` pooled rows | Sec. 6.1-6.2 | Does CDRO-UG stay competitive on the source batch, and where does the strongest shifted-batch gain appear? | This is the core result chain and keeps the main text on pooled evidence only. |
| Figure 2 | `fig1_pooled_results.png` | Sec. 6.1-6.2 | What is the visual pattern behind the source-vs-shift comparison? | It immediately shows that the strongest supported difference is external-shift FPR reduction, not universal pooled-F1 gain. |
| Table 2 | `table_maintext_deployment_transfer.csv` assembled from `table18_deployment_checks.csv` | Sec. 6.3 | What happens when thresholds are frozen and the model is read as a deployment artifact? | It translates the external-shift benefit into alert burden, FPR, and delay tradeoffs. |
| Figure 3 | `fig2_mechanism_probe.png` | Sec. 7.1-7.3 | Which mechanism evidence must stay visible in the body? | It visualizes the two decisive ablations; the false-positive source decomposition is described in prose and moved to appendix support. |
| Figure 4 | `fig3_fp_sources.png` | Sec. 7.3-7.4 | Where are benign false positives actually being removed? | It ties the pooled FPR gain directly to benign abstain, weak-benign, and high shift-risk regions, which is the strongest failure-mode explanation for BlockSys reviewers. |

## Recommended Main-Text Narrative Order

1. Open the method section with Figure 1.
2. Show Table 1 and Figure 2 next.
3. Read the primary batch as a competitiveness control, not as the headline.
4. Read the external-J block of Table 1 as the strongest positive result.
5. Follow immediately with Table 2 so the result is translated into operator-facing burden.
6. Then explain the gain with Figure 3, Figure 4, and one compact mechanism paragraph tied to appendix mechanism tables.

## Appendix Mapping

| Appendix id | Source asset(s) | Use in the submission package |
|---|---|---|
| Table A1 | `table1_main_results.csv` | Full primary-batch per-protocol results. |
| Table A2 | `table2_batch2_results.csv` | Full external-J per-protocol results. |
| Table A3 | `table3_significance.csv` | Raw paired significance summary for reviewer verification. |
| Table A4 | `table4_mechanism_probe.csv` and `table_maintext_mechanism_summary.csv` | Full mechanism probe plus the compact two-row summary now moved out of the main-text display chain. |
| Table A5 | `table5_fp_sources.csv` | Full false-positive decomposition behind the main-text Figure 4. |
| Table A6 | `table6_weak_label_quality.csv` and `fig4_weak_label_quality.png` | Full weak-label audit and effective-trust visual now moved to the appendix. |
| Table A7 | `table20_external_direction_consistency.csv` and `external_direction_consistency.md` | Scenario-wise external consistency support that strengthens the external-J story without upgrading it into a universal claim. |
| Table A8 | `table10_external4_validation.csv` and `table11_strong_baselines.csv` | Boundary-defining pooled external and stronger-baseline evidence. |
| Table A9 | `multiple_testing_corrections.csv` and `table8_runtime_costs.csv` | Statistical correction and practicality support. |
| Table A10 | `table9_calibration_risk.csv`, `table12_operating_points.csv`, `fig5_calibration_risk.png`, and `fig6_operating_points.png` | Calibration and operating-point completeness. |
| Table A11 | `table13_hard_protocols.csv`, `table14_stress_sweeps.csv`, `fig7_stress_f1.png`, and `fig8_stress_fpr.png` | Hard-suite and stress-test boundaries. |
| Table A12 | `table15_public_http_benchmark.csv`, `table16_label_budget.csv`, `fig9_label_budget.png`, and `table17_non_graph_clean_upper.csv` | Public sanity check, sparse-label viability, and reference ceilings. |
| Table A13 | `table18_deployment_checks.csv`, `table19_attack_family_breakdown.csv`, and `fig10_analyst_case_studies.png` | Full deployment supplement, family breakdown, and analyst-facing examples. |

## Assembly Rules

- Do not leave asset numbering such as `Table 18` or `Fig. 10` in the main paper.
- Use the two compact main-text tables for the submission PDF; keep the full CSV artifacts in the appendix package.
- Keep pooled rows in the main paper; move per-protocol rows to the appendix.
- Keep `external-4`, scenario-wise external consistency, strong baselines, calibration, runtime, hard protocols, stress sweeps, public benchmark, label budget, non-graph references, family breakdown, case studies, and weak-label audit visuals out of the main figure/table chain.
- Do not add a new figure or table for frontier positioning; if needed, handle it with 2-3 prose sentences and citations only.
- Under the current page budget, do not reserve main-text space for a standalone mechanism table; keep the two decisive rows in prose and use Figure 4 as the only restored failure-mode graphic.
