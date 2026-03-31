#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch

TRAINING_DIR = Path(__file__).resolve().parent.parent / "training"
if str(TRAINING_DIR) not in sys.path:
    sys.path.insert(0, str(TRAINING_DIR))

from pi_gnn_train_v2 import SpatioTemporalGNN, build_physics_context_features, resolve_feature_indices

METHOD_LABELS = {
    "noisy_ce": "Noisy-CE",
    "posterior_ce": "Posterior-CE",
    "cdro_fixed": "CDRO-Fixed",
    "cdro_ug": "CDRO-UG (sw0)",
    "cdro_ug_priorcorr": "CDRO-UG + PriorCorr",
}
METHOD_COLORS = {
    "noisy_ce": "#7A8892",
    "posterior_ce": "#A44A3F",
    "cdro_fixed": "#D68C45",
    "cdro_ug": "#1F6E8C",
    "cdro_ug_priorcorr": "#4E937A",
}
BASELINE_METHODS = ["noisy_ce", "posterior_ce", "cdro_fixed", "cdro_ug", "cdro_ug_priorcorr"]
CORE_METHODS = ["noisy_ce", "cdro_fixed", "cdro_ug"]
METRICS = ["f1", "fpr", "ece", "brier"]
DEFAULT_RUNTIME_WARMUP = 5
DEFAULT_RUNTIME_REPEATS = 20
DEFAULT_RUNTIME_THREADS = 1


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


def safe_ratio(numer: float, denom: float) -> float:
    return float(numer / denom) if abs(float(denom)) > 1e-12 else 0.0


def graph_input_tensor(graph: Any) -> torch.Tensor:
    if hasattr(graph, "x_model"):
        return graph.x_model
    if hasattr(graph, "x_norm"):
        return graph.x_norm
    return graph.x


