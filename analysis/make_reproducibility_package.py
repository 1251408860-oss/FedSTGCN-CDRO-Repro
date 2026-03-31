#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import torch


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def suite_output_dir(summary: dict[str, Any]) -> Path:
    return Path(summary["config"]["output_dir"]).resolve()


def main() -> None:
    ap = argparse.ArgumentParser(description="Build reproducibility package for the weak-supervision/CDRO paper")
    ap.add_argument("--main-summary", default="/home/user/FedSTGCN/cdro_suite/main_baselineplus_s3_v1/cdro_summary.json")
    ap.add_argument("--external-summary", default="/home/user/FedSTGCN/cdro_suite/batch2_baselineplus_s3_v1/cdro_summary.json")
    ap.add_argument("--output-dir", default="/home/user/FedSTGCN/cdro_suite/repro_package_v1")
    ap.add_argument("--paper-dir", default="/home/user/FedSTGCN/cdro_suite/paper_ready_plus")
    args = ap.parse_args()

    out_dir = Path(args.output_dir).resolve()
    paper_dir = Path(args.paper_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    paper_dir.mkdir(parents=True, exist_ok=True)

    main_summary = load_json(Path(args.main_summary).resolve())
    external_summary = load_json(Path(args.external_summary).resolve())
    main_suite_dir = suite_output_dir(main_summary)
    external_suite_dir = suite_output_dir(external_summary)
    main_graph = torch.load(main_suite_dir / "protocol_graphs" / "weak_attack_strategy_ood.pt", map_location="cpu", weights_only=False)
    weak_sidecar = torch.load(external_suite_dir / "weak_labels" / "scenario_j_three_tier_high_b2_weak_labels.pt", map_location="cpu", weights_only=False)

    graph_schema = {
        "num_nodes": int(main_graph.num_nodes),
        "x_shape": list(main_graph.x.shape),
        "edge_index_shape": list(main_graph.edge_index.shape),
        "edge_type_shape": list(main_graph.edge_type.shape),
        "required_fields": [
            "x",
            "y",
            "edge_index",
            "edge_type",
            "train_mask",
            "val_mask",
            "test_mask",
            "temporal_test_mask",
            "window_idx",
            "ip_idx",
            "source_ips",
            "weak_label",
            "weak_posterior",
            "weak_agreement",
            "weak_uncertainty",
            "rho_proxy",
        ],
        "feature_index": {str(k): int(v) for k, v in getattr(main_graph, "feature_index", {}).items()},
    }
    write_text(out_dir / "schema" / "graph_schema.json", json.dumps(graph_schema, indent=2))
    write_text(
        out_dir / "schema" / "graph_schema.md",
        "\n".join(
            [
                "# Graph Schema",
                "",
                "Required graph fields for the weak-supervision/CDRO experiments:",
                "",
                *[f"- `{name}`" for name in graph_schema["required_fields"]],
                "",
                f"Representative shape: `x={tuple(graph_schema['x_shape'])}`, `edge_index={tuple(graph_schema['edge_index_shape'])}`.",
                "",
                "Feature index:",
                "",
                *[f"- `{k}` -> `{v}`" for k, v in graph_schema["feature_index"].items()],
            ]
        ),
    )

    sidecar_schema = {
        "keys": list(weak_sidecar.keys()),
        "shapes": {k: list(v.shape) for k, v in weak_sidecar.items() if hasattr(v, "shape")},
        "view_names": list(weak_sidecar["view_names"]),
        "scenario_tags": dict(weak_sidecar["scenario_tags"]),
    }
    write_text(out_dir / "schema" / "weak_label_sidecar_schema.json", json.dumps(sidecar_schema, indent=2))
    write_text(
        out_dir / "schema" / "weak_label_sidecar_format.md",
        "\n".join(
            [
                "# Weak-Label Sidecar Format",
                "",
                "Serialized keys:",
                "",
                *[f"- `{key}`" for key in sidecar_schema["keys"]],
                "",
                "View names:",
                "",
                *[f"- `{name}`" for name in sidecar_schema["view_names"]],
                "",
                "Representative tensor shapes:",
                "",
                *[f"- `{k}`: `{tuple(v)}`" for k, v in sidecar_schema["shapes"].items()],
            ]
        ),
    )

    for name, summary in [("main", main_summary), ("external_j", external_summary)]:
        suite_dir = suite_output_dir(summary)
        manifests = {
            "suite_summary": str(suite_dir),
            "base_graph": str(summary["config"]["base_graph"]),
            "manifest_file": str(summary["config"]["manifest_file"]),
            "weak_label_dir": str(suite_dir / "weak_labels"),
            "protocol_graphs": {},
        }
        for proto, info in summary["protocol_graphs"].items():
            manifests["protocol_graphs"][proto] = {
                "graph_file": info["graph_file"],
                "summary_file": info["summary_file"],
            }
        write_text(out_dir / "protocol_split_manifests" / f"{name}_protocol_splits.json", json.dumps(manifests, indent=2))

    script_map = {
        "run_public_http_sanity.sh": "set -e\n/home/user/miniconda3/envs/DL/bin/python /home/user/FedSTGCN/pipelines/run_public_http_sanity_suite.py\n",
        "run_label_budget.sh": "set -e\n/home/user/miniconda3/envs/DL/bin/python /home/user/FedSTGCN/pipelines/run_cdro_budget_suite.py --force-cpu\n",
        "run_non_graph_clean.sh": "set -e\n/home/user/miniconda3/envs/DL/bin/python /home/user/FedSTGCN/pipelines/run_non_graph_clean_upper_suite.py --force-cpu\n",
        "run_deployment_checks.sh": "set -e\n/home/user/miniconda3/envs/DL/bin/python /home/user/FedSTGCN/analysis/make_deployment_artifacts.py\n",
        "run_attack_family_breakdown.sh": "set -e\n/home/user/miniconda3/envs/DL/bin/python /home/user/FedSTGCN/analysis/make_attack_family_breakdown.py\n",
        "run_analyst_case_studies.sh": "set -e\n/home/user/miniconda3/envs/DL/bin/python /home/user/FedSTGCN/analysis/make_analyst_case_studies.py\n",
        "run_reproducibility_package.sh": "set -e\n/home/user/miniconda3/envs/DL/bin/python /home/user/FedSTGCN/analysis/make_reproducibility_package.py\n",
    }
    for filename, body in script_map.items():
        path = out_dir / "scripts" / filename
        write_text(path, "#!/usr/bin/env bash\n" + body)
        path.chmod(0o755)

    sample_graph = torch.load(external_suite_dir / "protocol_graphs" / "weak_attack_strategy_ood.pt", map_location="cpu", weights_only=False)
    sample_idx = torch.nonzero(sample_graph.temporal_test_mask.bool(), as_tuple=False).view(-1)[:12]
    sampled_nodes = []
    anon_ips: dict[int, str] = {}
    for order, idx_t in enumerate(sample_idx.tolist()):
        ip_i = int(sample_graph.ip_idx[idx_t].item())
        anon_ips.setdefault(ip_i, f"sample_ip_{len(anon_ips):03d}")
        sampled_nodes.append(
            {
                "sample_node_id": order,
                "anon_ip": anon_ips[ip_i],
                "window_idx": int(sample_graph.window_idx[idx_t].item()),
                "label": int(sample_graph.y[idx_t].item()),
                "features": [float(x) for x in sample_graph.x[idx_t].tolist()],
                "weak_label": int(sample_graph.weak_label[idx_t].item()),
                "weak_posterior": [float(x) for x in sample_graph.weak_posterior[idx_t].tolist()],
                "weak_agreement": float(sample_graph.weak_agreement[idx_t].item()),
                "weak_uncertainty": float(sample_graph.weak_uncertainty[idx_t].item()),
                "rho_proxy": float(sample_graph.rho_proxy[idx_t].item()),
                "view_probs": [float(x) for x in sample_graph.weak_view_probs[idx_t].tolist()],
            }
        )
    sample_payload = {
        "description": "Small sanitized node slice from external-J weak_attack_strategy_ood. IPs are anonymized and only numeric graph/weak-label fields are retained.",
        "feature_index": {str(k): int(v) for k, v in getattr(sample_graph, "feature_index", {}).items()},
        "nodes": sampled_nodes,
    }
    write_text(out_dir / "sample" / "sanitized_node_slice.json", json.dumps(sample_payload, indent=2))

    package_manifest = {
        "schemas": [
            "schema/graph_schema.json",
            "schema/graph_schema.md",
            "schema/weak_label_sidecar_schema.json",
            "schema/weak_label_sidecar_format.md",
        ],
        "protocol_split_manifests": [
            "protocol_split_manifests/main_protocol_splits.json",
            "protocol_split_manifests/external_j_protocol_splits.json",
        ],
        "scripts": sorted(script_map),
        "sample": ["sample/sanitized_node_slice.json"],
    }
    write_text(out_dir / "package_manifest.json", json.dumps(package_manifest, indent=2))
    write_text(
        out_dir / "README.md",
        "\n".join(
            [
                "# Weak-Supervision/CDRO Reproducibility Package",
                "",
                "Contents:",
                "",
                "- `schema/`: graph schema and weak-label sidecar format.",
                "- `protocol_split_manifests/`: source/target split manifests for main and external-J suites.",
                "- `scripts/`: one-command wrappers for the added public benchmark, budget, deployment, family, and case-study analyses.",
                "- `sample/`: small sanitized JSON slice with graph features plus weak-label sidecar fields.",
                "",
                "This package is intended for paper reproducibility when the full private raw captures cannot be released.",
            ]
        ),
    )

    write_text(
        paper_dir / "reproducibility_package.md",
        "\n".join(
            [
                "# Reproducibility Package",
                "",
                f"Package root: `{out_dir}`.",
                "",
                "Included items:",
                "",
                "- Graph schema.",
                "- Weak-label sidecar format.",
                "- Main / external-J protocol split manifests.",
                "- Runnable wrapper scripts for the added experiments.",
                "- A small sanitized JSON node slice.",
            ]
        ),
    )


if __name__ == "__main__":
    main()
