#!/usr/bin/env python3
"""
Train weak-label ST-GNN baselines and a minimal conditional DRO variant.

Methods:
  - noisy_ce
  - gce
  - sce
  - bootstrap_ce
  - elr
  - posterior_ce
  - cdro_fixed
  - cdro_ug
  - cdro_ug_priorcorr
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F

from pi_gnn_train_v2 import (
    SpatioTemporalGNN,
    build_physics_context_features,
    get_device,
    resolve_feature_indices,
)

try:
    from torch_geometric.data import Data
except ImportError:
    raise SystemExit("ERROR: torch_geometric required")


METHOD_CHOICES = [
    "noisy_ce",
    "gce",
    "sce",
    "bootstrap_ce",
    "elr",
    "posterior_ce",
    "cdro_fixed",
    "cdro_ug",
    "cdro_ug_priorcorr",
]
HARD_LABEL_METHODS = {"noisy_ce", "gce", "sce", "bootstrap_ce", "elr"}
UG_METHODS = {"cdro_ug", "cdro_ug_priorcorr"}


def soft_cross_entropy(logits: torch.Tensor, soft_targets: torch.Tensor) -> torch.Tensor:
    logp = F.log_softmax(logits, dim=1)
    return -(soft_targets * logp).sum(dim=1)


def per_sample_class_weights(targets: torch.Tensor, class_weights: torch.Tensor | None) -> torch.Tensor | None:
    if class_weights is None or int(targets.numel()) == 0:
        return None
    return class_weights[targets.long()]


def generalized_cross_entropy_loss(logits: torch.Tensor, targets: torch.Tensor, q: float) -> torch.Tensor:
    prob = F.softmax(logits, dim=1).gather(1, targets.long().view(-1, 1)).squeeze(1).clamp(min=1e-6, max=1.0)
    q_val = float(q)
    if abs(q_val) <= 1e-6:
        return -torch.log(prob)
    return (1.0 - torch.pow(prob, q_val)) / q_val


def symmetric_cross_entropy_loss(
    logits: torch.Tensor,
    targets: torch.Tensor,
    alpha: float,
    beta: float,
) -> torch.Tensor:
    one_hot = F.one_hot(targets.long(), num_classes=logits.shape[1]).float()
    ce = F.cross_entropy(logits, targets.long(), reduction="none")
    prob = F.softmax(logits, dim=1).clamp(min=1e-7, max=1.0)
    safe_target = one_hot.clamp(min=1e-4, max=1.0)
    rce = -(prob * torch.log(safe_target)).sum(dim=1)
    return float(alpha) * ce + float(beta) * rce


def bootstrap_soft_targets(logits: torch.Tensor, targets: torch.Tensor, beta: float) -> torch.Tensor:
    one_hot = F.one_hot(targets.long(), num_classes=logits.shape[1]).float()
    pred = F.softmax(logits.detach(), dim=1)
    mixed = float(beta) * one_hot + (1.0 - float(beta)) * pred
    return mixed / mixed.sum(dim=1, keepdim=True).clamp(min=1e-6)


def early_learning_regularization_loss(
    logits: torch.Tensor,
    targets: torch.Tensor,
    history: torch.Tensor,
    beta: float,
    lam: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    prob = F.softmax(logits, dim=1).clamp(min=1e-4, max=1.0 - 1e-4)
    updated = float(beta) * history + (1.0 - float(beta)) * prob.detach()
    updated = updated / updated.sum(dim=1, keepdim=True).clamp(min=1e-6)
    ce = F.cross_entropy(logits, targets.long(), reduction="none")
    reg = torch.log((1.0 - (updated * prob).sum(dim=1)).clamp(min=1e-4))
    return ce + float(lam) * reg, updated


def expected_calibration_error(prob_attack: torch.Tensor, true: torch.Tensor, n_bins: int = 10) -> float:
    if int(prob_attack.numel()) == 0:
        return 0.0
    bins = torch.linspace(0.0, 1.0, n_bins + 1, device=prob_attack.device)
    ece = torch.tensor(0.0, device=prob_attack.device)
    for i in range(n_bins):
        lo = bins[i]
        hi = bins[i + 1]
        if i == n_bins - 1:
            mask = (prob_attack >= lo) & (prob_attack <= hi)
        else:
            mask = (prob_attack >= lo) & (prob_attack < hi)
        if int(mask.sum().item()) == 0:
            continue
        conf = prob_attack[mask].mean()
        acc = true[mask].float().mean()
        ece = ece + mask.float().mean() * torch.abs(acc - conf)
    return float(ece.item())


def apply_temperature(logits: torch.Tensor, temperature: float) -> torch.Tensor:
    return logits / max(float(temperature), 1e-6)


def evaluate_logits(
    logits: torch.Tensor,
    true_labels: torch.Tensor,
    mask: torch.Tensor,
    threshold: float = 0.5,
    temperature: float = 1.0,
) -> dict[str, float]:
    if int(mask.sum().item()) == 0:
        return {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "fpr": 0.0,
            "ece": 0.0,
            "brier": 0.0,
            "tp": 0,
            "fp": 0,
            "fn": 0,
            "tn": 0,
            "threshold": float(threshold),
            "temperature": float(temperature),
        }

    scaled_logits = apply_temperature(logits[mask], temperature)
    prob = F.softmax(scaled_logits, dim=1)[:, 1]
    pred = (prob >= float(threshold)).long()
    true = true_labels[mask]

    tp = int(((pred == 1) & (true == 1)).sum().item())
    fp = int(((pred == 1) & (true == 0)).sum().item())
    fn = int(((pred == 0) & (true == 1)).sum().item())
    tn = int(((pred == 0) & (true == 0)).sum().item())

    total = max(tp + fp + fn + tn, 1)
    accuracy = (tp + tn) / total
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2.0 * precision * recall / max(precision + recall, 1e-8)
    fpr = fp / max(fp + tn, 1)
    ece = expected_calibration_error(prob, true)
    brier = float(torch.mean((prob - true.float()) ** 2).item())

    return {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "fpr": float(fpr),
        "ece": float(ece),
        "brier": float(brier),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "threshold": float(threshold),
        "temperature": float(temperature),
    }


@torch.no_grad()
def evaluate(
    model: nn.Module,
    graph: Data,
    mask: torch.Tensor,
    threshold: float = 0.5,
    temperature: float = 1.0,
) -> dict[str, float]:
    model.eval()
    x_model = graph.x_model if hasattr(graph, "x_model") else graph.x_norm
    logits, _ = model(x_model, graph.edge_index, graph.edge_type)
    return evaluate_logits(logits=logits, true_labels=graph.y, mask=mask, threshold=threshold, temperature=temperature)


@torch.no_grad()
def find_best_threshold_from_logits(
    logits: torch.Tensor,
    true_labels: torch.Tensor,
    val_mask: torch.Tensor,
    temperature: float = 1.0,
) -> tuple[float, dict[str, float]]:
    best_t = 0.5
    best_m = evaluate_logits(logits=logits, true_labels=true_labels, mask=val_mask, threshold=0.5, temperature=temperature)
    for t in torch.linspace(0.05, 0.95, 19):
        m = evaluate_logits(logits=logits, true_labels=true_labels, mask=val_mask, threshold=float(t.item()), temperature=temperature)
        if m["f1"] > best_m["f1"]:
            best_t = float(t.item())
            best_m = m
    return best_t, best_m


@torch.no_grad()
def find_best_threshold(model: nn.Module, graph: Data, val_mask: torch.Tensor, temperature: float = 1.0) -> tuple[float, dict[str, float]]:
    model.eval()
    x_model = graph.x_model if hasattr(graph, "x_model") else graph.x_norm
    logits, _ = model(x_model, graph.edge_index, graph.edge_type)
    return find_best_threshold_from_logits(logits=logits, true_labels=graph.y, val_mask=val_mask, temperature=temperature)


@torch.no_grad()
def masked_nll(logits: torch.Tensor, true_labels: torch.Tensor, mask: torch.Tensor, temperature: float = 1.0) -> float:
    if int(mask.sum().item()) == 0:
        return 0.0
    scaled_logits = apply_temperature(logits[mask], temperature)
    return float(F.cross_entropy(scaled_logits, true_labels[mask], reduction="mean").item())


@torch.no_grad()
def fit_temperature(
    logits: torch.Tensor,
    true_labels: torch.Tensor,
    val_mask: torch.Tensor,
    temp_min: float,
    temp_max: float,
    temp_steps: int,
) -> dict[str, float]:
    if int(val_mask.sum().item()) == 0:
        return {
            "enabled": False,
            "temperature": 1.0,
            "val_nll_raw": 0.0,
            "val_nll_calibrated": 0.0,
            "val_ece_raw": 0.0,
            "val_ece_calibrated": 0.0,
            "val_brier_raw": 0.0,
            "val_brier_calibrated": 0.0,
            "val_threshold_raw": 0.5,
            "val_threshold_calibrated": 0.5,
            "val_f1_raw": 0.0,
            "val_f1_calibrated": 0.0,
        }

    lo = max(float(temp_min), 1e-3)
    hi = max(float(temp_max), lo + 1e-3)
    steps = max(int(temp_steps), 3)
    raw_threshold, raw_metrics = find_best_threshold_from_logits(logits=logits, true_labels=true_labels, val_mask=val_mask, temperature=1.0)
    raw_nll = masked_nll(logits=logits, true_labels=true_labels, mask=val_mask, temperature=1.0)

    best_temperature = 1.0
    best_nll = raw_nll
    grid = torch.logspace(math.log10(lo), math.log10(hi), steps=steps, device=logits.device)
    for temp in grid:
        t = float(temp.item())
        nll = masked_nll(logits=logits, true_labels=true_labels, mask=val_mask, temperature=t)
        if nll < best_nll - 1e-8:
            best_nll = nll
            best_temperature = t

    cal_threshold, cal_metrics = find_best_threshold_from_logits(
        logits=logits,
        true_labels=true_labels,
        val_mask=val_mask,
        temperature=best_temperature,
    )
    return {
        "enabled": True,
        "temperature": float(best_temperature),
        "val_nll_raw": float(raw_nll),
        "val_nll_calibrated": float(best_nll),
        "val_ece_raw": float(raw_metrics["ece"]),
        "val_ece_calibrated": float(cal_metrics["ece"]),
        "val_brier_raw": float(raw_metrics["brier"]),
        "val_brier_calibrated": float(cal_metrics["brier"]),
        "val_threshold_raw": float(raw_threshold),
        "val_threshold_calibrated": float(cal_threshold),
        "val_f1_raw": float(raw_metrics["f1"]),
        "val_f1_calibrated": float(cal_metrics["f1"]),
    }


def build_group_ids(graph: Data, train_supervised_mask: torch.Tensor) -> tuple[torch.Tensor, dict[int, str], dict[str, float]]:
    uncertainty = graph.weak_uncertainty.float()
    rho = graph.rho_proxy.float()
    valid = train_supervised_mask

    if int(valid.sum().item()) == 0:
        zero = torch.zeros_like(graph.y, dtype=torch.long)
        return zero, {0: "all"}, {"uncertainty_mid": 0.0, "rho_mid": 0.0}

    u_mid = float(torch.quantile(uncertainty[valid], 0.50).item())
    r_mid = float(torch.quantile(rho[valid], 0.50).item())
    u_bin = (uncertainty >= u_mid).long()
    r_bin = (rho >= r_mid).long()
    group_ids = r_bin * 2 + u_bin
    group_names = {
        0: "low_rho_low_uncertainty",
        1: "low_rho_high_uncertainty",
        2: "high_rho_low_uncertainty",
        3: "high_rho_high_uncertainty",
    }
    return group_ids, group_names, {"uncertainty_mid": u_mid, "rho_mid": r_mid}


def norm01(x: torch.Tensor) -> torch.Tensor:
    x_min = torch.min(x)
    x_max = torch.max(x)
    return (x - x_min) / (x_max - x_min + 1e-6)


def build_prior_corrected_posteriors(
    base_targets: torch.Tensor,
    source_mask: torch.Tensor,
    target_mask: torch.Tensor,
) -> tuple[torch.Tensor, dict[str, list[float]]]:
    source = base_targets[source_mask].float()
    target = base_targets[target_mask].float()
    if int(source.shape[0]) == 0 or int(target.shape[0]) == 0:
        return base_targets.float(), {"source_prior": [0.5, 0.5], "target_prior": [0.5, 0.5]}

    source_prior = source.mean(dim=0).clamp(min=1e-4)
    target_prior = target.mean(dim=0).clamp(min=1e-4)
    ratio = target_prior / source_prior
    corrected = base_targets.float() * ratio.unsqueeze(0)
    corrected = corrected / corrected.sum(dim=1, keepdim=True).clamp(min=1e-6)
    stats = {
        "source_prior": [float(v) for v in source_prior.tolist()],
        "target_prior": [float(v) for v in target_prior.tolist()],
    }
    return corrected, stats


def build_training_targets(
    method: str,
    graph: Data,
    train_mask: torch.Tensor,
    flow_mask: torch.Tensor,
    pseudo_attack_thr: float,
    pseudo_benign_thr: float,
    pseudo_weight: float,
    attack_trust: float,
    benign_trust: float,
    pseudo_attack_trust: float,
    pseudo_benign_trust: float,
    ug_sample_weight_scale: float,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, dict[str, Any]]:
    weak_label = graph.weak_label.long()
    posterior = graph.weak_posterior.float().clone()
    confidence = (posterior[:, 1] - 0.5).abs() * 2.0
    agreement = graph.weak_agreement.float().clamp(0.0, 1.0)
    uncertainty = graph.weak_uncertainty.float().clamp(0.0, 1.0)
    rho = norm01(graph.rho_proxy.float()) if hasattr(graph, "rho_proxy") else torch.zeros_like(confidence)
    disagreement = 1.0 - agreement

    covered = train_mask & (weak_label >= 0)
    if method not in UG_METHODS:
        sample_weights = torch.ones_like(graph.y, dtype=torch.float)
        meta = {
            "covered_train_nodes": int(covered.sum().item()),
            "pseudo_attack_nodes": 0,
            "pseudo_benign_nodes": 0,
            "effective_train_nodes": int(covered.sum().item()),
        }
        return covered, posterior, sample_weights, meta

    hard_targets = F.one_hot(torch.clamp(weak_label, min=0), num_classes=2).float()
    trust = torch.zeros_like(graph.y, dtype=torch.float)
    atk_mask = covered & (weak_label == 1)
    ben_mask = covered & (weak_label == 0)
    trust[atk_mask] = (
        float(attack_trust)
        * (0.70 + 0.30 * agreement[atk_mask])
        * (0.80 + 0.20 * confidence[atk_mask])
    )
    trust[ben_mask] = (
        float(benign_trust)
        * (0.75 + 0.25 * agreement[ben_mask])
        * (0.80 + 0.20 * confidence[ben_mask])
        * (1.0 - 0.25 * uncertainty[ben_mask])
    )
    trust = trust.clamp(0.0, 0.97)

    hybrid = posterior.clone()
    hybrid[covered] = trust[covered].unsqueeze(1) * hard_targets[covered] + (1.0 - trust[covered]).unsqueeze(1) * posterior[covered]
    hybrid = hybrid / hybrid.sum(dim=1, keepdim=True).clamp(min=1e-6)

    sample_weights = torch.ones_like(graph.y, dtype=torch.float)
    ug_score = 0.45 * uncertainty + 0.35 * rho + 0.20 * disagreement
    sample_weights[covered] = (1.0 + float(ug_sample_weight_scale) * ug_score[covered]).clamp(max=1.25)

    meta = {
        "covered_train_nodes": int(covered.sum().item()),
        "pseudo_attack_nodes": 0,
        "pseudo_benign_nodes": 0,
        "effective_train_nodes": int(covered.sum().item()),
    }
    return covered, hybrid, sample_weights, meta


def compute_train_loss(
    method: str,
    logits: torch.Tensor,
    graph: Data,
    train_supervised_mask: torch.Tensor,
    class_weights: torch.Tensor | None,
    group_ids: torch.Tensor,
    lambda_dro: float,
    sample_weights: torch.Tensor,
    soft_targets_all: torch.Tensor,
    ug_priority_loss_scale: float,
    ug_temperature: float,
    ug_uncertainty_scale: float,
    ug_disagreement_scale: float,
    gce_q: float,
    sce_alpha: float,
    sce_beta: float,
    bootstrap_beta: float,
    elr_lambda: float,
    elr_beta: float,
    elr_targets: torch.Tensor | None,
) -> tuple[torch.Tensor, dict[str, float]]:
    idx = train_supervised_mask.nonzero(as_tuple=False).view(-1)
    if int(idx.numel()) == 0:
        zero = torch.tensor(0.0, device=logits.device)
        return zero, {"base_loss": 0.0, "dro_loss": 0.0}

    if method in HARD_LABEL_METHODS:
        y_weak = graph.weak_label[idx].long()
        sample_class_weights = per_sample_class_weights(y_weak, class_weights)
        if method == "noisy_ce":
            per_sample = F.cross_entropy(logits[idx], y_weak, reduction="none", weight=class_weights)
        elif method == "gce":
            per_sample = generalized_cross_entropy_loss(logits[idx], y_weak, q=gce_q)
        elif method == "sce":
            per_sample = symmetric_cross_entropy_loss(logits[idx], y_weak, alpha=sce_alpha, beta=sce_beta)
        elif method == "bootstrap_ce":
            boot_targets = bootstrap_soft_targets(logits[idx], y_weak, beta=bootstrap_beta)
            per_sample = soft_cross_entropy(logits[idx], boot_targets)
        else:
            if elr_targets is None:
                raise RuntimeError("ELR requires an initialized target buffer")
            per_sample, updated = early_learning_regularization_loss(
                logits[idx],
                y_weak,
                history=elr_targets[idx],
                beta=elr_beta,
                lam=elr_lambda,
            )
            elr_targets[idx] = updated.detach()
        if sample_class_weights is not None and method != "noisy_ce":
            per_sample = per_sample * sample_class_weights
            base_loss = per_sample.sum() / sample_class_weights.sum().clamp(min=1e-6)
        else:
            base_loss = per_sample.mean()
        return base_loss, {"base_loss": float(base_loss.item()), "dro_loss": 0.0}

    soft_targets = soft_targets_all[idx].float()
    per_sample = soft_cross_entropy(logits[idx], soft_targets)

    if method in UG_METHODS:
        per_sample = per_sample * sample_weights[idx]
        base_loss = per_sample.sum() / sample_weights[idx].sum().clamp(min=1e-6)
    else:
        base_loss = per_sample.mean()

    if method == "posterior_ce":
        return base_loss, {"base_loss": float(base_loss.item()), "dro_loss": 0.0}

    group_values = []
    group_priority_terms = []
    group_terms = {}
    for gid in sorted(set(int(v) for v in group_ids[idx].tolist())):
        gmask = idx[group_ids[idx] == gid]
        if int(gmask.numel()) == 0:
            continue
        gl_sample = soft_cross_entropy(logits[gmask], soft_targets_all[gmask].float())
        if method in UG_METHODS:
            gl = (gl_sample * sample_weights[gmask]).sum() / sample_weights[gmask].sum().clamp(min=1e-6)
        else:
            gl = gl_sample.mean()
        group_values.append(gl)
        group_terms[str(gid)] = float(gl.item())
        if method in UG_METHODS:
            g_unc = float(graph.weak_uncertainty[gmask].float().mean().item())
            g_dis = float((1.0 - graph.weak_agreement[gmask].float()).mean().item())
            priority = (
                float(ug_priority_loss_scale) * gl.detach()
                + float(ug_uncertainty_scale) * g_unc
                + float(ug_disagreement_scale) * g_dis
            )
            group_priority_terms.append(priority)

    if not group_values:
        return base_loss, {"base_loss": float(base_loss.item()), "dro_loss": 0.0}

    if method in UG_METHODS:
        priorities = torch.stack(group_priority_terms)
        weights = torch.softmax(priorities / max(float(ug_temperature), 1e-6), dim=0)
        group_stack = torch.stack(group_values)
        dro_loss = torch.sum(weights * group_stack)
        for gid_i, gid in enumerate(sorted(set(int(v) for v in group_ids[idx].tolist()))):
            if str(gid) in group_terms:
                group_terms[f"weight_{gid}"] = float(weights[gid_i].item())
    else:
        dro_loss = torch.stack(group_values).max()
    total_loss = (1.0 - float(lambda_dro)) * base_loss + float(lambda_dro) * dro_loss
    info = {"base_loss": float(base_loss.item()), "dro_loss": float(dro_loss.item()), **{f"group_{k}": v for k, v in group_terms.items()}}
    return total_loss, info


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train CDRO and weak-label baselines")
    p.add_argument("--graph-file", required=True)
    p.add_argument("--model-file", required=True)
    p.add_argument("--results-file", required=True)
    p.add_argument("--logits-file", default="")
    p.add_argument("--method", choices=METHOD_CHOICES, required=True)
    p.add_argument("--hidden-dim", type=int, default=64)
    p.add_argument("--heads", type=int, default=4)
    p.add_argument("--dropout", type=float, default=0.3)
    p.add_argument("--lr", type=float, default=0.005)
    p.add_argument("--weight-decay", type=float, default=5e-4)
    p.add_argument("--epochs", type=int, default=80)
    p.add_argument("--patience", type=int, default=25)
    p.add_argument("--lambda-dro", type=float, default=0.50)
    p.add_argument("--pseudo-attack-thr", type=float, default=0.60)
    p.add_argument("--pseudo-benign-thr", type=float, default=0.25)
    p.add_argument("--pseudo-weight", type=float, default=0.60)
    p.add_argument("--attack-trust", type=float, default=0.90)
    p.add_argument("--benign-trust", type=float, default=0.55)
    p.add_argument("--pseudo-attack-trust", type=float, default=0.85)
    p.add_argument("--pseudo-benign-trust", type=float, default=0.80)
    p.add_argument("--ug-temperature", type=float, default=0.35)
    p.add_argument("--ug-priority-loss-scale", type=float, default=1.0)
    p.add_argument("--ug-uncertainty-scale", type=float, default=0.20)
    p.add_argument("--ug-disagreement-scale", type=float, default=0.10)
    p.add_argument("--ug-sample-weight-scale", type=float, default=0.20)
    p.add_argument("--gce-q", type=float, default=0.70)
    p.add_argument("--sce-alpha", type=float, default=1.00)
    p.add_argument("--sce-beta", type=float, default=0.50)
    p.add_argument("--bootstrap-beta", type=float, default=0.80)
    p.add_argument("--elr-lambda", type=float, default=0.20)
    p.add_argument("--elr-beta", type=float, default=0.70)
    p.add_argument("--posthoc-temperature-scaling", action="store_true")
    p.add_argument("--temp-scale-min", type=float, default=0.5)
    p.add_argument("--temp-scale-max", type=float, default=5.0)
    p.add_argument("--temp-scale-steps", type=int, default=31)
    p.add_argument("--train-mask-name", default="train_mask")
    p.add_argument("--val-mask-name", default="val_mask")
    p.add_argument("--test-mask-name", default="test_mask")
    p.add_argument("--temporal-test-mask-name", default="temporal_test_mask")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--force-cpu", action="store_true")
    p.add_argument("--physics-context", action="store_true")
    p.add_argument("--capacity", type=float, default=120000.0)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    graph_file = os.path.abspath(os.path.expanduser(args.graph_file))
    model_file = os.path.abspath(os.path.expanduser(args.model_file))
    results_file = os.path.abspath(os.path.expanduser(args.results_file))
    logits_file = os.path.abspath(os.path.expanduser(args.logits_file)) if args.logits_file else os.path.splitext(results_file)[0] + "_logits.pt"
    os.makedirs(os.path.dirname(model_file), exist_ok=True)
    os.makedirs(os.path.dirname(results_file), exist_ok=True)

    torch.manual_seed(int(args.seed))
    device = get_device(force_cpu=bool(args.force_cpu))
    if device.type == "cuda":
        torch.cuda.manual_seed_all(int(args.seed))

    t0 = time.time()
    graph: Data = torch.load(graph_file, weights_only=False).to(device)
    feat_idx = resolve_feature_indices(graph)
    flow_mask = graph.window_idx >= 0

    train_mask = getattr(graph, args.train_mask_name).bool() & flow_mask
    val_mask = getattr(graph, args.val_mask_name).bool() & flow_mask
    test_mask = getattr(graph, args.test_mask_name).bool() & flow_mask
    temporal_test_mask = getattr(graph, args.temporal_test_mask_name).bool() & flow_mask if hasattr(graph, args.temporal_test_mask_name) else test_mask
    graph.x_model = graph.x_norm
    if bool(args.physics_context):
        ctx = build_physics_context_features(graph, capacity=float(args.capacity), feat_idx=feat_idx)
        ctx_flow = ctx[flow_mask]
        c_mean = ctx_flow.mean(dim=0)
        c_std = ctx_flow.std(dim=0).clamp(min=1e-6)
        ctx_norm = (ctx - c_mean) / c_std
        ctx_norm[~flow_mask] = 0.0
        graph.physics_context = ctx_norm
        graph.x_model = torch.cat([graph.x_norm, ctx_norm], dim=1)

    model = SpatioTemporalGNN(
        in_channels=graph.x_model.shape[1],
        hidden_channels=int(args.hidden_dim),
        out_channels=2,
        num_heads=int(args.heads),
        dropout=float(args.dropout),
    ).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=float(args.lr), weight_decay=float(args.weight_decay))
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=int(args.epochs), eta_min=1e-5)

    train_supervised_mask, soft_targets_all, sample_weights, target_meta = build_training_targets(
        method=args.method,
        graph=graph,
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
    elr_targets = torch.zeros((graph.num_nodes, 2), dtype=torch.float, device=device) if args.method == "elr" else None

    group_ids, group_names, group_thresholds = build_group_ids(graph, train_supervised_mask)
    prior_stats = {"source_prior": [], "target_prior": []}
    if args.method == "cdro_ug_priorcorr":
        covered_only = train_mask & (graph.weak_label >= 0)
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

    print("=" * 72)
    print(f"CDRO Training: {args.method}")
    print("=" * 72)
    print(f"Graph            : {graph_file}")
    print(f"Train/Val/Test   : {int(train_mask.sum())}/{int(val_mask.sum())}/{int(test_mask.sum())}")
    print(f"Weak-covered     : {int(train_supervised_mask.sum())}")
    print(f"Method           : {args.method}")
    print(f"Physics context  : {bool(args.physics_context)}")
    print(f"Device           : {device}")
    print(
        f"Covered/Pseudo+/-: {target_meta.get('covered_train_nodes', 0)}/"
        f"{target_meta.get('pseudo_attack_nodes', 0)}/{target_meta.get('pseudo_benign_nodes', 0)}"
    )
    print("=" * 72)

    for epoch in range(1, int(args.epochs) + 1):
        model.train()
        optimizer.zero_grad()
        x_model = graph.x_model if hasattr(graph, "x_model") else graph.x_norm
        logits, _ = model(x_model, graph.edge_index, graph.edge_type)
        loss, info = compute_train_loss(
            method=args.method,
            logits=logits,
            graph=graph,
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
            val_thr, val_metrics = find_best_threshold(model, graph, val_mask)
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
            print(
                f"{epoch:4d} | loss={loss.item():.4f} base={info.get('base_loss', 0.0):.4f} "
                f"dro={info.get('dro_loss', 0.0):.4f} | val_f1={val_metrics['f1']:.4f} "
                f"val_ece={val_metrics['ece']:.4f} thr={val_thr:.2f}"
            )

        if int(args.patience) > 0 and bad_epochs >= int(args.patience):
            print(f"Early stop at epoch {epoch}")
            break

    model.load_state_dict(torch.load(model_file, weights_only=True, map_location=device))
    x_model = graph.x_model if hasattr(graph, "x_model") else graph.x_norm
    with torch.no_grad():
        logits, _ = model(x_model, graph.edge_index, graph.edge_type)
        probs_raw = F.softmax(logits, dim=1)

    best_threshold_raw = float(best_threshold)
    eval_temperature = 1.0
    temperature_stats = {
        "enabled": False,
        "temperature": 1.0,
        "val_nll_raw": 0.0,
        "val_nll_calibrated": 0.0,
        "val_ece_raw": 0.0,
        "val_ece_calibrated": 0.0,
        "val_brier_raw": 0.0,
        "val_brier_calibrated": 0.0,
        "val_threshold_raw": float(best_threshold_raw),
        "val_threshold_calibrated": float(best_threshold_raw),
        "val_f1_raw": float(best_val_f1),
        "val_f1_calibrated": float(best_val_f1),
    }
    if bool(args.posthoc_temperature_scaling):
        temperature_stats = fit_temperature(
            logits=logits,
            true_labels=graph.y,
            val_mask=val_mask,
            temp_min=float(args.temp_scale_min),
            temp_max=float(args.temp_scale_max),
            temp_steps=int(args.temp_scale_steps),
        )
        eval_temperature = float(temperature_stats["temperature"])
        best_threshold = float(temperature_stats["val_threshold_calibrated"])

    probs = F.softmax(apply_temperature(logits, eval_temperature), dim=1)

    final_eval_raw = {
        "train": evaluate_logits(logits=logits, true_labels=graph.y, mask=train_mask, threshold=best_threshold_raw, temperature=1.0),
        "val": evaluate_logits(logits=logits, true_labels=graph.y, mask=val_mask, threshold=best_threshold_raw, temperature=1.0),
        "test_random": evaluate_logits(logits=logits, true_labels=graph.y, mask=test_mask, threshold=best_threshold_raw, temperature=1.0),
        "test_temporal": evaluate_logits(logits=logits, true_labels=graph.y, mask=temporal_test_mask, threshold=best_threshold_raw, temperature=1.0),
    }
    final_eval = {
        "train": evaluate_logits(logits=logits, true_labels=graph.y, mask=train_mask, threshold=best_threshold, temperature=eval_temperature),
        "val": evaluate_logits(logits=logits, true_labels=graph.y, mask=val_mask, threshold=best_threshold, temperature=eval_temperature),
        "test_random": evaluate_logits(logits=logits, true_labels=graph.y, mask=test_mask, threshold=best_threshold, temperature=eval_temperature),
        "test_temporal": evaluate_logits(logits=logits, true_labels=graph.y, mask=temporal_test_mask, threshold=best_threshold, temperature=eval_temperature),
    }

    logits_bundle = {
        "logits": logits.detach().cpu(),
        "probs_raw": probs_raw.detach().cpu(),
        "probs": probs.detach().cpu(),
        "y_true": graph.y.detach().cpu(),
        "train_mask": train_mask.detach().cpu(),
        "val_mask": val_mask.detach().cpu(),
        "test_mask": test_mask.detach().cpu(),
        "temporal_test_mask": temporal_test_mask.detach().cpu(),
        "weak_label": graph.weak_label.detach().cpu(),
        "weak_posterior": graph.weak_posterior.detach().cpu(),
        "temperature": float(eval_temperature),
    }
    torch.save(logits_bundle, logits_file)

    elapsed = float(time.time() - t0)
    results = {
        "best_epoch": int(best_epoch),
        "best_val_f1": float(best_val_f1),
        "best_threshold_raw": float(best_threshold_raw),
        "best_threshold": float(best_threshold),
        "eval_temperature": float(eval_temperature),
        "temperature_scaling": temperature_stats,
        "final_eval_raw": final_eval_raw,
        "final_eval": final_eval,
        "group_names": group_names,
        "group_thresholds": group_thresholds,
        "prior_stats": prior_stats,
        "history": history,
        "runtime_sec": elapsed,
        "config": {
            "graph_file": graph_file,
            "method": args.method,
            "hidden_dim": int(args.hidden_dim),
            "heads": int(args.heads),
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
            "gce_q": float(args.gce_q),
            "sce_alpha": float(args.sce_alpha),
            "sce_beta": float(args.sce_beta),
            "bootstrap_beta": float(args.bootstrap_beta),
            "elr_lambda": float(args.elr_lambda),
            "elr_beta": float(args.elr_beta),
            "posthoc_temperature_scaling": bool(args.posthoc_temperature_scaling),
            "temp_scale_min": float(args.temp_scale_min),
            "temp_scale_max": float(args.temp_scale_max),
            "temp_scale_steps": int(args.temp_scale_steps),
            "seed": int(args.seed),
            "force_cpu": bool(args.force_cpu),
            "physics_context": bool(args.physics_context),
            "capacity": float(args.capacity),
            "train_supervised_nodes": int(train_supervised_mask.sum().item()),
            "target_meta": target_meta,
        },
    }

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("=" * 72)
    print("Final Metrics")
    print("=" * 72)
    for name, metrics in final_eval.items():
        print(
            f"{name:14s} | F1={metrics['f1']:.4f} Recall={metrics['recall']:.4f} "
            f"FPR={metrics['fpr']:.4f} ECE={metrics['ece']:.4f} Brier={metrics['brier']:.4f}"
        )
    print(f"Best epoch       : {best_epoch}")
    print(f"Best threshold   : {best_threshold:.2f}")
    print(f"Raw threshold    : {best_threshold_raw:.2f}")
    print(f"Eval temperature : {eval_temperature:.3f}")
    print(f"Runtime sec      : {elapsed:.2f}")
    print(f"Saved model      : {model_file}")
    print(f"Saved results    : {results_file}")
    print(f"Saved logits     : {logits_file}")
    print("=" * 72)


if __name__ == "__main__":
    main()
