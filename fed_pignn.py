#!/usr/bin/env python3
"""
Phase 4: Federated Physics-Informed ST-GNN (Fed-PI-STGNN)

Adds robust aggregation options:
  - fedavg
  - median
  - trimmed_mean
  - shapley_proxy
  - krum
  - multi_krum
  - bulyan
  - rfa
"""

from __future__ import annotations

import argparse
import json
import math
import os
from collections import OrderedDict
from typing import Any

import flwr as fl
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from flwr.common import Context, ndarrays_to_parameters, parameters_to_ndarrays
from flwr.server.strategy import FedAvg
from torch_geometric.data import Data
from torch_geometric.nn import GATConv
from torch_geometric.utils import subgraph

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_device(force_cpu: bool) -> torch.device:
    if (not force_cpu) and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


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


class FederatedSTGNN(nn.Module):
    def __init__(self, in_channels: int, hidden_channels: int, out_channels: int, heads: int = 2, dropout: float = 0.3):
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
            nn.Linear(hidden_channels // 2, out_channels),
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

        h_s = self.s_conv1(h, spatial_edges)
        h_s = self.s_norm1(h_s)
        h_s = F.elu(h_s)
        h_s = F.dropout(h_s, p=self.dropout, training=self.training)
        h_s = self.s_conv2(h_s, spatial_edges)
        h_s = self.s_norm2(h_s)
        h_s = F.elu(h_s)

        h_t = self.t_conv1(h, temporal_edges)
        h_t = self.t_norm1(h_t)
        h_t = F.elu(h_t)
        h_t = F.dropout(h_t, p=self.dropout, training=self.training)
        h_t = self.t_conv2(h_t, temporal_edges)
        h_t = self.t_norm2(h_t)
        h_t = F.elu(h_t)

        g = self.gate(torch.cat([h_s, h_t], dim=-1))
        h_fused = g * h_s + (1.0 - g) * h_t

        return self.head(h_fused)


class PhysicsLoss(nn.Module):
    """Differentiable physics regularization weighted by predicted attack probability."""

    def __init__(self, alpha: float, beta: float, capacity: float, feat_idx: dict[str, int]):
        super().__init__()
        self.alpha_base = float(alpha)
        self.beta_base = float(beta)
        self.alpha = float(alpha)
        self.beta = float(beta)
        self.capacity = float(capacity)
        self.idx_lnN = int(feat_idx.get("ln(N+1)", feat_idx.get("lnN", 0)))
        self.idx_dobs = int(feat_idx.get("D_observed", 2))
        self.idx_rate = int(feat_idx.get("pkt_rate", 3))

    def set_scale(self, ratio: float) -> None:
        r = max(0.0, min(1.0, float(ratio)))
        self.alpha = self.alpha_base * r
        self.beta = self.beta_base * r

    def forward(
        self,
        logits: torch.Tensor,
        y: torch.Tensor,
        mask: torch.Tensor,
        x_raw: torch.Tensor,
        window_idx: torch.Tensor,
        class_weights: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        if int(mask.sum().item()) == 0:
            zero = torch.tensor(0.0, device=logits.device)
            return zero, zero, zero, zero

        l_data = F.cross_entropy(logits[mask], y[mask], weight=class_weights)

        attack_prob = F.softmax(logits, dim=1)[:, 1]
        valid = (window_idx >= 0) & mask
        uniq_windows = torch.unique(window_idx[valid])

        flow_vol = torch.exp(x_raw[:, self.idx_lnN]).clamp(min=1.0) - 1.0
        flow_rate = x_raw[:, self.idx_rate].clamp(min=0.0)
        d_obs = x_raw[:, self.idx_dobs].clamp(min=0.0)

        if int(valid.sum().item()) > 0:
            ref_dobs = torch.quantile(d_obs[valid], q=0.75).clamp(min=1e-6)
        else:
            ref_dobs = torch.tensor(1.0, device=logits.device)

        flow_terms = []
        lat_terms = []

        for w in uniq_windows:
            w_mask = (window_idx == w) & valid
            if int(w_mask.sum().item()) < 2:
                continue

            p = attack_prob[w_mask]
            if float(p.sum().item()) < 1e-6:
                continue

            vol_w = flow_vol[w_mask]
            rate_w = flow_rate[w_mask]
            d_obs_w = d_obs[w_mask]

            agg_vol = torch.sum(p * vol_w)
            agg_rate = torch.sum(p * rate_w)
            active_est = torch.sum(p)
            d_mean = torch.sum(p * d_obs_w) / (active_est + 1e-6)

            rate_ratio = agg_rate / (self.capacity + 1e-6)
            buildup = F.relu(rate_ratio - 1.0)
            flow_terms.append(buildup * buildup)

            rho = torch.clamp(rate_ratio, min=0.0, max=0.99)
            d_theory = 1.0 / (1.0 - rho + 1e-6)
            d_scaled = d_mean / ref_dobs
            lat_terms.append(F.relu(d_theory - d_scaled))

        l_flow = torch.stack(flow_terms).mean() if flow_terms else torch.tensor(0.0, device=logits.device)
        l_lat = torch.stack(lat_terms).mean() if lat_terms else torch.tensor(0.0, device=logits.device)

        l_total = l_data + self.alpha * l_flow + self.beta * l_lat
        return l_total, l_data, l_flow, l_lat


def metrics_from_logits(logits: torch.Tensor, y: torch.Tensor, mask: torch.Tensor) -> dict[str, float]:
    if int(mask.sum().item()) == 0:
        return {"acc": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "tp": 0.0, "fp": 0.0, "fn": 0.0, "tn": 0.0}

    pred = logits[mask].argmax(dim=1)
    true = y[mask]

    tp = float(((pred == 1) & (true == 1)).sum().item())
    fp = float(((pred == 1) & (true == 0)).sum().item())
    fn = float(((pred == 0) & (true == 1)).sum().item())
    tn = float(((pred == 0) & (true == 0)).sum().item())

    total = max(tp + fp + fn + tn, 1.0)
    acc = (tp + tn) / total
    precision = tp / max(tp + fp, 1.0)
    recall = tp / max(tp + fn, 1.0)
    f1 = 2.0 * precision * recall / max(precision + recall, 1e-8)

    return {
        "acc": float(acc),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def get_parameters(model: nn.Module) -> list[np.ndarray]:
    return [v.detach().cpu().numpy() for _, v in model.state_dict().items()]


def set_parameters(model: nn.Module, parameters: list[np.ndarray]) -> None:
    keys = list(model.state_dict().keys())
    state_dict = OrderedDict((k, torch.tensor(v)) for k, v in zip(keys, parameters))
    model.load_state_dict(state_dict, strict=True)


def build_partition_graph(global_graph: Data, partition_id: int, num_clients: int) -> Data:
    flow_mask = (global_graph.ip_idx >= 0) & ((global_graph.ip_idx % num_clients) == partition_id)
    node_mask = flow_mask.clone()
    node_mask[0] = True

    subset = node_mask.nonzero(as_tuple=False).view(-1)

    edge_index, edge_type = subgraph(
        subset,
        global_graph.edge_index,
        edge_attr=global_graph.edge_type,
        relabel_nodes=True,
    )

    edge_index_u, edge_type_u = subgraph(
        subset,
        global_graph.edge_index_undirected,
        edge_attr=global_graph.edge_type_undirected,
        relabel_nodes=True,
    )

    window_local = global_graph.window_idx[subset]
    flow_local = window_local >= 0

    local = Data(
        x=global_graph.x[subset].clone(),
        x_norm=global_graph.x_norm[subset].clone(),
        y=global_graph.y[subset].clone(),
        edge_index=edge_index,
        edge_type=edge_type,
        edge_index_undirected=edge_index_u,
        edge_type_undirected=edge_type_u,
        window_idx=window_local.clone(),
        ip_idx=global_graph.ip_idx[subset].clone(),
        train_mask=(global_graph.train_mask[subset] & flow_local),
        val_mask=(global_graph.val_mask[subset] & flow_local),
        test_mask=(global_graph.test_mask[subset] & flow_local),
        temporal_train_mask=(global_graph.temporal_train_mask[subset] & flow_local),
        temporal_test_mask=(global_graph.temporal_test_mask[subset] & flow_local),
    )

    local.partition_id = partition_id
    local.num_clients = num_clients
    if hasattr(global_graph, "feature_index"):
        local.feature_index = global_graph.feature_index
    return local


class EdgeGatewayClient(fl.client.NumPyClient):
    def __init__(self, partition_id: int, args: argparse.Namespace, device: torch.device):
        self.partition_id = partition_id
        self.args = args
        self.device = device

        global_graph = torch.load(args.graph_file, weights_only=False)
        self.graph = build_partition_graph(global_graph, partition_id, args.num_clients).to(device)

        self.model = FederatedSTGNN(
            in_channels=self.graph.x_norm.shape[1],
            hidden_channels=args.hidden_dim,
            out_channels=2,
            heads=args.heads,
            dropout=args.dropout,
        ).to(device)

        feat_idx = resolve_feature_indices(self.graph)
        self.criterion = PhysicsLoss(args.alpha_flow, args.beta_latency, args.capacity, feat_idx)
        n_pos = int(((self.graph.y == 1) & self.graph.train_mask).sum().item())
        n_neg = int(((self.graph.y == 0) & self.graph.train_mask).sum().item())
        w_pos = float(n_neg / max(n_pos, 1))
        self.class_weights = torch.tensor([1.0, max(1.0, w_pos)], dtype=torch.float, device=device)

        poison_cut = int(round(args.simulate_poison_frac * args.num_clients))
        self.is_poisoned = partition_id < poison_cut and args.poison_scale > 0.0

    def get_parameters(self, config: dict[str, Any]) -> list[np.ndarray]:
        return get_parameters(self.model)

    def fit(self, parameters: list[np.ndarray], config: dict[str, Any]):
        set_parameters(self.model, parameters)

        local_epochs = int(config.get("local_epochs", self.args.local_epochs))
        lr = float(config.get("lr", self.args.lr))
        server_round = int(config.get("server_round", 1))
        num_train = int(self.graph.train_mask.sum().item())
        if num_train == 0:
            return self.get_parameters(config={}), 0, {"train_loss": 0.0, "train_acc": 0.0, "train_f1": 0.0}

        opt = torch.optim.Adam(self.model.parameters(), lr=lr, weight_decay=self.args.weight_decay)

        self.model.train()
        last_total = 0.0
        last_data = 0.0
        last_flow = 0.0
        last_lat = 0.0

        if self.args.warmup_rounds > 0:
            self.criterion.set_scale(min(1.0, float(server_round) / float(self.args.warmup_rounds)))
        else:
            self.criterion.set_scale(1.0)

        for _ in range(local_epochs):
            opt.zero_grad()
            logits = self.model(self.graph.x_norm, self.graph.edge_index, self.graph.edge_type)
            l_total, l_data, l_flow, l_lat = self.criterion(
                logits,
                self.graph.y,
                self.graph.train_mask,
                self.graph.x,
                self.graph.window_idx,
                class_weights=self.class_weights,
            )
            l_total.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            opt.step()

            last_total = float(l_total.detach().cpu().item())
            last_data = float(l_data.detach().cpu().item())
            last_flow = float(l_flow.detach().cpu().item())
            last_lat = float(l_lat.detach().cpu().item())

        self.model.eval()
        with torch.no_grad():
            logits = self.model(self.graph.x_norm, self.graph.edge_index, self.graph.edge_type)
            m = metrics_from_logits(logits, self.graph.y, self.graph.train_mask)

        out_params = self.get_parameters(config={})

        if self.is_poisoned:
            out_params = [
                w + np.random.normal(0.0, self.args.poison_scale, size=w.shape).astype(w.dtype)
                for w in out_params
            ]

        return out_params, num_train, {
            "train_loss": last_total,
            "train_loss_data": last_data,
            "train_loss_flow": last_flow,
            "train_loss_latency": last_lat,
            "train_acc": m["acc"],
            "train_f1": m["f1"],
            "is_poisoned": float(1 if self.is_poisoned else 0),
        }

    def evaluate(self, parameters: list[np.ndarray], config: dict[str, Any]):
        set_parameters(self.model, parameters)

        eval_mask = self.graph.val_mask
        if int(eval_mask.sum().item()) == 0:
            eval_mask = self.graph.test_mask
        if int(eval_mask.sum().item()) == 0:
            eval_mask = self.graph.train_mask

        num_eval = int(eval_mask.sum().item())
        if num_eval == 0:
            return 0.0, 0, {"val_acc": 0.0, "val_f1": 0.0}

        self.model.eval()
        with torch.no_grad():
            logits = self.model(self.graph.x_norm, self.graph.edge_index, self.graph.edge_type)
            loss = F.cross_entropy(logits[eval_mask], self.graph.y[eval_mask])
            m = metrics_from_logits(logits, self.graph.y, eval_mask)

        return float(loss.item()), num_eval, {
            "val_acc": m["acc"],
            "val_f1": m["f1"],
            "val_precision": m["precision"],
            "val_recall": m["recall"],
        }


def flatten_params(params: list[np.ndarray]) -> np.ndarray:
    return np.concatenate([p.reshape(-1) for p in params], axis=0)


def aggregate_weighted(client_params: list[list[np.ndarray]], weights: np.ndarray) -> list[np.ndarray]:
    w = weights.astype(np.float64)
    w = w / max(w.sum(), 1e-12)
    out: list[np.ndarray] = []
    for layer_vals in zip(*client_params):
        acc = np.zeros_like(layer_vals[0], dtype=np.float64)
        for i, val in enumerate(layer_vals):
            acc += w[i] * val.astype(np.float64)
        out.append(acc.astype(layer_vals[0].dtype))
    return out


def aggregate_median(client_params: list[list[np.ndarray]]) -> list[np.ndarray]:
    out: list[np.ndarray] = []
    for layer_vals in zip(*client_params):
        stack = np.stack(layer_vals, axis=0)
        out.append(np.median(stack, axis=0).astype(layer_vals[0].dtype))
    return out


def aggregate_trimmed_mean(client_params: list[list[np.ndarray]], trim_ratio: float) -> list[np.ndarray]:
    n = len(client_params)
    if n <= 2:
        return aggregate_median(client_params)

    k = int(math.floor(trim_ratio * n))
    if 2 * k >= n:
        k = max(0, (n - 1) // 2)

    out: list[np.ndarray] = []
    for layer_vals in zip(*client_params):
        stack = np.stack(layer_vals, axis=0).astype(np.float64)
        sorted_stack = np.sort(stack, axis=0)
        if k > 0:
            trimmed = sorted_stack[k:n - k]
        else:
            trimmed = sorted_stack
        out.append(np.mean(trimmed, axis=0).astype(layer_vals[0].dtype))
    return out


def unflatten_params(flat: np.ndarray, template: list[np.ndarray]) -> list[np.ndarray]:
    out: list[np.ndarray] = []
    offset = 0
    for arr in template:
        size = int(arr.size)
        chunk = flat[offset:offset + size].reshape(arr.shape)
        out.append(chunk.astype(arr.dtype))
        offset += size
    return out


def pairwise_sq_dists(vectors: list[np.ndarray]) -> np.ndarray:
    n = len(vectors)
    dists = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(i + 1, n):
            diff = vectors[i] - vectors[j]
            dist = float(np.dot(diff, diff))
            dists[i, j] = dist
            dists[j, i] = dist
    return dists


def krum_order(vectors: list[np.ndarray], num_byzantine: int) -> tuple[np.ndarray, list[float]]:
    n = len(vectors)
    if n <= (2 * num_byzantine + 2):
        raise ValueError(
            f"Krum requires n > 2f + 2, got n={n}, f={num_byzantine}. "
            "Increase --num-clients or lower --robust-f."
        )

    dists = pairwise_sq_dists(vectors)
    neighbor_count = n - num_byzantine - 2
    scores: list[float] = []
    for i in range(n):
        row = np.delete(dists[i], i)
        nearest = np.partition(row, neighbor_count - 1)[:neighbor_count]
        scores.append(float(np.sum(nearest)))
    order = np.argsort(np.asarray(scores, dtype=np.float64))
    return order, scores


def aggregate_krum(
    client_params: list[list[np.ndarray]],
    client_examples: list[int],
    num_byzantine: int,
    multi: bool,
    multi_select: int,
) -> tuple[list[np.ndarray], list[float], list[int]]:
    vectors = [flatten_params(params).astype(np.float64) for params in client_params]
    order, scores = krum_order(vectors, num_byzantine)

    if not multi:
        winner = int(order[0])
        return client_params[winner], scores, [winner]

    n = len(client_params)
    max_select = max(1, n - num_byzantine - 2)
    select = int(multi_select) if multi_select > 0 else max_select
    select = min(max_select, max(1, select))
    chosen = [int(i) for i in order[:select]]
    chosen_params = [client_params[i] for i in chosen]
    chosen_weights = np.array([client_examples[i] for i in chosen], dtype=np.float64)
    agg = aggregate_weighted(chosen_params, chosen_weights)
    return agg, scores, chosen


def aggregate_bulyan(
    client_params: list[list[np.ndarray]],
    num_byzantine: int,
) -> tuple[list[np.ndarray], list[int]]:
    n = len(client_params)
    if n < (4 * num_byzantine + 3):
        raise ValueError(
            f"Bulyan requires n >= 4f + 3, got n={n}, f={num_byzantine}. "
            "Use more clients or lower --robust-f."
        )

    target_size = n - 2 * num_byzantine
    vectors = [flatten_params(params).astype(np.float64) for params in client_params]
    order, _ = krum_order(vectors, num_byzantine)
    selected = [int(i) for i in order[:target_size]]
    chosen_stack = np.stack([vectors[i] for i in selected], axis=0)
    coord_median = np.median(chosen_stack, axis=0)
    beta = chosen_stack.shape[0] - 2 * num_byzantine
    if beta <= 0:
        raise ValueError("Bulyan candidate set too small after trimming.")

    deviations = np.abs(chosen_stack - coord_median)
    closest_idx = np.argsort(deviations, axis=0)[:beta]
    closest_vals = np.take_along_axis(chosen_stack, closest_idx, axis=0)
    flat = np.mean(closest_vals, axis=0)
    return unflatten_params(flat, client_params[0]), selected


def aggregate_rfa(
    client_params: list[list[np.ndarray]],
    client_examples: list[int],
    max_iters: int,
    tol: float,
) -> list[np.ndarray]:
    vectors = [flatten_params(params).astype(np.float64) for params in client_params]
    pts = np.stack(vectors, axis=0)
    weights = np.array(client_examples, dtype=np.float64)
    weights = weights / max(float(weights.sum()), 1e-12)

    estimate = np.sum(pts * weights[:, None], axis=0)
    eps = 1e-12
    for _ in range(max(1, int(max_iters))):
        dists = np.linalg.norm(pts - estimate[None, :], axis=1).clip(min=eps)
        reweighted = weights / dists
        new_estimate = np.sum(pts * reweighted[:, None], axis=0) / max(float(reweighted.sum()), eps)
        if np.linalg.norm(new_estimate - estimate) <= float(tol) * max(1.0, np.linalg.norm(estimate)):
            estimate = new_estimate
            break
        estimate = new_estimate

    return unflatten_params(estimate, client_params[0])


def shapley_proxy_scores(
    client_params: list[list[np.ndarray]],
    prev_global: list[np.ndarray],
    client_metrics: list[dict[str, Any]],
) -> tuple[np.ndarray, list[float], list[int]]:
    updates = [flatten_params([c - g for c, g in zip(cp, prev_global)]) for cp in client_params]
    update_stack = np.stack(updates, axis=0)
    ref = np.median(update_stack, axis=0)
    ref_norm = float(np.linalg.norm(ref) + 1e-12)

    raw_scores: list[float] = []
    for i, upd in enumerate(updates):
        upd_norm = float(np.linalg.norm(upd) + 1e-12)
        cos = float(np.dot(upd, ref) / (upd_norm * ref_norm))
        dist = float(np.linalg.norm(upd - ref) / ref_norm)
        f1 = float(client_metrics[i].get("train_f1", 0.5))
        score = max(cos, 0.0) * math.exp(-dist) * max(0.05, f1)
        raw_scores.append(score)

    score_arr = np.array(raw_scores, dtype=np.float64)
    if np.all(score_arr <= 1e-12):
        weights = np.ones_like(score_arr) / len(score_arr)
        return weights, raw_scores, []

    threshold = float(np.median(score_arr) * 0.3)
    isolated = [i for i, s in enumerate(score_arr) if s < threshold]
    score_arr = np.where(score_arr >= threshold, score_arr, 0.0)

    if float(score_arr.sum()) <= 1e-12:
        weights = np.ones_like(score_arr) / len(score_arr)
    else:
        weights = score_arr / score_arr.sum()

    return weights, raw_scores, isolated


class RobustFedStrategy(FedAvg):
    def __init__(
        self,
        aggregation_method: str,
        trim_ratio: float,
        robust_f: int,
        multi_krum_select: int,
        rfa_iters: int,
        rfa_tol: float,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.aggregation_method = aggregation_method
        self.trim_ratio = trim_ratio
        self.robust_f = max(0, int(robust_f))
        self.multi_krum_select = int(multi_krum_select)
        self.rfa_iters = int(rfa_iters)
        self.rfa_tol = float(rfa_tol)
        self.latest_parameters_ndarrays: list[np.ndarray] | None = None
        self.round_debug: list[dict[str, Any]] = []

        init_params = kwargs.get("initial_parameters")
        if init_params is not None:
            self.latest_parameters_ndarrays = parameters_to_ndarrays(init_params)

    def aggregate_fit(self, server_round, results, failures):  # type: ignore[override]
        if not results:
            return None

        client_params: list[list[np.ndarray]] = []
        client_examples: list[int] = []
        client_metrics: list[dict[str, Any]] = []

        for _, fit_res in results:
            client_params.append(parameters_to_ndarrays(fit_res.parameters))
            client_examples.append(int(fit_res.num_examples))
            client_metrics.append(dict(fit_res.metrics) if fit_res.metrics else {})

        method = self.aggregation_method
        round_info: dict[str, Any] = {
            "round": int(server_round),
            "method": method,
            "num_clients": len(client_params),
            "robust_f": int(self.robust_f),
        }

        if method == "fedavg":
            weights = np.array(client_examples, dtype=np.float64)
            agg = aggregate_weighted(client_params, weights)
            round_info["weights"] = (weights / max(weights.sum(), 1e-12)).tolist()
        elif method == "median":
            agg = aggregate_median(client_params)
        elif method == "trimmed_mean":
            agg = aggregate_trimmed_mean(client_params, self.trim_ratio)
            round_info["trim_ratio"] = float(self.trim_ratio)
        elif method == "shapley_proxy":
            prev = self.latest_parameters_ndarrays or client_params[0]
            weights, raw_scores, isolated = shapley_proxy_scores(client_params, prev, client_metrics)
            agg = aggregate_weighted(client_params, weights)
            round_info["shapley_scores"] = raw_scores
            round_info["weights"] = weights.tolist()
            round_info["isolated_client_indices"] = isolated
        elif method == "krum":
            agg, scores, selected = aggregate_krum(
                client_params,
                client_examples=client_examples,
                num_byzantine=self.robust_f,
                multi=False,
                multi_select=1,
            )
            round_info["krum_scores"] = scores
            round_info["selected_client_indices"] = selected
        elif method == "multi_krum":
            agg, scores, selected = aggregate_krum(
                client_params,
                client_examples=client_examples,
                num_byzantine=self.robust_f,
                multi=True,
                multi_select=self.multi_krum_select,
            )
            round_info["krum_scores"] = scores
            round_info["selected_client_indices"] = selected
        elif method == "bulyan":
            agg, selected = aggregate_bulyan(client_params, num_byzantine=self.robust_f)
            round_info["selected_client_indices"] = selected
        elif method == "rfa":
            agg = aggregate_rfa(
                client_params,
                client_examples=client_examples,
                max_iters=self.rfa_iters,
                tol=self.rfa_tol,
            )
            round_info["rfa_iters"] = int(self.rfa_iters)
            round_info["rfa_tol"] = float(self.rfa_tol)
        else:
            raise ValueError(f"Unsupported aggregation method: {method}")

        self.latest_parameters_ndarrays = agg
        self.round_debug.append(round_info)

        aggregated_metrics: dict[str, float] = {}
        if self.fit_metrics_aggregation_fn is not None:
            fit_metrics = [(res.num_examples, res.metrics) for _, res in results]
            aggregated_metrics = self.fit_metrics_aggregation_fn(fit_metrics)

        return ndarrays_to_parameters(agg), aggregated_metrics


def weighted_average(metrics: list[tuple[int, dict[str, float]]]) -> dict[str, float]:
    if not metrics:
        return {}

    total_examples = sum(num_examples for num_examples, _ in metrics)
    if total_examples <= 0:
        return {}

    agg: dict[str, float] = {}
    for num_examples, m in metrics:
        for k, v in m.items():
            if isinstance(v, (int, float)):
                agg[k] = agg.get(k, 0.0) + num_examples * float(v)

    for k in list(agg.keys()):
        agg[k] /= float(total_examples)
    return agg


def make_server_eval_fn(graph_file: str, args: argparse.Namespace, device: torch.device):
    graph = torch.load(graph_file, weights_only=False).to(device)
    model = FederatedSTGNN(
        in_channels=graph.x_norm.shape[1],
        hidden_channels=args.hidden_dim,
        out_channels=2,
        heads=args.heads,
        dropout=args.dropout,
    ).to(device)

    def evaluate_fn(server_round: int, parameters_ndarrays: list[np.ndarray], config: dict[str, Any]):
        set_parameters(model, parameters_ndarrays)
        model.eval()
        with torch.no_grad():
            logits = model(graph.x_norm, graph.edge_index, graph.edge_type)

        mask = graph.temporal_test_mask
        if int(mask.sum().item()) == 0:
            mask = graph.test_mask

        if int(mask.sum().item()) == 0:
            return 0.0, {"acc": 0.0, "f1": 0.0}

        loss = F.cross_entropy(logits[mask], graph.y[mask])
        m = metrics_from_logits(logits, graph.y, mask)
        return float(loss.item()), {"acc": m["acc"], "f1": m["f1"], "recall": m["recall"]}

    return evaluate_fn


@torch.no_grad()
def evaluate_global(model: nn.Module, graph: Data, mask: torch.Tensor) -> dict[str, float]:
    if int(mask.sum().item()) == 0:
        return {"acc": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "fpr": 0.0}

    model.eval()
    logits = model(graph.x_norm, graph.edge_index, graph.edge_type)
    m = metrics_from_logits(logits, graph.y, mask)
    fpr = m["fp"] / max(m["fp"] + m["tn"], 1.0)
    return {
        "acc": m["acc"],
        "precision": m["precision"],
        "recall": m["recall"],
        "f1": m["f1"],
        "fpr": float(fpr),
    }


def print_partition_summary(graph_file: str, num_clients: int) -> None:
    graph = torch.load(graph_file, weights_only=False)
    print("\nPartition summary:")
    for cid in range(num_clients):
        local = build_partition_graph(graph, cid, num_clients)
        n_nodes = int(local.num_nodes)
        n_edges = int(local.num_edges)
        n_train = int(local.train_mask.sum().item())
        n_val = int(local.val_mask.sum().item())
        n_test = int(local.test_mask.sum().item())
        n_benign = int(((local.y == 0) & (local.window_idx >= 0)).sum().item())
        n_attack = int(((local.y == 1) & (local.window_idx >= 0)).sum().item())
        print(
            f"  client {cid}: nodes={n_nodes}, edges={n_edges}, "
            f"train/val/test={n_train}/{n_val}/{n_test}, "
            f"benign={n_benign}, attack={n_attack}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 4 Federated PI-STGNN")
    parser.add_argument("--graph-file", default=os.path.join(BASE_DIR, "st_graph.pt"))
    parser.add_argument("--model-file", default=os.path.join(BASE_DIR, "fed_pignn_model.pt"))
    parser.add_argument("--results-file", default=os.path.join(BASE_DIR, "phase4_federated_results.json"))

    parser.add_argument("--num-clients", type=int, default=3)
    parser.add_argument("--rounds", type=int, default=4)
    parser.add_argument("--local-epochs", type=int, default=3)

    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--heads", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument("--lr", type=float, default=0.003)
    parser.add_argument("--weight-decay", type=float, default=5e-4)

    parser.add_argument("--alpha-flow", type=float, default=0.05)
    parser.add_argument("--beta-latency", type=float, default=0.05)
    parser.add_argument("--capacity", type=float, default=500.0)
    parser.add_argument("--warmup-rounds", type=int, default=2)

    parser.add_argument(
        "--aggregation",
        choices=["fedavg", "median", "trimmed_mean", "shapley_proxy", "krum", "multi_krum", "bulyan", "rfa"],
        default="trimmed_mean",
    )
    parser.add_argument("--trim-ratio", type=float, default=0.2)
    parser.add_argument("--robust-f", type=int, default=-1)
    parser.add_argument("--multi-krum-select", type=int, default=0)
    parser.add_argument("--rfa-iters", type=int, default=25)
    parser.add_argument("--rfa-tol", type=float, default=1e-5)

    parser.add_argument("--simulate-poison-frac", type=float, default=0.0)
    parser.add_argument("--poison-scale", type=float, default=0.0)

    parser.add_argument("--client-cpus", type=float, default=2.0)
    parser.add_argument("--client-gpus", type=float, default=0.0)
    parser.add_argument("--force-cpu", action="store_true")
    parser.add_argument("--seed", type=int, default=42)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    device = get_device(force_cpu=args.force_cpu)

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    if not os.path.exists(args.graph_file):
        raise FileNotFoundError(f"Graph not found: {args.graph_file}")

    print("=" * 70)
    print("Phase 4: Federated Physics-Informed ST-GNN")
    print("=" * 70)
    print(f"Device: {device}")
    print(f"Graph: {args.graph_file}")
    print(f"Clients: {args.num_clients}, Rounds: {args.rounds}, Local epochs: {args.local_epochs}")
    print(f"Aggregation: {args.aggregation}")

    if args.robust_f < 0:
        args.robust_f = int(round(args.simulate_poison_frac * args.num_clients))

    print_partition_summary(args.graph_file, args.num_clients)

    template_graph = torch.load(args.graph_file, weights_only=False)
    init_model = FederatedSTGNN(
        in_channels=template_graph.x_norm.shape[1],
        hidden_channels=args.hidden_dim,
        out_channels=2,
        heads=args.heads,
        dropout=args.dropout,
    )
    initial_parameters = ndarrays_to_parameters(get_parameters(init_model))

    strategy = RobustFedStrategy(
        aggregation_method=args.aggregation,
        trim_ratio=args.trim_ratio,
        robust_f=args.robust_f,
        multi_krum_select=args.multi_krum_select,
        rfa_iters=args.rfa_iters,
        rfa_tol=args.rfa_tol,
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=args.num_clients,
        min_evaluate_clients=args.num_clients,
        min_available_clients=args.num_clients,
        initial_parameters=initial_parameters,
        evaluate_fn=make_server_eval_fn(args.graph_file, args, device),
        on_fit_config_fn=lambda r: {"local_epochs": int(args.local_epochs), "lr": float(args.lr), "server_round": int(r)},
        fit_metrics_aggregation_fn=weighted_average,
        evaluate_metrics_aggregation_fn=weighted_average,
    )

    def client_fn(context: Context):
        partition_id = int(context.node_config.get("partition-id", context.node_id)) % args.num_clients
        return EdgeGatewayClient(partition_id, args, device).to_client()

    history = fl.simulation.start_simulation(
        client_fn=client_fn,
        num_clients=args.num_clients,
        config=fl.server.ServerConfig(num_rounds=args.rounds),
        strategy=strategy,
        client_resources={"num_cpus": float(args.client_cpus), "num_gpus": float(args.client_gpus)},
        ray_init_args={"include_dashboard": False, "ignore_reinit_error": True},
    )

    final_ndarrays = strategy.latest_parameters_ndarrays
    if final_ndarrays is None:
        final_ndarrays = get_parameters(init_model)

    final_model = FederatedSTGNN(
        in_channels=template_graph.x_norm.shape[1],
        hidden_channels=args.hidden_dim,
        out_channels=2,
        heads=args.heads,
        dropout=args.dropout,
    ).to(device)
    set_parameters(final_model, final_ndarrays)

    torch.save(final_model.state_dict(), args.model_file)

    graph = template_graph.to(device)
    metrics_global = {
        "train": evaluate_global(final_model, graph, graph.train_mask),
        "val": evaluate_global(final_model, graph, graph.val_mask),
        "test_random": evaluate_global(final_model, graph, graph.test_mask),
        "test_temporal": evaluate_global(final_model, graph, graph.temporal_test_mask),
    }

    results = {
        "config": vars(args),
        "device": str(device),
        "global_metrics": metrics_global,
        "round_debug": strategy.round_debug,
        "history": {
            "losses_distributed": history.losses_distributed,
            "losses_centralized": history.losses_centralized,
            "metrics_distributed_fit": history.metrics_distributed_fit,
            "metrics_distributed": history.metrics_distributed,
            "metrics_centralized": history.metrics_centralized,
        },
    }

    with open(args.results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\nGlobal metrics:")
    for split, m in metrics_global.items():
        print(
            f"  {split:12s} acc={m['acc']:.4f} precision={m['precision']:.4f} "
            f"recall={m['recall']:.4f} f1={m['f1']:.4f} fpr={m['fpr']:.4f}"
        )

    print("\nSaved:")
    print(f"  Model  : {args.model_file}")
    print(f"  Results: {args.results_file}")


if __name__ == "__main__":
    main()
