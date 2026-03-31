# Repository Structure

This repository is split into a small reviewer-facing surface and a larger preserved experiment history.

## Reviewer-facing paths

- `README.md`: top-level release overview.
- `REPRODUCIBILITY.md`: replay contract and expected outputs.
- `repro/`: official entry points for full replay and quick verification.
- `cdro_suite/main_rewrite_sw0_s5_v1/`: paper-aligned main-batch suite.
- `cdro_suite/batch2_rewrite_sw0_s3_v2/`: paper-aligned external-J suite.
- `cdro_suite/paper_ready_plus/`: checked-in paper-facing tables and figures.

## Core code organization

- `analysis/`: significance tests, paper-ready tables/figures, deployment checks, and artifact assembly.
- `training/`: PI-GNN, CDRO, federated, and tabular/XGBoost training scripts.
- `data_prep/`: graph building, weak-label generation, and protocol construction.
- `pipelines/`: multi-stage experiment runners and orchestration helpers.

## Supporting material

- `env/`: one preserved historical conda export from the original runs.
- `biblio_us17/`: public benchmark assets retained with the repo.

If you only need to validate the paper artifact, start with `repro/run_review_artifact.sh` and ignore the rest.
