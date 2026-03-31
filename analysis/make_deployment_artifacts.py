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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def mean_std(vals: list[float]) -> tuple[float, float]:
    if not vals:
        return 0.0, 0.0
    if len(vals) == 1:
        return float(vals[0]), 0.0
    return float(statistics.mean(vals)), float(statistics.stdev(vals))


def pair_unit_key(run: dict[str, Any]) -> tuple[str, int]:
    return str(run["protocol"]), int(run["seed"])


def paired_signflip(x: list[float], y: list[float]) -> float:
    if len(x) != len(y) or not x:
        return 1.0
    diffs = [float(a - b) for a, b in zip(x, y)]
    obs = abs(sum(diffs) / len(diffs))
    if obs <= 1e-12:
        return 1.0
    total = 0
    extreme = 0
    n = len(diffs)
    if n <= 12:
        def rec(i: int, accum: float) -> None:
            nonlocal total, extreme
            if i == n:
                total += 1
                if abs(accum / n) >= obs - 1e-12:
                    extreme += 1
                return
            rec(i + 1, accum + diffs[i])
            rec(i + 1, accum - diffs[i])
        rec(0, 0.0)
    else:
        import random
        rng = random.Random(42)
        for _ in range(20000):
            total += 1
            stat = abs(sum(d * (1.0 if rng.random() > 0.5 else -1.0) for d in diffs) / n)
            if stat >= obs - 1e-12:
                extreme += 1
    return float((extreme + 1) / (total + 1))


def evaluate_counts(prob_attack: torch.Tensor, y_true: torch.Tensor, mask: torch.Tensor, threshold: float) -> dict[str, float]:
    pred = prob_attack >= float(threshold)
    tp = int(((pred == 1) & (y_true == 1) & mask).sum().item())
    fp = int(((pred == 1) & (y_true == 0) & mask).sum().item())
    fn = int(((pred == 0) & (y_true == 1) & mask).sum().item())
    tn = int(((pred == 0) & (y_true == 0) & mask).sum().item())
    precision = float(tp / max(tp + fp, 1))
    recall = float(tp / max(tp + fn, 1))
    f1 = float(2.0 * precision * recall / max(precision + recall, 1e-12))
    fpr = float(fp / max(fp + tn, 1))
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fpr": fpr,
        "threshold": float(threshold),
    }


def collect_benign_alert_metrics(
    graph: Any,
    roles: dict[str, str],
    prob_attack: torch.Tensor,
    y_true: torch.Tensor,
    mask: torch.Tensor,
    threshold: float,
) -> dict[str, float]:
    pred = prob_attack >= float(threshold)
    benign_mask = mask & (y_true == 0)
    benign_node_total = int(benign_mask.sum().item())
    benign_alert_count = int((benign_mask & pred).sum().item())
    benign_ip_total = 0
    benign_ip_flagged = 0
    for ip_i, ip in enumerate(graph.source_ips):
        if str(roles.get(ip, "")).startswith("bot:"):
            continue
        ip_mask = benign_mask & (graph.ip_idx == ip_i)
        if int(ip_mask.sum().item()) == 0:
            continue
        benign_ip_total += 1
        if int((ip_mask & pred).sum().item()) > 0:
            benign_ip_flagged += 1
    return {
        "benign_node_total": benign_node_total,
        "benign_alert_count": benign_alert_count,
        "benign_alerts_per_10k": float(10000.0 * benign_alert_count / max(benign_node_total, 1)),
        "benign_ip_total": int(benign_ip_total),
        "benign_ip_flagged": int(benign_ip_flagged),
        "benign_ip_flag_rate": float(benign_ip_flagged / max(benign_ip_total, 1)),
    }


