#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F

from pi_gnn_train_cdro import (
    HARD_LABEL_METHODS,
    METHOD_CHOICES,
    UG_METHODS,
    build_group_ids,
    build_prior_corrected_posteriors,
    build_training_targets,
    compute_train_loss,
    evaluate_logits,
    find_best_threshold_from_logits,
)


class TabularMLP(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int, dropout: float) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 2),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def load_bundle(path: Path, device: torch.device) -> SimpleNamespace:
    raw = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(raw, dict):
        raise RuntimeError(f"expected dict bundle, got: {type(raw)}")
    obj = SimpleNamespace()
    for key, value in raw.items():
        if isinstance(value, torch.Tensor):
            setattr(obj, key, value.to(device))
        else:
            setattr(obj, key, value)
    if not hasattr(obj, "num_nodes"):
        obj.num_nodes = int(obj.x.shape[0])
    if not hasattr(obj, "x_norm"):
        obj.x_norm = obj.x
    return obj


def choose_device(force_cpu: bool) -> torch.device:
    if (not force_cpu) and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


@torch.no_grad()
def forward_eval(
    model: nn.Module,
    x: torch.Tensor,
    y_true: torch.Tensor,
    mask: torch.Tensor,
    threshold: float,
    temperature: float = 1.0,
) -> dict[str, float]:
    model.eval()
    logits = model(x)
    return evaluate_logits(logits=logits, true_labels=y_true, mask=mask, threshold=threshold, temperature=temperature)


@torch.no_grad()
def find_best_threshold(
    model: nn.Module,
    x: torch.Tensor,
    y_true: torch.Tensor,
    val_mask: torch.Tensor,
) -> tuple[float, dict[str, float]]:
    model.eval()
    logits = model(x)
    return find_best_threshold_from_logits(logits=logits, true_labels=y_true, val_mask=val_mask, temperature=1.0)


