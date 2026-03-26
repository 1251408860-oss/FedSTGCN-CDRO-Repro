#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
from xgboost import XGBClassifier

from pi_gnn_train_cdro import evaluate_logits, find_best_threshold_from_logits


def main() -> None:
    ap = argparse.ArgumentParser(description="Train XGBoost weak-label baseline on graph node features")
    ap.add_argument("--graph-file", required=True)
    ap.add_argument("--model-file", required=True)
    ap.add_argument("--results-file", required=True)
    ap.add_argument("--n-estimators", type=int, default=300)
    ap.add_argument("--max-depth", type=int, default=6)
    ap.add_argument("--learning-rate", type=float, default=0.05)
    ap.add_argument("--subsample", type=float, default=0.8)
    ap.add_argument("--colsample-bytree", type=float, default=0.8)
    ap.add_argument("--min-child-weight", type=float, default=1.0)
    ap.add_argument("--reg-lambda", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--n-jobs", type=int, default=4)
    args = ap.parse_args()

    graph_file = Path(args.graph_file).resolve()
    model_file = Path(args.model_file).resolve()
    results_file = Path(args.results_file).resolve()
    model_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.parent.mkdir(parents=True, exist_ok=True)

    graph = torch.load(graph_file, map_location="cpu", weights_only=False)
    x = graph.x.float().cpu().numpy()
    y_true = graph.y.long()

    train_mask = graph.train_mask.bool()
    val_mask = graph.val_mask.bool()
    test_mask = graph.test_mask.bool()
    temporal_test_mask = graph.temporal_test_mask.bool() if hasattr(graph, "temporal_test_mask") else test_mask
    flow_mask = graph.window_idx >= 0 if hasattr(graph, "window_idx") else torch.ones(graph.num_nodes, dtype=torch.bool)
    weak_covered = graph.weak_label >= 0
    weak_train_mask = train_mask & flow_mask & weak_covered
    if int(weak_train_mask.sum().item()) == 0:
        raise RuntimeError("No weak-label-covered training nodes for XGBoost baseline")

    train_idx = weak_train_mask.nonzero(as_tuple=False).view(-1).cpu().numpy()
    y_weak = graph.weak_label[weak_train_mask].long().cpu().numpy()
    n_pos = int((y_weak == 1).sum())
    n_neg = int((y_weak == 0).sum())
    scale_pos_weight = float(n_neg / max(n_pos, 1))

    t0 = time.time()
    model = XGBClassifier(
        n_estimators=int(args.n_estimators),
        max_depth=int(args.max_depth),
        learning_rate=float(args.learning_rate),
        subsample=float(args.subsample),
        colsample_bytree=float(args.colsample_bytree),
        min_child_weight=float(args.min_child_weight),
        reg_lambda=float(args.reg_lambda),
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        random_state=int(args.seed),
        n_jobs=int(args.n_jobs),
        scale_pos_weight=scale_pos_weight,
    )
    model.fit(x[train_idx], y_weak)
    train_sec = float(time.time() - t0)
    model.save_model(str(model_file))

    prob = np.clip(model.predict_proba(x)[:, 1], 1e-6, 1.0 - 1e-6)
    logits = torch.from_numpy(np.stack([np.log(1.0 - prob), np.log(prob)], axis=1)).float()
    best_threshold, val_metrics = find_best_threshold_from_logits(logits=logits, true_labels=y_true, val_mask=val_mask, temperature=1.0)

    final_eval = {
        "train": evaluate_logits(logits=logits, true_labels=y_true, mask=train_mask & flow_mask, threshold=best_threshold, temperature=1.0),
        "val": evaluate_logits(logits=logits, true_labels=y_true, mask=val_mask & flow_mask, threshold=best_threshold, temperature=1.0),
        "test_random": evaluate_logits(logits=logits, true_labels=y_true, mask=test_mask & flow_mask, threshold=best_threshold, temperature=1.0),
        "test_temporal": evaluate_logits(logits=logits, true_labels=y_true, mask=temporal_test_mask & flow_mask, threshold=best_threshold, temperature=1.0),
    }

    results = {
        "graph_file": str(graph_file),
        "model_file": str(model_file),
        "training_seconds": train_sec,
        "best_threshold": float(best_threshold),
        "val_metrics": val_metrics,
        "training_supervision": {
            "weak_train_nodes": int(weak_train_mask.sum().item()),
            "weak_attack_nodes": int((graph.weak_label[weak_train_mask] == 1).sum().item()),
            "weak_benign_nodes": int((graph.weak_label[weak_train_mask] == 0).sum().item()),
        },
        "config": {
            "seed": int(args.seed),
            "n_estimators": int(args.n_estimators),
            "max_depth": int(args.max_depth),
            "learning_rate": float(args.learning_rate),
            "subsample": float(args.subsample),
            "colsample_bytree": float(args.colsample_bytree),
            "min_child_weight": float(args.min_child_weight),
            "reg_lambda": float(args.reg_lambda),
            "scale_pos_weight": scale_pos_weight,
        },
        "final_eval": final_eval,
    }
    results_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(results_file)


if __name__ == "__main__":
    main()
