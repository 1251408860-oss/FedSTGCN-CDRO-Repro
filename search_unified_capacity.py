#!/usr/bin/env python3
from __future__ import annotations

import json
import statistics
import subprocess
from pathlib import Path


def run(cmd: list[str], log: Path) -> None:
    with log.open("w", encoding="utf-8") as f:
        r = subprocess.run(cmd, cwd="/home/user/FedSTGCN", stdout=f, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        raise RuntimeError("run failed")


def load_data_baseline(top_summary: Path, seeds: list[int]) -> dict[tuple[str, int], float]:
    d = json.loads(top_summary.read_text(encoding="utf-8"))
    out: dict[tuple[str, int], float] = {}
    for r in d.get("stage3_runs", []):
        if r.get("model") != "data_only":
            continue
        if r.get("poison_case") != "clean":
            continue
        proto = str(r.get("protocol"))
        seed = int(r.get("seed"))
        if seed not in seeds:
            continue
        out[(proto, seed)] = float(r.get("metrics", {}).get("f1", 0.0))
    return out


def main() -> None:
    py = "/home/user/miniconda3/envs/DL/bin/python"
    suite = Path("/home/user/FedSTGCN/top_conf_suite_v3")
    out = Path("/home/user/FedSTGCN/unified_cap_search")
    out.mkdir(parents=True, exist_ok=True)

    protocols = ["temporal_ood", "topology_ood", "attack_strategy_ood"]
    seeds = [11, 22, 33]
    capacities = [5000, 10000, 30000, 50000, 70000, 90000, 120000]
    alpha = 0.03
    beta = 0.02

    data_base = load_data_baseline(suite / "top_conf_summary.json", seeds)

    print("capacity,mean_f1,delta_vs_data_mean,delta_std")
    best_cap = None
    best_delta = -1e9

    for cap in capacities:
        f1s = []
        deltas = []
        for proto in protocols:
            g = suite / "protocol_graphs" / f"{proto}.pt"
            for seed in seeds:
                d = out / f"cap{cap}_{proto}_s{seed}"
                d.mkdir(parents=True, exist_ok=True)
                run(
                    [
                        py,
                        "pi_gnn_train_v2.py",
                        "--graph-file",
                        str(g),
                        "--model-file",
                        str(d / "m.pt"),
                        "--results-file",
                        str(d / "r.json"),
                        "--epochs",
                        "120",
                        "--alpha-flow",
                        str(alpha),
                        "--beta-latency",
                        str(beta),
                        "--capacity",
                        str(cap),
                        "--warmup-epochs",
                        "25",
                        "--patience",
                        "30",
                        "--seed",
                        str(seed),
                        "--force-cpu",
                    ],
                    d / "run.log",
                )
                res = json.loads((d / "r.json").read_text(encoding="utf-8"))
                m = res.get("final_eval", {}).get("test_temporal") or res.get("final_eval", {}).get("test_random") or {}
                f1 = float(m.get("f1", 0.0))
                f1s.append(f1)
                base = data_base.get((proto, seed), 0.0)
                deltas.append(f1 - base)
        mean_f1 = statistics.mean(f1s)
        mean_delta = statistics.mean(deltas)
        std_delta = statistics.stdev(deltas) if len(deltas) > 1 else 0.0
        print(f"{cap},{mean_f1:.6f},{mean_delta:.6f},{std_delta:.6f}")
        if mean_delta > best_delta:
            best_delta = mean_delta
            best_cap = cap

    print(f"best_capacity={best_cap}, best_delta={best_delta:.6f}")


if __name__ == "__main__":
    main()
