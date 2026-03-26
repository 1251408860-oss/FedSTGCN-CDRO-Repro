#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

METRICS = ["f1", "recall", "fpr", "ece", "brier"]
METHOD_ORDER = ["noisy_ce", "cdro_fixed", "cdro_ug"]
METHOD_LABELS = {
    "noisy_ce": "Noisy-CE",
    "cdro_fixed": "CDRO-Fixed",
    "cdro_ug": "CDRO-UG (sw0)",
}
METHOD_COLORS = {
    "noisy_ce": "#7A8892",
    "cdro_fixed": "#D68C45",
    "cdro_ug": "#1F6E8C",
}
PROTOCOL_ORDER = [
    "weak_temporal_ood",
    "weak_topology_ood",
    "weak_attack_strategy_ood",
    "label_prior_shift_ood",
]
PROTOCOL_LABELS = {
    "weak_temporal_ood": "Weak Temporal OOD",
    "weak_topology_ood": "Weak Topology OOD",
    "weak_attack_strategy_ood": "Weak Attack-Strategy OOD",
    "label_prior_shift_ood": "Label-Prior Shift OOD",
    "pooled": "Pooled",
}
VARIANT_ORDER = ["sw0_full", "sw0_lossonly", "sw0_uniform", "sw0_b035", "sw0_b075"]
VARIANT_LABELS = {
    "sw0_full": "Full",
    "sw0_lossonly": "Loss-only",
    "sw0_uniform": "Uniform",
    "sw0_b035": "b=0.35",
    "sw0_b075": "b=0.75",
}
VARIANT_COLORS = {
    "sw0_full": "#1F6E8C",
    "sw0_lossonly": "#4E937A",
    "sw0_uniform": "#C1666B",
    "sw0_b035": "#D68C45",
    "sw0_b075": "#6C7A89",
}
BUCKET_ORDER = {
    "weak_bucket": ["abstain", "weak_benign", "weak_attack"],
    "group_bucket": [
        "low_rho_low_uncertainty",
        "low_rho_high_uncertainty",
        "high_rho_low_uncertainty",
        "high_rho_high_uncertainty",
    ],
}
BUCKET_LABELS = {
    "abstain": "Abstain",
    "weak_benign": "Weak benign",
    "weak_attack": "Weak attack",
    "low_rho_low_uncertainty": "Low-rho / low-u",
    "low_rho_high_uncertainty": "Low-rho / high-u",
    "high_rho_low_uncertainty": "High-rho / low-u",
    "high_rho_high_uncertainty": "High-rho / high-u",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def stat_block(values: list[float]) -> dict[str, float]:
    if not values:
        return {"n": 0, "mean": 0.0, "std": 0.0}
    return {
        "n": len(values),
        "mean": float(statistics.mean(values)),
        "std": float(statistics.stdev(values)) if len(values) > 1 else 0.0,
    }


def fmt(value: float, digits: int = 4) -> str:
    return f"{value:.{digits}f}"


def fmt_p(value: float) -> str:
    if value < 0.001:
        return f"{value:.2e}"
    return f"{value:.4f}"


def aggregate_cdro_summary(summary: dict[str, Any]) -> dict[str, dict[str, dict[str, dict[str, float]]]]:
    runs = summary["runs"]
    stats: dict[str, dict[str, dict[str, dict[str, float]]]] = defaultdict(dict)
    for protocol in PROTOCOL_ORDER:
        for method in METHOD_ORDER:
            selected = [row["metrics"] for row in runs if row["protocol"] == protocol and row["method"] == method]
            stats[protocol][method] = {metric: stat_block([row[metric] for row in selected]) for metric in METRICS}
    stats["pooled"] = {}
    for method in METHOD_ORDER:
        selected = [row["metrics"] for row in runs if row["method"] == method]
        stats["pooled"][method] = {metric: stat_block([row[metric] for row in selected]) for metric in METRICS}
    return stats


def find_comparison(sig: dict[str, Any], method_a: str, method_b: str) -> dict[str, Any]:
    for comp in sig.get("comparisons", []):
        if comp.get("method_a") == method_a and comp.get("method_b") == method_b:
            return comp
    return {}


def build_result_table_rows(
    setting: str, stats: dict[str, dict[str, dict[str, dict[str, float]]]]
) -> list[list[object]]:
    rows: list[list[object]] = [[
        "setting",
        "protocol",
        "protocol_label",
        "method",
        "method_label",
        "n",
        "f1_mean",
        "f1_std",
        "recall_mean",
        "recall_std",
        "fpr_mean",
        "fpr_std",
        "ece_mean",
        "ece_std",
        "brier_mean",
        "brier_std",
    ]]
    for protocol in PROTOCOL_ORDER + ["pooled"]:
        for method in METHOD_ORDER:
            block = stats[protocol][method]
            rows.append(
                [
                    setting,
                    protocol,
                    PROTOCOL_LABELS[protocol],
                    method,
                    METHOD_LABELS[method],
                    block["f1"]["n"],
                    block["f1"]["mean"],
                    block["f1"]["std"],
                    block["recall"]["mean"],
                    block["recall"]["std"],
                    block["fpr"]["mean"],
                    block["fpr"]["std"],
                    block["ece"]["mean"],
                    block["ece"]["std"],
                    block["brier"]["mean"],
                    block["brier"]["std"],
                ]
            )
    return rows


def build_significance_rows(main_sig: dict[str, Any], batch2_sig: dict[str, Any]) -> list[list[object]]:
    rows: list[list[object]] = [[
        "setting",
        "comparison",
        "scope",
        "protocol",
        "metric",
        "delta_mean",
        "p_value",
        "significant_005",
    ]]
    for setting, sig in [("main", main_sig), ("batch2", batch2_sig)]:
        for comp in sig.get("comparisons", []):
            comp_name = f"{comp['method_a']} vs {comp['method_b']}"
            for metric, values in comp["pooled"].items():
                rows.append(
                    [
                        setting,
                        comp_name,
                        "pooled",
                        "pooled",
                        metric,
                        values["delta_mean"],
                        values["p_value"],
                        int(values["p_value"] < 0.05),
                    ]
                )
            for protocol in PROTOCOL_ORDER:
                per_protocol = comp["per_protocol"][protocol]
                for metric, values in per_protocol.items():
                    rows.append(
                        [
                            setting,
                            comp_name,
                            "per_protocol",
                            protocol,
                            metric,
                            values["delta_mean"],
                            values["p_value"],
                            int(values["p_value"] < 0.05),
                        ]
                    )
    return rows


def build_mechanism_probe_rows(setting: str, mech: dict[str, Any]) -> list[list[object]]:
    rows: list[list[object]] = [[
        "setting",
        "variant",
        "variant_label",
        "n",
        "f1_mean",
        "f1_std",
        "recall_mean",
        "recall_std",
        "fpr_mean",
        "fpr_std",
        "ece_mean",
        "ece_std",
        "brier_mean",
        "brier_std",
        "delta_f1_vs_full",
        "p_f1_vs_full",
        "delta_fpr_vs_full",
        "p_fpr_vs_full",
    ]]
    for variant in VARIANT_ORDER:
        pooled = mech["stats"]["pooled"][variant]
        if variant == "sw0_full":
            delta_f1 = ""
            p_f1 = ""
            delta_fpr = ""
            p_fpr = ""
        else:
            delta_f1 = mech["p_values"][variant]["pooled"]["f1"]["delta_mean"]
            p_f1 = mech["p_values"][variant]["pooled"]["f1"]["p_value"]
            delta_fpr = mech["p_values"][variant]["pooled"]["fpr"]["delta_mean"]
            p_fpr = mech["p_values"][variant]["pooled"]["fpr"]["p_value"]
        rows.append(
            [
                setting,
                variant,
                VARIANT_LABELS[variant],
                pooled["f1"]["n"],
                pooled["f1"]["mean"],
                pooled["f1"]["std"],
                pooled["recall"]["mean"],
                pooled["recall"]["std"],
                pooled["fpr"]["mean"],
                pooled["fpr"]["std"],
                pooled["ece"]["mean"],
                pooled["ece"]["std"],
                pooled["brier"]["mean"],
                pooled["brier"]["std"],
                delta_f1,
                p_f1,
                delta_fpr,
                p_fpr,
            ]
        )
    return rows


def append_fp_rows(
    rows: list[list[object]],
    setting: str,
    scope: str,
    bucket_type: str,
    bucket_map: dict[str, Any],
) -> None:
    ordered_buckets = BUCKET_ORDER.get(bucket_type, list(bucket_map.keys()))
    for bucket in ordered_buckets:
        if bucket not in bucket_map:
            continue
        block = bucket_map[bucket]
        rows.append(
            [
                setting,
                scope,
                bucket_type,
                bucket,
                BUCKET_LABELS.get(bucket, bucket),
                block["method_a"]["benign_total"],
                block["method_a"]["fpr"],
                block["method_b"]["fpr"],
                block["delta_fpr"],
                block["delta_fp"],
                block["method_a"]["mean_prob_attack"],
                block["method_b"]["mean_prob_attack"],
                block["delta_mean_prob_attack"],
            ]
        )


def build_fp_source_rows(main_fp: dict[str, Any], batch2_fp: dict[str, Any]) -> list[list[object]]:
    rows: list[list[object]] = [[
        "setting",
        "scope",
        "bucket_type",
        "bucket",
        "bucket_label",
        "benign_total",
        "ug_fpr",
        "noisy_fpr",
        "delta_fpr",
        "delta_fp",
        "ug_mean_prob_attack",
        "noisy_mean_prob_attack",
        "delta_mean_prob_attack",
    ]]
    for setting, fp in [("main", main_fp), ("batch2", batch2_fp)]:
        append_fp_rows(rows, setting, "pooled", "weak_bucket", fp["pooled"]["weak_bucket"])
        append_fp_rows(rows, setting, "pooled", "group_bucket", fp["pooled"]["group_bucket"])
        for protocol in PROTOCOL_ORDER:
            append_fp_rows(rows, setting, protocol, "weak_bucket", fp["per_protocol"][protocol]["weak_bucket"])
            append_fp_rows(rows, setting, protocol, "group_bucket", fp["per_protocol"][protocol]["group_bucket"])
    return rows


def build_weak_label_rows(setting: str, quality: dict[str, Any]) -> list[list[object]]:
    rows: list[list[object]] = [[
        "setting",
        "protocol",
        "protocol_label",
        "bucket",
        "n",
        "precision",
        "agreement_mean",
        "uncertainty_mean",
        "confidence_mean",
        "effective_trust_mean",
    ]]
    for protocol in PROTOCOL_ORDER:
        for bucket in ["weak_attack", "weak_benign"]:
            block = quality["protocols"][protocol]["buckets"][bucket]
            rows.append(
                [
                    setting,
                    protocol,
                    PROTOCOL_LABELS[protocol],
                    bucket,
                    block["n"],
                    block["precision"],
                    block["agreement"]["mean"],
                    block["uncertainty"]["mean"],
                    block["confidence"]["mean"],
                    block["effective_trust"]["mean"],
                ]
            )
    return rows


def style_bar_ax(ax: plt.Axes, title: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=11)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def plot_pooled_results(
    out_path: Path,
    main_stats: dict[str, dict[str, dict[str, dict[str, float]]]],
    batch2_stats: dict[str, dict[str, dict[str, dict[str, float]]]],
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.5), constrained_layout=True)
    panels = [
        (axes[0, 0], main_stats["pooled"], "f1", "Main batch: pooled F1", "F1"),
        (axes[0, 1], main_stats["pooled"], "fpr", "Main batch: pooled FPR", "FPR"),
        (axes[1, 0], batch2_stats["pooled"], "f1", "Batch2: pooled F1", "F1"),
        (axes[1, 1], batch2_stats["pooled"], "fpr", "Batch2: pooled FPR", "FPR"),
    ]
    for ax, block, metric, title, ylabel in panels:
        x = np.arange(len(METHOD_ORDER))
        values = [block[method][metric]["mean"] for method in METHOD_ORDER]
        errors = [block[method][metric]["std"] for method in METHOD_ORDER]
        colors = [METHOD_COLORS[method] for method in METHOD_ORDER]
        ax.bar(x, values, yerr=errors, capsize=4, color=colors, edgecolor="black", linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels([METHOD_LABELS[method] for method in METHOD_ORDER], rotation=14, ha="right")
        style_bar_ax(ax, title, ylabel)
    axes[0, 0].set_ylim(0.82, 0.92)
    axes[1, 0].set_ylim(0.84, 0.92)
    axes[0, 1].set_ylim(0.0, 0.35)
    axes[1, 1].set_ylim(0.0, 0.35)
    fig.suptitle("CDRO pooled results overview", fontsize=14)
    fig.savefig(out_path, dpi=240)
    plt.close(fig)


def plot_mechanism_probe(out_path: Path, mech_main: dict[str, Any], mech_batch2: dict[str, Any]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.8), constrained_layout=True)
    panels = [
        (axes[0, 0], mech_main["stats"]["pooled"], "f1", "Main probe: pooled F1", "F1"),
        (axes[0, 1], mech_main["stats"]["pooled"], "fpr", "Main probe: pooled FPR", "FPR"),
        (axes[1, 0], mech_batch2["stats"]["pooled"], "f1", "Batch2 probe: pooled F1", "F1"),
        (axes[1, 1], mech_batch2["stats"]["pooled"], "fpr", "Batch2 probe: pooled FPR", "FPR"),
    ]
    for ax, block, metric, title, ylabel in panels:
        x = np.arange(len(VARIANT_ORDER))
        values = [block[variant][metric]["mean"] for variant in VARIANT_ORDER]
        errors = [block[variant][metric]["std"] for variant in VARIANT_ORDER]
        colors = [VARIANT_COLORS[variant] for variant in VARIANT_ORDER]
        ax.bar(x, values, yerr=errors, capsize=4, color=colors, edgecolor="black", linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels([VARIANT_LABELS[variant] for variant in VARIANT_ORDER], rotation=18, ha="right")
        style_bar_ax(ax, title, ylabel)
    axes[0, 0].text(
        0.02,
        0.96,
        "Uniform vs full:\ndelta F1 = -0.0041, p = 0.0149",
        transform=axes[0, 0].transAxes,
        va="top",
        ha="left",
        fontsize=9,
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "#999999"},
    )
    axes[1, 1].text(
        0.02,
        0.96,
        "b=0.35 vs full:\ndelta FPR = +0.0119, p = 7.32e-04",
        transform=axes[1, 1].transAxes,
        va="top",
        ha="left",
        fontsize=9,
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "#999999"},
    )
    axes[0, 0].set_ylim(0.84, 0.89)
    axes[1, 0].set_ylim(0.86, 0.90)
    axes[0, 1].set_ylim(0.14, 0.22)
    axes[1, 1].set_ylim(0.20, 0.25)
    fig.suptitle("Mechanism probe for the rewritten UG design", fontsize=14)
    fig.savefig(out_path, dpi=240)
    plt.close(fig)


