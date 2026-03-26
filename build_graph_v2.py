#!/usr/bin/env python3
"""
Phase 2: Cross-Flow Spatiotemporal Heterogeneous Graph Construction

Input:  full_arena_v2.pcap
Output: st_graph.pt

Per-window flow node features (7D):
  [ln(N+1), ln(T+1), entropy, D_observed, pkt_rate, avg_pkt_size, port_diversity]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter, defaultdict
from typing import Any

import torch

try:
    from torch_geometric.data import Data
except ImportError:
    print("ERROR: torch_geometric required")
    sys.exit(1)

try:
    from scapy.all import IP, TCP, Raw, rdpcap
except ImportError:
    print("ERROR: scapy required")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PCAP_FILE = os.path.join(BASE_DIR, "full_arena_v2.pcap")
OUTPUT_FILE = os.path.join(BASE_DIR, "st_graph.pt")
MANIFEST_FILE = os.path.join(BASE_DIR, "arena_manifest_v2.json")

DELTA_T = 1.0
TARGET_IP = "10.0.0.100"

FEATURE_NAMES = [
    "ln(N+1)",
    "ln(T+1)",
    "entropy",
    "D_observed",
    "pkt_rate",
    "avg_pkt_size",
    "port_diversity",
]
FEATURE_INDEX = {name: i for i, name in enumerate(FEATURE_NAMES)}


def shannon_entropy(data_bytes: bytes) -> float:
    if not data_bytes:
        return 0.0
    counts = Counter(data_bytes)
    n = len(data_bytes)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def classify_ip_fallback(ip: str) -> int:
    last = int(ip.split(".")[-1])
    # Legacy captures used 10.0.0.30-99 for bots; repaired captures start bots at 10.0.0.110+.
    if 30 <= last <= 99 or 110 <= last <= 254:
        return 1
    return 0


def load_ip_labels() -> dict[str, int]:
    labels: dict[str, int] = {}
    if not os.path.exists(MANIFEST_FILE):
        return labels

    try:
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        ip_labels = data.get("ip_labels", {}) if isinstance(data, dict) else {}
        if isinstance(ip_labels, dict):
            for ip, v in ip_labels.items():
                try:
                    labels[str(ip)] = int(v)
                except Exception:
                    continue
    except Exception as exc:
        print(f"[WARN] failed to read manifest labels: {exc}")

    return labels


def label_ip(ip: str, manifest_labels: dict[str, int]) -> int:
    if ip in manifest_labels:
        return int(manifest_labels[ip])
    return classify_ip_fallback(ip)


def extract_window_features(pkts: list[Any]) -> list[float]:
    if not pkts:
        return [0.0] * len(FEATURE_NAMES)

    n_packets = len(pkts)
    total_bytes = sum(len(p) for p in pkts)

    ts = sorted(float(p.time) for p in pkts)
    duration = max(ts[-1] - ts[0], 0.0) if len(ts) > 1 else 0.0

    payload = b""
    for p in pkts:
        if Raw in p:
            payload += bytes(p[Raw].load)
    entropy = shannon_entropy(payload)

    if len(ts) > 1:
        iats = [ts[i + 1] - ts[i] for i in range(len(ts) - 1)]
        d_observed = sum(iats) / len(iats)
    else:
        d_observed = 0.0

    pkt_rate = n_packets / max(duration, 0.001)
    avg_pkt_size = total_bytes / n_packets

    src_ports = set()
    for p in pkts:
        if TCP in p:
            src_ports.add(int(p[TCP].sport))
    port_diversity = len(src_ports) / n_packets

    return [
        math.log(total_bytes + 1.0),
        math.log(duration + 1.0),
        entropy,
        d_observed,
        pkt_rate,
        avg_pkt_size / 1000.0,
        port_diversity,
    ]


def build_spatiotemporal_graph() -> None:
    print("=" * 68)
    print("Phase 2: Build Graph from PCAP")
    print("=" * 68)

    if not os.path.exists(PCAP_FILE):
        raise FileNotFoundError(f"PCAP not found: {PCAP_FILE}")

    print(f"[1/5] Load PCAP: {PCAP_FILE}")
    packets = rdpcap(PCAP_FILE)
    print(f"  packets={len(packets)}")

    inbound = []
    for p in packets:
        if IP in p and TCP in p and p[IP].dst == TARGET_IP and p[IP].src != TARGET_IP:
            inbound.append(p)

    if not inbound:
        raise RuntimeError("No inbound TCP packets to target found")

    times = [float(p.time) for p in inbound]
    t_start = min(times)
    t_end = max(times)
    duration = max(t_end - t_start, 0.0)
    n_windows = max(1, int(math.ceil(duration / DELTA_T)))

    print(f"[2/5] Inbound packets={len(inbound)} duration={duration:.1f}s windows={n_windows}")

    window_packets: dict[tuple[str, int], list[Any]] = defaultdict(list)
    target_window_packets: dict[int, list[Any]] = defaultdict(list)

    for p in inbound:
        src = p[IP].src
        w = min(int((float(p.time) - t_start) / DELTA_T), n_windows - 1)
        window_packets[(src, w)].append(p)
        target_window_packets[w].append(p)

    source_ips = sorted({ip for ip, _ in window_packets.keys()})
    print(f"  source_ips={len(source_ips)}")

    manifest_labels = load_ip_labels()
    if manifest_labels:
        print(f"  labels=manifest ({len(manifest_labels)} entries)")
    else:
        print("  labels=fallback(ip range)")

    print("[3/5] Build nodes and edges")
    node_features: list[list[float]] = []
    node_labels: list[int] = []
    node_window_idx: list[int] = []
    node_ip_idx: list[int] = []

    spatial_src: list[int] = []
    spatial_dst: list[int] = []
    temporal_src: list[int] = []
    temporal_dst: list[int] = []

    all_target_pkts = [p for v in target_window_packets.values() for p in v]
    node_features.append(extract_window_features(all_target_pkts))
    node_labels.append(0)
    node_window_idx.append(-1)
    node_ip_idx.append(-1)

    flow_node_map: dict[tuple[str, int], int] = {}
    active_per_window: dict[int, int] = defaultdict(int)

    for w in range(n_windows):
        for ip_i, src_ip in enumerate(source_ips):
            pkts = window_packets.get((src_ip, w))
            if not pkts:
                continue

            node_id = len(node_features)
            flow_node_map[(src_ip, w)] = node_id

            node_features.append(extract_window_features(pkts))
            node_labels.append(label_ip(src_ip, manifest_labels))
            node_window_idx.append(w)
            node_ip_idx.append(ip_i)
            active_per_window[w] += 1

            spatial_src.append(node_id)
            spatial_dst.append(0)

            prev = flow_node_map.get((src_ip, w - 1))
            if prev is not None:
                temporal_src.append(prev)
                temporal_dst.append(node_id)

    n_nodes = len(node_features)
    n_spatial = len(spatial_src)
    n_temporal = len(temporal_src)

    print(f"  nodes={n_nodes} flow_nodes={n_nodes - 1} edges={n_spatial + n_temporal}")

    print("[4/5] Assemble tensors")
    all_src = spatial_src + temporal_src
    all_dst = spatial_dst + temporal_dst
    edge_type = [0] * n_spatial + [1] * n_temporal

    x = torch.tensor(node_features, dtype=torch.float)
    y = torch.tensor(node_labels, dtype=torch.long)
    edge_index = torch.tensor([all_src, all_dst], dtype=torch.long)
    edge_type_t = torch.tensor(edge_type, dtype=torch.long)

    window_idx = torch.tensor(node_window_idx, dtype=torch.long)
    ip_idx = torch.tensor(node_ip_idx, dtype=torch.long)

    bi_src = all_src + all_dst
    bi_dst = all_dst + all_src
    bi_type = edge_type + edge_type

    flow_mask = torch.arange(n_nodes) > 0
    x_flow = x[flow_mask]
    feat_mean = x_flow.mean(dim=0)
    feat_std = x_flow.std(dim=0).clamp(min=1e-6)
    x_norm = (x - feat_mean) / feat_std
    x_norm[0] = 0.0

    n_flow = n_nodes - 1
    perm = torch.randperm(n_flow) + 1
    n_train = int(0.70 * n_flow)
    n_val = int(0.15 * n_flow)

    train_mask = torch.zeros(n_nodes, dtype=torch.bool)
    val_mask = torch.zeros(n_nodes, dtype=torch.bool)
    test_mask = torch.zeros(n_nodes, dtype=torch.bool)
    train_mask[perm[:n_train]] = True
    val_mask[perm[n_train:n_train + n_val]] = True
    test_mask[perm[n_train + n_val:]] = True

    temporal_train = torch.zeros(n_nodes, dtype=torch.bool)
    temporal_test = torch.zeros(n_nodes, dtype=torch.bool)
    cutoff = int(0.7 * n_windows)
    for i, w in enumerate(node_window_idx):
        if w < 0:
            continue
        if w < cutoff:
            temporal_train[i] = True
        else:
            temporal_test[i] = True

    graph = Data(
        x=x,
        x_norm=x_norm,
        y=y,
        edge_index=edge_index,
        edge_type=edge_type_t,
        edge_index_undirected=torch.tensor([bi_src, bi_dst], dtype=torch.long),
        edge_type_undirected=torch.tensor(bi_type, dtype=torch.long),
        window_idx=window_idx,
        ip_idx=ip_idx,
        train_mask=train_mask,
        val_mask=val_mask,
        test_mask=test_mask,
        temporal_train_mask=temporal_train,
        temporal_test_mask=temporal_test,
        feat_mean=feat_mean,
        feat_std=feat_std,
    )

    graph.source_ips = source_ips
    graph.target_ip = TARGET_IP
    graph.delta_t = DELTA_T
    graph.n_windows = n_windows
    graph.feature_names = FEATURE_NAMES
    graph.feature_index = FEATURE_INDEX
    graph.label_source = "manifest" if manifest_labels else "fallback_ip_range"

    print(f"[5/5] Save: {OUTPUT_FILE}")
    torch.save(graph, OUTPUT_FILE)

    benign = int(((y == 0) & flow_mask).sum().item())
    attack = int(((y == 1) & flow_mask).sum().item())

    print("=" * 68)
    print(f"Done: nodes={graph.num_nodes} edges={graph.num_edges} windows={n_windows}")
    print(f"Flow labels: benign={benign} attack={attack}")
    print(f"Features ({len(FEATURE_NAMES)}D): {FEATURE_NAMES}")
    print(f"feature_index={FEATURE_INDEX}")
    print(f"label_source={graph.label_source}")
    print("=" * 68)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build spatiotemporal graph from PCAP")
    parser.add_argument("--pcap-file", default=PCAP_FILE)
    parser.add_argument("--output-file", default=OUTPUT_FILE)
    parser.add_argument("--manifest-file", default=MANIFEST_FILE)
    parser.add_argument("--delta-t", type=float, default=DELTA_T)
    parser.add_argument("--target-ip", default=TARGET_IP)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    global PCAP_FILE, OUTPUT_FILE, MANIFEST_FILE, DELTA_T, TARGET_IP
    args = parse_args()
    PCAP_FILE = os.path.abspath(os.path.expanduser(args.pcap_file))
    OUTPUT_FILE = os.path.abspath(os.path.expanduser(args.output_file))
    MANIFEST_FILE = os.path.abspath(os.path.expanduser(args.manifest_file))
    DELTA_T = float(args.delta_t)
    TARGET_IP = str(args.target_ip)

    torch.manual_seed(int(args.seed))
    build_spatiotemporal_graph()


if __name__ == "__main__":
    main()