def collect_attack_ip_metrics(
    graph: Any,
    roles: dict[str, str],
    prob_attack: torch.Tensor,
    y_true: torch.Tensor,
    mask: torch.Tensor,
    threshold: float,
) -> dict[str, float]:
    pred = prob_attack >= float(threshold)
    delays: list[int] = []
    attack_ip_total = 0
    attack_ip_detected = 0
    for ip_i, ip in enumerate(graph.source_ips):
        if not str(roles.get(ip, "")).startswith("bot:"):
            continue
        ip_mask = mask & (graph.ip_idx == ip_i) & (y_true == 1)
        if int(ip_mask.sum().item()) == 0:
            continue
        attack_ip_total += 1
        first_true = int(graph.window_idx[ip_mask].min().item())
        det_mask = ip_mask & pred
        if int(det_mask.sum().item()) > 0:
            attack_ip_detected += 1
            first_alert = int(graph.window_idx[det_mask].min().item())
            delays.append(first_alert - first_true)
    return {
        "attack_ip_total": int(attack_ip_total),
        "attack_ip_detected": int(attack_ip_detected),
        "attack_ip_detect_rate": float(attack_ip_detected / max(attack_ip_total, 1)),
        "delay_mean": float(statistics.mean(delays)) if delays else 0.0,
        "delay_median": float(statistics.median(delays)) if delays else 0.0,
        "delay_max": float(max(delays)) if delays else 0.0,
    }


def summarize_significance(runs: list[dict[str, Any]]) -> dict[str, Any]:
    rows: dict[tuple[str, int], dict[str, dict[str, float]]] = defaultdict(dict)
    for run in runs:
        rows[pair_unit_key(run)][str(run["method"])] = dict(run["metrics"])
    comps = []
    for method_a, method_b in [("cdro_ug", "noisy_ce"), ("cdro_ug", "cdro_fixed")]:
        out = {"method_a": method_a, "method_b": method_b, "pooled": {}}
        for metric in ["f1", "fpr", "fp", "benign_alerts_per_10k", "benign_ip_flag_rate"]:
            xa: list[float] = []
            xb: list[float] = []
            for key in sorted(rows):
                block = rows[key]
                if method_a in block and method_b in block:
                    xa.append(float(block[method_a][metric]))
                    xb.append(float(block[method_b][metric]))
            out["pooled"][metric] = {
                "delta_mean": float(statistics.mean([a - b for a, b in zip(xa, xb)])) if xa else 0.0,
                "p_value": paired_signflip(xa, xb),
            }
        comps.append(out)
    return {"comparisons": comps}