def plot_delta_panel(ax: plt.Axes, labels: list[str], values: list[float], title: str) -> None:
    colors = ["#2E7D32" if value <= 0 else "#C62828" for value in values]
    ax.bar(range(len(labels)), values, color=colors, edgecolor="black", linewidth=0.8)
    ax.axhline(0.0, color="black", linewidth=0.9)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=18, ha="right")
    style_bar_ax(ax, title, "delta FPR (UG - Noisy-CE)")


def plot_fp_sources(out_path: Path, main_fp: dict[str, Any], batch2_fp: dict[str, Any]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.8), constrained_layout=True)
    main_weak = main_fp["pooled"]["weak_bucket"]
    batch2_weak = batch2_fp["pooled"]["weak_bucket"]
    main_group = main_fp["per_protocol"]["weak_attack_strategy_ood"]["group_bucket"]
    batch2_group = batch2_fp["pooled"]["group_bucket"]

    panels = [
        (axes[0, 0], "weak_bucket", main_weak, "Main pooled: weak buckets"),
        (axes[0, 1], "weak_bucket", batch2_weak, "Batch2 pooled: weak buckets"),
        (axes[1, 0], "group_bucket", main_group, "Main attack-strategy: group buckets"),
        (axes[1, 1], "group_bucket", batch2_group, "Batch2 pooled: group buckets"),
    ]
    for ax, bucket_type, block, title in panels:
        order = [bucket for bucket in BUCKET_ORDER[bucket_type] if bucket in block]
        labels = [BUCKET_LABELS[bucket] for bucket in order]
        values = [block[bucket]["delta_fpr"] for bucket in order]
        plot_delta_panel(ax, labels, values, title)
    fig.suptitle("Where the rewritten UG reduces false positives", fontsize=14)
    fig.savefig(out_path, dpi=240)
    plt.close(fig)


