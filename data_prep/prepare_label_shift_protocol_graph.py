#!/usr/bin/env python3
"""
Prepare weak-supervision protocol graphs with attached weak labels.

Protocols:
  - weak_temporal_ood
  - weak_topology_ood
  - weak_attack_strategy_ood
  - label_prior_shift_ood
  - camouflage_biased_noise_ood
  - congestion_ood
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

import torch


def load_manifest(path: str) -> dict[str, Any]:
    if not path or not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def role_for_ip(manifest: dict[str, Any], ip: str) -> str:
    roles = manifest.get("roles", {})
    if isinstance(roles, dict):
        return str(roles.get(ip, ""))
    return ""


def attach_weak_bundle(graph: Any, weak_bundle: dict[str, Any]) -> Any:
    graph.weak_label = weak_bundle["weak_label"].clone()
    graph.weak_posterior = weak_bundle["posterior"].clone()
    graph.weak_uncertainty = weak_bundle["uncertainty"].clone()
    graph.weak_agreement = weak_bundle["agreement"].clone()
    graph.weak_num_votes = weak_bundle["num_votes"].clone()
    graph.weak_view_votes = weak_bundle["view_votes"].clone()
    graph.weak_view_probs = weak_bundle["view_probs"].clone()
    graph.weak_flow_mask = weak_bundle["flow_mask"].clone()
    graph.rho_proxy = weak_bundle.get("rho_proxy", torch.zeros_like(graph.y, dtype=torch.float)).clone()
    graph.window_rate_share = weak_bundle.get("window_rate_share", torch.zeros_like(graph.y, dtype=torch.float)).clone()
    graph.camouflage_proxy = weak_bundle.get("camouflage_proxy", torch.zeros_like(graph.y, dtype=torch.float)).clone()
    graph.congestion_proxy = weak_bundle.get("congestion_proxy", torch.zeros_like(graph.y, dtype=torch.float)).clone()
    graph.strategy_proxy = weak_bundle.get("strategy_proxy", torch.zeros_like(graph.y, dtype=torch.float)).clone()
    graph.weak_view_names = list(weak_bundle.get("view_names", []))
    graph.scenario_tags = dict(weak_bundle.get("scenario_tags", {}))
    return graph


def classwise_ordered_indices(mask: torch.Tensor, y: torch.Tensor, score: torch.Tensor, descending: bool = False) -> dict[int, torch.Tensor]:
    out: dict[int, torch.Tensor] = {}
    for cls in [0, 1]:
        idx = ((mask) & (y == cls)).nonzero(as_tuple=False).view(-1)
        if int(idx.numel()) == 0:
            out[cls] = idx
            continue
        vals = score[idx]
        order = torch.argsort(vals, descending=descending)
        out[cls] = idx[order]
    return out


def split_quantile_per_class(mask: torch.Tensor, y: torch.Tensor, score: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    train = torch.zeros_like(mask)
    val = torch.zeros_like(mask)
    test = torch.zeros_like(mask)
    ordered = classwise_ordered_indices(mask, y, score, descending=False)

    for cls, idx in ordered.items():
        n = int(idx.numel())
        if n == 0:
            continue
        a = max(1, int(round(0.60 * n)))
        b = max(a + 1, int(round(0.80 * n))) if n >= 3 else n
        b = min(b, n)
        train[idx[:a]] = True
        val[idx[a:b]] = True
        test[idx[b:]] = True
        if int(test[idx].sum().item()) == 0:
            test[idx[-1:]] = True
            if int(train[idx].sum().item()) > 1:
                train[idx[-1:]] = False
    return train, val, test


def protocol_temporal_ood(graph: Any, flow_mask: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    w = graph.window_idx[flow_mask]
    w_valid = w[w >= 0]
    if int(w_valid.numel()) == 0:
        zero = torch.zeros_like(flow_mask)
        return zero, zero, zero
    w_min = int(torch.min(w_valid).item())
    w_max = int(torch.max(w_valid).item())
    span = max(w_max - w_min + 1, 1)
    tr_end = w_min + int(0.60 * span)
    va_end = w_min + int(0.80 * span)
    train = flow_mask & (graph.window_idx >= w_min) & (graph.window_idx < tr_end)
    val = flow_mask & (graph.window_idx >= tr_end) & (graph.window_idx < va_end)
    test = flow_mask & (graph.window_idx >= va_end)
    return train, val, test


def protocol_topology_ood(graph: Any, flow_mask: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    gid = graph.ip_idx.remainder(5)
    train = flow_mask & (gid <= 2)
    val = flow_mask & (gid == 3)
    test = flow_mask & (gid == 4)
    return train, val, test


def protocol_attack_strategy_ood(
    graph: Any,
    manifest: dict[str, Any],
    flow_mask: torch.Tensor,
    holdout_attack_type: str,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    source_ips = list(getattr(graph, "source_ips", []))
    if not source_ips:
        raise RuntimeError("graph.source_ips missing, cannot build weak_attack_strategy_ood split")

    val_attack_type = "burst" if holdout_attack_type != "burst" else "slowburn"
    gid = graph.ip_idx.remainder(5)
    benign_train = (graph.y == 0) & flow_mask & (gid <= 2)
    benign_val = (graph.y == 0) & flow_mask & (gid == 3)
    benign_test = (graph.y == 0) & flow_mask & (gid == 4)

    attack_train = torch.zeros_like(flow_mask)
    attack_val = torch.zeros_like(flow_mask)
    attack_test = torch.zeros_like(flow_mask)

    for ip_i, ip in enumerate(source_ips):
        ip_mask = flow_mask & (graph.ip_idx == ip_i) & (graph.y == 1)
        if int(ip_mask.sum().item()) == 0:
            continue
        role = role_for_ip(manifest, ip)
        atype = role.split(":", 1)[1].strip().lower() if role.startswith("bot:") else ""
        if atype == holdout_attack_type:
            attack_test |= ip_mask
        elif atype == val_attack_type:
            attack_val |= ip_mask
        else:
            attack_train |= ip_mask

    return benign_train | attack_train, benign_val | attack_val, benign_test | attack_test


def protocol_label_prior_shift(graph: Any, flow_mask: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    stable_score = graph.window_idx.float() * 1021.0 + graph.ip_idx.float() * 31.0
    ordered = classwise_ordered_indices(flow_mask, graph.y, stable_score, descending=False)
    train = torch.zeros_like(flow_mask)
    val = torch.zeros_like(flow_mask)
    test = torch.zeros_like(flow_mask)

    # Make train attack-heavy and test benign-heavy.
    alloc = {
        1: (0.70, 0.10, 0.20),  # attack
        0: (0.40, 0.15, 0.45),  # benign
    }
    for cls, idx in ordered.items():
        n = int(idx.numel())
        if n == 0:
            continue
        tr = max(1, int(round(alloc[cls][0] * n)))
        va = max(1, int(round(alloc[cls][1] * n))) if n >= 3 else 0
        tr = min(tr, n)
        va = min(va, max(0, n - tr))
        te_start = tr + va
        train[idx[:tr]] = True
        if va > 0:
            val[idx[tr:te_start]] = True
        test[idx[te_start:]] = True
        if int(test[idx].sum().item()) == 0:
            test[idx[-1:]] = True
            if int(train[idx].sum().item()) > 1:
                train[idx[-1:]] = False

    return train, val, test


def protocol_camouflage_bias(graph: Any, flow_mask: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    score = graph.camouflage_proxy.float()
    return split_quantile_per_class(flow_mask, graph.y, score)


def protocol_congestion_ood(graph: Any, flow_mask: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    score = 0.70 * graph.congestion_proxy.float() + 0.30 * graph.rho_proxy.float()
    return split_quantile_per_class(flow_mask, graph.y, score)


def mask_counts(y: torch.Tensor, weak_label: torch.Tensor, mask: torch.Tensor) -> dict[str, int]:
    covered = mask & (weak_label >= 0)
    return {
        "nodes": int(mask.sum().item()),
        "benign_true": int(((y == 0) & mask).sum().item()),
        "attack_true": int(((y == 1) & mask).sum().item()),
        "weak_covered": int(covered.sum().item()),
        "weak_benign": int(((weak_label == 0) & mask).sum().item()),
        "weak_attack": int(((weak_label == 1) & mask).sum().item()),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Prepare weak-label protocol graph")
    p.add_argument("--input-graph", required=True)
    p.add_argument("--weak-labels", required=True)
    p.add_argument("--output-graph", required=True)
    p.add_argument("--protocol", choices=[
        "weak_temporal_ood",
        "weak_topology_ood",
        "weak_attack_strategy_ood",
        "label_prior_shift_ood",
        "camouflage_biased_noise_ood",
        "congestion_ood",
    ], required=True)
    p.add_argument("--manifest-file", default="")
    p.add_argument("--holdout-attack-type", default="mimic")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    torch.manual_seed(int(args.seed))
    graph = torch.load(args.input_graph, weights_only=False, map_location="cpu")
    weak_bundle = torch.load(args.weak_labels, weights_only=False, map_location="cpu")
    manifest = load_manifest(args.manifest_file)

    graph = attach_weak_bundle(graph, weak_bundle)
    flow_mask = graph.window_idx >= 0

    if args.protocol == "weak_temporal_ood":
        train_mask, val_mask, test_mask = protocol_temporal_ood(graph, flow_mask)
    elif args.protocol == "weak_topology_ood":
        train_mask, val_mask, test_mask = protocol_topology_ood(graph, flow_mask)
    elif args.protocol == "weak_attack_strategy_ood":
        train_mask, val_mask, test_mask = protocol_attack_strategy_ood(
            graph, manifest=manifest, flow_mask=flow_mask, holdout_attack_type=args.holdout_attack_type.strip().lower()
        )
    elif args.protocol == "label_prior_shift_ood":
        train_mask, val_mask, test_mask = protocol_label_prior_shift(graph, flow_mask)
    elif args.protocol == "camouflage_biased_noise_ood":
        train_mask, val_mask, test_mask = protocol_camouflage_bias(graph, flow_mask)
    else:
        train_mask, val_mask, test_mask = protocol_congestion_ood(graph, flow_mask)

    graph.train_mask = train_mask.bool()
    graph.val_mask = val_mask.bool()
    graph.test_mask = test_mask.bool()
    graph.temporal_test_mask = test_mask.bool()
    graph.split_protocol = args.protocol
    graph.holdout_attack_type = args.holdout_attack_type.strip().lower()
    graph.weak_label_source = args.weak_labels

    out_dir = os.path.dirname(os.path.abspath(args.output_graph))
    os.makedirs(out_dir, exist_ok=True)
    torch.save(graph, args.output_graph)

    summary = {
        "protocol": args.protocol,
        "input_graph": os.path.abspath(args.input_graph),
        "weak_labels": os.path.abspath(args.weak_labels),
        "output_graph": os.path.abspath(args.output_graph),
        "holdout_attack_type": args.holdout_attack_type.strip().lower(),
        "scenario_tags": dict(getattr(graph, "scenario_tags", {})),
        "train": mask_counts(graph.y, graph.weak_label, graph.train_mask),
        "val": mask_counts(graph.y, graph.weak_label, graph.val_mask),
        "test": mask_counts(graph.y, graph.weak_label, graph.test_mask),
    }
    json_path = os.path.splitext(args.output_graph)[0] + "_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("=" * 72)
    print(f"Protocol: {args.protocol}")
    print(f"Output  : {args.output_graph}")
    print("Train   :", summary["train"])
    print("Val     :", summary["val"])
    print("Test    :", summary["test"])
    print(f"Summary : {json_path}")
    print("=" * 72)


if __name__ == "__main__":
    main()
