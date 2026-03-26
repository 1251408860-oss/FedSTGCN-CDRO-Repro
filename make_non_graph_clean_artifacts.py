#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def agg(vals: list[float]) -> tuple[float, float]:
    if not vals:
        return 0.0, 0.0
    if len(vals) == 1:
        return float(vals[0]), 0.0
    return float(mean(vals)), float(pstdev(vals))


def add_runs(dst: dict[tuple[str, str], list[dict[str, float]]], dataset: str, summary: dict[str, Any], methods: set[str] | None = None) -> None:
    for run in summary["runs"]:
        method = run["method"]
        if methods is not None and method not in methods:
            continue
        dst[(dataset, method)].append(run["metrics"])


def main() -> None:
    ap = argparse.ArgumentParser(description="Make paper-ready non-graph + clean-upper artifacts")
    ap.add_argument("--main-summary", default="/home/user/FedSTGCN/cdro_suite/main_baselineplus_s3_v1/cdro_summary.json")
    ap.add_argument("--external-summary", default="/home/user/FedSTGCN/cdro_suite/batch2_baselineplus_s3_v1/cdro_summary.json")
    ap.add_argument("--new-summary", default="/home/user/FedSTGCN/cdro_suite/non_graph_clean_upper_s3_v1/non_graph_clean_summary.json")
    ap.add_argument("--paper-dir", default="/home/user/FedSTGCN/cdro_suite/paper_ready_plus")
    args = ap.parse_args()

    paper_dir = Path(args.paper_dir).resolve()
    paper_dir.mkdir(parents=True, exist_ok=True)

    pooled: dict[tuple[str, str], list[dict[str, float]]] = defaultdict(list)
    add_runs(pooled, "main", load_json(Path(args.main_summary).resolve()), methods={"noisy_ce", "cdro_fixed", "cdro_ug"})
    add_runs(pooled, "external_j", load_json(Path(args.external_summary).resolve()), methods={"noisy_ce", "cdro_fixed", "cdro_ug"})
    new_summary = load_json(Path(args.new_summary).resolve())
    for run in new_summary["runs"]:
        pooled[(run["dataset"], run["method"])].append(run["metrics"])

    methods = ["noisy_ce", "cdro_fixed", "cdro_ug", "xgboost_weak", "pignn_clean"]
    labels = {
        "noisy_ce": "Noisy-CE",
        "cdro_fixed": "CDRO-Fixed",
        "cdro_ug": "CDRO-UG(sw0)",
        "xgboost_weak": "XGBoost(weak)",
        "pignn_clean": "PI-GNN(clean)",
    }

    csv_rows: list[dict[str, Any]] = []
    table_map: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for dataset in ["main", "external_j"]:
        for method in methods:
            metrics = pooled[(dataset, method)]
            f1_mean, f1_std = agg([m.get("f1", 0.0) for m in metrics])
            fpr_mean, fpr_std = agg([m.get("fpr", 0.0) for m in metrics])
            ece_mean, ece_std = agg([m.get("ece", 0.0) for m in metrics])
            table_map[dataset][method] = {
                "f1_mean": f1_mean,
                "f1_std": f1_std,
                "fpr_mean": fpr_mean,
                "fpr_std": fpr_std,
                "ece_mean": ece_mean,
                "ece_std": ece_std,
            }
            csv_rows.append(
                {
                    "dataset": dataset,
                    "method": method,
                    "label": labels[method],
                    "n": len(metrics),
                    "f1_mean": f1_mean,
                    "f1_std": f1_std,
                    "fpr_mean": fpr_mean,
                    "fpr_std": fpr_std,
                    "ece_mean": ece_mean,
                    "ece_std": ece_std,
                }
            )

    csv_path = paper_dir / "table17_non_graph_clean_upper.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["dataset", "method", "label", "n", "f1_mean", "f1_std", "fpr_mean", "fpr_std", "ece_mean", "ece_std"],
        )
        writer.writeheader()
        writer.writerows(csv_rows)

    md_lines = [
        "# Non-Graph Baseline And Clean-Label Upper Bound",
        "",
        "Weak-label graph-family references are pooled from the existing `main_baselineplus_s3_v1` and `batch2_baselineplus_s3_v1` summaries; new runs add `XGBoost(weak)` and `PI-GNN(clean)`.",
        "",
        f"Artifact table: `{csv_path.name}`.",
        "",
    ]
    for dataset in ["main", "external_j"]:
        md_lines.append(f"## {dataset}")
        md_lines.append("")
        md_lines.append("| Method | F1 | FPR | ECE |")
        md_lines.append("|---|---:|---:|---:|")
        for method in methods:
            vals = table_map[dataset][method]
            md_lines.append(
                f"| {labels[method]} | {vals['f1_mean']:.3f} +- {vals['f1_std']:.3f} | {vals['fpr_mean']:.3f} +- {vals['fpr_std']:.3f} | {vals['ece_mean']:.3f} +- {vals['ece_std']:.3f} |"
            )
        ug = table_map[dataset]["cdro_ug"]
        xgb = table_map[dataset]["xgboost_weak"]
        clean = table_map[dataset]["pignn_clean"]
        md_lines.append("")
        md_lines.append(
            f"Graph-vs-tabular readout: `CDRO-UG(sw0)` vs `XGBoost(weak)` = "
            f"delta F1 `{ug['f1_mean'] - xgb['f1_mean']:+.3f}`, delta FPR `{ug['fpr_mean'] - xgb['fpr_mean']:+.3f}`."
        )
        md_lines.append(
            f"Weak-vs-clean gap: `PI-GNN(clean)` minus `CDRO-UG(sw0)` = "
            f"delta F1 `{clean['f1_mean'] - ug['f1_mean']:+.3f}`, delta FPR `{clean['fpr_mean'] - ug['fpr_mean']:+.3f}`."
        )
        md_lines.append("")

    (paper_dir / "non_graph_clean_upper.md").write_text("\n".join(md_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
