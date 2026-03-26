#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
    p = argparse.ArgumentParser()
    p.add_argument("--python-bin", default="/home/user/miniconda3/envs/DL/bin/python")
    p.add_argument("--suite-dir", default="/home/user/FedSTGCN/top_conf_suite_final")
    p.add_argument("--seeds", default="11,22,33,44,55")
    p.add_argument("--aggregations", default="fedavg,median,shapley_proxy")
    p.add_argument("--robust-f", type=int, default=-1)
    args = p.parse_args()

    py = args.python_bin
    suite = Path(args.suite_dir)
    out = suite / "fed_cross_protocol"
    out.mkdir(parents=True, exist_ok=True)

    protocols = ["temporal_ood", "topology_ood", "attack_strategy_ood"]
    seeds = [int(x.strip()) for x in str(args.seeds).split(",") if x.strip()]
    aggs = [x.strip() for x in str(args.aggregations).split(",") if x.strip()]

    runs = []
    for proto in protocols:
        graph = suite / "protocol_graphs" / f"{proto}.pt"
        for agg in aggs:
            for seed in seeds:
                d = out / f"{proto}_{agg}_s{seed}"
                d.mkdir(parents=True, exist_ok=True)
                run(
                    [
                        py,
                        "fed_pignn.py",
                        "--graph-file",
                        str(graph),
                        "--model-file",
                        str(d / "model.pt"),
                        "--results-file",
                        str(d / "results.json"),
                        "--num-clients",
                        "3",
                        "--rounds",
                        "4",
                        "--local-epochs",
                        "2",
                        "--aggregation",
                        agg,
                        "--simulate-poison-frac",
                        "0.4",
                        "--poison-scale",
                        "0.4",
                        "--alpha-flow",
                        "0.01",
                        "--beta-latency",
                        "0.01",
                        "--capacity",
                        "120000",
                        "--warmup-rounds",
                        "2",
                        "--seed",
                        str(seed),
                        "--client-cpus",
                        "2.0",
                        "--client-gpus",
                        "0.0",
                        "--force-cpu",
                        *([] if args.robust_f < 0 else ["--robust-f", str(args.robust_f)]),
                    ],
                    d / "run.log",
                )
                j = json.loads((d / "results.json").read_text(encoding="utf-8"))
                m = j.get("global_metrics", {}).get("test_temporal") or j.get("global_metrics", {}).get("test_random") or {}
                runs.append(
                    {
                        "protocol": proto,
                        "aggregation": agg,
                        "seed": seed,
                        "f1": float(m.get("f1", 0.0)),
                        "recall": float(m.get("recall", 0.0)),
                        "fpr": float(m.get("fpr", 0.0)),
                    }
                )

    summary: dict[str, object] = {"runs": runs, "stats": {}, "p_values": {}}
    for proto in protocols:
        summary["stats"][proto] = {}
        for agg in aggs:
            rs = [r for r in runs if r["protocol"] == proto and r["aggregation"] == agg]
            f1 = [r["f1"] for r in rs]
            rc = [r["recall"] for r in rs]
            fp = [r["fpr"] for r in rs]
            summary["stats"][proto][agg] = {
                "f1_mean": statistics.mean(f1),
                "f1_std": statistics.stdev(f1),
                "recall_mean": statistics.mean(rc),
                "recall_std": statistics.stdev(rc),
                "fpr_mean": statistics.mean(fp),
                "fpr_std": statistics.stdev(fp),
            }

        fedavg = [r["f1"] for r in runs if r["protocol"] == proto and r["aggregation"] == "fedavg"]
        for agg in aggs:
            if agg == "fedavg":
                continue
            vals = [r["f1"] for r in runs if r["protocol"] == proto and r["aggregation"] == agg]
            if fedavg and vals:
                pval = pval_signflip(vals, fedavg)
                summary["p_values"][f"{proto}_{agg}_vs_fedavg_f1"] = pval
                if agg == "shapley_proxy":
                    summary["p_values"][f"{proto}_shapley_vs_fedavg_f1"] = pval

    # pooled across all protocols and seeds
    pooled_fedavg = [r["f1"] for r in runs if r["aggregation"] == "fedavg"]
    for agg in aggs:
        if agg == "fedavg":
            continue
        pooled_vals = [r["f1"] for r in runs if r["aggregation"] == agg]
        if pooled_fedavg and pooled_vals:
            pval = pval_signflip(pooled_vals, pooled_fedavg)
            summary["p_values"][f"pooled_{agg}_vs_fedavg_f1"] = pval
            if agg == "shapley_proxy":
                summary["p_values"]["pooled_shapley_vs_fedavg_f1"] = pval
            if agg == "median":
                summary["p_values"]["pooled_median_vs_fedavg_f1"] = pval

    out_file = out / "fed_cross_protocol_summary.json"
    out_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[DONE] {out_file}")
    if "pooled_shapley_vs_fedavg_f1" in summary["p_values"]:
        print("pooled p(shapley_vs_fedavg)=", summary["p_values"]["pooled_shapley_vs_fedavg_f1"])


if __name__ == "__main__":
    main()
