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

## Legacy Capture / Recharge Scripts

The older recharge and capture helpers are still preserved in this folder for project history and internal reuse, but the reviewer-facing paper reproduction path should use `run_review_artifact.sh`.
