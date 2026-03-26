#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
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


def main() -> None:
    ap = argparse.ArgumentParser(description="Make paper-ready public HTTP benchmark artifacts")
    ap.add_argument("--summary-json", default="/home/user/FedSTGCN/cdro_suite/public_http_biblio_us17_s3_v1/public_summary.json")
    ap.add_argument("--significance-json", default="/home/user/FedSTGCN/cdro_suite/public_http_biblio_us17_s3_v1/public_significance.json")
    ap.add_argument("--bundle-summary-json", default="/home/user/FedSTGCN/public_http_biblio_us17/public_http_biblio_us17_summary.json")
    ap.add_argument("--paper-dir", default="/home/user/FedSTGCN/cdro_suite/paper_ready_plus")
    args = ap.parse_args()

    summary = load_json(Path(args.summary_json).resolve())
    sig = load_json(Path(args.significance_json).resolve())
    bundle_summary = load_json(Path(args.bundle_summary_json).resolve())
    paper_dir = Path(args.paper_dir).resolve()
    paper_dir.mkdir(parents=True, exist_ok=True)
    metadata = bundle_summary.get("metadata", {})
    dataset_label = str(metadata.get("dataset_label") or metadata.get("dataset") or "Public HTTP")
    dataset_description = str(
        metadata.get("dataset_description")
        or f"{dataset_label} public HTTP request corpus, prepared into a compact weak-supervision tabular benchmark."
    )

    methods = ["noisy_ce", "posterior_ce", "cdro_fixed", "cdro_ug"]
    labels = {
        "noisy_ce": "Noisy-CE",
        "posterior_ce": "Posterior-CE",
        "cdro_fixed": "CDRO-Fixed",
        "cdro_ug": "CDRO-UG(sw0)",
    }

    rows = []
    for method in methods:
        metrics = [run["metrics"] for run in summary["runs"] if run["method"] == method]
        f1_mean, f1_std = agg([m["f1"] for m in metrics])
        fpr_mean, fpr_std = agg([m["fpr"] for m in metrics])
        ece_mean, ece_std = agg([m["ece"] for m in metrics])
        brier_mean, brier_std = agg([m["brier"] for m in metrics])
        rows.append(
            {
                "method": method,
                "label": labels[method],
                "n": len(metrics),
                "f1_mean": f1_mean,
                "f1_std": f1_std,
                "fpr_mean": fpr_mean,
                "fpr_std": fpr_std,
                "ece_mean": ece_mean,
                "ece_std": ece_std,
                "brier_mean": brier_mean,
                "brier_std": brier_std,
            }
        )

    csv_path = paper_dir / "table15_public_http_benchmark.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "method",
                "label",
                "n",
                "f1_mean",
                "f1_std",
                "fpr_mean",
                "fpr_std",
                "ece_mean",
                "ece_std",
                "brier_mean",
                "brier_std",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    sig_lines = []
    for comp in sig["comparisons"]:
        a = labels[comp["method_a"]]
        b = labels[comp["method_b"]]
        pooled = comp["pooled"]
        sig_lines.append(
            f"- `{a}` vs `{b}`: delta F1 `{pooled['f1']['delta_mean']:+.3f}`, "
            f"delta FPR `{pooled['fpr']['delta_mean']:+.3f}`, delta ECE `{pooled['ece']['delta_mean']:+.3f}`."
        )

    md = [
        "# Public HTTP Benchmark",
        "",
        f"Dataset: `{dataset_label}` {dataset_description}",
        "",
        f"Train weak-label coverage: `{100.0 * bundle_summary['weak_supervision']['train_coverage']:.1f}%`.",
        f"Weak attack precision on train-covered nodes: `{bundle_summary['weak_supervision']['weak_attack_precision_train']:.3f}`.",
        f"Weak benign precision on train-covered nodes: `{bundle_summary['weak_supervision']['weak_benign_precision_train']:.3f}`.",
        "",
        "## Results",
        "",
        "| Method | F1 | FPR | ECE | Brier |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        md.append(
            f"| {row['label']} | {row['f1_mean']:.3f} +- {row['f1_std']:.3f} | "
            f"{row['fpr_mean']:.3f} +- {row['fpr_std']:.3f} | "
            f"{row['ece_mean']:.3f} +- {row['ece_std']:.3f} | "
            f"{row['brier_mean']:.3f} +- {row['brier_std']:.3f} |"
        )
    md.extend(
        [
            "",
            "## Pairwise Readout",
            "",
            *sig_lines,
            "",
            f"Artifact table: `{csv_path.name}`.",
        ]
    )
    (paper_dir / "public_http_benchmark.md").write_text("\n".join(md), encoding="utf-8")


if __name__ == "__main__":
    main()
