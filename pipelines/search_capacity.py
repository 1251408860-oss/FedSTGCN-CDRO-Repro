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
        raise RuntimeError("command failed")


def main() -> None:
    py = "/home/user/miniconda3/envs/DL/bin/python"
    graph = "/home/user/FedSTGCN/top_conf_suite_v3/protocol_graphs/attack_strategy_ood.pt"
    out = Path("/home/user/FedSTGCN/cap_search")
    out.mkdir(parents=True, exist_ok=True)
    seeds = [11, 22, 33]
    capacities = [500, 1000, 5000, 10000, 30000, 50000, 70000, 90000, 120000]
    alpha, beta = 0.03, 0.02

    print("capacity search on attack_strategy_ood clean")
    for cap in capacities:
        f1s = []
        recs = []
        for s in seeds:
            d = out / f"cap{cap}_s{s}"
            d.mkdir(parents=True, exist_ok=True)
            run(
                [
                    py,
                    "training/pi_gnn_train_v2.py",
                    "--graph-file",
                    graph,
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
            data = json.loads((d / "r.json").read_text(encoding="utf-8"))
            m = data.get("final_eval", {}).get("test_temporal") or data.get("final_eval", {}).get("test_random") or {}
            f1s.append(float(m.get("f1", 0.0)))
            recs.append(float(m.get("recall", 0.0)))
        print(
            "cap", cap,
            "F1", round(statistics.mean(f1s), 4), "+-", round(statistics.stdev(f1s), 4),
            "Recall", round(statistics.mean(recs), 4), "+-", round(statistics.stdev(recs), 4),
        )


if __name__ == "__main__":
    main()
