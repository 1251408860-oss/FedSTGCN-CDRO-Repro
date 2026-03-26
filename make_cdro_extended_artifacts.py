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
import torch


METRICS = ["f1", "fpr", "ece", "brier"]
CORE_METHODS = ["noisy_ce", "cdro_fixed", "cdro_ug"]
BASELINEPLUS_METHODS = ["noisy_ce", "posterior_ce", "cdro_fixed", "cdro_ug", "cdro_ug_priorcorr"]
STRONGBASE_METHODS = ["noisy_ce", "gce", "sce", "bootstrap_ce", "elr", "posterior_ce", "cdro_fixed", "cdro_ug", "cdro_ug_priorcorr"]

METHOD_LABELS = {
    "noisy_ce": "Noisy-CE",
    "gce": "GCE",
    "sce": "SCE",
    "bootstrap_ce": "Bootstrap-CE",
    "elr": "ELR",
    "posterior_ce": "Posterior-CE",
    "cdro_fixed": "CDRO-Fixed",
    "cdro_ug": "CDRO-UG (sw0)",
    "cdro_ug_priorcorr": "CDRO-UG + PriorCorr",
}
METHOD_COLORS = {
    "noisy_ce": "#7A8892",
    "gce": "#8E6C8A",
    "sce": "#D97D54",
    "bootstrap_ce": "#A44A3F",
    "elr": "#7C9B5B",
    "posterior_ce": "#C1666B",
    "cdro_fixed": "#D6A24C",
    "cdro_ug": "#1F6E8C",
    "cdro_ug_priorcorr": "#4E937A",
}
SCENARIO_LABELS = {
    "scenario_i_three_tier_low_b2": "External-I / 3-tier low",
    "scenario_j_three_tier_high_b2": "External-J / 3-tier high",
    "scenario_k_two_tier_high_b2": "External-K / 2-tier high",
    "scenario_l_mimic_heavy_b2": "External-L / mimic-heavy",
    "pooled": "Pooled external",
}
HARD_PROTOCOL_LABELS = {
    "temporal_ood": "Hard temporal OOD",
    "topology_ood": "Hard topology OOD",
    "attack_strategy_ood": "Hard attack-strategy OOD",
    "congestion_ood": "Hard congestion OOD",
    "pooled": "Pooled hard suite",
}
SETTING_LABELS = {
    "main": "Main",
    "batch2": "Batch2",
}
STRESS_KIND_LABELS = {
    "noise": "Weak-label flip ratio",
    "coverage": "Weak-label drop ratio",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def mean_std(vals: list[float]) -> tuple[int, float, float]:
    if not vals:
        return 0, 0.0, 0.0
    if len(vals) == 1:
        return 1, float(vals[0]), 0.0
    return len(vals), float(statistics.mean(vals)), float(statistics.stdev(vals))


def stats_for_runs(runs: list[dict[str, Any]], methods: list[str]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for method in methods:
        selected = [run["metrics"] for run in runs if run["method"] == method]
        block: dict[str, float] = {}
        for metric in METRICS:
            n, mean_v, std_v = mean_std([float(row.get(metric, 0.0)) for row in selected])
            block[f"{metric}_n"] = n
            block[f"{metric}_mean"] = mean_v
            block[f"{metric}_std"] = std_v
        out[method] = block
    return out


def find_comparison(sig: dict[str, Any], method_a: str, method_b: str) -> dict[str, Any]:
    for comp in sig.get("comparisons", []):
        if comp.get("method_a") == method_a and comp.get("method_b") == method_b:
            return comp
    return {}


def append_lines_once(path: Path, lines: list[str]) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    updated = text.rstrip("\n")
    changed = False
    for line in lines:
        if line not in text:
            updated += ("\n" if updated else "") + line
            changed = True
    if changed:
        path.write_text(updated.rstrip() + "\n", encoding="utf-8")


def pooled_probs_from_summary(summary: dict[str, Any], methods: list[str]) -> dict[str, tuple[torch.Tensor, torch.Tensor]]:
    out: dict[str, tuple[list[torch.Tensor], list[torch.Tensor]]] = {m: ([], []) for m in methods}
    for run in summary.get("runs", []):
        method = run["method"]
        if method not in methods:
            continue
        logits_path = Path(run["result_file"]).with_name("results_logits.pt")
        bundle = torch.load(logits_path, map_location="cpu")
        probs = bundle["probs"][:, 1].float()
        y_true = bundle["y_true"].long()
        mask = bundle["temporal_test_mask"].bool() if "temporal_test_mask" in bundle else bundle["test_mask"].bool()
        out[method][0].append(probs[mask])
        out[method][1].append(y_true[mask])
    return {m: (torch.cat(xs, dim=0), torch.cat(ys, dim=0)) for m, (xs, ys) in out.items() if xs}


def roc_curve(prob: torch.Tensor, y_true: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    order = torch.argsort(prob, descending=True)
    y = y_true[order].float()
    pos = max(int(y.sum().item()), 1)
    neg = max(int((1 - y).sum().item()), 1)
    tp = torch.cumsum(y, dim=0)
    fp = torch.cumsum(1.0 - y, dim=0)
    tpr = torch.cat([torch.tensor([0.0]), tp / pos, torch.tensor([1.0])])
    fpr = torch.cat([torch.tensor([0.0]), fp / neg, torch.tensor([1.0])])
    return fpr, tpr


def pr_curve(prob: torch.Tensor, y_true: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    order = torch.argsort(prob, descending=True)
    y = y_true[order].float()
    pos = max(int(y.sum().item()), 1)
    tp = torch.cumsum(y, dim=0)
    denom = torch.arange(1, y.numel() + 1, dtype=torch.float)
    precision = tp / denom
    recall = tp / pos
    precision = torch.cat([torch.tensor([precision[0].item() if precision.numel() > 0 else 1.0]), precision])
    recall = torch.cat([torch.tensor([0.0]), recall])
    return recall, precision


def auc_xy(x: torch.Tensor, y: torch.Tensor) -> float:
    return float(torch.trapz(y, x).item())


def fpr_at_target_recall(prob: torch.Tensor, y_true: torch.Tensor, target_recall: float) -> float:
    fpr, tpr = roc_curve(prob, y_true)
    mask = tpr >= float(target_recall)
    if int(mask.sum().item()) == 0:
        return 1.0
    return float(torch.min(fpr[mask]).item())


def recall_at_target_fpr(prob: torch.Tensor, y_true: torch.Tensor, target_fpr: float) -> float:
    fpr, tpr = roc_curve(prob, y_true)
    mask = fpr <= float(target_fpr)
    if int(mask.sum().item()) == 0:
        return 0.0
    return float(torch.max(tpr[mask]).item())


def write_external_validation(out_dir: Path, root: Path) -> None:
    summary = load_json(root / "cdro_suite/external4_baselineplus_s3_v1/cdro_summary.json")
    sig = load_json(root / "cdro_suite/external4_baselineplus_s3_v1/cdro_significance.json")
    rows = [[
        "source_tag", "source_label", "method", "method_label", "n", "f1_mean", "f1_std", "fpr_mean", "fpr_std", "ece_mean", "ece_std", "brier_mean", "brier_std"
    ]]
    lines = ["# External 4-Batch Validation", ""]

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in summary.get("runs", []):
        grouped[str(run.get("source_tag", "unknown"))].append(run)
    grouped["pooled"] = list(summary.get("runs", []))

    deltas = []
    for source_tag in ["scenario_i_three_tier_low_b2", "scenario_j_three_tier_high_b2", "scenario_k_two_tier_high_b2", "scenario_l_mimic_heavy_b2", "pooled"]:
        runs = grouped.get(source_tag, [])
        stats = stats_for_runs(runs, BASELINEPLUS_METHODS)
        lines.append(f"## {SCENARIO_LABELS.get(source_tag, source_tag)}")
        for method in BASELINEPLUS_METHODS:
            block = stats[method]
            rows.append([
                source_tag,
                SCENARIO_LABELS.get(source_tag, source_tag),
                method,
                METHOD_LABELS[method],
                block["f1_n"],
                block["f1_mean"],
                block["f1_std"],
                block["fpr_mean"],
                block["fpr_std"],
                block["ece_mean"],
                block["ece_std"],
                block["brier_mean"],
                block["brier_std"],
            ])
            lines.append(f"- {METHOD_LABELS[method]}: F1={block['f1_mean']:.4f}, FPR={block['fpr_mean']:.4f}, ECE={block['ece_mean']:.4f}")
        if source_tag != "pooled":
            delta = stats["cdro_ug"]["fpr_mean"] - stats["noisy_ce"]["fpr_mean"]
            deltas.append((source_tag, delta))
        lines.append("")

    comp_noisy = find_comparison(sig, "cdro_ug", "noisy_ce")
    comp_post = find_comparison(sig, "cdro_ug", "posterior_ce")
    strongest = min(deltas, key=lambda x: x[1]) if deltas else ("none", 0.0)
    lines.extend([
        "## Reading",
        f"- Pooled external 4-batch comparison: CDRO-UG vs Noisy-CE has delta_F1={comp_noisy['pooled']['f1']['delta_mean']:+.6f}, p={comp_noisy['pooled']['f1']['p_value']:.6g}; delta_FPR={comp_noisy['pooled']['fpr']['delta_mean']:+.6f}, p={comp_noisy['pooled']['fpr']['p_value']:.6g}.",
        f"- Pooled external 4-batch comparison against Posterior-CE: delta_F1={comp_post['pooled']['f1']['delta_mean']:+.6f}, p={comp_post['pooled']['f1']['p_value']:.6g}; delta_FPR={comp_post['pooled']['fpr']['delta_mean']:+.6f}, p={comp_post['pooled']['fpr']['p_value']:.6g}.",
        f"- The strongest scenario-level FPR drop against Noisy-CE appears in {SCENARIO_LABELS.get(strongest[0], strongest[0])} with delta_FPR={strongest[1]:+.6f}.",
    ])

    write_csv(out_dir / "table10_external4_validation.csv", rows)
    write_text(out_dir / "external4_validation.md", "\n".join(lines))


def write_strong_baselines(out_dir: Path, root: Path) -> None:
    suites = {
        "main": (
            load_json(root / "cdro_suite/main_strongbase_s3_v1/cdro_summary.json"),
            load_json(root / "cdro_suite/main_strongbase_s3_v1/cdro_significance.json"),
        ),
        "batch2": (
            load_json(root / "cdro_suite/batch2_strongbase_s3_v1/cdro_summary.json"),
            load_json(root / "cdro_suite/batch2_strongbase_s3_v1/cdro_significance.json"),
        ),
    }
    rows = [[
        "setting", "method", "method_label", "n", "f1_mean", "f1_std", "fpr_mean", "fpr_std", "ece_mean", "ece_std", "brier_mean", "brier_std"
    ]]
    lines = ["# Strong Noisy-Label Baselines", ""]
    for setting, (summary, sig) in suites.items():
        stats = stats_for_runs(list(summary.get("runs", [])), STRONGBASE_METHODS)
        lines.append(f"## {SETTING_LABELS[setting]}")
        for method in STRONGBASE_METHODS:
            block = stats[method]
            rows.append([
                setting,
                method,
                METHOD_LABELS[method],
                block["f1_n"],
                block["f1_mean"],
                block["f1_std"],
                block["fpr_mean"],
                block["fpr_std"],
                block["ece_mean"],
                block["ece_std"],
                block["brier_mean"],
                block["brier_std"],
            ])
            lines.append(f"- {METHOD_LABELS[method]}: F1={block['f1_mean']:.4f}, FPR={block['fpr_mean']:.4f}, ECE={block['ece_mean']:.4f}")
        best_non_cdro = min(
            [m for m in STRONGBASE_METHODS if m != "cdro_ug"],
            key=lambda m: stats[m]["fpr_mean"],
        )
        comp_best = find_comparison(sig, "cdro_ug", best_non_cdro)
        lines.extend([
            "",
            f"- Best non-CDRO baseline by pooled FPR in {SETTING_LABELS[setting]} is {METHOD_LABELS[best_non_cdro]}.",
            f"- CDRO-UG vs {METHOD_LABELS[best_non_cdro]}: delta_F1={comp_best['pooled']['f1']['delta_mean']:+.6f}, p={comp_best['pooled']['f1']['p_value']:.6g}; delta_FPR={comp_best['pooled']['fpr']['delta_mean']:+.6f}, p={comp_best['pooled']['fpr']['p_value']:.6g}.",
            "",
        ])
    write_csv(out_dir / "table11_strong_baselines.csv", rows)
    write_text(out_dir / "strong_baselines.md", "\n".join(lines))


def write_operating_points(out_dir: Path, root: Path) -> None:
    suites = {
        "main": load_json(root / "cdro_suite/main_rewrite_sw0_s5_v1/cdro_summary.json"),
        "batch2": load_json(root / "cdro_suite/batch2_rewrite_sw0_s3_v2/cdro_summary.json"),
    }
    rows = [[
        "setting", "method", "method_label", "n", "auroc", "auprc", "fpr_at_95_recall", "recall_at_1_fpr", "recall_at_5_fpr", "recall_at_10_fpr"
    ]]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    for col, (setting, summary) in enumerate(suites.items()):
        pooled = pooled_probs_from_summary(summary, CORE_METHODS)
        ax_roc = axes[0, col]
        ax_pr = axes[1, col]
        for method in CORE_METHODS:
            prob, y_true = pooled[method]
            fpr, tpr = roc_curve(prob, y_true)
            recall, precision = pr_curve(prob, y_true)
            auroc = auc_xy(fpr, tpr)
            auprc = auc_xy(recall, precision)
            rows.append([
                setting,
                method,
                METHOD_LABELS[method],
                int(prob.numel()),
                auroc,
                auprc,
                fpr_at_target_recall(prob, y_true, target_recall=0.95),
                recall_at_target_fpr(prob, y_true, target_fpr=0.01),
                recall_at_target_fpr(prob, y_true, target_fpr=0.05),
                recall_at_target_fpr(prob, y_true, target_fpr=0.10),
            ])
            ax_roc.plot(fpr.tolist(), tpr.tolist(), linewidth=2.0, color=METHOD_COLORS[method], label=METHOD_LABELS[method])
            ax_pr.plot(recall.tolist(), precision.tolist(), linewidth=2.0, color=METHOD_COLORS[method], label=METHOD_LABELS[method])
        ax_roc.plot([0, 1], [0, 1], linestyle="--", linewidth=1.0, color="#444444")
        ax_roc.set_title(f"{SETTING_LABELS[setting]} ROC")
        ax_roc.set_xlabel("FPR")
        ax_roc.set_ylabel("Recall")
        ax_roc.grid(alpha=0.25, linestyle="--")
        ax_pr.set_title(f"{SETTING_LABELS[setting]} PR")
        ax_pr.set_xlabel("Recall")
        ax_pr.set_ylabel("Precision")
        ax_pr.grid(alpha=0.25, linestyle="--")
    axes[0, 1].legend(loc="lower right", fontsize=8)
    axes[1, 1].legend(loc="lower left", fontsize=8)
    fig.suptitle("Operating-point analysis for locked main methods", fontsize=14)
    fig.savefig(out_dir / "fig6_operating_points.png", dpi=240)
    plt.close(fig)

    lines = [
        "# Operating-Point Analysis",
        "",
        "- This artifact summarizes ROC/PR behaviour and operating points that matter for low-FPR deployment.",
        "- The main reviewer-facing readout is FPR@95%Recall and Recall@1/5/10% FPR rather than global calibration.",
    ]
    write_csv(out_dir / "table12_operating_points.csv", rows)
    write_text(out_dir / "operating_points.md", "\n".join(lines))


def write_hard_protocols(out_dir: Path, root: Path) -> None:
    suites = {
        "main": load_json(root / "cdro_suite/hard_main_core_s3_v1/cdro_hard_summary.json"),
        "batch2": load_json(root / "cdro_suite/hard_batch2_core_s3_v1/cdro_hard_summary.json"),
    }
    sig = load_json(root / "cdro_suite/hard_combined_core_s3_v1/cdro_significance.json")
    rows = [[
        "setting", "protocol", "protocol_label", "method", "method_label", "n", "f1_mean", "f1_std", "fpr_mean", "fpr_std", "ece_mean", "ece_std", "brier_mean", "brier_std"
    ]]
    lines = ["# Hard / Camouflaged Protocol Suite", ""]
    for setting, summary in suites.items():
        lines.append(f"## {SETTING_LABELS[setting]}")
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for run in summary.get("runs", []):
            grouped[str(run["protocol"])].append(run)
        grouped["pooled"] = list(summary.get("runs", []))
        for proto in ["temporal_ood", "topology_ood", "attack_strategy_ood", "congestion_ood", "pooled"]:
            stats = stats_for_runs(grouped.get(proto, []), CORE_METHODS)
            lines.append(f"### {HARD_PROTOCOL_LABELS[proto]}")
            for method in CORE_METHODS:
                block = stats[method]
                rows.append([
                    setting,
                    proto,
                    HARD_PROTOCOL_LABELS[proto],
                    method,
                    METHOD_LABELS[method],
                    block["f1_n"],
                    block["f1_mean"],
                    block["f1_std"],
                    block["fpr_mean"],
                    block["fpr_std"],
                    block["ece_mean"],
                    block["ece_std"],
                    block["brier_mean"],
                    block["brier_std"],
                ])
                lines.append(f"- {METHOD_LABELS[method]}: F1={block['f1_mean']:.4f}, FPR={block['fpr_mean']:.4f}, ECE={block['ece_mean']:.4f}")
            lines.append("")
    comp = find_comparison(sig, "cdro_ug", "noisy_ce")
    lines.extend([
        "## Reading",
        f"- Combined hard-suite pooled comparison against Noisy-CE: delta_F1={comp['pooled']['f1']['delta_mean']:+.6f}, p={comp['pooled']['f1']['p_value']:.6g}; delta_FPR={comp['pooled']['fpr']['delta_mean']:+.6f}, p={comp['pooled']['fpr']['p_value']:.6g}.",
        "- This suite should be read as a stress-test supplement: after correcting merged pairing, the combined hard-suite pooled delta is near zero, so the safe takeaway is no catastrophic collapse rather than a new advantage claim.",
    ])
    write_csv(out_dir / "table13_hard_protocols.csv", rows)
    write_text(out_dir / "hard_protocols.md", "\n".join(lines))


def stress_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    meta_map = {
        (v["protocol"], v["stress_kind"], round(float(v["stress_level"]), 6)): v.get("stress_meta", {})
        for v in summary.get("stress_graphs", {}).values()
    }
    for run in summary.get("runs", []):
        key = (run["protocol"], run["stress_kind"], round(float(run["stress_level"]), 6))
        meta = meta_map.get(key, {})
        row = {
            "protocol": str(run["protocol"]),
            "stress_kind": str(run["stress_kind"]),
            "stress_level": float(run["stress_level"]),
            "method": str(run["method"]),
            "seed": int(run["seed"]),
            "covered_ratio_after": float(meta.get("covered_train_nodes_after", 0.0)) / max(float(meta.get("covered_train_nodes_before", 1.0)), 1.0),
            **{metric: float(run["metrics"].get(metric, 0.0)) for metric in METRICS},
        }
        rows.append(row)
    return rows


def plot_stress_metric(ax: Any, rows: list[dict[str, Any]], metric: str, title: str) -> None:
    for method in ["noisy_ce", "posterior_ce", "cdro_ug"]:
        xs = sorted({float(row["stress_level"]) for row in rows if row["method"] == method})
        ys = []
        for x in xs:
            vals = [float(row[metric]) for row in rows if row["method"] == method and abs(float(row["stress_level"]) - x) <= 1e-9]
            ys.append(statistics.mean(vals) if vals else 0.0)
        ax.plot(xs, ys, marker="o", linewidth=2.0, color=METHOD_COLORS[method], label=METHOD_LABELS[method])
    ax.set_title(title)
    ax.set_xlabel("Stress level")
    ax.set_ylabel(metric.upper())
    ax.grid(alpha=0.25, linestyle="--")


def write_stress_sweeps(out_dir: Path, root: Path) -> None:
    suite_paths = {
        ("main", "noise"): root / "cdro_suite/stress_noise_main_s3_v1/cdro_stress_summary.json",
        ("batch2", "noise"): root / "cdro_suite/stress_noise_batch2_s3_v1/cdro_stress_summary.json",
        ("main", "coverage"): root / "cdro_suite/stress_coverage_main_s3_v1/cdro_stress_summary.json",
        ("batch2", "coverage"): root / "cdro_suite/stress_coverage_batch2_s3_v1/cdro_stress_summary.json",
    }
    rows_out = [[
        "setting", "stress_kind", "protocol", "stress_level", "method", "n", "covered_ratio_after_mean", "f1_mean", "f1_std", "fpr_mean", "fpr_std", "ece_mean", "ece_std"
    ]]
    lines = ["# Noise / Coverage Stress Sweeps", ""]
    fig_f1, axes_f1 = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    fig_fpr, axes_fpr = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)

    for row_idx, stress_kind in enumerate(["noise", "coverage"]):
        for col_idx, setting in enumerate(["main", "batch2"]):
            summary = load_json(suite_paths[(setting, stress_kind)])
            rows = stress_rows(summary)
            pooled_by_level: defaultdict[tuple[float, str], list[dict[str, Any]]] = defaultdict(list)
            for row in rows:
                pooled_by_level[(float(row["stress_level"]), str(row["method"]))].append(row)
            grouped_proto: defaultdict[tuple[str, float, str], list[dict[str, Any]]] = defaultdict(list)
            for row in rows:
                grouped_proto[(row["protocol"], float(row["stress_level"]), str(row["method"]))].append(row)
            for (proto, level, method), vals in sorted(grouped_proto.items()):
                f1_vals = [float(v["f1"]) for v in vals]
                fpr_vals = [float(v["fpr"]) for v in vals]
                ece_vals = [float(v["ece"]) for v in vals]
                cov_vals = [float(v["covered_ratio_after"]) for v in vals]
                rows_out.append([
                    setting,
                    stress_kind,
                    proto,
                    level,
                    method,
                    len(vals),
                    statistics.mean(cov_vals) if cov_vals else 0.0,
                    statistics.mean(f1_vals) if f1_vals else 0.0,
                    statistics.stdev(f1_vals) if len(f1_vals) > 1 else 0.0,
                    statistics.mean(fpr_vals) if fpr_vals else 0.0,
                    statistics.stdev(fpr_vals) if len(fpr_vals) > 1 else 0.0,
                    statistics.mean(ece_vals) if ece_vals else 0.0,
                    statistics.stdev(ece_vals) if len(ece_vals) > 1 else 0.0,
                ])
            pooled_rows = []
            for (level, method), vals in sorted(pooled_by_level.items()):
                for v in vals:
                    pooled_rows.append(v)
            plot_stress_metric(
                axes_f1[row_idx, col_idx],
                pooled_rows,
                metric="f1",
                title=f"{SETTING_LABELS[setting]} {stress_kind}: F1",
            )
            plot_stress_metric(
                axes_fpr[row_idx, col_idx],
                pooled_rows,
                metric="fpr",
                title=f"{SETTING_LABELS[setting]} {stress_kind}: FPR",
            )
            hardest = max({float(v["stress_level"]) for v in rows}) if rows else 0.0
            ug_hard = [float(v["fpr"]) for v in rows if v["method"] == "cdro_ug" and abs(float(v["stress_level"]) - hardest) <= 1e-9]
            noisy_hard = [float(v["fpr"]) for v in rows if v["method"] == "noisy_ce" and abs(float(v["stress_level"]) - hardest) <= 1e-9]
            if ug_hard and noisy_hard:
                lines.append(
                    f"- {SETTING_LABELS[setting]} {stress_kind} hardest level {hardest:.2f}: CDRO-UG pooled FPR={statistics.mean(ug_hard):.4f}, Noisy-CE pooled FPR={statistics.mean(noisy_hard):.4f}, delta={statistics.mean(ug_hard) - statistics.mean(noisy_hard):+.4f}."
                )

    axes_f1[0, 1].legend(loc="best", fontsize=8)
    axes_fpr[0, 1].legend(loc="best", fontsize=8)
    fig_f1.suptitle("Stress sweeps: pooled F1 under weak-label degradation", fontsize=14)
    fig_fpr.suptitle("Stress sweeps: pooled FPR under weak-label degradation", fontsize=14)
    fig_f1.savefig(out_dir / "fig7_stress_f1.png", dpi=240)
    fig_fpr.savefig(out_dir / "fig8_stress_fpr.png", dpi=240)
    plt.close(fig_f1)
    plt.close(fig_fpr)

    write_csv(out_dir / "table14_stress_sweeps.csv", rows_out)
    write_text(out_dir / "stress_sweeps.md", "\n".join(lines))


def update_indexes(out_dir: Path) -> None:
    append_lines_once(
        out_dir / "INDEX.md",
        [
            "- `table10_external4_validation.csv`",
            "- `external4_validation.md`",
            "- `table11_strong_baselines.csv`",
            "- `strong_baselines.md`",
            "- `table12_operating_points.csv`",
            "- `operating_points.md`",
            "- `fig6_operating_points.png`",
            "- `table13_hard_protocols.csv`",
            "- `hard_protocols.md`",
            "- `table14_stress_sweeps.csv`",
            "- `stress_sweeps.md`",
            "- `fig7_stress_f1.png`",
            "- `fig8_stress_fpr.png`",
        ],
    )
    append_lines_once(
        out_dir / "FIGURE_CAPTIONS.md",
        [
            "",
            "## Fig 6. Operating-point analysis",
            "ROC and PR curves are pooled over the locked main methods on the main batch and batch2. The accompanying table reports FPR at 95% recall and recall at 1/5/10% FPR to support low-false-positive deployment claims.",
            "",
            "## Fig 7. Stress sweep F1 curves",
            "Pooled F1 is plotted against weak-label flip ratio and weak-label drop ratio for the main batch and batch2. This figure is intended to show degradation trends rather than a single significance headline.",
            "",
            "## Fig 8. Stress sweep FPR curves",
            "Pooled FPR is plotted against weak-label flip ratio and weak-label drop ratio. The key reviewer-facing readout is whether CDRO-UG degrades more slowly than Noisy-CE under harsher weak-label corruption.",
        ],
    )
    append_lines_once(
        out_dir / "TABLE_NOTES.md",
        [
            "",
            "## Table 10. External 4-batch validation",
            "This table pools four independent external batch2-style captures. It should be used to support the claim that the rewritten UG is not relying on a single external batch.",
            "",
            "## Table 11. Strong noisy-label baselines",
            "This table adds GCE, SCE, Bootstrap-CE, and ELR on top of the previous supplemental baseline family. It is primarily for rebuttal and reviewer concerns about stronger noisy-label competitors.",
            "",
            "## Table 12. Operating-point analysis",
            "This table reports ROC/PR-derived deployment metrics such as FPR@95%Recall and Recall@1/5/10%FPR. Use it to strengthen the practical interpretation of the FPR claim.",
            "",
            "## Table 13. Hard / camouflaged protocols",
            "This table summarizes overlap-hardened and camouflaged protocol variants. It should be framed as a stress-test supplement rather than the main headline table.",
            "",
            "## Table 14. Stress sweeps",
            "This table reports pooled trends under increasing weak-label noise and weak-label coverage loss. It is most useful for appendix placement and reviewer-facing robustness discussion.",
        ],
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent))
    args = ap.parse_args()
    root = Path(args.root).resolve()
    out_dir = root / "cdro_suite" / "paper_ready_plus"
    out_dir.mkdir(parents=True, exist_ok=True)

    write_external_validation(out_dir, root)
    write_strong_baselines(out_dir, root)
    write_operating_points(out_dir, root)
    write_hard_protocols(out_dir, root)
    write_stress_sweeps(out_dir, root)
    update_indexes(out_dir)
    print(out_dir)


if __name__ == "__main__":
    main()
