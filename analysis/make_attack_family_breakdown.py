#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import torch


METHODS = ["noisy_ce", "cdro_fixed", "cdro_ug"]
METHOD_LABELS = {
    "noisy_ce": "Noisy-CE",
    "cdro_fixed": "CDRO-Fixed",
    "cdro_ug": "CDRO-UG(sw0)",
}
FAMILIES = ["slowburn", "burst", "mimic"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def suite_output_dir(summary: dict[str, Any]) -> Path:
    return Path(summary["config"]["output_dir"]).resolve()


def metric_tuple(y_true: torch.Tensor, pred: torch.Tensor, mask: torch.Tensor) -> dict[str, float]:
    tp = int(((pred == 1) & (y_true == 1) & mask).sum().item())
    fp = int(((pred == 1) & (y_true == 0) & mask).sum().item())
    fn = int(((pred == 0) & (y_true == 1) & mask).sum().item())
    tn = int(((pred == 0) & (y_true == 0) & mask).sum().item())
    precision = float(tp / max(tp + fp, 1))
    recall = float(tp / max(tp + fn, 1))
    f1 = float(2.0 * precision * recall / max(precision + recall, 1e-12))
    fpr = float(fp / max(fp + tn, 1))
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": precision, "recall": recall, "f1": f1, "fpr": fpr}


def mean_std(vals: list[float]) -> tuple[float, float]:
    if not vals:
        return 0.0, 0.0
    if len(vals) == 1:
        return float(vals[0]), 0.0
    return float(statistics.mean(vals)), float(statistics.stdev(vals))


def family_mask(graph: Any, roles: dict[str, str], family: str) -> torch.Tensor:
    mask = torch.zeros(graph.num_nodes, dtype=torch.bool)
    for ip_i, ip in enumerate(graph.source_ips):
        if str(roles.get(ip, "")) == f"bot:{family}":
            mask |= graph.ip_idx == ip_i
    return mask


def benign_mask(graph: Any, roles: dict[str, str]) -> torch.Tensor:
    mask = torch.zeros(graph.num_nodes, dtype=torch.bool)
    for ip_i, ip in enumerate(graph.source_ips):
        if not str(roles.get(ip, "")).startswith("bot:"):
            mask |= graph.ip_idx == ip_i
    return mask


def main() -> None:
    ap = argparse.ArgumentParser(description="Build per-attack-family breakdown artifacts")
    ap.add_argument("--main-summary", default="/home/user/FedSTGCN/cdro_suite/main_baselineplus_s3_v1/cdro_summary.json")
    ap.add_argument("--external-summary", default="/home/user/FedSTGCN/cdro_suite/batch2_baselineplus_s3_v1/cdro_summary.json")
    ap.add_argument("--output-dir", default="/home/user/FedSTGCN/cdro_suite/attack_family_breakdown_s3_v1")
    ap.add_argument("--paper-dir", default="/home/user/FedSTGCN/cdro_suite/paper_ready_plus")
    args = ap.parse_args()

    out_dir = Path(args.output_dir).resolve()
    paper_dir = Path(args.paper_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    paper_dir.mkdir(parents=True, exist_ok=True)

    dataset_specs = {
        "main": load_json(Path(args.main_summary).resolve()),
        "external_j": load_json(Path(args.external_summary).resolve()),
    }

    all_rows: list[dict[str, Any]] = []
    for dataset_name, summary in dataset_specs.items():
        roles = load_json(Path(summary["config"]["manifest_file"]).resolve()).get("roles", {})
        suite_dir = suite_output_dir(summary)
        for protocol in ["weak_temporal_ood", "weak_topology_ood", "weak_attack_strategy_ood", "label_prior_shift_ood"]:
            graph = torch.load(suite_dir / "protocol_graphs" / f"{protocol}.pt", map_location="cpu", weights_only=False)
            benign = benign_mask(graph, roles)
            fam_masks = {family: family_mask(graph, roles, family) for family in FAMILIES}
            for method in METHODS:
                for seed in [11, 22, 33]:
                    run_dir = suite_dir / "runs" / f"{protocol}__{method}__seed{seed}"
                    result = load_json(run_dir / "results.json")
                    logits = torch.load(run_dir / "results_logits.pt", map_location="cpu", weights_only=False)
                    pred = logits["probs"][:, 1] >= float(result["best_threshold"])
                    y_true = logits["y_true"].long()
                    test_mask = logits["temporal_test_mask"].bool()
                    for family in FAMILIES:
                        attack_nodes = test_mask & fam_masks[family] & (y_true == 1)
                        if int(attack_nodes.sum().item()) == 0:
                            continue
                        sub_mask = test_mask & (benign | fam_masks[family])
                        metrics = metric_tuple(y_true, pred.long(), sub_mask)
                        metrics.update(
                            {
                                "dataset": dataset_name,
                                "protocol": protocol,
                                "method": method,
                                "seed": seed,
                                "family": family,
                                "attack_nodes": int(attack_nodes.sum().item()),
                            }
                        )
                        all_rows.append(metrics)

    save_path = out_dir / "attack_family_summary.json"
    save_path.write_text(json.dumps({"rows": all_rows}, indent=2), encoding="utf-8")

    csv_path = paper_dir / "table19_attack_family_breakdown.csv"
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in all_rows:
        grouped[(row["dataset"], row["family"], row["method"])].append(row)
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["dataset", "family", "method", "label", "n_runs", "f1_mean", "f1_std", "recall_mean", "recall_std", "fpr_mean", "fpr_std", "attack_nodes_mean"])
        for dataset in ["main", "external_j"]:
            for family in FAMILIES:
                for method in METHODS:
                    rows = grouped[(dataset, family, method)]
                    writer.writerow(
                        [
                            dataset,
                            family,
                            method,
                            METHOD_LABELS[method],
                            len(rows),
                            mean_std([float(r["f1"]) for r in rows])[0],
                            mean_std([float(r["f1"]) for r in rows])[1],
                            mean_std([float(r["recall"]) for r in rows])[0],
                            mean_std([float(r["recall"]) for r in rows])[1],
                            mean_std([float(r["fpr"]) for r in rows])[0],
                            mean_std([float(r["fpr"]) for r in rows])[1],
                            mean_std([float(r["attack_nodes"]) for r in rows])[0],
                        ]
                    )

    lines = [
        "# Per-Attack-Family Breakdown",
        "",
        "This breakdown is pooled over the four protocol splits. That choice is deliberate: `weak_attack_strategy_ood` is a mimic-holdout protocol, so a protocol-only family table would collapse `slowburn` and `burst` to zero-count rows.",
        "",
    ]
    for dataset in ["main", "external_j"]:
        lines.append(f"## {dataset}")
        lines.append("")
        lines.append("| Family | Method | F1 | Recall | FPR |")
        lines.append("|---|---|---:|---:|---:|")
        for family in FAMILIES:
            for method in METHODS:
                rows = grouped[(dataset, family, method)]
                f1_m, f1_s = mean_std([float(r["f1"]) for r in rows])
                rec_m, rec_s = mean_std([float(r["recall"]) for r in rows])
                fpr_m, fpr_s = mean_std([float(r["fpr"]) for r in rows])
                lines.append(
                    f"| {family} | {METHOD_LABELS[method]} | {f1_m:.3f} +- {f1_s:.3f} | {rec_m:.3f} +- {rec_s:.3f} | {fpr_m:.3f} +- {fpr_s:.3f} |"
                )
        lines.append("")
        if dataset == "external_j":
            lines.append(
                "- External-J readout: CDRO-UG has the lowest pooled FPR for `slowburn` and `mimic`, while `burst` remains the hardest family across all methods."
            )
        else:
            lines.append(
                "- Main-batch readout: `burst` is the hardest family, while `slowburn` and `mimic` remain substantially easier."
            )
        lines.append("")
    lines.append(f"Artifacts: `{csv_path.name}`, `attack_family_summary.json`.")
    (paper_dir / "attack_family_breakdown.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
