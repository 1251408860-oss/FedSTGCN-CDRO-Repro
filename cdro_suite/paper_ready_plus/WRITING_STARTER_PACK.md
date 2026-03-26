# Writing Starter Pack

This file is the shortest path from the current artifact set to the actual paper-writing workflow.

## 1. Core MD files to open first

Read these first, in order:

1. `FULL_PAPER_DRAFT.md`
   - Full assembled draft.
   - Use this as the base manuscript text.
2. `CH5_BOUNDARY_CONCLUSION_CN_DRAFT.md`
   - Chinese Chapter 5 draft for advisor review.
   - Use this when writing the final boundary / conclusion section in Chinese first.
3. `APPENDIX_TWO_SECTION_CN_DRAFT.md`
   - Two-section Chinese appendix draft for the 4-page compressed version.
   - Use this when preparing the submission-facing appendix in Chinese first.
4. `PAPER_WRITING_DRAFT.md`
   - Section-level alternative wording.
   - Use this when you want to rewrite abstract, contributions, introduction, results, or discussion paragraphs.
5. `MANUSCRIPT_FIGURE_TABLE_PLAN.md`
   - Final main-text vs appendix placement plan.
   - Use this to avoid putting appendix material into the main paper.
6. `TABLE_NOTES.md`
   - Final table numbering and safe interpretation notes.
7. `FIGURE_CAPTIONS.md`
   - Final figure numbering and caption guidance.
8. `CONTRIBUTION_EVIDENCE_MAP.md`
   - Use this to ensure every contribution bullet has evidence.
9. `BLOCKSYS_PRE_SUBMISSION_CHECKLIST.md`
   - Final wording and overclaim prevention pass.

Use when needed:

- `APPENDIX_REPRODUCIBILITY_TEXT.md`
  - Ready-to-paste appendix artifact / reproducibility subsection.
- `reproducibility_package.md`
  - Short artifact summary.
- `MASTER_SUMMARY.md`
  - One-page paper positioning summary.
- `SAFE_CLAIMS_AND_LIMITATIONS.md`
  - Safe wording boundary.
- `SUBMISSION_COVER_LETTER.md`
  - Cover letter draft, not part of the paper body.
- `external_direction_consistency.md`
  - Appendix interpretation for multi-external scenario consistency.

## 2. Main-paper figures

These are the figures that should stay in the main paper.

### Figure 1
- File: `fig_method_overview.svg`
- Role: end-to-end method + deployment overview
- Section: Method

### Figure 2
- File: `fig1_pooled_results.png`
- Role: pooled source-vs-shift overview
- Section: Main results

### Figure 3
- File: `fig2_mechanism_probe.png`
- Role: mechanism probe / ablation trend
- Section: Ablation

### Figure 4
- File: `fig3_fp_sources.png`
- Role: false-positive source decomposition
- Section: Mechanism / failure-mode explanation

## 3. Main-paper tables

These are the tables that should stay in the main paper.

### Table 1
- File: `table_maintext_core_results.csv`
- Role: pooled core results on primary batch + external-J

### Table 2
- File: `table_maintext_deployment_transfer.csv`
- Role: frozen-threshold deployment transfer on external-J

## 4. Appendix tables and figures you are most likely to cite

These are important, but should usually stay out of the main display chain.

### High-priority appendix items

- `table1_main_results.csv`
  - Full primary-batch per-protocol results
- `table2_batch2_results.csv`
  - Full external-J per-protocol results
- `table3_significance.csv`
  - Raw paired significance
- `table_maintext_mechanism_summary.csv`
  - Compact mechanism summary now kept out of the main display chain
- `table4_mechanism_probe.csv`
  - Full ablation sheet
- `table5_fp_sources.csv`
  - Full FP decomposition
- `table6_weak_label_quality.csv`
  - Weak-label audit
- `fig4_weak_label_quality.png`
  - Weak-label quality / effective trust visual
- `table20_external_direction_consistency.csv`
  - External scenario-wise tuned-threshold consistency
- `external_direction_consistency.md`
  - Safe explanation for the table above

### Boundary / reviewer-facing appendix items

- `table10_external4_validation.csv`
- `table11_strong_baselines.csv`
- `table8_runtime_costs.csv`
- `table9_calibration_risk.csv`
- `table12_operating_points.csv`
- `table13_hard_protocols.csv`
- `table14_stress_sweeps.csv`
- `table15_public_http_benchmark.csv`
- `table16_label_budget.csv`
- `table17_non_graph_clean_upper.csv`
- `table18_deployment_checks.csv`
- `table19_attack_family_breakdown.csv`
- `fig5_calibration_risk.png`
- `fig6_operating_points.png`
- `fig7_stress_f1.png`
- `fig8_stress_fpr.png`
- `fig9_label_budget.png`
- `fig10_analyst_case_studies.png`

## 5. Fast writing workflow

If you want the fastest way to start:

1. Open `FULL_PAPER_DRAFT.md`.
2. Keep `MANUSCRIPT_FIGURE_TABLE_PLAN.md`, `TABLE_NOTES.md`, and `FIGURE_CAPTIONS.md` beside it.
3. Insert only:
   - `fig_method_overview.svg`
   - `table_maintext_core_results.csv`
   - `fig1_pooled_results.png`
   - `table_maintext_deployment_transfer.csv`
   - `fig2_mechanism_probe.png`
   - `fig3_fp_sources.png`
4. Use `APPENDIX_REPRODUCIBILITY_TEXT.md` directly for the artifact appendix.
5. Use `BLOCKSYS_PRE_SUBMISSION_CHECKLIST.md` for the final pass.

## 6. Safe claim hierarchy

When writing, keep this evidence order fixed:

1. Strongest headline:
   - external-J pooled FPR reduction
2. Systems translation:
   - frozen-threshold alert-burden reduction on external-J
3. Mechanism:
   - non-uniform prioritization + asymmetric trust
4. Appendix strengthening:
   - scenario-wise external consistency
5. Boundary:
   - pooled external non-significant
   - stronger baselines can be competitive
   - public benchmark is not a headline win

## 7. Do not promote into the main headline

Keep these as appendix / boundary evidence:

- pooled external-4 result
- public benchmark
- hard/camouflaged suite
- stress sweeps
- calibration
- operating-point supplement
- external-K frozen-threshold deployment rerun

## 8. Minimal file set if you only want to write now

Open only these files:

- `FULL_PAPER_DRAFT.md`
- `PAPER_WRITING_DRAFT.md`
- `MANUSCRIPT_FIGURE_TABLE_PLAN.md`
- `TABLE_NOTES.md`
- `FIGURE_CAPTIONS.md`
- `APPENDIX_REPRODUCIBILITY_TEXT.md`
- `BLOCKSYS_PRE_SUBMISSION_CHECKLIST.md`
- `fig_method_overview.svg`
- `fig1_pooled_results.png`
- `fig2_mechanism_probe.png`
- `fig3_fp_sources.png`
- `table_maintext_core_results.csv`
- `table_maintext_deployment_transfer.csv`
