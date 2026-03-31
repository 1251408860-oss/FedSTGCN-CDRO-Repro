#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from typing import Any

import torch


def bool_mask(graph: Any, name: str) -> torch.Tensor:
    if not hasattr(graph, name):
        raise RuntimeError(f"graph missing mask: {name}")
    return getattr(graph, name).bool()


def swap_binary_prob(prob: torch.Tensor) -> torch.Tensor:
    if prob.ndim == 1 or prob.shape[-1] != 2:
        return prob
    out = prob.clone()
    out[..., 0] = prob[..., 1]
    out[..., 1] = prob[..., 0]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Stress weak labels by injecting noise or coverage loss")
    ap.add_argument("--input-graph", required=True)
    ap.add_argument("--output-graph", required=True)
    ap.add_argument("--train-mask-name", default="train_mask")
    ap.add_argument("--flip-frac", type=float, default=0.0)
    ap.add_argument("--drop-frac", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    torch.manual_seed(int(args.seed))
    graph = torch.load(args.input_graph, weights_only=False, map_location="cpu")
    train_mask = bool_mask(graph, args.train_mask_name)
    flow_mask = graph.window_idx >= 0 if hasattr(graph, "window_idx") else torch.ones(graph.num_nodes, dtype=torch.bool)

    if not hasattr(graph, "weak_label") or not hasattr(graph, "weak_posterior"):
        raise RuntimeError("graph does not contain attached weak supervision bundle")

    covered = train_mask & flow_mask & (graph.weak_label >= 0)
    idx_all = covered.nonzero(as_tuple=False).view(-1)
    perm = idx_all[torch.randperm(int(idx_all.numel()))] if int(idx_all.numel()) > 0 else idx_all

    flip_k = min(int(round(float(args.flip_frac) * int(idx_all.numel()))), int(idx_all.numel()))
    flip_idx = perm[:flip_k]
    drop_rest = perm[flip_k:]
    drop_k = min(int(round(float(args.drop_frac) * int(idx_all.numel()))), int(drop_rest.numel()))
    drop_idx = drop_rest[:drop_k]

    if int(flip_idx.numel()) > 0:
        graph.weak_label[flip_idx] = 1 - graph.weak_label[flip_idx]
        graph.weak_posterior[flip_idx] = swap_binary_prob(graph.weak_posterior[flip_idx])
        if hasattr(graph, "weak_view_probs"):
            graph.weak_view_probs[flip_idx] = swap_binary_prob(graph.weak_view_probs[flip_idx])
        if hasattr(graph, "weak_view_votes"):
            graph.weak_view_votes[flip_idx] = swap_binary_prob(graph.weak_view_votes[flip_idx])

    if int(drop_idx.numel()) > 0:
        graph.weak_label[drop_idx] = -1
        graph.weak_posterior[drop_idx] = 0.5
        if hasattr(graph, "weak_uncertainty"):
            graph.weak_uncertainty[drop_idx] = 1.0
        if hasattr(graph, "weak_agreement"):
            graph.weak_agreement[drop_idx] = 0.0
        if hasattr(graph, "weak_num_votes"):
            graph.weak_num_votes[drop_idx] = 0
        if hasattr(graph, "weak_view_votes"):
            graph.weak_view_votes[drop_idx] = 0.0
        if hasattr(graph, "weak_view_probs"):
            graph.weak_view_probs[drop_idx] = 0.5

    graph.stress_spec = {
        "flip_frac": float(args.flip_frac),
        "drop_frac": float(args.drop_frac),
        "seed": int(args.seed),
        "flipped_nodes": int(flip_idx.numel()),
        "dropped_nodes": int(drop_idx.numel()),
        "covered_train_nodes_before": int(idx_all.numel()),
        "covered_train_nodes_after": int((train_mask & flow_mask & (graph.weak_label >= 0)).sum().item()),
    }

    out_dir = os.path.dirname(os.path.abspath(args.output_graph))
    os.makedirs(out_dir, exist_ok=True)
    torch.save(graph, args.output_graph)
    with open(os.path.splitext(args.output_graph)[0] + "_stress.json", "w", encoding="utf-8") as f:
        json.dump(graph.stress_spec, f, indent=2)

    print(json.dumps(graph.stress_spec, indent=2))


if __name__ == "__main__":
    main()
