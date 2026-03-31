# FedSTGCN-CDRO-Repro

This repository is the reviewer-facing reproducibility release for the `CDRO-UG` conditional-shift experiments built on the FedSTGCN codebase. The official review path starts from released processed artifacts rather than private raw-capture regeneration. For the paper-aligned `main` and `external-J` suites, the released replay pipeline has already been validated locally on March 26, 2026, with `runs_compared = 96`, `core_table_exact_match = true`, `deployment_table_exact_match = true`, `max_metric_delta = 0.0`, and `max_threshold_delta = 0.0`.

## Repository Layout

The repository root is organized around the reviewer workflow:

| Path | Role in the release |
| --- | --- |
| `repro/` | reviewer entry points, lockfiles, and replay helpers |
| `cdro_suite/` | released suites, paper-ready references, and lightweight artifact bundles |
| `analysis/` | significance scripts, paper table/figure builders, and artifact assembly |
| `training/` | PI-GNN, CDRO, federated, and tabular training entry points |
| `data_prep/` | weak-label generation and protocol-graph construction |
| `pipelines/` | larger experiment orchestration scripts |
| `env/` | one preserved historical environment export from the original runs |
| `docs/` | public-facing repository structure notes |

Key reviewer assets:

| Path | Role in the release |
| --- | --- |
| `repro/run_review_artifact.sh` | one-command reviewer entry point |
| `repro/review_artifact.py` | replay and verification pipeline |
| `REPRODUCIBILITY.md` | exact replay contract, outputs, and boundaries |
| `cdro_suite/main_rewrite_sw0_s5_v1/` | paper-aligned main-batch suite |
| `cdro_suite/batch2_rewrite_sw0_s3_v2/` | paper-aligned external-J suite |
| `cdro_suite/paper_ready_plus/` | checked-in paper tables and figures used for comparison |
| `cdro_suite/main_baselineplus_s3_v1/` | supplementary baselineplus main suite |
| `cdro_suite/batch2_baselineplus_s3_v1/` | supplementary baselineplus external suite |
| `cdro_suite/repro_package_v1/` | lightweight schema and manifest package |

The reviewer-facing path is intentionally narrow: start from `repro/run_review_artifact.sh`, then inspect `review_artifact/*` outputs if needed. Most other directories are preserved for traceability and internal reuse.

The intended environment is the same PyTorch/PyG environment used in the original experiments. The repository keeps reviewer lockfiles in `repro/` and one preserved historical export in `env/DL_env_export.yml`; in local verification the replay command was executed with `PYTHON_BIN=/home/user/miniconda3/envs/DL/bin/python` on Ubuntu/WSL.

The full reviewer replay is:

```bash
PYTHON_BIN=/home/user/miniconda3/envs/DL/bin/python bash repro/run_review_artifact.sh
```

This command replays the released `main_rewrite_sw0_s5_v1` and `batch2_rewrite_sw0_s3_v2` suites from `protocol_graphs/*.pt`, rebuilds the paired significance summaries, regenerates the core main-text tables and pooled-results figure, and checks the regenerated core tables against the references in `cdro_suite/paper_ready_plus/`. The main outputs are written under `review_artifact/rerun/`, with the final verification summary stored in `review_artifact/rerun/repro_report.json` and `review_artifact/rerun/REPRO_SUMMARY.md`.

If a reviewer only wants to verify the released run artifacts without retraining, the quick path is:

```bash
PYTHON_BIN=/home/user/miniconda3/envs/DL/bin/python bash repro/run_review_artifact.sh --skip-rerun
```

That path writes its outputs under `review_artifact/reference/` and checks the checked-in core tables directly.

For reviewers who prefer a compact download instead of cloning the full repository tree, the same material is mirrored in the GitHub Release at <https://github.com/1251408860-oss/FedSTGCN-CDRO-Repro/releases/tag/review-artifact-v1>. The paper-aligned bundle is `FedSTGCN-CDRO-paper-aligned-suites-v1.tar.gz` with SHA-256 `747a87bea6d68cdee0b9d2e89eb37d47eb7cdb7385048654067fb22bec856ab9`, and the supplementary audit bundle is `FedSTGCN-CDRO-baselineplus-supplement-v1.tar.gz` with SHA-256 `055c8668674781e210db6eb34e9d900a08ff7374bf2f1f90502fc16fd2a6837a`. The corresponding machine-readable checksum file is `SHA256SUMS.txt`.

This public release includes processed protocol graphs, weak-label sidecars, reference run outputs, reviewer replay scripts, and the paper-facing tables and figures needed to reproduce the reported results. It does not include raw private PCAPs, unreleased pre-graph base captures, or the private-data recapture workflow. The release boundary is therefore the processed-graph stage, while the reported paper numbers are fully reproducible from the released artifacts inside that boundary.
