# Reproducibility Guide

## Reviewer Entry Point

Full replay:

```bash
PYTHON_BIN=/home/user/miniconda3/envs/DL/bin/python bash repro/run_review_artifact.sh
```

Quick verification without retraining:

```bash
PYTHON_BIN=/home/user/miniconda3/envs/DL/bin/python bash repro/run_review_artifact.sh --skip-rerun
```

Reference documentation:

- `../README.md`
- `../REPRODUCIBILITY.md`

## Environment Files

- `environment-lock-dl.yml`
- `requirements-lock-dl.txt`
- `requirements-lock-plot.txt`
- `Dockerfile.eval`
- `../env/DL_env_export.yml`

This folder intentionally keeps only the reviewer-facing replay surface. Older recharge-oriented orchestration helpers were removed because they depended on unreleased/private collection paths and were not part of the paper reproduction contract.
