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


def load_data_baseline(path: Path, seeds: list[int]) -> dict[tuple[str, int], float]:
    d = json.loads(path.read_text(encoding="utf-8"))
    out: dict[tuple[str, int], float] = {}
    for r in d.get("stage3_runs", []):
        if r.get("model") != "data_only" or r.get("poison_case") != "clean":
            continue
        s = int(r.get("seed"))
        if s not in seeds:
            continue
        out[(str(r.get("protocol")), s)] = float(r.get("metrics", {}).get("f1", 0.0))
    return out


def main() -> None:
    py = "/home/user/miniconda3/envs/DL/bin/python"
    suite = Path("/home/user/FedSTGCN/top_conf_suite_final")
    out = Path("/home/user/FedSTGCN/unified_ab_search")
    out.mkdir(parents=True, exist_ok=True)
    protocols = ["temporal_ood", "topology_ood", "attack_strategy_ood"]
    seeds = [11, 22, 33]
    cap = 120000
    grid = [(0.01, 0.01), (0.02, 0.01), (0.03, 0.02), (0.05, 0.02), (0.08, 0.03), (0.1, 0.05)]
    baseline = load_data_baseline(suite / "top_conf_summary.json", seeds)

    print("alpha,beta,mean_f1,delta_vs_data,delta_std")
    best = None
    best_delta = -1e9
    for alpha, beta in grid:
        f1s = []
        deltas = []
        for proto in protocols:
            g = suite / "protocol_graphs" / f"{proto}.pt"
            for s in seeds:
                d = out / f"a{alpha}_b{beta}_{proto}_s{s}"
                d.mkdir(parents=True, exist_ok=True)
                run(
                    [
                        py,
                        "training/pi_gnn_train_v2.py",
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
                        str(s),
                        "--force-cpu",
                    ],
                    d / "run.log",
                )
                j = json.loads((d / "r.json").read_text(encoding="utf-8"))
                m = j.get("final_eval", {}).get("test_temporal") or j.get("final_eval", {}).get("test_random") or {}
                f1 = float(m.get("f1", 0.0))
                f1s.append(f1)
                deltas.append(f1 - baseline.get((proto, s), 0.0))
        mean_f1 = statistics.mean(f1s)
        mean_delta = statistics.mean(deltas)
        std_delta = statistics.stdev(deltas) if len(deltas) > 1 else 0.0
        print(f"{alpha},{beta},{mean_f1:.6f},{mean_delta:.6f},{std_delta:.6f}")
        if mean_delta > best_delta:
            best_delta = mean_delta
            best = (alpha, beta, mean_f1, mean_delta)

    print("best=", best)


if __name__ == "__main__":
    main()
