#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def mean_std(vals: list[float]) -> dict[str, float]:
    if not vals:
        return {"n": 0, "mean": 0.0, "std": 0.0}
    if len(vals) == 1:
        return {"n": 1, "mean": float(vals[0]), "std": 0.0}
    return {"n": len(vals), "mean": float(statistics.mean(vals)), "std": float(statistics.stdev(vals))}


def write_csv(path: Path, rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerows(rows)


def summarize_stage3(summary: dict[str, Any]) -> list[dict[str, Any]]:
    runs = summary.get("stage3_runs", [])
    rows: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], list[float]] = {}
    for run in runs:
        key = (str(run.get("poison_case", "clean")), str(run.get("model", "unknown")))
        grouped.setdefault(key, []).append(float(run.get("duration_sec", 0.0)))

    baseline_mean = mean_std(grouped.get(("clean", "data_only"), []))["mean"]
    for (poison_case, model), vals in sorted(grouped.items()):
        stats = mean_std(vals)
        rows.append(
            {
                "category": "stage3",
                "group": poison_case,
                "method": model,
                "n": stats["n"],
                "mean_sec": stats["mean"],
                "std_sec": stats["std"],
                "delta_vs_clean_data_sec": stats["mean"] - baseline_mean,
                "ratio_vs_clean_data": (stats["mean"] / baseline_mean) if baseline_mean > 0 else 0.0,
            }
        )
    return rows


def summarize_federated(summary: dict[str, Any]) -> list[dict[str, Any]]:
    runs = summary.get("federated_runs", [])
    rows: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], list[float]] = {}
    for run in runs:
        key = (str(run.get("poison_case", "clean")), str(run.get("aggregation", "unknown")))
        grouped.setdefault(key, []).append(float(run.get("duration_sec", 0.0)))

    baseline_means: dict[str, float] = {}
    for poison_case, _ in grouped.keys():
        baseline_means[poison_case] = mean_std(grouped.get((poison_case, "fedavg"), []))["mean"]

    for (poison_case, aggregation), vals in sorted(grouped.items()):
        stats = mean_std(vals)
        baseline_mean = baseline_means.get(poison_case, 0.0)
        rows.append(
            {
                "category": "federated",
                "group": poison_case,
                "method": aggregation,
                "n": stats["n"],
                "mean_sec": stats["mean"],
                "std_sec": stats["std"],
                "delta_vs_same_case_fedavg_sec": stats["mean"] - baseline_mean,
                "ratio_vs_same_case_fedavg": (stats["mean"] / baseline_mean) if baseline_mean > 0 else 0.0,
            }
        )
    return rows


def summarize_optional_classic(root: Path) -> list[dict[str, Any]]:
    summary_path = root / "fed_classic_robust_baselines" / "fed_classic_robust_baselines_summary.json"
    if not summary_path.exists():
        return []

    data = read_json(summary_path)
    runs = data.get("runs", [])
    grouped: dict[str, list[float]] = {}
    for run in runs:
        grouped.setdefault(str(run.get("aggregation", "unknown")), []).append(float(run.get("duration_sec", 0.0)))

    baseline_mean = mean_std(grouped.get("fedavg", []))["mean"]
    rows: list[dict[str, Any]] = []
    for aggregation, vals in sorted(grouped.items()):
        stats = mean_std(vals)
        rows.append(
            {
                "category": "fed_classic",
                "group": "supplemental",
                "method": aggregation,
                "n": stats["n"],
                "mean_sec": stats["mean"],
                "std_sec": stats["std"],
                "delta_vs_same_case_fedavg_sec": stats["mean"] - baseline_mean,
                "ratio_vs_same_case_fedavg": (stats["mean"] / baseline_mean) if baseline_mean > 0 else 0.0,
            }
        )
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="Summarize runtime cost tables for paper-ready artifacts.")
    ap.add_argument("--suite-dir", default="/home/user/FedSTGCN/top_conf_suite_recharge")
    args = ap.parse_args()

    suite_dir = Path(args.suite_dir).resolve()
    root = suite_dir.parent
    out_dir = suite_dir / "paper_ready_plus"
    out_dir.mkdir(parents=True, exist_ok=True)

    top = read_json(suite_dir / "top_conf_summary.json")
    rows = summarize_stage3(top) + summarize_federated(top) + summarize_optional_classic(root)

    csv_rows: list[list[object]] = [[
        "category",
        "group",
        "method",
        "n",
        "mean_sec",
        "std_sec",
        "delta_vs_baseline_sec",
        "ratio_vs_baseline",
    ]]
    for row in rows:
        csv_rows.append(
            [
                row["category"],
                row["group"],
                row["method"],
                row["n"],
                row["mean_sec"],
                row["std_sec"],
                row.get("delta_vs_clean_data_sec", row.get("delta_vs_same_case_fedavg_sec", 0.0)),
                row.get("ratio_vs_clean_data", row.get("ratio_vs_same_case_fedavg", 0.0)),
            ]
        )
    write_csv(out_dir / "table5_runtime_costs.csv", csv_rows)

    lines: list[str] = [
        "# Runtime Cost Summary",
        "",
        "## Stage-3",
    ]
    for row in rows:
        if row["category"] != "stage3":
            continue
        lines.append(
            f"- {row['group']} / {row['method']}: "
            f"{row['mean_sec']:.2f} +/- {row['std_sec']:.2f} s (n={row['n']}), "
            f"delta vs clean data-only = {row['delta_vs_clean_data_sec']:+.2f} s"
        )

    lines.extend(["", "## Federated"])
    for row in rows:
        if row["category"] != "federated":
            continue
        lines.append(
            f"- {row['group']} / {row['method']}: "
            f"{row['mean_sec']:.2f} +/- {row['std_sec']:.2f} s (n={row['n']}), "
            f"delta vs {row['group']} FedAvg = {row['delta_vs_same_case_fedavg_sec']:+.2f} s"
        )

    classic_rows = [row for row in rows if row["category"] == "fed_classic"]
    if classic_rows:
        lines.extend(["", "## Supplemental Classic Robust Aggregation"])
        for row in classic_rows:
            lines.append(
                f"- {row['method']}: "
                f"{row['mean_sec']:.2f} +/- {row['std_sec']:.2f} s (n={row['n']}), "
                f"delta vs supplemental FedAvg = {row['delta_vs_same_case_fedavg_sec']:+.2f} s"
            )

    (out_dir / "runtime_costs.md").write_text("\n".join(lines), encoding="utf-8")
    print(out_dir / "runtime_costs.md")


if __name__ == "__main__":
    main()
