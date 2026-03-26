# FedSTGCN-CDRO-Repro

This repository is the reviewer-facing reproducibility release for the `CDRO-UG` conditional-shift experiments built on the FedSTGCN codebase. The release now supports full replay of the paper-aligned `main` and `external-J` suites from released processed protocol graphs, and local validation on 2026-03-26 reproduced all 96 runs with `max_metric_delta = 0.0` and `max_threshold_delta = 0.0`.

## Repository Navigation & Artifact Mapping

| Path | What it contains | Reviewer usage |
| --- | --- | --- |
| `repro/run_review_artifact.sh` | One-command reviewer entry point | Full replay or quick verification |
| `repro/review_artifact.py` | Replay / verification pipeline | Regenerates the core tables and figure |
| `REPRODUCIBILITY.md` | Exact commands, outputs, and expectations | Start here for artifact evaluation |
| `cdro_suite/main_rewrite_sw0_s5_v1/` | Paper-aligned main-batch suite | Replayed by default |
| `cdro_suite/batch2_rewrite_sw0_s3_v2/` | Paper-aligned external-J suite | Replayed by default |
| `cdro_suite/paper_ready_plus/` | Paper-ready tables, figures, and manuscript assets | Reference outputs for comparison |
| `cdro_suite/main_baselineplus_s3_v1/` | Supplementary baselineplus main suite | Extra audit / ablation support |
| `cdro_suite/batch2_baselineplus_s3_v1/` | Supplementary baselineplus external suite | Extra audit / ablation support |
| `cdro_suite/repro_package_v1/` | Lightweight schema + manifest package | Fast structure review |
| `biblio_us17/` | Public benchmark helper materials | Public-benchmark sanity path |

## Global Environment Overview

Recommended replay environment:

- Python with `torch`, `torch_geometric`, `numpy`, and `matplotlib`
- The original project environment file is kept at `repro/environment-lock-dl.yml`
- The lockfile mirror is kept at `repro/requirements-lock-dl.txt`

The commands below assume a Linux or WSL environment. In the local validation pass, the replay was executed with:

```bash
PYTHON_BIN=/home/user/miniconda3/envs/DL/bin/python
```

## Complete Reviewer Replay

Run the full paper-aligned replay:

```bash
PYTHON_BIN=/home/user/miniconda3/envs/DL/bin/python bash repro/run_review_artifact.sh
```

This command:

1. Replays all runs in `main_rewrite_sw0_s5_v1`
2. Replays all runs in `batch2_rewrite_sw0_s3_v2`
3. Regenerates paired significance summaries
4. Rebuilds the paper core tables
5. Rebuilds the pooled-results figure
6. Verifies the regenerated tables against `cdro_suite/paper_ready_plus/`

Expected outputs:

- `review_artifact/rerun/replayed_suites/main_rewrite_sw0_s5_v1/cdro_summary.json`
- `review_artifact/rerun/replayed_suites/batch2_rewrite_sw0_s3_v2/cdro_summary.json`
- `review_artifact/rerun/paper_ready/table_maintext_core_results.csv`
- `review_artifact/rerun/paper_ready/table_maintext_deployment_transfer.csv`
- `review_artifact/rerun/paper_ready/fig1_pooled_results.png`
- `review_artifact/rerun/repro_report.json`
- `review_artifact/rerun/REPRO_SUMMARY.md`

Expected report fields:

- `core_table_exact_match: true`
- `deployment_table_exact_match: true`
- `result_comparison.runs_compared: 96`
- `result_comparison.max_metric_delta: 0.0`
- `result_comparison.max_threshold_delta: 0.0`

## Quick Verification Without Retraining

If a reviewer only wants to rebuild the tables from the released run artifacts:

```bash
PYTHON_BIN=/home/user/miniconda3/envs/DL/bin/python bash repro/run_review_artifact.sh --skip-rerun
```

This writes outputs under `review_artifact/reference/` and verifies the checked-in core tables without rerunning training.

## Scope of Release

Included:

- Paper-aligned processed protocol graphs
- Weak-label sidecars
- Reference run outputs
- Reviewer replay scripts
- Paper-ready tables and figures

Not included:

- Raw private PCAPs
- Private source base graphs used before the released protocol-graph stage
- Mininet recapture workflow for private data regeneration

The public release therefore starts from processed protocol graphs, but the reported paper numbers are fully replayable from those released artifacts.
