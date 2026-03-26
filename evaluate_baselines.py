#!/usr/bin/env python3
"""
Evaluate baselines and export Recall/FPR/ROC-AUC:
  - RandomForest
  - GCN baseline
  - PI-GNN (pretrained)
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, roc_curve

try:
    from torch_geometric.data import Data
    from torch_geometric.nn import GATConv, GCNConv
except ImportError:
    raise SystemExit("torch_geometric is required")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def resolve_feature_indices(graph: Data) -> dict[str, int]:
    if hasattr(graph, "feature_index") and isinstance(graph.feature_index, dict):
        idx = {str(k): int(v) for k, v in graph.feature_index.items()}
        if "ln(N+1)" in idx and "lnN" not in idx:
            idx["lnN"] = idx["ln(N+1)"]
        return idx
    return {
        "ln(N+1)": 0,
        "lnN": 0,
        "entropy": 1,
        "D_observed": 2,
        "pkt_rate": 3,
        "avg_pkt_size": 4,
        "port_diversity": 5,
    }


class GCNBaseline(nn.Module):
    def __init__(self, in_channels: int, hidden_channels: int = 64, dropout: float = 0.3):
        super().__init__()
        self.dropout = dropout
        self.conv1 = GCNConv(in_channels, hidden_channels)
        self.conv2 = GCNConv(hidden_channels, hidden_channels)
        self.head = nn.Sequential(
            nn.Linear(hidden_channels, hidden_channels // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_channels // 2, 2),
        )

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        h = self.conv1(x, edge_index)
        h = F.relu(h)
        h = F.dropout(h, p=self.dropout, training=self.training)
        h = self.conv2(h, edge_index)
        h = F.relu(h)
        return self.head(h)


class PIGNNModel(nn.Module):
    def __init__(self, in_channels: int, hidden_channels: int = 64, heads: int = 4, dropout: float = 0.3):
        super().__init__()
        self.dropout = dropout

        self.input_proj = nn.Linear(in_channels, hidden_channels)

        self.s_conv1 = GATConv(hidden_channels, hidden_channels, heads=heads, concat=False, dropout=dropout)
        self.s_conv2 = GATConv(hidden_channels, hidden_channels, heads=heads, concat=False, dropout=dropout)
        self.s_norm1 = nn.LayerNorm(hidden_channels)
        self.s_norm2 = nn.LayerNorm(hidden_channels)

        self.t_conv1 = GATConv(hidden_channels, hidden_channels, heads=heads, concat=False, dropout=dropout)
        self.t_conv2 = GATConv(hidden_channels, hidden_channels, heads=heads, concat=False, dropout=dropout)
        self.t_norm1 = nn.LayerNorm(hidden_channels)
        self.t_norm2 = nn.LayerNorm(hidden_channels)

        self.gate = nn.Sequential(nn.Linear(hidden_channels * 2, hidden_channels), nn.Sigmoid())

        self.head = nn.Sequential(
            nn.Linear(hidden_channels, hidden_channels // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_channels // 2, 2),
        )

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, edge_type: torch.Tensor) -> torch.Tensor:
        spatial_edges = edge_index[:, edge_type == 0]
        temporal_edges = edge_index[:, edge_type == 1]

        n = x.size(0)
        self_loops = torch.arange(n, device=x.device).unsqueeze(0).expand(2, -1)
        spatial_edges = torch.cat([spatial_edges, self_loops], dim=1)
        temporal_edges = torch.cat([temporal_edges, self_loops], dim=1)

        h = F.elu(self.input_proj(x))
        h = F.dropout(h, p=self.dropout, training=self.training)

        hs = self.s_conv1(h, spatial_edges)
        hs = self.s_norm1(hs)
        hs = F.elu(hs)
        hs = F.dropout(hs, p=self.dropout, training=self.training)
        hs = self.s_conv2(hs, spatial_edges)
        hs = self.s_norm2(hs)
        hs = F.elu(hs)

        ht = self.t_conv1(h, temporal_edges)
        ht = self.t_norm1(ht)
        ht = F.elu(ht)
        ht = F.dropout(ht, p=self.dropout, training=self.training)
        ht = self.t_conv2(ht, temporal_edges)
        ht = self.t_norm2(ht)
        ht = F.elu(ht)

        g = self.gate(torch.cat([hs, ht], dim=-1))
        h_fused = g * hs + (1.0 - g) * ht
        return self.head(h_fused)


def classification_report_from_probs(y_true: np.ndarray, y_prob: np.ndarray) -> tuple[dict[str, float], dict[str, list[float]]]:
    y_pred = (y_prob >= 0.5).astype(np.int64)

    tp = int(np.sum((y_pred == 1) & (y_true == 1)))
    fp = int(np.sum((y_pred == 1) & (y_true == 0)))
    fn = int(np.sum((y_pred == 0) & (y_true == 1)))
    tn = int(np.sum((y_pred == 0) & (y_true == 0)))

    recall = tp / max(tp + fn, 1)
    precision = tp / max(tp + fp, 1)
    f1 = 2.0 * precision * recall / max(precision + recall, 1e-8)
    acc = (tp + tn) / max(tp + fp + fn + tn, 1)
    fpr = fp / max(fp + tn, 1)

    if len(np.unique(y_true)) >= 2:
        auc = float(roc_auc_score(y_true, y_prob))
        fpr_pts, tpr_pts, _ = roc_curve(y_true, y_prob)
        roc_pts = {"fpr": fpr_pts.tolist(), "tpr": tpr_pts.tolist()}
    else:
        auc = 0.5
        roc_pts = {"fpr": [0.0, 1.0], "tpr": [0.0, 1.0]}

    metrics = {
        "accuracy": float(acc),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "fpr": float(fpr),
        "roc_auc": float(auc),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }
    return metrics, roc_pts


def get_eval_mask(graph: Data) -> tuple[torch.Tensor, str]:
    if hasattr(graph, "temporal_test_mask") and int(graph.temporal_test_mask.sum().item()) > 0:
        return graph.temporal_test_mask, "temporal_test"
    return graph.test_mask, "random_test"


def train_gcn(graph: Data, device: torch.device, epochs: int, lr: float, wd: float, hidden: int) -> GCNBaseline:
    model = GCNBaseline(graph.x_norm.shape[1], hidden_channels=hidden).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=wd)

    edge_index = graph.edge_index_undirected if hasattr(graph, "edge_index_undirected") else graph.edge_index

    best_state = None
    best_f1 = -1.0

    for _ in range(epochs):
        model.train()
        opt.zero_grad()
        logits = model(graph.x_norm, edge_index)
        loss = F.cross_entropy(logits[graph.train_mask], graph.y[graph.train_mask])
        loss.backward()
        opt.step()

        if int(graph.val_mask.sum().item()) > 0:
            model.eval()
            with torch.no_grad():
                val_prob = F.softmax(model(graph.x_norm, edge_index), dim=1)[:, 1]
                y_true = graph.y[graph.val_mask].detach().cpu().numpy()
                y_prob = val_prob[graph.val_mask].detach().cpu().numpy()
                m, _ = classification_report_from_probs(y_true, y_prob)
                if m["f1"] > best_f1:
                    best_f1 = m["f1"]
                    best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)
    return model


def run(args: argparse.Namespace) -> None:
    device = torch.device("cuda" if torch.cuda.is_available() and not args.force_cpu else "cpu")

    graph: Data = torch.load(args.graph_file, weights_only=False).to(device)
    eval_mask, eval_split = get_eval_mask(graph)

    y_eval = graph.y[eval_mask].detach().cpu().numpy()

    results: dict[str, Any] = {
        "config": vars(args),
        "device": str(device),
        "eval_split": eval_split,
        "feature_index": resolve_feature_indices(graph),
        "metrics": {},
        "roc_points": {},
    }

    # 1) RandomForest baseline (node features only)
    x_train = graph.x_norm[graph.train_mask].detach().cpu().numpy()
    y_train = graph.y[graph.train_mask].detach().cpu().numpy()
    x_eval = graph.x_norm[eval_mask].detach().cpu().numpy()

    rf = RandomForestClassifier(
        n_estimators=args.rf_trees,
        random_state=args.seed,
        n_jobs=-1,
        class_weight="balanced",
    )
    rf.fit(x_train, y_train)
    rf_prob = rf.predict_proba(x_eval)[:, 1]

    rf_metrics, rf_roc = classification_report_from_probs(y_eval, rf_prob)
    results["metrics"]["random_forest"] = rf_metrics
    results["roc_points"]["random_forest"] = rf_roc

    # 2) GCN baseline (graph structure)
    gcn = train_gcn(graph, device=device, epochs=args.gcn_epochs, lr=args.gcn_lr, wd=args.gcn_weight_decay, hidden=args.gcn_hidden)
    gcn.eval()
    with torch.no_grad():
        edge_index = graph.edge_index_undirected if hasattr(graph, "edge_index_undirected") else graph.edge_index
        gcn_prob = F.softmax(gcn(graph.x_norm, edge_index), dim=1)[:, 1][eval_mask].detach().cpu().numpy()

    gcn_metrics, gcn_roc = classification_report_from_probs(y_eval, gcn_prob)
    results["metrics"]["gcn"] = gcn_metrics
    results["roc_points"]["gcn"] = gcn_roc

    # 3) PI-GNN pretrained
    pi_model = PIGNNModel(
        in_channels=graph.x_norm.shape[1],
        hidden_channels=args.pi_hidden,
        heads=args.pi_heads,
        dropout=args.pi_dropout,
    ).to(device)

    if not os.path.exists(args.pi_model_file):
        raise FileNotFoundError(f"PI-GNN model not found: {args.pi_model_file}")

    state = torch.load(args.pi_model_file, map_location=device, weights_only=True)
    pi_model.load_state_dict(state, strict=False)
    pi_model.eval()
    with torch.no_grad():
        pi_prob = F.softmax(pi_model(graph.x_norm, graph.edge_index, graph.edge_type), dim=1)[:, 1][eval_mask].detach().cpu().numpy()

    pi_metrics, pi_roc = classification_report_from_probs(y_eval, pi_prob)
    results["metrics"]["pi_gnn"] = pi_metrics
    results["roc_points"]["pi_gnn"] = pi_roc

    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("=" * 70)
    print("Baseline Evaluation Complete")
    print("=" * 70)
    print(f"Eval split: {eval_split}")
    for name, m in results["metrics"].items():
        print(
            f"{name:14s} recall={m['recall']:.4f} fpr={m['fpr']:.4f} "
            f"auc={m['roc_auc']:.4f} f1={m['f1']:.4f}"
        )
    print(f"Saved: {args.output_file}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate RF/GCN/PI-GNN baselines")
    p.add_argument("--graph-file", default=os.path.join(BASE_DIR, "st_graph.pt"))
    p.add_argument("--pi-model-file", default=os.path.join(BASE_DIR, "pi_gnn_model.pt"))
    p.add_argument("--output-file", default=os.path.join(BASE_DIR, "baseline_eval_results.json"))

    p.add_argument("--rf-trees", type=int, default=400)

    p.add_argument("--gcn-epochs", type=int, default=120)
    p.add_argument("--gcn-lr", type=float, default=0.01)
    p.add_argument("--gcn-weight-decay", type=float, default=5e-4)
    p.add_argument("--gcn-hidden", type=int, default=64)

    p.add_argument("--pi-hidden", type=int, default=64)
    p.add_argument("--pi-heads", type=int, default=4)
    p.add_argument("--pi-dropout", type=float, default=0.3)

    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--force-cpu", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    run(args)
