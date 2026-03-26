# Appendix Reproducibility Text

Use the following text as the appendix-facing artifact / reproducibility subsection for the BlockSys version.

## Artifact Package and Replay

Because the controlled capture graphs and raw traffic cannot be publicly released, we provide a lightweight reproducibility package that exposes the structure of the data and the exact replay hooks for the public and reference analyses. The package includes `schema/graph_schema.json` and `schema/weak_label_sidecar_schema.json`, together with their accompanying Markdown descriptions, so reviewers can inspect the required graph tensors, weak-label sidecar fields, representative shapes, view names, and feature indices. It also includes `protocol_split_manifests/main_protocol_splits.json` and `protocol_split_manifests/external_j_protocol_splits.json`, which document the source graph, weak-label directory, and protocol-graph files used by the main and external-J suites.

To make the appendix analyses replayable, the package contains executable wrappers for the added studies: `run_public_http_sanity.sh`, `run_label_budget.sh`, `run_non_graph_clean.sh`, `run_deployment_checks.sh`, `run_attack_family_breakdown.sh`, `run_analyst_case_studies.sh`, and `run_reproducibility_package.sh`. These scripts are intended as one-command entry points for regenerating the public HTTP sanity benchmark, sparse-label budget sweep, non-graph / clean-label reference checks, deployment-style transfer artifacts, per-family breakdown, analyst-facing case studies, and the package itself. Finally, `sample/sanitized_node_slice.json` provides an anonymized external-J node slice containing graph features, weak posterior fields, agreement, uncertainty, `rho` proxy values, and per-view probabilities, so reviewers can inspect the serialized data format without access to the private raw captures.

The correct claim for this package is transparency and replay support, not full raw-data release. It is sufficient for reviewers to inspect the graph / weak-label interface and to rerun the public or reference artifact chain that backs the appendix, but it does not eliminate the private-data boundary of the controlled captures.

## Shorter Variant

Because the controlled captures are private, we release a lightweight reproducibility package instead of the raw graphs. The package contains graph and weak-label schemas (`schema/graph_schema.json`, `schema/weak_label_sidecar_schema.json`), main and external-J split manifests, replay wrappers for the public benchmark and appendix analyses, and a sanitized node slice (`sample/sanitized_node_slice.json`). This package allows reviewers to inspect the expected data format and rerun the public/reference artifact chain, while keeping the paper's claims appropriately scoped to a partially private evaluation setup.
