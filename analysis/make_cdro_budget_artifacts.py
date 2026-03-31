#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

import matplotlib.pyplot as plt


def agg(vals: list[float]) -> tuple[float, float]:
    if not vals:
        return 0.0, 0.0
    if len(vals) == 1:
        return float(vals[0]), 0.0
    return float(mean(vals)), float(pstdev(vals))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Make paper-ready label-budget artifacts")
    ap.add_argument("--summary-json", default="/home/user/FedSTGCN/cdro_suite/label_budget_s3_v1/budget_summary.json")
    ap.add_argument("--paper-dir", default="/home/user/FedSTGCN/cdro_suite/paper_ready_plus")
    args = ap.parse_args()

    summary = load_json(Path(args.summary_json).resolve())
    paper_dir = Path(args.paper_dir).resolve()
    paper_dir.mkdir(parents=True, exist_ok=True)

    rows_by_key: dict[tuple[str, float, str], list[dict[str, Any]]] = defaultdict(list)
    effective_budget_by_key: dict[tuple[str, float], list[float]] = defaultdict(list)
    for budget_id, info in summary["budget_graphs"].items():
        _ = budget_id
        meta = info["stress_meta"]
        before = max(1, int(meta["covered_train_nodes_before"]))
        after = int(meta["covered_train_nodes_after"])
        effective_budget_by_key[(info["dataset"], float(info["budget"]))].append(after / before)
    for run in summary["runs"]:
        rows_by_key[(run["dataset"], float(run["budget"]), run["method"])].append(run["metrics"])

    methods = ["noisy_ce", "cdro_fixed", "cdro_ug"]
    datasets = ["main", "external_j"]
    budgets = sorted({float(run["budget"]) for run in summary["runs"]})

    csv_rows: list[dict[str, Any]] = []
    table_map: dict[str, dict[float, dict[str, dict[str, float]]]] = defaultdict(lambda: defaultdict(dict))
    for dataset in datasets:
        for budget in budgets:
            eff_mean, eff_std = agg(effective_budget_by_key[(dataset, budget)])
            for method in methods:
                metrics_list = rows_by_key[(dataset, budget, method)]
                f1_mean, f1_std = agg([m.get("f1", 0.0) for m in metrics_list])
                fpr_mean, fpr_std = agg([m.get("fpr", 0.0) for m in metrics_list])
                ece_mean, ece_std = agg([m.get("ece", 0.0) for m in metrics_list])
                csv_rows.append(
                    {
                        "dataset": dataset,
                        "budget": budget,
                        "effective_budget_mean": eff_mean,
                        "effective_budget_std": eff_std,
                        "method": method,
                        "n": len(metrics_list),
                        "f1_mean": f1_mean,
                        "f1_std": f1_std,
                        "fpr_mean": fpr_mean,
                        "fpr_std": fpr_std,
                        "ece_mean": ece_mean,
                        "ece_std": ece_std,
                    }
                )
                table_map[dataset][budget][method] = {
                    "f1_mean": f1_mean,
                    "f1_std": f1_std,
                    "fpr_mean": fpr_mean,
                    "fpr_std": fpr_std,
                    "ece_mean": ece_mean,
                    "ece_std": ece_std,
                }

    csv_path = paper_dir / "table16_label_budget.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "dataset",
                "budget",
                "effective_budget_mean",
                "effective_budget_std",
                "method",
                "n",
                "f1_mean",
                "f1_std",
                "fpr_mean",
                "fpr_std",
                "ece_mean",
                "ece_std",
            ],
        )
        writer.writeheader()
        writer.writerows(csv_rows)

    fig_path = paper_dir / "fig9_label_budget.png"
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), sharex=True)
    style = {
        "noisy_ce": {"label": "Noisy-CE", "color": "#444444", "marker": "o"},
        "cdro_fixed": {"label": "CDRO-Fixed", "color": "#1f77b4", "marker": "s"},
        "cdro_ug": {"label": "CDRO-UG(sw0)", "color": "#d62728", "marker": "^"},
    }
    for row_idx, dataset in enumerate(datasets):
        xs = [100.0 * b for b in budgets]
        for method in methods:
            label = style[method]["label"]
            color = style[method]["color"]
            marker = style[method]["marker"]
            f1s = [table_map[dataset][budget][method]["f1_mean"] for budget in budgets]
            fprs = [table_map[dataset][budget][method]["fpr_mean"] for budget in budgets]
            axes[row_idx, 0].plot(xs, f1s, label=label, color=color, marker=marker, linewidth=2)
            axes[row_idx, 1].plot(xs, fprs, label=label, color=color, marker=marker, linewidth=2)
        axes[row_idx, 0].set_ylabel(f"{dataset}\nF1")
        axes[row_idx, 1].set_ylabel(f"{dataset}\nFPR")
        axes[row_idx, 0].grid(alpha=0.25)
        axes[row_idx, 1].grid(alpha=0.25)
    axes[1, 0].set_xlabel("Weak-label budget (%)")
    axes[1, 1].set_xlabel("Weak-label budget (%)")
    axes[0, 0].legend(frameon=False, ncol=3, loc="lower right")
    fig.tight_layout()
    fig.savefig(fig_path, dpi=220, bbox_inches="tight")
    plt.close(fig)

    md_lines = [
        "# Label-Budget Sweep",
        "",
        "Settings: `weak_topology_ood + weak_attack_strategy_ood`, seeds `11/22/33`, methods `Noisy-CE / CDRO-Fixed / CDRO-UG(sw0)`.",
        "",
        f"Artifacts: `{csv_path.name}`, `{fig_path.name}`.",
        "",
        "## Pooled Means",
        "",
    ]
    for dataset in datasets:
        md_lines.append(f"### {dataset}")
        md_lines.append("")
        md_lines.append("| Budget | Effective | Noisy-CE F1 / FPR | CDRO-Fixed F1 / FPR | CDRO-UG(sw0) F1 / FPR |")
        md_lines.append("|---:|---:|---:|---:|---:|")
        for budget in budgets:
            eff_mean, _ = agg(effective_budget_by_key[(dataset, budget)])
            def cell(method: str) -> str:
                vals = table_map[dataset][budget][method]
                return f"{vals['f1_mean']:.3f} / {vals['fpr_mean']:.3f}"
            md_lines.append(
                f"| {100.0 * budget:.0f}% | {100.0 * eff_mean:.1f}% | {cell('noisy_ce')} | {cell('cdro_fixed')} | {cell('cdro_ug')} |"
            )
        md_lines.append("")

        best_low_budget = max((budget for budget in budgets if budget <= 0.20), key=lambda b: table_map[dataset][b]["cdro_ug"]["f1_mean"])
        ug_low = table_map[dataset][best_low_budget]["cdro_ug"]
        noisy_low = table_map[dataset][best_low_budget]["noisy_ce"]
        fixed_low = table_map[dataset][best_low_budget]["cdro_fixed"]
        md_lines.append(
            f"Low-budget readout ({100.0 * best_low_budget:.0f}%): `CDRO-UG(sw0)` F1 `{ug_low['f1_mean']:.3f}`, "
            f"vs `Noisy-CE` `{noisy_low['f1_mean']:.3f}` and `CDRO-Fixed` `{fixed_low['f1_mean']:.3f}`."
        )
        md_lines.append("")

    save_markdown(paper_dir / "label_budget.md", "\n".join(md_lines))


if __name__ == "__main__":
    main()