def plot_grouped_protocol_bars(
    ax: plt.Axes,
    quality: dict[str, Any],
    field: str,
    title: str,
    ylabel: str,
) -> None:
    x = np.arange(len(PROTOCOL_ORDER))
    width = 0.36
    attack_vals = []
    benign_vals = []
    for protocol in PROTOCOL_ORDER:
        attack = quality["protocols"][protocol]["buckets"]["weak_attack"]
        benign = quality["protocols"][protocol]["buckets"]["weak_benign"]
        attack_vals.append(attack[field]["mean"] if isinstance(attack[field], dict) else attack[field])
        benign_vals.append(benign[field]["mean"] if isinstance(benign[field], dict) else benign[field])
    ax.bar(x - width / 2, attack_vals, width=width, color="#C1666B", edgecolor="black", linewidth=0.8, label="weak_attack")
    ax.bar(x + width / 2, benign_vals, width=width, color="#4E937A", edgecolor="black", linewidth=0.8, label="weak_benign")
    ax.set_xticks(x)
    ax.set_xticklabels([PROTOCOL_LABELS[protocol] for protocol in PROTOCOL_ORDER], rotation=18, ha="right")
    style_bar_ax(ax, title, ylabel)


def plot_weak_label_quality(out_path: Path, main_quality: dict[str, Any], batch2_quality: dict[str, Any]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8), constrained_layout=True)
    plot_grouped_protocol_bars(axes[0, 0], main_quality, "precision", "Main: weak-label precision", "Precision")
    plot_grouped_protocol_bars(axes[0, 1], batch2_quality, "precision", "Batch2: weak-label precision", "Precision")
    plot_grouped_protocol_bars(axes[1, 0], main_quality, "effective_trust", "Main: effective trust", "Effective trust")
    plot_grouped_protocol_bars(axes[1, 1], batch2_quality, "effective_trust", "Batch2: effective trust", "Effective trust")
    axes[0, 0].legend(loc="lower right")
    axes[0, 0].set_ylim(0.5, 1.02)
    axes[0, 1].set_ylim(0.5, 1.02)
    axes[1, 0].set_ylim(0.35, 0.85)
    axes[1, 1].set_ylim(0.35, 0.85)
    fig.suptitle("Weak-label quality supports asymmetric trust", fontsize=14)
    fig.savefig(out_path, dpi=240)
    plt.close(fig)


