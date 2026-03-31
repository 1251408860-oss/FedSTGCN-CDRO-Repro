#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


def load_json(path: str | Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def bar_panel(ax, labels, values, title, ylabel, color):
    ax.bar(range(len(labels)), values, color=color, edgecolor="black", linewidth=0.8)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_title(title, fontsize=11)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25, linestyle="--")


def main() -> None:
    root = Path("/home/user/FedSTGCN")
    mech_main = load_json(root / "cdro_suite/mechanism_main_s3_v1/mechanism_probe_summary.json")
    mech_batch2 = load_json(root / "cdro_suite/mechanism_batch2_s3_v1/mechanism_probe_summary.json")
    fp_main = load_json(root / "cdro_suite/main_rewrite_sw0_s5_v1/fp_sources_ug_vs_noisy.json")
    fp_batch2 = load_json(root / "cdro_suite/batch2_rewrite_sw0_s3_v2/fp_sources_ug_vs_noisy.json")

    out_dir = root / "cdro_suite/mechanism_figs"
    out_dir.mkdir(parents=True, exist_ok=True)

    variants = mech_main["config"]["variants"]
    short_labels = {
        "sw0_full": "full",
        "sw0_lossonly": "loss-only",
        "sw0_uniform": "uniform",
        "sw0_b035": "b=0.35",
        "sw0_b075": "b=0.75",
    }
    labels = [short_labels.get(v, v) for v in variants]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    main_f1 = [mech_main["stats"]["pooled"][v]["f1"]["mean"] for v in variants]
    main_fpr = [mech_main["stats"]["pooled"][v]["fpr"]["mean"] for v in variants]
    batch2_f1 = [mech_batch2["stats"]["pooled"][v]["f1"]["mean"] for v in variants]
    batch2_fpr = [mech_batch2["stats"]["pooled"][v]["fpr"]["mean"] for v in variants]

    bar_panel(axes[0, 0], labels, main_f1, "Main Probe: Pooled F1", "F1", "#3C6E71")
    bar_panel(axes[0, 1], labels, main_fpr, "Main Probe: Pooled FPR", "FPR", "#D9A441")
    bar_panel(axes[1, 0], labels, batch2_f1, "Batch2 Probe: Pooled F1", "F1", "#284B63")
    bar_panel(axes[1, 1], labels, batch2_fpr, "Batch2 Probe: Pooled FPR", "FPR", "#C1666B")
    fig.suptitle("sw0 Mechanism Probe", fontsize=14)
    fig.savefig(out_dir / "fig_mechanism_probe.png", dpi=220)
    plt.close(fig)

    main_attack_groups = fp_main["per_protocol"]["weak_attack_strategy_ood"]["group_bucket"]
    batch2_groups = fp_batch2["pooled"]["group_bucket"]
    weak_buckets = fp_batch2["pooled"]["weak_bucket"]
    group_labels = list(main_attack_groups.keys())
    weak_labels = list(weak_buckets.keys())

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), constrained_layout=True)
    bar_panel(
        axes[0],
        group_labels,
        [main_attack_groups[k]["delta_fpr"] for k in group_labels],
        "Main Attack-Strategy: delta FPR",
        "cdro_ug - noisy_ce",
        "#4C956C",
    )
    bar_panel(
        axes[1],
        list(batch2_groups.keys()),
        [batch2_groups[k]["delta_fpr"] for k in batch2_groups],
        "Batch2 Pooled Group delta FPR",
        "cdro_ug - noisy_ce",
        "#2C699A",
    )
    bar_panel(
        axes[2],
        weak_labels,
        [weak_buckets[k]["delta_fpr"] for k in weak_labels],
        "Batch2 Pooled Weak-Bucket delta FPR",
        "cdro_ug - noisy_ce",
        "#B56576",
    )
    for ax in axes:
        ax.axhline(0.0, color="black", linewidth=0.8, alpha=0.8)
    fig.suptitle("Where sw0 Reduces False Positives", fontsize=14)
    fig.savefig(out_dir / "fig_fp_sources.png", dpi=220)
    plt.close(fig)

    print(out_dir)


if __name__ == "__main__":
    main()
