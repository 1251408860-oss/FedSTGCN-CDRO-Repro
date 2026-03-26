#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import torch


def summarize(values: torch.Tensor) -> dict[str, float]:
    if int(values.numel()) == 0:
        return {"n": 0, "mean": 0.0, "std": 0.0, "q25": 0.0, "q50": 0.0, "q75": 0.0}
    if int(values.numel()) == 1:
        v = float(values.item())
        return {"n": 1, "mean": v, "std": 0.0, "q25": v, "q50": v, "q75": v}
    return {
        "n": int(values.numel()),
        "mean": float(values.mean().item()),
        "std": float(values.std(unbiased=True).item()),
        "q25": float(torch.quantile(values, 0.25).item()),
        "q50": float(torch.quantile(values, 0.50).item()),
        "q75": float(torch.quantile(values, 0.75).item()),
    }


def compute_trust(
    agreement: torch.Tensor,
    confidence: torch.Tensor,
    uncertainty: torch.Tensor,
    base_trust: float,
    is_benign: bool,
) -> torch.Tensor:
    if is_benign:
        trust = (
            float(base_trust)
            * (0.75 + 0.25 * agreement)
            * (0.80 + 0.20 * confidence)
            * (1.0 - 0.25 * uncertainty)
        )
    else:
        trust = (
            float(base_trust)
            * (0.70 + 0.30 * agreement)
            * (0.80 + 0.20 * confidence)
        )
    return trust.clamp(0.0, 0.97)


def analyze_graph(path: Path, attack_trust: float, benign_trust: float) -> dict[str, Any]:
    graph = torch.load(path, map_location="cpu", weights_only=False)
    flow_mask = graph.window_idx >= 0
    train_mask = graph.train_mask.bool() & flow_mask
    weak_label = graph.weak_label.long()
    covered = train_mask & (weak_label >= 0)

    posterior = graph.weak_posterior.float()
    confidence = (posterior[:, 1] - 0.5).abs() * 2.0
    agreement = graph.weak_agreement.float().clamp(0.0, 1.0)
    uncertainty = graph.weak_uncertainty.float().clamp(0.0, 1.0)
    y_true = graph.y.long()

    out: dict[str, Any] = {"graph_file": str(path), "covered_train_nodes": int(covered.sum().item()), "buckets": {}}
    for label_name, raw_label, is_benign, base_trust in [
        ("weak_attack", 1, False, attack_trust),
        ("weak_benign", 0, True, benign_trust),
    ]:
        mask = covered & (weak_label == raw_label)
        if int(mask.sum().item()) == 0:
            out["buckets"][label_name] = {
                "n": 0,
                "precision": 0.0,
                "agreement": summarize(torch.tensor([], dtype=torch.float)),
                "uncertainty": summarize(torch.tensor([], dtype=torch.float)),
                "confidence": summarize(torch.tensor([], dtype=torch.float)),
                "effective_trust": summarize(torch.tensor([], dtype=torch.float)),
            }
            continue
        target_true = 0 if is_benign else 1
        precision = float((y_true[mask] == target_true).float().mean().item())
        trust = compute_trust(
            agreement=agreement[mask],
            confidence=confidence[mask],
            uncertainty=uncertainty[mask],
            base_trust=base_trust,
            is_benign=is_benign,
        )
        out["buckets"][label_name] = {
            "n": int(mask.sum().item()),
            "precision": precision,
            "agreement": summarize(agreement[mask]),
            "uncertainty": summarize(uncertainty[mask]),
            "confidence": summarize(confidence[mask]),
            "effective_trust": summarize(trust),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Analyze weak-label quality and effective trust on protocol graphs")
    ap.add_argument("--protocol-graph-dir", required=True)
    ap.add_argument("--output-json", required=True)
    ap.add_argument("--attack-trust", type=float, default=0.90)
    ap.add_argument("--benign-trust", type=float, default=0.55)
    ap.add_argument("--protocols", default="weak_temporal_ood,weak_topology_ood,weak_attack_strategy_ood,label_prior_shift_ood")
    args = ap.parse_args()

    protocol_dir = Path(args.protocol_graph_dir)
    protocols = [x.strip() for x in str(args.protocols).split(",") if x.strip()]

    summary: dict[str, Any] = {
        "config": {
            "protocol_graph_dir": str(protocol_dir),
            "attack_trust": float(args.attack_trust),
            "benign_trust": float(args.benign_trust),
            "protocols": protocols,
        },
        "protocols": {},
    }

    for proto in protocols:
        summary["protocols"][proto] = analyze_graph(
            path=protocol_dir / f"{proto}.pt",
            attack_trust=float(args.attack_trust),
            benign_trust=float(args.benign_trust),
        )

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