def quality_range(quality: dict[str, Any], bucket: str, field: str) -> tuple[float, float]:
    values = []
    for protocol in PROTOCOL_ORDER:
        block = quality["protocols"][protocol]["buckets"][bucket][field]
        values.append(block["mean"] if isinstance(block, dict) else block)
    return min(values), max(values)


def build_master_summary(
    main_stats: dict[str, dict[str, dict[str, dict[str, float]]]],
    batch2_stats: dict[str, dict[str, dict[str, dict[str, float]]]],
    main_sig: dict[str, Any],
    batch2_sig: dict[str, Any],
    mech_main: dict[str, Any],
    mech_batch2: dict[str, Any],
    main_quality: dict[str, Any],
    batch2_quality: dict[str, Any],
) -> str:
    main_comp = find_comparison(main_sig, "cdro_ug", "noisy_ce")
    batch2_comp = find_comparison(batch2_sig, "cdro_ug", "noisy_ce")
    main_attack_prec = quality_range(main_quality, "weak_attack", "precision")
    main_benign_prec = quality_range(main_quality, "weak_benign", "precision")
    batch2_attack_prec = quality_range(batch2_quality, "weak_attack", "precision")
    batch2_benign_prec = quality_range(batch2_quality, "weak_benign", "precision")
    main_attack_trust = quality_range(main_quality, "weak_attack", "effective_trust")
    main_benign_trust = quality_range(main_quality, "weak_benign", "effective_trust")
    batch2_attack_trust = quality_range(batch2_quality, "weak_attack", "effective_trust")
    batch2_benign_trust = quality_range(batch2_quality, "weak_benign", "effective_trust")
    return "\n".join(
        [
            "# CDRO Paper-Ready Plus",
            "",
            "## Core claim",
            (
                f"- Main batch (4 protocols x 5 seeds): CDRO-UG (sw0) reaches pooled "
                f"F1={fmt(main_stats['pooled']['cdro_ug']['f1']['mean'])} and "
                f"FPR={fmt(main_stats['pooled']['cdro_ug']['fpr']['mean'])}. "
                f"Against Noisy-CE, delta F1={main_comp['pooled']['f1']['delta_mean']:+.6f} "
                f"(p={fmt_p(main_comp['pooled']['f1']['p_value'])}) and "
                f"delta FPR={main_comp['pooled']['fpr']['delta_mean']:+.6f} "
                f"(p={fmt_p(main_comp['pooled']['fpr']['p_value'])})."
            ),
            (
                f"- Batch2 (4 protocols x 3 seeds): CDRO-UG (sw0) reaches pooled "
                f"F1={fmt(batch2_stats['pooled']['cdro_ug']['f1']['mean'])} and "
                f"FPR={fmt(batch2_stats['pooled']['cdro_ug']['fpr']['mean'])}. "
                f"Against Noisy-CE, delta F1={batch2_comp['pooled']['f1']['delta_mean']:+.6f} "
                f"(p={fmt_p(batch2_comp['pooled']['f1']['p_value'])}) and "
                f"delta FPR={batch2_comp['pooled']['fpr']['delta_mean']:+.6f} "
                f"(p={fmt_p(batch2_comp['pooled']['fpr']['p_value'])})."
            ),
            "",
            "## Mechanism readout",
            (
                f"- Main probe: replacing non-uniform weighting with uniform weighting hurts pooled F1 "
                f"(delta={mech_main['p_values']['sw0_uniform']['pooled']['f1']['delta_mean']:+.6f}, "
                f"p={fmt_p(mech_main['p_values']['sw0_uniform']['pooled']['f1']['p_value'])})."
            ),
            (
                f"- Batch2 probe: lowering benign trust to 0.35 hurts pooled FPR "
                f"(delta={mech_batch2['p_values']['sw0_b035']['pooled']['fpr']['delta_mean']:+.6f}, "
                f"p={fmt_p(mech_batch2['p_values']['sw0_b035']['pooled']['fpr']['p_value'])})."
            ),
            "- FP-source analysis: the robust FPR gain comes mainly from benign `abstain` and `weak_benign` regions; the cleanest protocol-level evidence is `weak_attack_strategy_ood`.",
            "",
            "## Weak-label audit",
            (
                f"- Main weak_attack precision ranges from {fmt(main_attack_prec[0])} to {fmt(main_attack_prec[1])}, "
                f"while weak_benign ranges from {fmt(main_benign_prec[0])} to {fmt(main_benign_prec[1])}."
            ),
            (
                f"- Batch2 weak_attack precision ranges from {fmt(batch2_attack_prec[0])} to {fmt(batch2_attack_prec[1])}, "
                f"while weak_benign ranges from {fmt(batch2_benign_prec[0])} to {fmt(batch2_benign_prec[1])}."
            ),
            (
                f"- Effective trust follows the same split: main weak_attack={fmt(main_attack_trust[0])}-{fmt(main_attack_trust[1])}, "
                f"main weak_benign={fmt(main_benign_trust[0])}-{fmt(main_benign_trust[1])}; "
                f"batch2 weak_attack={fmt(batch2_attack_trust[0])}-{fmt(batch2_attack_trust[1])}, "
                f"batch2 weak_benign={fmt(batch2_benign_trust[0])}-{fmt(batch2_benign_trust[1])}."
            ),
            "",
            "## Recommended paper usage",
            "- Main text: Table 1, Table 2, Fig 1, Fig 2, Fig 3.",
            "- Mechanism subsection: Table 4, Table 5, Fig 2, Fig 3, Fig 4.",
            "- Appendix / reproducibility: Table 3, Table 6.",
        ]
    )


