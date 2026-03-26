# Reproducibility Guide

This document is the reviewer-facing command reference for the released `CDRO-UG` artifact.

## 1. Recommended Environment

Use the same environment family as the original experiments.

Primary files:

- `repro/environment-lock-dl.yml`
- `repro/requirements-lock-dl.txt`
- `DL_env_export.yml`
- `DL_pip_freeze.txt`

Validated replay command in the local release check:

```bash
PYTHON_BIN=/home/user/miniconda3/envs/DL/bin/python
```

## 2. Full Replay

```bash
PYTHON_BIN=/home/user/miniconda3/envs/DL/bin/python bash repro/run_review_artifact.sh
```

Default replay target suites:

- `cdro_suite/main_rewrite_sw0_s5_v1/`
- `cdro_suite/batch2_rewrite_sw0_s3_v2/`

What this command does:

1. Retrains all released runs from `protocol_graphs/*.pt`
2. Rebuilds `cdro_summary.json` and `cdro_significance.json`
3. Runs the deployment-burden replay
4. Rebuilds:
   - `table_maintext_core_results.csv`
   - `table_maintext_deployment_transfer.csv`
   - `fig1_pooled_results.png`
5. Checks the regenerated core tables against `cdro_suite/paper_ready_plus/`

Expected final report:

- `review_artifact/rerun/repro_report.json`
- `review_artifact/rerun/REPRO_SUMMARY.md`

Expected key values:

- `core_table_exact_match = true`
- `deployment_table_exact_match = true`
- `runs_compared = 96`
- `max_metric_delta = 0.0`
- `max_threshold_delta = 0.0`

## 3. Quick Verification

```bash
PYTHON_BIN=/home/user/miniconda3/envs/DL/bin/python bash repro/run_review_artifact.sh --skip-rerun
```

This mode reuses the released run artifacts and only rebuilds the reviewer-facing core outputs.

## 4. Main Output Files

Paper-facing outputs written by the replay:

- `review_artifact/rerun/paper_ready/table_maintext_core_results.csv`
- `review_artifact/rerun/paper_ready/table_maintext_deployment_transfer.csv`
- `review_artifact/rerun/paper_ready/fig1_pooled_results.png`
- `review_artifact/rerun/paper_ready/table18_deployment_checks.csv`

Reference files already checked into the repository:

- `cdro_suite/paper_ready_plus/table_maintext_core_results.csv`
- `cdro_suite/paper_ready_plus/table_maintext_deployment_transfer.csv`
- `cdro_suite/paper_ready_plus/fig1_pooled_results.png`

## 5. Release Boundary

Released:

- Processed protocol graphs
- Weak-label sidecars
- Reference run outputs
- Reviewer role manifests for deployment replay

Not released:

- Raw private PCAPs
- Private source base graphs before protocol-graph preparation

The artifact therefore begins from the processed graph stage, but the published paper numbers are fully replayable from the released bundle.
