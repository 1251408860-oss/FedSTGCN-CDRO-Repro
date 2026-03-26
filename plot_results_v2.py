#!/usr/bin/env python3
"""
Plot Phase-3 and baseline evaluation figures.

Inputs:
  - phase3_results.json
  - st_graph.pt
  - baseline_eval_results.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import torch

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    print("ERROR: matplotlib required")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RESULTS_FILE = os.path.join(BASE_DIR, "phase3_results.json")
DEFAULT_GRAPH_FILE = os.path.join(BASE_DIR, "st_graph.pt")
DEFAULT_BASELINE_FILE = os.path.join(BASE_DIR, "baseline_eval_results.json")
DEFAULT_OUTPUT_DIR = BASE_DIR

plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams.update({"font.size": 12, "figure.dpi": 200})


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def output_path(output_dir: str, prefix: str, name: str) -> str:
    if prefix:
        return os.path.join(output_dir, f"{prefix}_{name}")
    return os.path.join(output_dir, name)


def plot_loss_landscape(history: dict, output_dir: str, prefix: str = "") -> str:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    epochs = range(1, len(history.get("L_total", [])) + 1)
    ax1.plot(epochs, history.get("L_data", []), linewidth=2, color="#2C7FB8", label=r"$L_{data}$")
    ax1.plot(epochs, history.get("L_flow", []), linewidth=2, color="#D95F0E", label=r"$L_{flow}$")
    ax1.plot(epochs, history.get("L_latency", []), linewidth=2, color="#31A354", label=r"$L_{latency}$")
    ax1.set_yscale("log")
    ax1.set_xlabel("Epoch")
    ax1.set_ylabel("Loss (log)")
    ax1.set_title("Physics vs Data Loss")
    ax1.legend(loc="upper right", fontsize=10)

    ax2.plot(epochs, history.get("L_total", []), linewidth=2, color="#111111", label=r"$L_{total}$")
    val_f1 = history.get("val_f1", [])
    if val_f1:
        eval_epochs = list(range(1, 6)) + list(range(10, len(history.get("L_total", [])) + 1, 10))
        eval_epochs = eval_epochs[: len(val_f1)]
        ax2r = ax2.twinx()
        ax2r.plot(eval_epochs, val_f1, "o-", linewidth=2, color="#C51B8A", markersize=4, label="Val F1")
        ax2r.set_ylabel("Val F1")
        ax2r.set_ylim(0, 1.05)
        ax2r.legend(loc="lower right", fontsize=10)

    ax2.set_xlabel("Epoch")
    ax2.set_ylabel("Total Loss")
    ax2.set_title("Training Convergence")
    ax2.legend(loc="upper right", fontsize=10)

    plt.tight_layout()
    out = output_path(output_dir, prefix, "fig1_loss_landscape.png")
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    return out


def plot_entropy_distribution(graph: torch.Tensor, output_dir: str, prefix: str = "") -> str:
    feat_idx = getattr(graph, "feature_index", {}) if hasattr(graph, "feature_index") else {}
    if isinstance(feat_idx, dict) and "entropy" in feat_idx:
        entropy_col = int(feat_idx["entropy"])
    else:
        entropy_col = 1

    flow_mask = torch.arange(graph.num_nodes) > 0
    x = graph.x[flow_mask]
    y = graph.y[flow_mask]

    benign_entropy = x[y == 0, entropy_col].detach().cpu().numpy()
    attack_entropy = x[y == 1, entropy_col].detach().cpu().numpy()

    fig, ax = plt.subplots(figsize=(8, 5.5))
    bins = np.linspace(0, max(7.0, float(x[:, entropy_col].max().item() + 0.5)), 40)

    ax.hist(benign_entropy, bins=bins, alpha=0.7, color="#2E8B57", label=f"Benign (n={len(benign_entropy)})", density=True)
    ax.hist(attack_entropy, bins=bins, alpha=0.7, color="#C83200", label=f"Attack (n={len(attack_entropy)})", density=True)

    ax.axvline(np.mean(benign_entropy), color="#2E8B57", linestyle="--", linewidth=2)
    ax.axvline(np.mean(attack_entropy), color="#C83200", linestyle="--", linewidth=2)

    ax.set_xlabel("Shannon Entropy")
    ax.set_ylabel("Density")
    ax.set_title("Entropy Comparison: Benign vs LLM-like Attack")
    ax.legend(loc="upper left", fontsize=10)

    plt.tight_layout()
    out = output_path(output_dir, prefix, "fig2_entropy_distribution.png")
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    return out


def plot_baseline_roc(baseline: dict, output_dir: str, prefix: str = "") -> str:
    roc_points = baseline.get("roc_points", {})

    fig, ax = plt.subplots(figsize=(7, 6))
    colors = {
        "random_forest": "#1F78B4",
        "gcn": "#33A02C",
        "pi_gnn": "#E31A1C",
    }

    for key, color in colors.items():
        pts = roc_points.get(key)
        if not isinstance(pts, dict):
            continue
        fpr = pts.get("fpr", [])
        tpr = pts.get("tpr", [])
        auc = baseline.get("metrics", {}).get(key, {}).get("roc_auc", 0.0)
        ax.plot(fpr, tpr, linewidth=2.2, color=color, label=f"{key} (AUC={auc:.3f})")

    ax.plot([0, 1], [0, 1], "k--", linewidth=1.2)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Comparison")
    ax.legend(loc="lower right", fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out = output_path(output_dir, prefix, "fig3_roc_comparison.png")
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    return out


def plot_recall_fpr_bar(baseline: dict, output_dir: str, prefix: str = "") -> str:
    metrics = baseline.get("metrics", {})
    models = ["random_forest", "gcn", "pi_gnn"]

    recalls = [float(metrics.get(m, {}).get("recall", 0.0)) for m in models]
    fprs = [float(metrics.get(m, {}).get("fpr", 0.0)) for m in models]

    x = np.arange(len(models))
    width = 0.34

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - width / 2, recalls, width, label="Recall", color="#2C7FB8")
    ax.bar(x + width / 2, fprs, width, label="FPR", color="#D95F0E")

    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Score")
    ax.set_title("Recall/FPR Baseline Comparison")
    ax.legend(loc="upper right")

    plt.tight_layout()
    out = output_path(output_dir, prefix, "fig4_recall_fpr.png")
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Plot Phase-3 and baseline evaluation figures")
    p.add_argument("--results-file", default=DEFAULT_RESULTS_FILE)
    p.add_argument("--graph-file", default=DEFAULT_GRAPH_FILE)
    p.add_argument("--baseline-file", default=DEFAULT_BASELINE_FILE)
    p.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--prefix", default="")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    results_file = os.path.abspath(os.path.expanduser(args.results_file))
    graph_file = os.path.abspath(os.path.expanduser(args.graph_file))
    baseline_file = os.path.abspath(os.path.expanduser(args.baseline_file))
    output_dir = os.path.abspath(os.path.expanduser(args.output_dir))
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 65)
    print("Plotting Results")
    print("=" * 65)

    if not os.path.exists(results_file):
        raise FileNotFoundError(f"Missing {results_file}")
    if not os.path.exists(graph_file):
        raise FileNotFoundError(f"Missing {graph_file}")

    results = load_json(results_file)
    graph = torch.load(graph_file, weights_only=False, map_location="cpu")

    out1 = plot_loss_landscape(results.get("history", {}), output_dir=output_dir, prefix=args.prefix)
    out2 = plot_entropy_distribution(graph, output_dir=output_dir, prefix=args.prefix)
    print(f"  saved: {out1}")
    print(f"  saved: {out2}")

    if os.path.exists(baseline_file):
        baseline = load_json(baseline_file)
        out3 = plot_baseline_roc(baseline, output_dir=output_dir, prefix=args.prefix)
        out4 = plot_recall_fpr_bar(baseline, output_dir=output_dir, prefix=args.prefix)
        print(f"  saved: {out3}")
        print(f"  saved: {out4}")
    else:
        print(f"  skip baseline figures (missing {baseline_file})")


if __name__ == "__main__":
    main()