def build_index() -> str:
    return "\n".join(
        [
            "# CDRO Paper Ready Plus Index",
            "",
            "- `MASTER_SUMMARY.md`: one-page summary of the paper-safe claims and the main mechanism readout.",
            "- `FIGURE_CAPTIONS.md`: manuscript-ready figure captions and usage guidance.",
            "- `TABLE_NOTES.md`: table captions, interpretation notes, and suggested placement.",
            "",
            "Core tables:",
            "- `table1_main_results.csv`",
            "- `table2_batch2_results.csv`",
            "- `table3_significance.csv`",
            "- `table4_mechanism_probe.csv`",
            "- `table5_fp_sources.csv`",
            "- `table6_weak_label_quality.csv`",
            "",
            "Core figures:",
            "- `fig1_pooled_results.png`",
            "- `fig2_mechanism_probe.png`",
            "- `fig3_fp_sources.png`",
            "- `fig4_weak_label_quality.png`",
        ]
    )


def build_figure_captions() -> str:
    return "\n".join(
        [
            "# Figure Captions",
            "",
            "## Fig 1. Pooled results overview",
            "CDRO-UG (sw0) is compared with Noisy-CE and CDRO-Fixed on the main batch and batch2. The figure should be used to support the restrained claim that the rewritten UG mainly improves false-positive control, while pooled F1 stays close to the baseline. The significant result to cite is the batch2 FPR reduction against Noisy-CE.",
            "",
            "## Fig 2. Mechanism probe for the rewritten UG",
            "Ablations isolate whether the benefit comes from non-uniform group prioritization or from secondary refinements. The figure highlights two stable findings: removing non-uniform weighting hurts main pooled F1, and setting benign trust too low hurts batch2 pooled FPR.",
            "",
            "## Fig 3. False-positive source decomposition",
            "Delta FPR is shown as CDRO-UG minus Noisy-CE. Negative bars indicate fewer benign false alarms. The intended reading is that the gain comes mainly from `abstain` and `weak_benign` benign regions, with strong protocol-level evidence in `weak_attack_strategy_ood` and strong batch2 evidence in high-rho benign groups.",
            "",
            "## Fig 4. Weak-label quality and effective trust",
            "Weak attack labels are consistently more precise than weak benign labels in both datasets, and the effective trust values follow the same split. This figure supports the design choice of class-asymmetric trust in the rewritten UG.",
        ]
    )