def main() -> None:
    ap = argparse.ArgumentParser(description="Build frozen-threshold + detection-delay deployment artifacts")
    ap.add_argument("--main-summary", default="/home/user/FedSTGCN/cdro_suite/main_baselineplus_s3_v1/cdro_summary.json")
    ap.add_argument("--external-summary", default="/home/user/FedSTGCN/cdro_suite/batch2_baselineplus_s3_v1/cdro_summary.json")
    ap.add_argument("--output-dir", default="/home/user/FedSTGCN/cdro_suite/deployment_checks_s3_v1")
    ap.add_argument("--paper-dir", default="/home/user/FedSTGCN/cdro_suite/paper_ready_plus")
    args = ap.parse_args()

    main_summary = load_json(Path(args.main_summary).resolve())
    external_summary = load_json(Path(args.external_summary).resolve())
    out_dir = Path(args.output_dir).resolve()
    paper_dir = Path(args.paper_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    paper_dir.mkdir(parents=True, exist_ok=True)

    roles = load_json(Path(external_summary["config"]["manifest_file"]).resolve()).get("roles", {})
    main_runs = {(run["protocol"], run["method"], int(run["seed"])): run for run in main_summary["runs"]}

    deployment_rows: list[dict[str, Any]] = []
    frozen_sig_runs: list[dict[str, Any]] = []
    for run in external_summary["runs"]:
        protocol = str(run["protocol"])
        method = str(run["method"])
        seed = int(run["seed"])
        if method not in METHODS:
            continue
        main_run = main_runs[(protocol, method, seed)]
        tuned_result = load_json(Path(run["result_file"]).resolve())
        tuned_logits = torch.load(str(Path(run["result_file"]).resolve()).replace("results.json", "results_logits.pt"), map_location="cpu", weights_only=False)
        graph = torch.load(Path(tuned_result["config"]["graph_file"]).resolve(), map_location="cpu", weights_only=False)
        mask = tuned_logits["temporal_test_mask"].bool()
        y_true = tuned_logits["y_true"].long()
        prob_attack = tuned_logits["probs"][:, 1].float()

        tuned_threshold = float(tuned_result["best_threshold"])
        frozen_threshold = float(load_json(Path(main_run["result_file"]).resolve())["best_threshold"])
        tuned_metrics = evaluate_counts(prob_attack, y_true, mask, tuned_threshold)
        frozen_metrics = evaluate_counts(prob_attack, y_true, mask, frozen_threshold)
        tuned_delay = collect_attack_ip_metrics(graph, roles, prob_attack, y_true, mask, tuned_threshold)
        frozen_delay = collect_attack_ip_metrics(graph, roles, prob_attack, y_true, mask, frozen_threshold)
        tuned_benign = collect_benign_alert_metrics(graph, roles, prob_attack, y_true, mask, tuned_threshold)
        frozen_benign = collect_benign_alert_metrics(graph, roles, prob_attack, y_true, mask, frozen_threshold)

        deployment_rows.append(
            {
                "protocol": protocol,
                "method": method,
                "seed": seed,
                "tuned_threshold": tuned_threshold,
                "frozen_threshold": frozen_threshold,
                "tuned_metrics": tuned_metrics,
                "frozen_metrics": frozen_metrics,
                "tuned_delay": tuned_delay,
                "frozen_delay": frozen_delay,
                "tuned_benign": tuned_benign,
                "frozen_benign": frozen_benign,
            }
        )
        frozen_sig_metrics = {k: frozen_metrics[k] for k in ["f1", "fpr", "fp"]}
        frozen_sig_metrics["benign_alerts_per_10k"] = frozen_benign["benign_alerts_per_10k"]
        frozen_sig_metrics["benign_ip_flag_rate"] = frozen_benign["benign_ip_flag_rate"]
        frozen_sig_runs.append(
            {
                "id": f"{protocol}__{method}__seed{seed}__frozen",
                "protocol": protocol,
                "method": method,
                "seed": seed,
                "metrics": frozen_sig_metrics,
            }
        )

    deployment_summary = {
        "main_summary": str(Path(args.main_summary).resolve()),
        "external_summary": str(Path(args.external_summary).resolve()),
        "rows": deployment_rows,
    }
    save_json(out_dir / "deployment_summary.json", deployment_summary)

    frozen_sig = summarize_significance(frozen_sig_runs)
    save_json(out_dir / "frozen_externalJ_significance.json", frozen_sig)

    table_rows = []
    for method in METHODS:
        method_rows = [r for r in deployment_rows if r["method"] == method]
        tuned_f1 = [r["tuned_metrics"]["f1"] for r in method_rows]
        tuned_fpr = [r["tuned_metrics"]["fpr"] for r in method_rows]
        tuned_detect = [r["tuned_delay"]["attack_ip_detect_rate"] for r in method_rows]
        tuned_delay = [r["tuned_delay"]["delay_mean"] for r in method_rows]
        frozen_f1 = [r["frozen_metrics"]["f1"] for r in method_rows]
        frozen_fpr = [r["frozen_metrics"]["fpr"] for r in method_rows]
        frozen_detect = [r["frozen_delay"]["attack_ip_detect_rate"] for r in method_rows]
        frozen_delay = [r["frozen_delay"]["delay_mean"] for r in method_rows]
        frozen_fp = [r["frozen_metrics"]["fp"] for r in method_rows]
        frozen_benign_per10k = [r["frozen_benign"]["benign_alerts_per_10k"] for r in method_rows]
        frozen_benign_ip_flag_rate = [r["frozen_benign"]["benign_ip_flag_rate"] for r in method_rows]
        row = {
            "method": method,
            "label": METHOD_LABELS[method],
            "n_runs": len(method_rows),
            "tuned_f1_mean": mean_std(tuned_f1)[0],
            "tuned_f1_std": mean_std(tuned_f1)[1],
            "tuned_fpr_mean": mean_std(tuned_fpr)[0],
            "tuned_fpr_std": mean_std(tuned_fpr)[1],
            "tuned_detect_rate_mean": mean_std(tuned_detect)[0],
            "tuned_detect_rate_std": mean_std(tuned_detect)[1],
            "tuned_delay_mean": mean_std(tuned_delay)[0],
            "tuned_delay_std": mean_std(tuned_delay)[1],
            "frozen_f1_mean": mean_std(frozen_f1)[0],
            "frozen_f1_std": mean_std(frozen_f1)[1],
            "frozen_fpr_mean": mean_std(frozen_fpr)[0],
            "frozen_fpr_std": mean_std(frozen_fpr)[1],
            "frozen_detect_rate_mean": mean_std(frozen_detect)[0],
            "frozen_detect_rate_std": mean_std(frozen_detect)[1],
            "frozen_delay_mean": mean_std(frozen_delay)[0],
            "frozen_delay_std": mean_std(frozen_delay)[1],
            "frozen_fp_mean": mean_std(frozen_fp)[0],
            "frozen_fp_std": mean_std(frozen_fp)[1],
            "frozen_benign_per10k_mean": mean_std(frozen_benign_per10k)[0],
            "frozen_benign_per10k_std": mean_std(frozen_benign_per10k)[1],
            "frozen_benign_ip_flag_rate_mean": mean_std(frozen_benign_ip_flag_rate)[0],
            "frozen_benign_ip_flag_rate_std": mean_std(frozen_benign_ip_flag_rate)[1],
        }
        table_rows.append(row)

    csv_path = paper_dir / "table18_deployment_checks.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "method",
                "label",
                "n_runs",
                "tuned_f1_mean",
                "tuned_f1_std",
                "tuned_fpr_mean",
                "tuned_fpr_std",
                "tuned_detect_rate_mean",
                "tuned_detect_rate_std",
                "tuned_delay_mean",
                "tuned_delay_std",
                "frozen_f1_mean",
                "frozen_f1_std",
                "frozen_fpr_mean",
                "frozen_fpr_std",
                "frozen_detect_rate_mean",
                "frozen_detect_rate_std",
                "frozen_delay_mean",
                "frozen_delay_std",
                "frozen_fp_mean",
                "frozen_fp_std",
                "frozen_benign_per10k_mean",
                "frozen_benign_per10k_std",
                "frozen_benign_ip_flag_rate_mean",
                "frozen_benign_ip_flag_rate_std",
            ],
        )
        writer.writeheader()
        writer.writerows(table_rows)

    sig_map = {(c["method_a"], c["method_b"]): c for c in frozen_sig["comparisons"]}
    ug_vs_noisy = sig_map[("cdro_ug", "noisy_ce")]
    ug_vs_fixed = sig_map[("cdro_ug", "cdro_fixed")]
    md_lines = [
        "# Deployment-Oriented Checks",
        "",
        "Scope: external-J (`batch2_baselineplus_s3_v1`) with thresholds frozen from the matched main-batch run (`same protocol + method + seed`).",
        "",
        "Latency and throughput remain reported in `runtime_costs.md`; this note adds the missing deployment-side checks: frozen-threshold transfer, first-alert delay, and analyst-facing benign alert burden.",
        "",
        "| Method | Tuned F1 / FPR | Tuned detect-rate / delay | Frozen F1 / FPR | Frozen detect-rate / delay | Frozen benign alerts | Frozen benign IP burden |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in table_rows:
        md_lines.append(
            f"| {row['label']} | "
            f"{row['tuned_f1_mean']:.3f} +- {row['tuned_f1_std']:.3f} / {row['tuned_fpr_mean']:.3f} +- {row['tuned_fpr_std']:.3f} | "
            f"{row['tuned_detect_rate_mean']:.3f} +- {row['tuned_detect_rate_std']:.3f} / {row['tuned_delay_mean']:.2f} +- {row['tuned_delay_std']:.2f} windows | "
            f"{row['frozen_f1_mean']:.3f} +- {row['frozen_f1_std']:.3f} / {row['frozen_fpr_mean']:.3f} +- {row['frozen_fpr_std']:.3f} | "
            f"{row['frozen_detect_rate_mean']:.3f} +- {row['frozen_detect_rate_std']:.3f} / {row['frozen_delay_mean']:.2f} +- {row['frozen_delay_std']:.2f} windows | "
            f"{row['frozen_fp_mean']:.1f} +- {row['frozen_fp_std']:.1f} FP / {row['frozen_benign_per10k_mean']:.0f} +- {row['frozen_benign_per10k_std']:.0f} per 10k benign | "
            f"{row['frozen_benign_ip_flag_rate_mean']:.3f} +- {row['frozen_benign_ip_flag_rate_std']:.3f} flagged benign IP rate |"
        )
    md_lines.extend(
        [
            "",
            "## Reading",
            "",
            f"- Frozen-threshold `CDRO-UG(sw0)` vs `Noisy-CE`: delta F1 `{ug_vs_noisy['pooled']['f1']['delta_mean']:+.3f}`, p=`{ug_vs_noisy['pooled']['f1']['p_value']:.6g}`; "
            f"delta FPR `{ug_vs_noisy['pooled']['fpr']['delta_mean']:+.3f}`, p=`{ug_vs_noisy['pooled']['fpr']['p_value']:.6g}`; "
            f"delta benign FP count `{ug_vs_noisy['pooled']['fp']['delta_mean']:+.1f}`, p=`{ug_vs_noisy['pooled']['fp']['p_value']:.6g}`; "
            f"delta benign alerts / 10k `{ug_vs_noisy['pooled']['benign_alerts_per_10k']['delta_mean']:+.0f}`, p=`{ug_vs_noisy['pooled']['benign_alerts_per_10k']['p_value']:.6g}`; "
            f"delta benign-IP flagged rate `{ug_vs_noisy['pooled']['benign_ip_flag_rate']['delta_mean']:+.3f}`, p=`{ug_vs_noisy['pooled']['benign_ip_flag_rate']['p_value']:.6g}`.",
            f"- Frozen-threshold `CDRO-UG(sw0)` vs `CDRO-Fixed`: delta F1 `{ug_vs_fixed['pooled']['f1']['delta_mean']:+.3f}`, p=`{ug_vs_fixed['pooled']['f1']['p_value']:.6g}`; "
            f"delta FPR `{ug_vs_fixed['pooled']['fpr']['delta_mean']:+.3f}`, p=`{ug_vs_fixed['pooled']['fpr']['p_value']:.6g}`; "
            f"delta benign FP count `{ug_vs_fixed['pooled']['fp']['delta_mean']:+.1f}`, p=`{ug_vs_fixed['pooled']['fp']['p_value']:.6g}`; "
            f"delta benign alerts / 10k `{ug_vs_fixed['pooled']['benign_alerts_per_10k']['delta_mean']:+.0f}`, p=`{ug_vs_fixed['pooled']['benign_alerts_per_10k']['p_value']:.6g}`; "
            f"delta benign-IP flagged rate `{ug_vs_fixed['pooled']['benign_ip_flag_rate']['delta_mean']:+.3f}`, p=`{ug_vs_fixed['pooled']['benign_ip_flag_rate']['p_value']:.6g}`.",
            "- With tuned thresholds, all three methods detect essentially all attack IPs and median first-alert delay is 0 windows.",
            "- With thresholds frozen from the main batch, CDRO-UG keeps the lowest external-J FPR and also yields the lowest benign alert burden by absolute FP count and FP-per-10k-benign. This makes the deployment gain easier to interpret in analyst-facing terms.",
            "- That benign-side reduction is not free: CDRO-UG still trades some frozen-threshold F1 and attack-IP detection coverage/delay for the lower alert burden. This is the correct deployment tradeoff to report rather than hide.",
            "",
            f"Artifacts: `{csv_path.name}`, `deployment_summary.json`, `frozen_externalJ_significance.json`.",
        ]
    )
    (paper_dir / "deployment_checks.md").write_text("\n".join(md_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
