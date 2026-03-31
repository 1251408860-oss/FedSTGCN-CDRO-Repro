# Reproducibility Guide

This document defines the reviewer-facing replay contract for the released `CDRO-UG` artifact. The official review path starts from released processed artifacts rather than private raw-capture regeneration.

Use the same environment family as the original experiments. The primary environment files are `repro/environment-lock-dl.yml`, `repro/requirements-lock-dl.txt`, `env/DL_env_export.yml`, and `env/DL_pip_freeze.txt`; the local release check used `PYTHON_BIN=/home/user/miniconda3/envs/DL/bin/python`.

The full replay command is:

```bash
PYTHON_BIN=/home/user/miniconda3/envs/DL/bin/python bash repro/run_review_artifact.sh
```

By default this command retrains all released runs in `cdro_suite/main_rewrite_sw0_s5_v1/` and `cdro_suite/batch2_rewrite_sw0_s3_v2/`, rebuilds `cdro_summary.json` and `cdro_significance.json`, reruns the deployment-burden evaluation, regenerates `table_maintext_core_results.csv`, `table_maintext_deployment_transfer.csv`, `table18_deployment_checks.csv`, and `fig1_pooled_results.png`, and verifies the regenerated core tables against the references already checked into `cdro_suite/paper_ready_plus/`. The replay outputs are written under `review_artifact/rerun/`, and the final machine-readable summary is `review_artifact/rerun/repro_report.json`.

The expected final report is strict: `core_table_exact_match = true`, `deployment_table_exact_match = true`, `runs_compared = 96`, `max_metric_delta = 0.0`, and `max_threshold_delta = 0.0`. These values were already confirmed in the local end-to-end release check.

The quick verification path is:

```bash
PYTHON_BIN=/home/user/miniconda3/envs/DL/bin/python bash repro/run_review_artifact.sh --skip-rerun
```

This mode reuses the released run artifacts, rebuilds the reviewer-facing core outputs under `review_artifact/reference/`, and verifies the checked-in paper tables without retraining.

The same replay material is mirrored in the GitHub Release at <https://github.com/1251408860-oss/FedSTGCN-CDRO-Repro/releases/tag/review-artifact-v1>. The paper-aligned archive is `FedSTGCN-CDRO-paper-aligned-suites-v1.tar.gz` with SHA-256 `747a87bea6d68cdee0b9d2e89eb37d47eb7cdb7385048654067fb22bec856ab9`, the supplementary audit archive is `FedSTGCN-CDRO-baselineplus-supplement-v1.tar.gz` with SHA-256 `055c8668674781e210db6eb34e9d900a08ff7374bf2f1f90502fc16fd2a6837a`, and `SHA256SUMS.txt` contains the same checksums in machine-readable form.

Within the public boundary, the release includes processed protocol graphs, weak-label sidecars, reference run outputs, reviewer role manifests, and the paper-facing tables and figures needed to regenerate the reported numbers. It does not include raw private PCAPs or private pre-graph base captures. In other words, the artifact begins from the processed-graph stage, but the published paper results are fully reproducible from the released bundle.
