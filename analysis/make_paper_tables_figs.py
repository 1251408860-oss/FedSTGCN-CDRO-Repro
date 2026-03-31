#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite-dir", default="/home/user/FedSTGCN/top_conf_suite_final")
    args = ap.parse_args()

    base = Path(args.suite_dir)
    out = base / "paper_ready"
    out.mkdir(parents=True, exist_ok=True)

    top = read_json(base / "top_conf_summary.json")
    baseline = read_json(base / "baseline_significance" / "baseline_significance_summary.json")
    fed_cross = read_json(base / "fed_cross_protocol" / "fed_cross_protocol_summary.json")
    fed_ext = read_json(base / "fed_sig_ext9" / "fed_sig_ext9_summary.json")

    # ---------------- table 1: stage3 main ----------------
    t1 = [["protocol", "model", "f1_mean", "f1_std", "recall_mean", "recall_std", "n"]]
    stage3_stats = top["statistics"]["stage3"]
    protocols = ["temporal_ood", "topology_ood", "attack_strategy_ood"]
    for proto in protocols:
        clean = stage3_stats[proto]["clean"]
        for model in ["data_only", "physics_stable"]:
            f1 = clean[model]["f1"]
            rc = clean[model]["recall"]
            t1.append([proto, model, f1["mean"], f1["std"], rc["mean"], rc["std"], f1["n"]])
    write_csv(out / "table1_stage3_main.csv", t1)

    # ---------------- table 2: baseline ----------------
    t2 = [["protocol", "model", "f1_mean", "f1_std", "recall_mean", "recall_std", "fpr_mean", "fpr_std"]]
    for proto in protocols:
        s = baseline["stats"][proto]
        for model in ["random_forest", "gcn", "pi_gnn"]:
            t2.append(
                [
                    proto,
                    model,
                    s[model]["f1"]["mean"],
                    s[model]["f1"]["std"],
                    s[model]["recall"]["mean"],
                    s[model]["recall"]["std"],
                    s[model]["fpr"]["mean"],
                    s[model]["fpr"]["std"],
                ]
            )
    write_csv(out / "table2_baseline.csv", t2)

    # ---------------- table 3: federated cross-protocol ----------------
    t3 = [["protocol", "aggregation", "f1_mean", "f1_std", "recall_mean", "recall_std", "fpr_mean", "fpr_std"]]
    for proto in protocols:
        s = fed_cross["stats"][proto]
        for agg in ["fedavg", "median", "shapley_proxy"]:
            t3.append(
                [
                    proto,
                    agg,
                    s[agg]["f1_mean"],
                    s[agg]["f1_std"],
                    s[agg]["recall_mean"],
                    s[agg]["recall_std"],
                    s[agg]["fpr_mean"],
                    s[agg]["fpr_std"],
                ]
            )
    write_csv(out / "table3_fed_cross_protocol.csv", t3)

    # ---------------- table 4: significance summary ----------------
    sig_lines = []
    sig_lines.append("# Significance Summary")
    sig_lines.append("")
    sig_lines.append("## Stage-3 (Physics vs Data-only, clean)")
    for proto in protocols:
        p = stage3_stats[proto]["clean"]["significance_vs_data_only"]["p_value_f1"]
        sig_lines.append(f"- {proto}: p(F1) = {p:.6g}")
    sig_lines.append("")
    sig_lines.append("## Federated (High poison, 9-seed)")
    sig_lines.append(f"- Shapley vs FedAvg: p(F1) = {fed_ext['p_values']['shapley_vs_fedavg_f1']:.6g}")
    sig_lines.append(f"- Median vs FedAvg: p(F1) = {fed_ext['p_values']['median_vs_fedavg_f1']:.6g}")
    sig_lines.append("")
    sig_lines.append("## Federated Cross-Protocol (pooled 3 protocols x 5 seeds)")
    sig_lines.append(f"- Shapley vs FedAvg: p(F1) = {fed_cross['p_values']['pooled_shapley_vs_fedavg_f1']:.6g}")
    sig_lines.append(f"- Median vs FedAvg: p(F1) = {fed_cross['p_values']['pooled_median_vs_fedavg_f1']:.6g}")
    (out / "table4_significance.md").write_text("\n".join(sig_lines), encoding="utf-8")

    # ---------------- figure 1: stage3 clean F1 ----------------
    x = np.arange(len(protocols))
    w = 0.35
    f1_data = [stage3_stats[p]["clean"]["data_only"]["f1"]["mean"] for p in protocols]
    f1_phys = [stage3_stats[p]["clean"]["physics_stable"]["f1"]["mean"] for p in protocols]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar(x - w / 2, f1_data, width=w, label="Data-only", color="#1f77b4")
    ax.bar(x + w / 2, f1_phys, width=w, label="Physics-stable", color="#d62728")
    ax.set_xticks(x)
    ax.set_xticklabels(protocols, rotation=10)
    ax.set_ylim(0.90, 1.00)
    ax.set_ylabel("F1")
    ax.set_title("Stage-3 Clean OOD Performance")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "fig1_stage3_clean_f1.png", dpi=220)
    plt.close(fig)

    # ---------------- figure 2: federated poison robustness ----------------
    fed_stats = top["statistics"]["federated"]
    poison = ["clean", "poison_mid", "poison_high"]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(poison, [fed_stats[p]["fedavg"]["f1"]["mean"] for p in poison], "o-", label="FedAvg", color="#1f77b4")
    ax.plot(poison, [fed_stats[p]["median"]["f1"]["mean"] for p in poison], "s-", label="Median", color="#2ca02c")
    ax.plot(poison, [fed_stats[p]["shapley_proxy"]["f1"]["mean"] for p in poison], "^-", label="Shapley", color="#d62728")
    ax.set_ylim(0.4, 1.0)
    ax.set_ylabel("F1")
    ax.set_title("Federated Robustness vs Poisoning")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "fig2_fed_poison_robustness.png", dpi=220)
    plt.close(fig)

    # ---------------- figure 3: cross-protocol fedavg vs shapley ----------------
    fig, ax = plt.subplots(figsize=(8, 4.8))
    xa = np.arange(len(protocols))
    ax.bar(xa - w / 2, [fed_cross["stats"][p]["fedavg"]["f1_mean"] for p in protocols], w, label="FedAvg", color="#1f77b4")
    ax.bar(xa + w / 2, [fed_cross["stats"][p]["shapley_proxy"]["f1_mean"] for p in protocols], w, label="Shapley", color="#d62728")
    ax.set_xticks(xa)
    ax.set_xticklabels(protocols, rotation=10)
    ax.set_ylim(0.6, 1.0)
    ax.set_ylabel("F1")
    ax.set_title("Cross-Protocol Federated Robustness (High Poison)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "fig3_fed_cross_protocol.png", dpi=220)
    plt.close(fig)

    print(f"[DONE] paper-ready artifacts: {out}")


if __name__ == "__main__":
    main()