def build_table_notes() -> str:
    return "\n".join(
        [
            "# Table Notes",
            "",
            "## Table 1. Main results",
            "Per-protocol and pooled results for the main batch. Use the pooled rows in the main text and the per-protocol rows in appendix tables or supplementary material.",
            "",
            "## Table 2. Batch2 results",
            "Per-protocol and pooled results for the independent batch2 evaluation. This is the strongest table for the robust false-positive claim because the pooled FPR reduction against Noisy-CE is significant.",
            "",
            "## Table 3. Significance summary",
            "Raw paired significance results for CDRO-UG against Noisy-CE and CDRO-Fixed across pooled and per-protocol scopes. This table is mainly for appendix reporting and reviewer clarification.",
            "",
            "## Table 4. Mechanism probe",
            "Pooled ablation statistics for the rewritten UG. Use this table when explaining why the final design keeps non-uniform group prioritization and avoids overly low benign trust.",
            "",
            "## Table 5. FP sources",
            "Benign false-positive decomposition by weak bucket and group bucket. This table supports the claim that the robust gain is concentrated in benign regions that were under-controlled by the baseline.",
            "",
            "## Table 6. Weak-label quality",
            "Per-protocol audit of weak_attack and weak_benign buckets. This table is the cleanest justification for the asymmetric trust design.",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--out-dir", default="")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = Path(args.out_dir).resolve() if args.out_dir else root / "cdro_suite" / "paper_ready_plus"
    out_dir.mkdir(parents=True, exist_ok=True)

    main_summary = load_json(root / "cdro_suite" / "main_rewrite_sw0_s5_v1" / "cdro_summary.json")
    main_sig = load_json(root / "cdro_suite" / "main_rewrite_sw0_s5_v1" / "cdro_significance.json")
    batch2_summary = load_json(root / "cdro_suite" / "batch2_rewrite_sw0_s3_v2" / "cdro_summary.json")
    batch2_sig = load_json(root / "cdro_suite" / "batch2_rewrite_sw0_s3_v2" / "cdro_significance.json")
    mech_main = load_json(root / "cdro_suite" / "mechanism_main_s3_v1" / "mechanism_probe_summary.json")
    mech_batch2 = load_json(root / "cdro_suite" / "mechanism_batch2_s3_v1" / "mechanism_probe_summary.json")
    fp_main = load_json(root / "cdro_suite" / "main_rewrite_sw0_s5_v1" / "fp_sources_ug_vs_noisy.json")
    fp_batch2 = load_json(root / "cdro_suite" / "batch2_rewrite_sw0_s3_v2" / "fp_sources_ug_vs_noisy.json")
    quality_main = load_json(root / "cdro_suite" / "main_rewrite_sw0_s5_v1" / "weak_label_quality_sw0.json")
    quality_batch2 = load_json(root / "cdro_suite" / "batch2_rewrite_sw0_s3_v2" / "weak_label_quality_sw0.json")

    main_stats = aggregate_cdro_summary(main_summary)
    batch2_stats = aggregate_cdro_summary(batch2_summary)

    write_csv(out_dir / "table1_main_results.csv", build_result_table_rows("main", main_stats))
    write_csv(out_dir / "table2_batch2_results.csv", build_result_table_rows("batch2", batch2_stats))
    write_csv(out_dir / "table3_significance.csv", build_significance_rows(main_sig, batch2_sig))

    mechanism_rows = build_mechanism_probe_rows("main", mech_main)
    batch2_mechanism_rows = build_mechanism_probe_rows("batch2", mech_batch2)
    write_csv(out_dir / "table4_mechanism_probe.csv", mechanism_rows + batch2_mechanism_rows[1:])

    write_csv(out_dir / "table5_fp_sources.csv", build_fp_source_rows(fp_main, fp_batch2))
    weak_label_rows = build_weak_label_rows("main", quality_main)
    weak_label_rows += build_weak_label_rows("batch2", quality_batch2)[1:]
    write_csv(out_dir / "table6_weak_label_quality.csv", weak_label_rows)

    plot_pooled_results(out_dir / "fig1_pooled_results.png", main_stats, batch2_stats)
    plot_mechanism_probe(out_dir / "fig2_mechanism_probe.png", mech_main, mech_batch2)
    plot_fp_sources(out_dir / "fig3_fp_sources.png", fp_main, fp_batch2)
    plot_weak_label_quality(out_dir / "fig4_weak_label_quality.png", quality_main, quality_batch2)

    write_text(
        out_dir / "MASTER_SUMMARY.md",
        build_master_summary(main_stats, batch2_stats, main_sig, batch2_sig, mech_main, mech_batch2, quality_main, quality_batch2),
    )
    write_text(out_dir / "INDEX.md", build_index())
    write_text(out_dir / "FIGURE_CAPTIONS.md", build_figure_captions())
    write_text(out_dir / "TABLE_NOTES.md", build_table_notes())

    manifest = {
        "root": str(root),
        "out_dir": str(out_dir),
        "inputs": [
            "cdro_suite/main_rewrite_sw0_s5_v1/cdro_summary.json",
            "cdro_suite/main_rewrite_sw0_s5_v1/cdro_significance.json",
            "cdro_suite/batch2_rewrite_sw0_s3_v2/cdro_summary.json",
            "cdro_suite/batch2_rewrite_sw0_s3_v2/cdro_significance.json",
            "cdro_suite/mechanism_main_s3_v1/mechanism_probe_summary.json",
            "cdro_suite/mechanism_batch2_s3_v1/mechanism_probe_summary.json",
            "cdro_suite/main_rewrite_sw0_s5_v1/fp_sources_ug_vs_noisy.json",
            "cdro_suite/batch2_rewrite_sw0_s3_v2/fp_sources_ug_vs_noisy.json",
            "cdro_suite/main_rewrite_sw0_s5_v1/weak_label_quality_sw0.json",
            "cdro_suite/batch2_rewrite_sw0_s3_v2/weak_label_quality_sw0.json",
        ],
        "outputs": sorted(path.name for path in out_dir.iterdir()),
    }
    write_text(out_dir / "artifact_manifest.json", json.dumps(manifest, indent=2))
    print(out_dir)


if __name__ == "__main__":
    main()


