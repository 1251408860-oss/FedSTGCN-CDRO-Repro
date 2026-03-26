# FedSTGCN CDRO Repro

This repository is a reviewer-facing reproducibility release for the `CDRO-UG` weak-supervision and conditional-shift experiments built on the FedSTGCN codebase.

## Scope

This release is meant to support paper review and artifact inspection.

It includes:

- Core training and evaluation code for the weak-supervision/CDRO pipeline
- Protocol construction scripts
- Public-benchmark preparation scripts
- A lightweight reproducibility package with schemas, manifests, wrapper scripts, and a sanitized sample slice
- Paper-ready figures, tables, and manuscript assets
- Environment locks and one-click reproduction helpers in [`repro/`](repro/README.md)

It does not include:

- Private controlled network captures
- Full raw traffic PCAPs
- Large intermediate tensors, checkpoints, or full experiment output trees

The exact private-capture runs for the main and `external-J` suites therefore cannot be replayed from raw data alone. Instead, this repository exposes the code paths, split manifests, schema definitions, lightweight replay wrappers, and sanitized sample objects needed for auditability.

## Repository Layout

- `generate_weak_supervision_views.py`: builds multi-view weak-label sidecars
- `prepare_label_shift_protocol_graph.py`: attaches weak labels and builds shifted protocol graphs
- `pi_gnn_train_cdro.py`: trains `noisy_ce`, `cdro_fixed`, `cdro_ug`, and related baselines
- `run_cdro_suite.py`: end-to-end suite runner for weak-supervision/CDRO experiments
- `analyze_cdro_fp_sources.py`: false-positive source decomposition
- `analyze_cdro_weak_label_quality.py`: weak-label quality and trust audit
- `make_reproducibility_package.py`: builds the lightweight reproducibility package
- [`repro/`](repro/README.md): environment locks and one-click scripts
- [`cdro_suite/repro_package_v1/`](cdro_suite/repro_package_v1/README.md): schemas, manifests, wrapper scripts, and sanitized sample slice
- [`cdro_suite/paper_ready_plus/`](cdro_suite/paper_ready_plus/): paper-ready tables, figures, and manuscript assets

## Suggested Reproduction Paths

### 1. Review the lightweight reproducibility package

Start with:

- [`cdro_suite/repro_package_v1/README.md`](cdro_suite/repro_package_v1/README.md)
- [`cdro_suite/repro_package_v1/package_manifest.json`](cdro_suite/repro_package_v1/package_manifest.json)

This is the smallest path to understand the graph schema, weak-label sidecar structure, split manifests, and replay entry points.

### 2. Reproduce public-benchmark processing

For the public HTTP benchmark path, inspect:

- [`prepare_public_http_biblio_us17.py`](prepare_public_http_biblio_us17.py)
- [`request_biblio_us17_copy.py`](request_biblio_us17_copy.py)
- [`biblio_us17/README.en`](biblio_us17/README.en)

### 3. Re-run artifact-generation helpers

Representative scripts:

- `run_public_http_sanity_suite.py`
- `run_non_graph_clean_upper_suite.py`
- `make_deployment_artifacts.py`
- `make_attack_family_breakdown.py`
- `make_analyst_case_studies.py`

### 4. Inspect paper-ready assets

The paper-facing figures, tables, and manuscript drafts are under:

- [`cdro_suite/paper_ready_plus/`](cdro_suite/paper_ready_plus/)

## Environment

Primary environment locks:

- [`DL_env_export.yml`](DL_env_export.yml)
- [`DL_pip_freeze.txt`](DL_pip_freeze.txt)
- [`repro/environment-lock-dl.yml`](repro/environment-lock-dl.yml)
- [`repro/requirements-lock-dl.txt`](repro/requirements-lock-dl.txt)

## Notes

This repository is intentionally scoped for review and reproducibility support. It is not a full raw-data release.
