#!/usr/bin/env python3
from __future__ import annotations

import itertools
import json
import statistics
import subprocess
from pathlib import Path


def pval(x: list[float], y: list[float]) -> float:
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
    g = "/home/user/FedSTGCN/top_conf_suite_v3/protocol_graphs/topology_ood.pt"
    out = Path("/home/user/FedSTGCN/topology9")
    out.mkdir(parents=True, exist_ok=True)
    seeds = [11, 22, 33, 44, 55, 66, 77, 88, 99, 101, 111, 121, 131, 141, 151, 161, 171, 181, 191, 201, 211]
    results = {"data": [], "physics": []}
    for model, alpha, beta in [("data", 0.0, 0.0), ("physics", 0.03, 0.02)]:
        for s in seeds:
            d = out / f"{model}_s{s}"
            d.mkdir(parents=True, exist_ok=True)
            run(
                [
                    py,
                    "pi_gnn_train_v2.py",
                    "--graph-file",
                    g,
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
            j = json.loads((d / "r.json").read_text(encoding="utf-8"))
            m = j.get("final_eval", {}).get("test_temporal") or j.get("final_eval", {}).get("test_random") or {}
            results[model].append({"f1": float(m.get("f1", 0.0)), "recall": float(m.get("recall", 0.0))})

    df1 = [x["f1"] for x in results["data"]]
    pf1 = [x["f1"] for x in results["physics"]]
    dr = [x["recall"] for x in results["data"]]
    pr = [x["recall"] for x in results["physics"]]
    print("data F1", round(statistics.mean(df1), 4), "+-", round(statistics.stdev(df1), 4), "Recall", round(statistics.mean(dr), 4), "+-", round(statistics.stdev(dr), 4))
    print("phys F1", round(statistics.mean(pf1), 4), "+-", round(statistics.stdev(pf1), 4), "Recall", round(statistics.mean(pr), 4), "+-", round(statistics.stdev(pr), 4))
    print("p(F1)", pval(pf1, df1))
    print("p(Recall)", pval(pr, dr))


if __name__ == "__main__":
    main()