def main() -> None:
    ap = argparse.ArgumentParser(description="Train tabular weak-label CDRO baselines")
    ap.add_argument("--bundle-file", required=True)
    ap.add_argument("--model-file", required=True)
    ap.add_argument("--results-file", required=True)
    ap.add_argument("--method", choices=["noisy_ce", "posterior_ce", "cdro_fixed", "cdro_ug", "cdro_ug_priorcorr"], required=True)
    ap.add_argument("--hidden-dim", type=int, default=128)
    ap.add_argument("--dropout", type=float, default=0.20)
    ap.add_argument("--lr", type=float, default=0.003)
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--patience", type=int, default=8)
    ap.add_argument("--lambda-dro", type=float, default=0.50)
    ap.add_argument("--pseudo-attack-thr", type=float, default=0.60)
    ap.add_argument("--pseudo-benign-thr", type=float, default=0.25)
    ap.add_argument("--pseudo-weight", type=float, default=0.60)
    ap.add_argument("--attack-trust", type=float, default=0.90)
    ap.add_argument("--benign-trust", type=float, default=0.55)
    ap.add_argument("--pseudo-attack-trust", type=float, default=0.85)
    ap.add_argument("--pseudo-benign-trust", type=float, default=0.80)
    ap.add_argument("--ug-temperature", type=float, default=0.35)
    ap.add_argument("--ug-priority-loss-scale", type=float, default=1.0)
    ap.add_argument("--ug-uncertainty-scale", type=float, default=0.20)
    ap.add_argument("--ug-disagreement-scale", type=float, default=0.10)
    ap.add_argument("--ug-sample-weight-scale", type=float, default=0.0)
    ap.add_argument("--gce-q", type=float, default=0.70)
    ap.add_argument("--sce-alpha", type=float, default=1.00)
    ap.add_argument("--sce-beta", type=float, default=0.50)
    ap.add_argument("--bootstrap-beta", type=float, default=0.80)
    ap.add_argument("--elr-lambda", type=float, default=1.00)
    ap.add_argument("--elr-beta", type=float, default=0.70)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--force-cpu", action="store_true")
    args = ap.parse_args()

    device = choose_device(force_cpu=bool(args.force_cpu))
    torch.manual_seed(int(args.seed))

    bundle_file = Path(args.bundle_file).resolve()
    model_file = Path(args.model_file).resolve()
    results_file = Path(args.results_file).resolve()
    model_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.parent.mkdir(parents=True, exist_ok=True)

    data = load_bundle(bundle_file, device=device)
    x = data.x_norm.float()
    y = data.y.long()
    train_mask = data.train_mask.bool()
    val_mask = data.val_mask.bool()
    test_mask = data.test_mask.bool()
    temporal_test_mask = data.temporal_test_mask.bool() if hasattr(data, "temporal_test_mask") else test_mask
    flow_mask = getattr(data, "flow_mask", torch.ones_like(train_mask)).bool()
    train_mask = train_mask & flow_mask
    val_mask = val_mask & flow_mask
    test_mask = test_mask & flow_mask
    temporal_test_mask = temporal_test_mask & flow_mask

    t0 = time.time()

    model = TabularMLP(in_dim=int(x.shape[1]), hidden_dim=int(args.hidden_dim), dropout=float(args.dropout)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=float(args.lr), weight_decay=float(args.weight_decay))
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=int(args.epochs), eta_min=1e-5)

    train_supervised_mask, soft_targets_all, sample_weights, target_meta = build_training_targets(
        method=args.method,
        graph=data,
        train_mask=train_mask,
        flow_mask=flow_mask,
        pseudo_attack_thr=float(args.pseudo_attack_thr),
        pseudo_benign_thr=float(args.pseudo_benign_thr),
        pseudo_weight=float(args.pseudo_weight),
        attack_trust=float(args.attack_trust),
        benign_trust=float(args.benign_trust),
        pseudo_attack_trust=float(args.pseudo_attack_trust),
        pseudo_benign_trust=float(args.pseudo_benign_trust),
        ug_sample_weight_scale=float(args.ug_sample_weight_scale),
    )
    if int(train_supervised_mask.sum().item()) == 0:
        raise RuntimeError("No effective weak supervision nodes in train split")

    weak_train = torch.argmax(soft_targets_all[train_supervised_mask], dim=1)
    n_pos = int((weak_train == 1).sum().item())
    n_neg = int((weak_train == 0).sum().item())
    pos_weight = float(n_neg / max(n_pos, 1))
    class_weights = (
        torch.tensor([1.0, max(1.0, pos_weight)], dtype=torch.float, device=device)
        if args.method in HARD_LABEL_METHODS
        else None
    )
    elr_targets = torch.zeros((data.num_nodes, 2), dtype=torch.float, device=device) if args.method == "elr" else None

    group_ids, group_names, group_thresholds = build_group_ids(data, train_supervised_mask)
    prior_stats = {"source_prior": [], "target_prior": []}
    if args.method == "cdro_ug_priorcorr":
        covered_only = train_mask & (data.weak_label >= 0)
        soft_targets_all, prior_stats = build_prior_corrected_posteriors(
            base_targets=soft_targets_all,
            source_mask=covered_only,
            target_mask=train_mask,
        )

    history: dict[str, list[float]] = {
        "train_loss": [],
        "val_f1": [],
        "val_ece": [],
        "val_threshold": [],
        "base_loss": [],
        "dro_loss": [],
    }
    best_val_f1 = -1.0
    best_epoch = 0
    best_threshold = 0.5
    bad_epochs = 0

    for epoch in range(1, int(args.epochs) + 1):
        model.train()
        optimizer.zero_grad()
        logits = model(x)
        loss, info = compute_train_loss(
            method=args.method,
            logits=logits,
            graph=data,
            train_supervised_mask=train_supervised_mask,
            class_weights=class_weights,
            group_ids=group_ids,
            lambda_dro=float(args.lambda_dro),
            sample_weights=sample_weights,
            soft_targets_all=soft_targets_all,
            ug_priority_loss_scale=float(args.ug_priority_loss_scale),
            ug_temperature=float(args.ug_temperature),
            ug_uncertainty_scale=float(args.ug_uncertainty_scale),
            ug_disagreement_scale=float(args.ug_disagreement_scale),
            gce_q=float(args.gce_q),
            sce_alpha=float(args.sce_alpha),
            sce_beta=float(args.sce_beta),
            bootstrap_beta=float(args.bootstrap_beta),
            elr_lambda=float(args.elr_lambda),
            elr_beta=float(args.elr_beta),
            elr_targets=elr_targets,
        )
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        scheduler.step()

        history["train_loss"].append(float(loss.item()))
        history["base_loss"].append(float(info.get("base_loss", 0.0)))
        history["dro_loss"].append(float(info.get("dro_loss", 0.0)))

        if epoch <= 5 or epoch % 5 == 0:
            val_thr, val_metrics = find_best_threshold(model=model, x=x, y_true=y, val_mask=val_mask)
            history["val_f1"].append(float(val_metrics["f1"]))
            history["val_ece"].append(float(val_metrics["ece"]))
            history["val_threshold"].append(float(val_thr))
            if val_metrics["f1"] > best_val_f1:
                best_val_f1 = float(val_metrics["f1"])
                best_epoch = epoch
                best_threshold = float(val_thr)
                torch.save(model.state_dict(), model_file)
                bad_epochs = 0
            else:
                bad_epochs += 1
        if int(args.patience) > 0 and bad_epochs >= int(args.patience):
            break

    model.load_state_dict(torch.load(model_file, weights_only=True, map_location=device))
    with torch.no_grad():
        logits = model(x)

    final_eval = {
        "train": evaluate_logits(logits=logits, true_labels=y, mask=train_mask, threshold=best_threshold, temperature=1.0),
        "val": evaluate_logits(logits=logits, true_labels=y, mask=val_mask, threshold=best_threshold, temperature=1.0),
        "test_random": evaluate_logits(logits=logits, true_labels=y, mask=test_mask, threshold=best_threshold, temperature=1.0),
        "test_temporal": evaluate_logits(logits=logits, true_labels=y, mask=temporal_test_mask, threshold=best_threshold, temperature=1.0),
    }

    elapsed = float(time.time() - t0)
    results = {
        "best_epoch": int(best_epoch),
        "best_val_f1": float(best_val_f1),
        "best_threshold": float(best_threshold),
        "final_eval": final_eval,
        "group_names": group_names,
        "group_thresholds": group_thresholds,
        "prior_stats": prior_stats,
        "history": history,
        "runtime_sec": elapsed,
        "config": {
            "bundle_file": str(bundle_file),
            "method": args.method,
            "hidden_dim": int(args.hidden_dim),
            "dropout": float(args.dropout),
            "lr": float(args.lr),
            "weight_decay": float(args.weight_decay),
            "epochs": int(args.epochs),
            "patience": int(args.patience),
            "lambda_dro": float(args.lambda_dro),
            "ug_temperature": float(args.ug_temperature),
            "ug_priority_loss_scale": float(args.ug_priority_loss_scale),
            "ug_uncertainty_scale": float(args.ug_uncertainty_scale),
            "ug_disagreement_scale": float(args.ug_disagreement_scale),
            "ug_sample_weight_scale": float(args.ug_sample_weight_scale),
            "seed": int(args.seed),
            "force_cpu": bool(args.force_cpu),
            "train_supervised_nodes": int(train_supervised_mask.sum().item()),
            "target_meta": target_meta,
        },
        "metadata": getattr(data, "metadata", {}),
    }
    results_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(results_file)


if __name__ == "__main__":
    main()