def holm_adjust(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    prev = 0.0
    for rank, idx in enumerate(order, start=1):
        val = max(prev, (m - rank + 1) * pvals[idx])
        prev = val
        adj[idx] = min(1.0, val)
    return adj


def bh_adjust(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    nxt = 1.0
    for i in range(m - 1, -1, -1):
        idx = order[i]
        rank = i + 1
        val = min(nxt, pvals[idx] * m / rank)
        nxt = val
        adj[idx] = min(1.0, val)
    return adj


def aggregate_pooled(summary: dict[str, Any], methods: list[str]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for method in methods:
        rows = [r["metrics"] for r in summary.get("runs", []) if r["method"] == method]
        out[method] = {}
        for metric in METRICS:
            n, mean_v, std_v = mean_std([float(row[metric]) for row in rows])
            out[method][f"{metric}_n"] = n
            out[method][f"{metric}_mean"] = mean_v
            out[method][f"{metric}_std"] = std_v
    return out


def find_comparison(sig: dict[str, Any], method_a: str, method_b: str) -> dict[str, Any]:
    for comp in sig.get("comparisons", []):
        if comp.get("method_a") == method_a and comp.get("method_b") == method_b:
            return comp
    return {}


def build_baseline_table(main_summary: dict[str, Any], batch2_summary: dict[str, Any]) -> list[list[object]]:
    rows = [[
        "setting", "method", "method_label", "n", "f1_mean", "f1_std", "fpr_mean", "fpr_std", "ece_mean", "ece_std", "brier_mean", "brier_std"
    ]]
    for setting, summary in [("main", main_summary), ("batch2", batch2_summary)]:
        pooled = aggregate_pooled(summary, BASELINE_METHODS)
        for method in BASELINE_METHODS:
            block = pooled[method]
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
    return rows


def build_baseline_md(main_summary: dict[str, Any], batch2_summary: dict[str, Any], main_sig: dict[str, Any], batch2_sig: dict[str, Any]) -> str:
    main_posterior = find_comparison(main_sig, "cdro_ug", "posterior_ce")
    batch2_posterior = find_comparison(batch2_sig, "cdro_ug", "posterior_ce")
    main_prior = find_comparison(main_sig, "cdro_ug", "cdro_ug_priorcorr")
    batch2_prior = find_comparison(batch2_sig, "cdro_ug", "cdro_ug_priorcorr")
    pooled_main = aggregate_pooled(main_summary, BASELINE_METHODS)
    pooled_batch2 = aggregate_pooled(batch2_summary, BASELINE_METHODS)
    lines = [
        "# Supplemental Baseline Family",
        "",
        "## Main (3 seeds)",
    ]
    for method in BASELINE_METHODS:
        block = pooled_main[method]
        lines.append(f"- {METHOD_LABELS[method]}: F1={block['f1_mean']:.4f}, FPR={block['fpr_mean']:.4f}, ECE={block['ece_mean']:.4f}, Brier={block['brier_mean']:.4f}")
    lines.extend([
        "",
        f"- CDRO-UG vs Posterior-CE: delta_F1={main_posterior['pooled']['f1']['delta_mean']:+.6f}, p={main_posterior['pooled']['f1']['p_value']:.6g}; delta_FPR={main_posterior['pooled']['fpr']['delta_mean']:+.6f}, p={main_posterior['pooled']['fpr']['p_value']:.6g}.",
        f"- CDRO-UG vs PriorCorr: delta_F1={main_prior['pooled']['f1']['delta_mean']:+.6f}, p={main_prior['pooled']['f1']['p_value']:.6g}; delta_FPR={main_prior['pooled']['fpr']['delta_mean']:+.6f}, p={main_prior['pooled']['fpr']['p_value']:.6g}.",
        "",
        "## Batch2 (3 seeds)",
    ])
    for method in BASELINE_METHODS:
        block = pooled_batch2[method]
        lines.append(f"- {METHOD_LABELS[method]}: F1={block['f1_mean']:.4f}, FPR={block['fpr_mean']:.4f}, ECE={block['ece_mean']:.4f}, Brier={block['brier_mean']:.4f}")
    lines.extend([
        "",
        f"- CDRO-UG vs Posterior-CE: delta_F1={batch2_posterior['pooled']['f1']['delta_mean']:+.6f}, p={batch2_posterior['pooled']['f1']['p_value']:.6g}; delta_FPR={batch2_posterior['pooled']['fpr']['delta_mean']:+.6f}, p={batch2_posterior['pooled']['fpr']['p_value']:.6g}.",
        f"- CDRO-UG vs PriorCorr: delta_F1={batch2_prior['pooled']['f1']['delta_mean']:+.6f}, p={batch2_prior['pooled']['f1']['p_value']:.6g}; delta_FPR={batch2_prior['pooled']['fpr']['delta_mean']:+.6f}, p={batch2_prior['pooled']['fpr']['p_value']:.6g}.",
        "",
        "## Reading",
        "- Posterior-CE does not overtake CDRO-UG in either setting, so the final method is not simply benefiting from replacing hard labels with posterior soft labels.",
        "- PriorCorr is unstable across datasets: it improves main pooled FPR slightly, but loses the key batch2 FPR advantage. This supports keeping raw sw0 as the locked main version.",
    ])
    return "\n".join(lines)


def collect_hypotheses(root: Path) -> list[dict[str, Any]]:
    main_sig = load_json(root / "cdro_suite/main_rewrite_sw0_s5_v1/cdro_significance.json")
    batch2_sig = load_json(root / "cdro_suite/batch2_rewrite_sw0_s3_v2/cdro_significance.json")
    mech_main = load_json(root / "cdro_suite/mechanism_main_s3_v1/mechanism_probe_summary.json")
    mech_batch2 = load_json(root / "cdro_suite/mechanism_batch2_s3_v1/mechanism_probe_summary.json")
    main_base_sig = load_json(root / "cdro_suite/main_baselineplus_s3_v1/cdro_significance.json")
    batch2_base_sig = load_json(root / "cdro_suite/batch2_baselineplus_s3_v1/cdro_significance.json")
    hyps: list[dict[str, Any]] = []
    for setting, sig in [("main", main_sig), ("batch2", batch2_sig)]:
        comp = find_comparison(sig, "cdro_ug", "noisy_ce")
        for metric in ["f1", "fpr"]:
            hyps.append({
                "family": "core_results",
                "name": f"{setting}_pooled_cdro_ug_vs_noisy_ce_{metric}",
                "delta_mean": float(comp["pooled"][metric]["delta_mean"]),
                "p_raw": float(comp["pooled"][metric]["p_value"]),
            })
    hyps.append({
        "family": "mechanism",
        "name": "main_uniform_vs_full_pooled_f1",
        "delta_mean": float(mech_main["p_values"]["sw0_uniform"]["pooled"]["f1"]["delta_mean"]),
        "p_raw": float(mech_main["p_values"]["sw0_uniform"]["pooled"]["f1"]["p_value"]),
    })
    hyps.append({
        "family": "mechanism",
        "name": "batch2_b035_vs_full_pooled_fpr",
        "delta_mean": float(mech_batch2["p_values"]["sw0_b035"]["pooled"]["fpr"]["delta_mean"]),
        "p_raw": float(mech_batch2["p_values"]["sw0_b035"]["pooled"]["fpr"]["p_value"]),
    })
    for setting, sig in [("main", main_base_sig), ("batch2", batch2_base_sig)]:
        for method in ["posterior_ce", "cdro_ug_priorcorr"]:
            comp = find_comparison(sig, "cdro_ug", method)
            for metric in ["f1", "fpr"]:
                hyps.append({
                    "family": "supplemental_baselines",
                    "name": f"{setting}_pooled_cdro_ug_vs_{method}_{metric}",
                    "delta_mean": float(comp["pooled"][metric]["delta_mean"]),
                    "p_raw": float(comp["pooled"][metric]["p_value"]),
                })
    return hyps


def write_multiple_testing(out_dir: Path, hyps: list[dict[str, Any]]) -> None:
    p_all = [h["p_raw"] for h in hyps]
    holm_all = holm_adjust(p_all)
    bh_all = bh_adjust(p_all)
    for idx, hyp in enumerate(hyps):
        hyp["p_holm_global"] = holm_all[idx]
        hyp["p_bh_global"] = bh_all[idx]
    fam_map: dict[str, list[int]] = {}
    for idx, hyp in enumerate(hyps):
        fam_map.setdefault(hyp["family"], []).append(idx)
    for fam, idxs in fam_map.items():
        fam_p = [hyps[i]["p_raw"] for i in idxs]
        fam_h = holm_adjust(fam_p)
        fam_b = bh_adjust(fam_p)
        for j, i in enumerate(idxs):
            hyps[i]["p_holm_family"] = fam_h[j]
            hyps[i]["p_bh_family"] = fam_b[j]
    write_text(out_dir / "multiple_testing_corrections.json", json.dumps({"hypotheses": hyps}, indent=2))
    csv_rows = [["family", "hypothesis", "delta_mean", "p_raw", "p_holm_family", "p_bh_family", "p_holm_global", "p_bh_global"]]
    lines = ["# Multiple Testing Corrections (Holm / BH)", "", "| family | hypothesis | delta_mean | p_raw | p_holm_family | p_bh_family | p_holm_global | p_bh_global |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for hyp in sorted(hyps, key=lambda x: (x["family"], x["p_raw"])):
        csv_rows.append([hyp[k] for k in ["family", "name", "delta_mean", "p_raw", "p_holm_family", "p_bh_family", "p_holm_global", "p_bh_global"]])
        lines.append(f"| {hyp['family']} | {hyp['name']} | {hyp['delta_mean']:+.6f} | {hyp['p_raw']:.6g} | {hyp['p_holm_family']:.6g} | {hyp['p_bh_family']:.6g} | {hyp['p_holm_global']:.6g} | {hyp['p_bh_global']:.6g} |")
    write_csv(out_dir / "multiple_testing_corrections.csv", csv_rows)
    write_text(out_dir / "multiple_testing_corrections.md", "\n".join(lines))


def summarize_preprocess_runtime(summary_path: Path) -> dict[str, float]:
    summary = load_json(summary_path)
    weak_label_sec = float(summary.get("weak_label", {}).get("duration_sec", 0.0))
    protocol_secs = [float(v.get("duration_sec", 0.0)) for v in summary.get("protocol_graphs", {}).values()]
    proto_n, proto_mean, proto_std = mean_std(protocol_secs)
    return {
        "weak_label_once_sec": weak_label_sec,
        "protocol_graph_count": proto_n,
        "protocol_graph_total_sec": float(sum(protocol_secs)),
        "protocol_graph_mean_sec": proto_mean,
        "protocol_graph_std_sec": proto_std,
        "fixed_setup_total_sec": weak_label_sec + float(sum(protocol_secs)),
    }


def summarize_train_runtime(summary_path: Path) -> list[dict[str, Any]]:
    summary = load_json(summary_path)
    grouped: dict[str, dict[str, list[float]]] = {}
    for run in summary.get("runs", []):
        method = run["method"]
        grouped.setdefault(method, {"wall": [], "train": []})
        grouped[method]["wall"].append(float(run.get("duration_sec", 0.0)))
        result = load_json(Path(run["result_file"]))
        grouped[method]["train"].append(float(result.get("runtime_sec", 0.0)))
    rows: list[dict[str, Any]] = []
    noisy_wall = mean_std(grouped.get("noisy_ce", {}).get("wall", []))[1]
    for method in BASELINE_METHODS:
        stats = grouped.get(method, {"wall": [], "train": []})
        n1, wall_mean, wall_std = mean_std(stats["wall"])
        _, train_mean, train_std = mean_std(stats["train"])
        rows.append({
            "method": method,
            "n": n1,
            "wall_mean": wall_mean,
            "wall_std": wall_std,
            "train_mean": train_mean,
            "train_std": train_std,
            "delta_vs_noisy_wall": wall_mean - noisy_wall,
            "ratio_vs_noisy_wall": (wall_mean / noisy_wall) if noisy_wall > 0 else 0.0,
        })
    return rows


def load_graph_for_runtime(graph_path: Path, physics_context: bool, capacity: float) -> Any:
    graph = torch.load(graph_path, map_location="cpu", weights_only=False)
    if physics_context and not hasattr(graph, "x_model"):
        base_x = graph.x_norm if hasattr(graph, "x_norm") else graph.x
        feat_idx = resolve_feature_indices(graph)
        ctx = build_physics_context_features(graph, capacity=capacity, feat_idx=feat_idx).cpu()
        graph.x_model = torch.cat([base_x.cpu(), ctx], dim=1)
    return graph


def benchmark_forward_runtime(
    summary_path: Path,
    warmup: int,
    repeats: int,
    threads: int,
) -> list[dict[str, Any]]:
    summary = load_json(summary_path)
    grouped: dict[str, dict[str, list[float]]] = {}
    graph_cache: dict[tuple[str, bool, float], Any] = {}
    prev_threads = torch.get_num_threads()
    torch.set_num_threads(max(int(threads), 1))
    try:
        for run in summary.get("runs", []):
            method = str(run["method"])
            grouped.setdefault(
                method,
                {
                    "forward_ms": [],
                    "nodes": [],
                    "test_nodes": [],
                    "windows": [],
                    "nodes_per_sec": [],
                    "windows_per_sec": [],
                    "ms_per_window": [],
                },
            )
            result = load_json(Path(run["result_file"]))
            cfg = result.get("config", {})
            graph_path = Path(cfg["graph_file"])
            physics_context = bool(cfg.get("physics_context", False))
            capacity = float(cfg.get("capacity", 500.0))
            cache_key = (str(graph_path), physics_context, round(capacity, 6))
            if cache_key not in graph_cache:
                graph_cache[cache_key] = load_graph_for_runtime(graph_path, physics_context=physics_context, capacity=capacity)
            graph = graph_cache[cache_key]
            x_model = graph_input_tensor(graph).cpu()
            edge_index = graph.edge_index.cpu()
            edge_type = graph.edge_type.cpu()

            model = SpatioTemporalGNN(
                in_channels=int(x_model.shape[1]),
                hidden_channels=int(cfg["hidden_dim"]),
                out_channels=2,
                num_heads=int(cfg["heads"]),
                dropout=float(cfg["dropout"]),
            ).cpu()
            model_path = Path(run["result_file"]).with_name("model.pt")
            model.load_state_dict(torch.load(model_path, map_location="cpu", weights_only=True))
            model.eval()

            with torch.inference_mode():
                for _ in range(max(int(warmup), 0)):
                    model(x_model, edge_index, edge_type)

                timings_ms: list[float] = []
                for _ in range(max(int(repeats), 1)):
                    t0 = time.perf_counter()
                    model(x_model, edge_index, edge_type)
                    timings_ms.append((time.perf_counter() - t0) * 1000.0)

            _, forward_mean_ms, forward_std_ms = mean_std(timings_ms)
            num_nodes = int(x_model.shape[0])
            if hasattr(graph, "temporal_test_mask"):
                test_nodes = int(graph.temporal_test_mask.bool().sum().item())
            elif hasattr(graph, "test_mask"):
                test_nodes = int(graph.test_mask.bool().sum().item())
            else:
                test_nodes = 0
            if hasattr(graph, "window_idx"):
                valid_windows = graph.window_idx[graph.window_idx >= 0]
                window_count = int(torch.unique(valid_windows).numel()) if int(valid_windows.numel()) > 0 else 0
            else:
                window_count = 0
            forward_sec = max(forward_mean_ms / 1000.0, 1e-9)

            grouped[method]["forward_ms"].append(forward_mean_ms)
            grouped[method]["nodes"].append(float(num_nodes))
            grouped[method]["test_nodes"].append(float(test_nodes))
            grouped[method]["windows"].append(float(window_count))
            grouped[method]["nodes_per_sec"].append(float(num_nodes) / forward_sec)
            grouped[method]["windows_per_sec"].append(float(window_count) / forward_sec if window_count > 0 else 0.0)
            grouped[method]["ms_per_window"].append(forward_mean_ms / float(window_count) if window_count > 0 else 0.0)
    finally:
        torch.set_num_threads(prev_threads)

    noisy_forward_ms = mean_std(grouped.get("noisy_ce", {}).get("forward_ms", []))[1]
    rows: list[dict[str, Any]] = []
    for method in BASELINE_METHODS:
        stats = grouped.get(
            method,
            {
                "forward_ms": [],
                "nodes": [],
                "test_nodes": [],
                "windows": [],
                "nodes_per_sec": [],
                "windows_per_sec": [],
                "ms_per_window": [],
            },
        )
        n, forward_mean_ms, forward_std_ms = mean_std(stats["forward_ms"])
        _, node_mean, _ = mean_std(stats["nodes"])
        _, test_node_mean, _ = mean_std(stats["test_nodes"])
        _, window_mean, _ = mean_std(stats["windows"])
        _, nodes_per_sec_mean, nodes_per_sec_std = mean_std(stats["nodes_per_sec"])
        _, windows_per_sec_mean, windows_per_sec_std = mean_std(stats["windows_per_sec"])
        _, ms_per_window_mean, ms_per_window_std = mean_std(stats["ms_per_window"])
        rows.append(
            {
                "method": method,
                "n": n,
                "forward_mean_ms": forward_mean_ms,
                "forward_std_ms": forward_std_ms,
                "node_count_mean": node_mean,
                "test_node_count_mean": test_node_mean,
                "window_count_mean": window_mean,
                "nodes_per_sec_mean": nodes_per_sec_mean,
                "nodes_per_sec_std": nodes_per_sec_std,
                "windows_per_sec_mean": windows_per_sec_mean,
                "windows_per_sec_std": windows_per_sec_std,
                "ms_per_window_mean": ms_per_window_mean,
                "ms_per_window_std": ms_per_window_std,
                "delta_vs_noisy_forward_ms": forward_mean_ms - noisy_forward_ms,
                "ratio_vs_noisy_forward": safe_ratio(forward_mean_ms, noisy_forward_ms),
            }
        )
    return rows


def write_runtime(out_dir: Path, root: Path, warmup: int, repeats: int, threads: int) -> None:
    suites = {
        "main": root / "cdro_suite/main_baselineplus_s3_v1/cdro_summary.json",
        "batch2": root / "cdro_suite/batch2_baselineplus_s3_v1/cdro_summary.json",
    }
    csv_rows = [[
        "setting",
        "section",
        "method",
        "method_label",
        "n",
        "weak_label_once_sec",
        "protocol_graph_total_sec",
        "protocol_graph_mean_sec",
        "protocol_graph_std_sec",
        "fixed_setup_total_sec",
        "wall_mean_sec",
        "wall_std_sec",
        "train_mean_sec",
        "train_std_sec",
        "delta_vs_noisy_wall_sec",
        "ratio_vs_noisy_wall",
        "forward_mean_ms",
        "forward_std_ms",
        "delta_vs_noisy_forward_ms",
        "ratio_vs_noisy_forward",
        "node_count_mean",
        "test_node_count_mean",
        "window_count_mean",
        "nodes_per_sec_mean",
        "windows_per_sec_mean",
        "ms_per_window_mean",
    ]]
    lines = [
        "# Runtime Cost Summary",
        "",
        "## Methodology",
        f"- CPU-only benchmark with `torch.set_num_threads({max(int(threads), 1)})`.",
        f"- Inference latency is measured as full-graph forward time over saved models, averaged over {max(int(repeats), 1)} timed repeats after {max(int(warmup), 0)} warmup passes.",
        "- `wall` is the outer process time recorded by the suite runner; `train` is the model-only runtime reported inside `results.json`.",
        "",
    ]
    for setting, path in suites.items():
        preprocess = summarize_preprocess_runtime(path)
        train_rows = summarize_train_runtime(path)
        inference_rows = benchmark_forward_runtime(path, warmup=warmup, repeats=repeats, threads=threads)
        inference_map = {row["method"]: row for row in inference_rows}
        lines.append(f"## {setting}")
        lines.append("")
        lines.append("### One-time preprocessing")
        lines.append(
            f"- Weak-label generation: {preprocess['weak_label_once_sec']:.2f}s."
        )
        lines.append(
            f"- Protocol graph preparation: {preprocess['protocol_graph_mean_sec']:.2f} +/- {preprocess['protocol_graph_std_sec']:.2f}s per protocol "
            f"({int(preprocess['protocol_graph_count'])} protocols, {preprocess['protocol_graph_total_sec']:.2f}s total)."
        )
        lines.append(
            f"- Fixed suite setup total: {preprocess['fixed_setup_total_sec']:.2f}s."
        )
        csv_rows.append([
            setting,
            "preprocess",
            "suite_setup",
            "Suite setup",
            int(preprocess["protocol_graph_count"]),
            preprocess["weak_label_once_sec"],
            preprocess["protocol_graph_total_sec"],
            preprocess["protocol_graph_mean_sec"],
            preprocess["protocol_graph_std_sec"],
            preprocess["fixed_setup_total_sec"],
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ])
        lines.append("")
        lines.append("### Per-run training")
        for row in train_rows:
            csv_rows.append([
                setting,
                "training",
                row["method"],
                METHOD_LABELS[row["method"]],
                row["n"],
                "",
                "",
                "",
                "",
                "",
                row["wall_mean"],
                row["wall_std"],
                row["train_mean"],
                row["train_std"],
                row["delta_vs_noisy_wall"],
                row["ratio_vs_noisy_wall"],
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ])
            lines.append(
                f"- {METHOD_LABELS[row['method']]}: wall={row['wall_mean']:.2f} +/- {row['wall_std']:.2f}s, "
                f"train={row['train_mean']:.2f} +/- {row['train_std']:.2f}s, "
                f"delta vs Noisy-CE wall={row['delta_vs_noisy_wall']:+.2f}s."
            )
        lines.append("")
        lines.append("### Per-run inference")
        for row in inference_rows:
            csv_rows.append([
                setting,
                "inference",
                row["method"],
                METHOD_LABELS[row["method"]],
                row["n"],
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                row["forward_mean_ms"],
                row["forward_std_ms"],
                row["delta_vs_noisy_forward_ms"],
                row["ratio_vs_noisy_forward"],
                row["node_count_mean"],
                row["test_node_count_mean"],
                row["window_count_mean"],
                row["nodes_per_sec_mean"],
                row["windows_per_sec_mean"],
                row["ms_per_window_mean"],
            ])
            lines.append(
                f"- {METHOD_LABELS[row['method']]}: forward={row['forward_mean_ms']:.2f} +/- {row['forward_std_ms']:.2f}ms, "
                f"{row['nodes_per_sec_mean']:.1f} nodes/s, {row['windows_per_sec_mean']:.1f} windows/s, "
                f"~{row['ms_per_window_mean']:.2f}ms per temporal window, "
                f"delta vs Noisy-CE forward={row['delta_vs_noisy_forward_ms']:+.2f}ms."
            )
        ug_train = next((row for row in train_rows if row["method"] == "cdro_ug"), None)
        ug_infer = inference_map.get("cdro_ug")
        if ug_train is not None and ug_infer is not None:
            lines.extend([
                "",
                "### Reading",
                f"- CDRO-UG changes wall time by {ug_train['delta_vs_noisy_wall']:+.2f}s relative to Noisy-CE and changes full-graph forward latency by {ug_infer['delta_vs_noisy_forward_ms']:+.2f}ms.",
                "- Under the current CPU-only setting, the rewritten UG does not introduce a meaningful deployment-time penalty; the extra method complexity mainly remains within the same runtime scale as the baseline family.",
            ])
        lines.append("")
    write_csv(out_dir / "table8_runtime_costs.csv", csv_rows)
    write_text(out_dir / "runtime_costs.md", "\n".join(lines))


def pooled_probs(suite_dir: Path, methods: list[str]) -> dict[str, tuple[torch.Tensor, torch.Tensor]]:
    out: dict[str, tuple[list[torch.Tensor], list[torch.Tensor]]] = {m: ([], []) for m in methods}
    for run_dir in (suite_dir / "runs").iterdir():
        method = run_dir.name.split("__")[1]
        if method not in methods:
            continue
        bundle = torch.load(run_dir / "results_logits.pt", map_location="cpu")
        probs = bundle["probs"][:, 1].float()
        y_true = bundle["y_true"].long()
        mask = bundle["temporal_test_mask"].bool() if "temporal_test_mask" in bundle else bundle["test_mask"].bool()
        out[method][0].append(probs[mask])
        out[method][1].append(y_true[mask])
    return {m: (torch.cat(xs, dim=0), torch.cat(ys, dim=0)) for m, (xs, ys) in out.items() if xs}


def ece(prob: torch.Tensor, y_true: torch.Tensor, n_bins: int = 10) -> float:
    bins = torch.linspace(0.0, 1.0, n_bins + 1)
    total = float(prob.numel())
    acc = 0.0
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (prob >= lo) & (prob <= hi) if i == n_bins - 1 else (prob >= lo) & (prob < hi)
        if int(mask.sum().item()) == 0:
            continue
        conf = float(prob[mask].mean().item())
        truth = float(y_true[mask].float().mean().item())
        acc += float(mask.sum().item()) / total * abs(truth - conf)
    return acc


def reliability_points(prob: torch.Tensor, y_true: torch.Tensor, n_bins: int = 10) -> tuple[list[float], list[float]]:
    bins = torch.linspace(0.0, 1.0, n_bins + 1)
    xs, ys = [], []
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (prob >= lo) & (prob <= hi) if i == n_bins - 1 else (prob >= lo) & (prob < hi)
        if int(mask.sum().item()) == 0:
            continue
        xs.append(float(prob[mask].mean().item()))
        ys.append(float(y_true[mask].float().mean().item()))
    return xs, ys


def risk_coverage(prob: torch.Tensor, y_true: torch.Tensor, points: int = 50) -> tuple[list[float], list[float], float]:
    pred = (prob >= 0.5).long()
    conf = torch.where(pred == 1, prob, 1.0 - prob)
    correct = (pred == y_true).float()
    order = torch.argsort(conf, descending=True)
    errors = 1.0 - correct[order]
    cum_risk = errors.cumsum(0) / torch.arange(1, errors.numel() + 1)
    aurc = float(cum_risk.mean().item())
    covs, risks = [], []
    for frac in torch.linspace(0.1, 1.0, points):
        k = max(1, int(round(float(frac.item()) * errors.numel())))
        covs.append(k / errors.numel())
        risks.append(float(cum_risk[k - 1].item()))
    return covs, risks, aurc


def write_calibration_risk(out_dir: Path, root: Path) -> None:
    suites = {
        "main": root / "cdro_suite/main_rewrite_sw0_s5_v1",
        "batch2": root / "cdro_suite/batch2_rewrite_sw0_s3_v2",
    }
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    summary_rows = [["setting", "method", "method_label", "n", "ece", "brier", "aurc"]]
    for col, (setting, suite_dir) in enumerate(suites.items()):
        pooled = pooled_probs(suite_dir, CORE_METHODS)
        ax_rel = axes[0, col]
        ax_risk = axes[1, col]
        ax_rel.plot([0, 1], [0, 1], linestyle="--", color="#444444", linewidth=1.0)
        for method in CORE_METHODS:
            prob, y_true = pooled[method]
            xs, ys = reliability_points(prob, y_true)
            covs, risks, aurc = risk_coverage(prob, y_true)
            brier = float(torch.mean((prob - y_true.float()) ** 2).item())
            summary_rows.append([setting, method, METHOD_LABELS[method], int(prob.numel()), ece(prob, y_true), brier, aurc])
            ax_rel.plot(xs, ys, marker="o", linewidth=1.8, markersize=4, color=METHOD_COLORS[method], label=METHOD_LABELS[method])
            ax_risk.plot(covs, risks, linewidth=2.0, color=METHOD_COLORS[method], label=f"{METHOD_LABELS[method]} (AURC={aurc:.3f})")
        ax_rel.set_title(f"{setting}: reliability")
        ax_rel.set_xlabel("Predicted attack probability")
        ax_rel.set_ylabel("Empirical attack rate")
        ax_rel.grid(alpha=0.25, linestyle="--")
        ax_risk.set_title(f"{setting}: risk-coverage")
        ax_risk.set_xlabel("Coverage")
        ax_risk.set_ylabel("Selective risk")
        ax_risk.grid(alpha=0.25, linestyle="--")
    axes[0, 1].legend(loc="lower right", fontsize=8)
    axes[1, 1].legend(loc="upper left", fontsize=8)
    fig.suptitle("Calibration and risk-coverage (locked main methods)", fontsize=14)
    fig.savefig(out_dir / "fig5_calibration_risk.png", dpi=240)
    plt.close(fig)
    write_csv(out_dir / "table9_calibration_risk.csv", summary_rows)
    lines = [
        "# Calibration and Risk-Coverage",
        "",
        "- This figure is intended as a completeness / reviewer-facing calibration appendix, not as the main positive claim.",
        "- In the locked raw-sw0 setting, the strongest stable benefit remains batch2 false-positive suppression, not a universal calibration improvement.",
    ]
    write_text(out_dir / "calibration_risk_notes.md", "\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--runtime-warmup", type=int, default=DEFAULT_RUNTIME_WARMUP)
    ap.add_argument("--runtime-repeats", type=int, default=DEFAULT_RUNTIME_REPEATS)
    ap.add_argument("--runtime-threads", type=int, default=DEFAULT_RUNTIME_THREADS)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    out_dir = root / "cdro_suite" / "paper_ready_plus"
    out_dir.mkdir(parents=True, exist_ok=True)

    main_summary = load_json(root / "cdro_suite/main_baselineplus_s3_v1/cdro_summary.json")
    batch2_summary = load_json(root / "cdro_suite/batch2_baselineplus_s3_v1/cdro_summary.json")
    main_sig = load_json(root / "cdro_suite/main_baselineplus_s3_v1/cdro_significance.json")
    batch2_sig = load_json(root / "cdro_suite/batch2_baselineplus_s3_v1/cdro_significance.json")

    write_csv(out_dir / "table7_supplemental_baselines.csv", build_baseline_table(main_summary, batch2_summary))
    write_text(out_dir / "supplemental_baselines.md", build_baseline_md(main_summary, batch2_summary, main_sig, batch2_sig))
    write_multiple_testing(out_dir, collect_hypotheses(root))
    write_runtime(
        out_dir,
        root,
        warmup=int(args.runtime_warmup),
        repeats=int(args.runtime_repeats),
        threads=int(args.runtime_threads),
    )
    write_calibration_risk(out_dir, root)
    print(out_dir)


if __name__ == "__main__":
    main()
