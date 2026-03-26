# Reproducibility Package

Package root: `/home/user/FedSTGCN/cdro_suite/repro_package_v1`.

## Reviewer-facing purpose

The controlled captures used in the main graph suites remain private, so this package is designed as a transparency and replay artifact rather than as a full raw-data release. Its purpose is to let reviewers inspect the graph / weak-label interface and rerun the public or reference analyses that support the appendix.

## Included items

- `schema/graph_schema.json` and `schema/graph_schema.md`: required graph fields, representative tensor shapes, and feature-index metadata.
- `schema/weak_label_sidecar_schema.json` and `schema/weak_label_sidecar_format.md`: serialized weak-label keys, tensor shapes, view names, and scenario tags.
- `protocol_split_manifests/main_protocol_splits.json`: source graph, manifest file, weak-label directory, and protocol-graph file map for the main suite.
- `protocol_split_manifests/external_j_protocol_splits.json`: the same manifest-style record for the external-J suite.
- Replay wrappers: `run_public_http_sanity.sh`, `run_label_budget.sh`, `run_non_graph_clean.sh`, `run_deployment_checks.sh`, `run_attack_family_breakdown.sh`, `run_analyst_case_studies.sh`, and `run_reproducibility_package.sh`.
- `sample/sanitized_node_slice.json`: anonymized external-J node slice with graph features, weak posterior fields, agreement, uncertainty, `rho_proxy`, and per-view probabilities.

## Replay path

1. Inspect the schema and split-manifest files first to understand the expected graph and weak-label inputs.
2. Use the wrapper scripts to regenerate the public benchmark and appendix-facing reference analyses.
3. Use `run_reproducibility_package.sh` to rebuild the package itself from the current suite outputs.

## Safe reading

This package supports reproducibility, artifact inspection, and appendix replay. It does not remove the private-data boundary of the controlled captures, so manuscript claims should remain scoped accordingly.
