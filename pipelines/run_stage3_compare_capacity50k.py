#!/usr/bin/env python3
from __future__ import annotations

import itertools
import json
import statistics
import subprocess
from pathlib import Path


def pval_signflip(x: list[float], y: list[float]) -> float:
    if len(x) != len(y) or not x:
        return 1.0
    d = [a - b for a, b in zip(x, y)]
    n = len(d)
    obs = abs(sum(d) / n)
    ext = 0
    tot = 0
    for bits in itertools.product([-1.0, 1.0], repeat=n):
        tot += 1
        s = abs(sum(di * si for di, si in zip(d, bits)) / n)
        if s >= obs - 1e-12:
            ext += 1
    return (ext + 1) / (tot + 1)


def run(cmd: list[str], log: Path) -> None:
    with log.open("w", encoding="utf-8") as f:
        r = subprocess.run(cmd, cwd="/home/user/FedSTGCN", stdout=f, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        raise RuntimeError("run failed")


def main() -> None:
    py = "/home/user/miniconda3/envs/DL/bin/python"
    suite = Path("/home/user/FedSTGCN/top_conf_suite_v3")
    out = Path("/home/user/FedSTGCN/stage3_cap50k")
    out.mkdir(parents=True, exist_ok=True)
    seeds = [11, 22, 33, 44, 55]
    protocols = ["temporal_ood", "topology_ood", "attack_strategy_ood"]
    runs = []

    for proto in protocols:
        g = suite / "protocol_graphs" / f"{proto}.pt"
        for model, alpha, beta in [("data_only", 0.0, 0.0), ("physics", 0.03, 0.02)]:
            for s in seeds:
                d = out / f"{proto}_{model}_s{s}"
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
                        "140",
                        "--alpha-flow",
                        str(alpha),
                        "--beta-latency",
                        str(beta),
                        "--capacity",
                        "50000",
                        "--warmup-epochs",
                        "25",
                        "--patience",
                        "35",
                        "--seed",
                        str(s),
                        "--force-cpu",
                    ],
                    d / "run.log",
                )
                res = json.loads((d / "r.json").read_text(encoding="utf-8"))
                m = res.get("final_eval", {}).get("test_temporal") or res.get("final_eval", {}).get("test_random") or {}
                runs.append({"protocol": proto, "model": model, "seed": s, "f1": float(m.get("f1", 0.0)), "recall": float(m.get("recall", 0.0))})

    print("=== Stage3 compare @capacity=50000 ===")
    for proto in protocols:
        d = [r for r in runs if r["protocol"] == proto and r["model"] == "data_only"]
        p = [r for r in runs if r["protocol"] == proto and r["model"] == "physics"]
        df1 = [x["f1"] for x in d]
        pf1 = [x["f1"] for x in p]
        dr = [x["recall"] for x in d]
        pr = [x["recall"] for x in p]
        print(proto)
        print(" data_only  F1", round(statistics.mean(df1), 4), "+-", round(statistics.stdev(df1), 4), "Recall", round(statistics.mean(dr), 4), "+-", round(statistics.stdev(dr), 4))
        print(" physics    F1", round(statistics.mean(pf1), 4), "+-", round(statistics.stdev(pf1), 4), "Recall", round(statistics.mean(pr), 4), "+-", round(statistics.stdev(pr), 4))
        print(" p(F1)=", pval_signflip(pf1, df1), "p(Recall)=", pval_signflip(pr, dr))


if __name__ == "__main__":
    main()
