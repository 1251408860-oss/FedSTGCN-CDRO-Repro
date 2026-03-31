#!/usr/bin/env python3
"""
Generate multi-view weak supervision metadata from a spatiotemporal graph.

Outputs:
  - weak_labels.pt: tensor sidecar for training/evaluation
  - weak_summary.json: aggregate statistics and audits
  - weak_view_stats.csv: per-view coverage/audit table
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from typing import Any

import torch


VIEW_NAMES = ["rate_view", "entropy_view", "port_view", "latency_view", "physics_view"]


def load_manifest(path: str) -> dict[str, Any]:
    if not path or not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def resolve_feature_indices(graph: Any) -> dict[str, int]:
    if hasattr(graph, "feature_index") and isinstance(graph.feature_index, dict):
        idx = {str(k): int(v) for k, v in graph.feature_index.items()}
        if "ln(N+1)" in idx and "lnN" not in idx:
            idx["lnN"] = idx["ln(N+1)"]
        if "ln(T+1)" in idx and "lnT" not in idx:
            idx["lnT"] = idx["ln(T+1)"]
        return idx
    return {
        "ln(N+1)": 0,
        "lnN": 0,
        "ln(T+1)": 1,
        "lnT": 1,
        "entropy": 2,
        "D_observed": 3,
        "pkt_rate": 4,
        "avg_pkt_size": 5,
        "port_diversity": 6,
    }


def robust_z(values: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    valid = values[mask]
    if int(valid.numel()) == 0:
        return torch.zeros_like(values)
    q1 = torch.quantile(valid, 0.25)
    q2 = torch.quantile(valid, 0.50)
    q3 = torch.quantile(valid, 0.75)
    iqr = (q3 - q1).clamp(min=1e-6)
    return (values - q2) / iqr


def sigmoid_prob(score: torch.Tensor, temperature: float = 1.0) -> torch.Tensor:
    t = max(float(temperature), 1e-6)
    return torch.sigmoid(score / t)


def hard_vote_from_prob(prob_attack: torch.Tensor, attack_thr: float, benign_thr: float) -> torch.Tensor:
    vote = torch.full_like(prob_attack, fill_value=-1, dtype=torch.long)
    vote[prob_attack >= float(attack_thr)] = 1
    vote[prob_attack <= float(benign_thr)] = 0
    return vote


def safe_mean(values: torch.Tensor, mask: torch.Tensor) -> float:
    if int(mask.sum().item()) == 0:
        return 0.0
    return float(values[mask].float().mean().item())


def parse_capacity_proxy(manifest: dict[str, Any], window_rate: torch.Tensor) -> float:
    topo = manifest.get("topology", {}) if isinstance(manifest, dict) else {}
    bottleneck = topo.get("core_bottleneck", {}) if isinstance(topo, dict) else {}
    bw_mbps = float(bottleneck.get("bw_mbps", 0.0) or 0.0)
    if bw_mbps > 0.0:
        # The graph feature stores packet rate rather than byte bandwidth.
        # Use a monotone proxy so the resulting congestion score preserves ranking.
        return max(bw_mbps * 400.0, 1.0)

    valid = window_rate[window_rate > 0]
    if int(valid.numel()) == 0:
        return 1.0
    return float(torch.quantile(valid, 0.90).item())


def build_window_context(graph: Any, feat_idx: dict[str, int], manifest: dict[str, Any]) -> dict[str, torch.Tensor]:
    n = int(graph.num_nodes)
    flow_mask = graph.window_idx >= 0

    pkt_rate = graph.x[:, feat_idx["pkt_rate"]].clamp(min=0.0)
    d_obs = graph.x[:, feat_idx["D_observed"]].clamp(min=0.0)
    entropy = graph.x[:, feat_idx["entropy"]].clamp(min=0.0)

    window_rate = torch.zeros(n, dtype=torch.float)
    window_rate_share = torch.zeros(n, dtype=torch.float)
    window_delay = torch.zeros(n, dtype=torch.float)
    window_entropy = torch.zeros(n, dtype=torch.float)

    valid_windows = graph.window_idx[flow_mask]
    if int(valid_windows.numel()) == 0:
        zero = torch.zeros(n, dtype=torch.float)
        return {
            "window_rate": zero,
            "window_rate_share": zero,
            "window_delay": zero,
            "window_entropy": zero,
            "rho_proxy": zero,
            "queue_gap": zero,
            "delay_gap": zero,
        }

    uniq_windows = torch.unique(valid_windows)
    totals = []
    for w in uniq_windows:
        w_mask = graph.window_idx == w
        total_rate = pkt_rate[w_mask].sum()
        totals.append(total_rate)
        mean_delay = d_obs[w_mask].mean()
        mean_entropy = entropy[w_mask].mean()
        window_rate[w_mask] = total_rate
        window_delay[w_mask] = mean_delay
        window_entropy[w_mask] = mean_entropy
        window_rate_share[w_mask] = pkt_rate[w_mask] / (total_rate + 1e-6)

    total_tensor = torch.stack(totals) if totals else torch.zeros(1, dtype=torch.float)
    capacity_proxy = parse_capacity_proxy(manifest, total_tensor)
    rho_proxy = window_rate / (capacity_proxy + 1e-6)
    queue_gap = torch.relu(rho_proxy - 1.0)

    valid_delay = d_obs[flow_mask]
    ref_delay = torch.quantile(valid_delay, 0.75).clamp(min=1e-6)
    d_theory = 1.0 / (1.0 - torch.clamp(rho_proxy, min=0.0, max=0.99) + 1e-6)
    delay_gap = torch.relu(d_theory - window_delay / ref_delay)

    return {
        "window_rate": window_rate,
        "window_rate_share": window_rate_share,
        "window_delay": window_delay,
        "window_entropy": window_entropy,
        "rho_proxy": rho_proxy,
        "queue_gap": queue_gap,
        "delay_gap": delay_gap,
    }


def build_scenario_tags(manifest: dict[str, Any]) -> dict[str, str]:
    topo = manifest.get("topology", {}) if isinstance(manifest, dict) else {}
    run_cfg = manifest.get("run_config", {}) if isinstance(manifest, dict) else {}
    roles = manifest.get("roles", {}) if isinstance(manifest.get("roles"), dict) else {}
    bot_roles = sorted({str(v).split(":", 1)[1] for v in roles.values() if str(v).startswith("bot:")})
    return {
        "topology_type": str(topo.get("type", "unknown")),
        "load_profile": str(run_cfg.get("load_profile", "unknown")),
        "bot_type_mode": str(run_cfg.get("bot_type_mode", "unknown")),
        "bot_role_types": ",".join(bot_roles) if bot_roles else "unknown",
    }


def build_view_probabilities(graph: Any, feat_idx: dict[str, int], context: dict[str, torch.Tensor]) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    flow_mask = graph.window_idx >= 0
    x = graph.x

    z_ln_n = robust_z(x[:, feat_idx["lnN"]], flow_mask)
    z_ln_t = robust_z(x[:, feat_idx["lnT"]], flow_mask)
    z_entropy = robust_z(x[:, feat_idx["entropy"]], flow_mask)
    z_d_obs = robust_z(x[:, feat_idx["D_observed"]], flow_mask)
    z_pkt_rate = robust_z(x[:, feat_idx["pkt_rate"]], flow_mask)
    z_pkt_size = robust_z(x[:, feat_idx["avg_pkt_size"]], flow_mask)
    z_port = robust_z(x[:, feat_idx["port_diversity"]], flow_mask)
    z_rho = robust_z(context["rho_proxy"], flow_mask)
    z_share = robust_z(context["window_rate_share"], flow_mask)
    z_delay_gap = robust_z(context["delay_gap"], flow_mask)

    rate_score = 1.10 * z_pkt_rate + 0.55 * z_ln_n - 0.35 * z_ln_t
    entropy_score = 1.25 * z_entropy + 0.35 * z_pkt_size
    port_score = 1.10 * z_port + 0.30 * z_pkt_size + 0.15 * z_pkt_rate
    latency_score = 0.80 * (-z_d_obs) + 0.45 * z_pkt_rate + 0.20 * z_ln_n
    physics_score = 0.95 * z_rho + 0.55 * z_share + 0.35 * z_delay_gap + 0.20 * z_entropy

    score_map = {
        "rate_view": rate_score,
        "entropy_view": entropy_score,
        "port_view": port_score,
        "latency_view": latency_score,
        "physics_view": physics_score,
    }

    probs = []
    for name in VIEW_NAMES:
        temp = 1.15 if name != "physics_view" else 1.30
        probs.append(sigmoid_prob(score_map[name], temperature=temp))
    return torch.stack(probs, dim=1), score_map


def apply_context_biases(
    prob_matrix: torch.Tensor,
    graph: Any,
    feat_idx: dict[str, int],
    context: dict[str, torch.Tensor],
    camouflage_bias: float,
    congestion_bias: float,
    strategy_bias: float,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    flow_mask = graph.window_idx >= 0

    z_entropy = robust_z(graph.x[:, feat_idx["entropy"]], flow_mask)
    z_port = robust_z(graph.x[:, feat_idx["port_diversity"]], flow_mask)
    z_pkt_rate = robust_z(graph.x[:, feat_idx["pkt_rate"]], flow_mask)
    z_d_obs = robust_z(graph.x[:, feat_idx["D_observed"]], flow_mask)
    z_share = robust_z(context["window_rate_share"], flow_mask)
    z_rho = robust_z(context["rho_proxy"], flow_mask)

    camouflage_proxy = sigmoid_prob(0.90 * z_pkt_rate + 0.60 * (-z_port.abs()) + 0.35 * (-z_entropy.abs()), 1.1)
    congestion_proxy = sigmoid_prob(0.95 * z_rho + 0.60 * z_d_obs, 1.1)
    strategy_proxy = sigmoid_prob(0.70 * z_share + 0.55 * z_port.abs() + 0.35 * z_entropy.abs(), 1.1)

    mean_prob = prob_matrix.mean(dim=1)
    logit = torch.logit(mean_prob.clamp(1e-4, 1.0 - 1e-4))
    logit = logit - float(camouflage_bias) * camouflage_proxy
    logit = logit + float(congestion_bias) * congestion_proxy
    logit = logit * (1.0 - float(strategy_bias) * strategy_proxy.clamp(0.0, 0.95))
    adjusted_mean = torch.sigmoid(logit)

    adjust_delta = (adjusted_mean - mean_prob).unsqueeze(1)
    adjusted = (prob_matrix + adjust_delta).clamp(1e-4, 1.0 - 1e-4)

    proxies = {
        "camouflage_proxy": camouflage_proxy,
        "congestion_proxy": congestion_proxy,
        "strategy_proxy": strategy_proxy,
    }
    return adjusted, proxies


def aggregate_views(
    prob_matrix: torch.Tensor,
    attack_thr: float,
    benign_thr: float,
    min_votes: int,
) -> dict[str, torch.Tensor]:
    view_votes = hard_vote_from_prob(prob_matrix, attack_thr=attack_thr, benign_thr=benign_thr)

    is_attack = (view_votes == 1).float()
    is_benign = (view_votes == 0).float()
    valid_votes = (view_votes >= 0).float()
    num_votes = valid_votes.sum(dim=1)
    attack_votes = is_attack.sum(dim=1)
    benign_votes = is_benign.sum(dim=1)

    mean_prob = prob_matrix.mean(dim=1)
    weighted_prob = torch.where(
        num_votes > 0,
        (prob_matrix * valid_votes).sum(dim=1) / num_votes.clamp(min=1.0),
        mean_prob,
    )

    agreement = torch.where(num_votes > 0, torch.maximum(attack_votes, benign_votes) / num_votes.clamp(min=1.0), torch.zeros_like(num_votes))
    entropy = -(weighted_prob * torch.log(weighted_prob.clamp(min=1e-6)) + (1.0 - weighted_prob) * torch.log((1.0 - weighted_prob).clamp(min=1e-6)))
    uncertainty = entropy / math.log(2.0)

    weak_label = torch.full_like(attack_votes, fill_value=-1, dtype=torch.long)
    attack_mask = (weighted_prob >= attack_thr) & (num_votes >= float(min_votes)) & (agreement >= 0.50)
    benign_mask = (weighted_prob <= benign_thr) & (num_votes >= float(min_votes)) & (agreement >= 0.50)
    weak_label[attack_mask] = 1
    weak_label[benign_mask] = 0

    return {
        "view_votes": view_votes,
        "num_votes": num_votes.to(torch.long),
        "attack_votes": attack_votes.to(torch.long),
        "benign_votes": benign_votes.to(torch.long),
        "agreement": agreement,
        "uncertainty": uncertainty,
        "posterior_attack": weighted_prob,
        "weak_label": weak_label,
    }


def collect_audit_stats(
    hard_label: torch.Tensor,
    prob_attack: torch.Tensor,
    y_true: torch.Tensor,
    flow_mask: torch.Tensor,
) -> dict[str, float]:
    covered = flow_mask & (hard_label >= 0)
    attack_pred = covered & (hard_label == 1)
    benign_pred = covered & (hard_label == 0)

    correct = covered & (hard_label == y_true)
    stats = {
        "coverage": float(covered.float().mean().item()),
        "abstain_rate": float(((flow_mask) & (hard_label < 0)).float().mean().item()),
        "attack_rate": safe_mean((hard_label == 1).float(), flow_mask),
        "mean_prob_attack": safe_mean(prob_attack, flow_mask),
        "accuracy_on_covered": float(correct[covered].float().mean().item()) if int(covered.sum().item()) > 0 else 0.0,
        "attack_precision": float((y_true[attack_pred] == 1).float().mean().item()) if int(attack_pred.sum().item()) > 0 else 0.0,
        "benign_precision": float((y_true[benign_pred] == 0).float().mean().item()) if int(benign_pred.sum().item()) > 0 else 0.0,
    }
    return stats


def write_csv(path: str, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "view",
        "coverage",
        "abstain_rate",
        "attack_rate",
        "mean_prob_attack",
        "accuracy_on_covered",
        "attack_precision",
        "benign_precision",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def main() -> None:
    p = argparse.ArgumentParser(description="Generate weak-supervision views from a graph")
    p.add_argument("--input-graph", required=True)
    p.add_argument("--manifest-file", default="")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--output-prefix", default="")
    p.add_argument("--attack-threshold", type=float, default=0.67)
    p.add_argument("--benign-threshold", type=float, default=0.33)
    p.add_argument("--min-votes", type=int, default=2)
    p.add_argument("--camouflage-bias", type=float, default=0.20)
    p.add_argument("--congestion-bias", type=float, default=0.15)
    p.add_argument("--strategy-bias", type=float, default=0.10)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    torch.manual_seed(int(args.seed))
    graph = torch.load(args.input_graph, weights_only=False, map_location="cpu")
    manifest = load_manifest(args.manifest_file)
    feat_idx = resolve_feature_indices(graph)
    flow_mask = graph.window_idx >= 0

    context = build_window_context(graph, feat_idx, manifest)
    base_probs, _ = build_view_probabilities(graph, feat_idx, context)
    adj_probs, proxies = apply_context_biases(
        base_probs,
        graph,
        feat_idx,
        context,
        camouflage_bias=args.camouflage_bias,
        congestion_bias=args.congestion_bias,
        strategy_bias=args.strategy_bias,
    )
    agg = aggregate_views(
        adj_probs,
        attack_thr=float(args.attack_threshold),
        benign_thr=float(args.benign_threshold),
        min_votes=int(args.min_votes),
    )

    n = int(graph.num_nodes)
    weak_label_full = torch.full((n,), fill_value=-1, dtype=torch.long)
    posterior_full = torch.full((n, 2), fill_value=0.5, dtype=torch.float)
    uncertainty_full = torch.ones((n,), dtype=torch.float)
    agreement_full = torch.zeros((n,), dtype=torch.float)
    num_votes_full = torch.zeros((n,), dtype=torch.long)
    view_votes_full = torch.full((n, len(VIEW_NAMES)), fill_value=-1, dtype=torch.long)
    view_probs_full = torch.full((n, len(VIEW_NAMES)), fill_value=0.5, dtype=torch.float)

    weak_label_full[flow_mask] = agg["weak_label"][flow_mask]
    posterior_full[:, 1] = agg["posterior_attack"]
    posterior_full[:, 0] = 1.0 - agg["posterior_attack"]
    uncertainty_full = agg["uncertainty"]
    agreement_full = agg["agreement"]
    num_votes_full = agg["num_votes"]
    view_votes_full = agg["view_votes"]
    view_probs_full = adj_probs

    scenario_tags = build_scenario_tags(manifest)
    weak_bundle = {
        "weak_label": weak_label_full,
        "posterior": posterior_full,
        "uncertainty": uncertainty_full,
        "agreement": agreement_full,
        "num_votes": num_votes_full,
        "view_votes": view_votes_full,
        "view_probs": view_probs_full,
        "flow_mask": flow_mask,
        "window_idx": graph.window_idx.clone(),
        "ip_idx": graph.ip_idx.clone(),
        "rho_proxy": context["rho_proxy"],
        "window_rate_share": context["window_rate_share"],
        "camouflage_proxy": proxies["camouflage_proxy"],
        "congestion_proxy": proxies["congestion_proxy"],
        "strategy_proxy": proxies["strategy_proxy"],
        "feature_index": feat_idx,
        "view_names": VIEW_NAMES,
        "scenario_tags": scenario_tags,
        "config": vars(args),
    }

    prefix = args.output_prefix.strip() or os.path.splitext(os.path.basename(args.input_graph))[0]
    os.makedirs(args.output_dir, exist_ok=True)
    pt_path = os.path.join(args.output_dir, f"{prefix}_weak_labels.pt")
    json_path = os.path.join(args.output_dir, f"{prefix}_weak_summary.json")
    csv_path = os.path.join(args.output_dir, f"{prefix}_weak_view_stats.csv")

    rows: list[dict[str, Any]] = []
    for view_i, name in enumerate(VIEW_NAMES):
        stats = collect_audit_stats(
            hard_label=view_votes_full[:, view_i],
            prob_attack=view_probs_full[:, view_i],
            y_true=graph.y,
            flow_mask=flow_mask,
        )
        row = {"view": name, **stats}
        rows.append(row)

    final_stats = collect_audit_stats(
        hard_label=weak_label_full,
        prob_attack=posterior_full[:, 1],
        y_true=graph.y,
        flow_mask=flow_mask,
    )
    rows.append({"view": "aggregate", **final_stats})
    write_csv(csv_path, rows)

    summary = {
        "input_graph": os.path.abspath(args.input_graph),
        "manifest_file": os.path.abspath(args.manifest_file) if args.manifest_file else "",
        "output_files": {
            "weak_labels_pt": os.path.abspath(pt_path),
            "weak_summary_json": os.path.abspath(json_path),
            "weak_view_stats_csv": os.path.abspath(csv_path),
        },
        "graph_stats": {
            "num_nodes": int(graph.num_nodes),
            "flow_nodes": int(flow_mask.sum().item()),
            "attack_nodes_true": int(((graph.y == 1) & flow_mask).sum().item()),
            "benign_nodes_true": int(((graph.y == 0) & flow_mask).sum().item()),
        },
        "scenario_tags": scenario_tags,
        "aggregate": final_stats,
        "view_rows": rows,
        "proxy_means": {
            "rho_proxy": safe_mean(context["rho_proxy"], flow_mask),
            "camouflage_proxy": safe_mean(proxies["camouflage_proxy"], flow_mask),
            "congestion_proxy": safe_mean(proxies["congestion_proxy"], flow_mask),
            "strategy_proxy": safe_mean(proxies["strategy_proxy"], flow_mask),
        },
        "config": vars(args),
    }

    torch.save(weak_bundle, pt_path)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("=" * 72)
    print("Weak Supervision Summary")
    print("=" * 72)
    print(f"Input graph      : {args.input_graph}")
    print(f"Output prefix    : {prefix}")
    print(f"Flow nodes       : {summary['graph_stats']['flow_nodes']}")
    print(f"Aggregate cover  : {final_stats['coverage']:.4f}")
    print(f"Aggregate abstain: {final_stats['abstain_rate']:.4f}")
    print(f"Aggregate acc    : {final_stats['accuracy_on_covered']:.4f}")
    print(f"Attack precision : {final_stats['attack_precision']:.4f}")
    print(f"Benign precision : {final_stats['benign_precision']:.4f}")
    print(f"Saved pt         : {pt_path}")
    print(f"Saved json       : {json_path}")
    print(f"Saved csv        : {csv_path}")
    print("=" * 72)


if __name__ == "__main__":
    main()
