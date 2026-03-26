#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
import statistics
import subprocess
import time
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


def mean_std(vals: list[float]) -> dict[str, float]:
    if not vals:
        return {"n": 0, "mean": 0.0, "std": 0.0}
    if len(vals) == 1:
        return {"n": 1, "mean": float(vals[0]), "std": 0.0}
    return {"n": len(vals), "mean": float(statistics.mean(vals)), "std": float(statistics.stdev(vals))}


def run(cmd: list[str], log: Path) -> float:
    t0 = time.time()
    with log.open("w", encoding="utf-8") as fh:
        proc = subprocess.run(cmd, cwd="/home/user/FedSTGCN", stdout=fh, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}")
    return float(time.time() - t0)


def main() -> None:
    ap = argparse.ArgumentParser(description="Supplemental classic robust-FL baseline suite.")
    ap.add_argument("--python-bin", default="/home/user/miniconda3/envs/DL/bin/python")
    ap.add_argument("--suite-dir", default="/home/user/FedSTGCN/top_conf_suite_recharge")
    ap.add_argument("--protocols", default="temporal_ood,topology_ood,attack_strategy_ood")
    ap.add_argument("--aggregations", default="fedavg,median,trimmed_mean,rfa,krum,multi_krum,bulyan,shapley_proxy")
    ap.add_argument("--seeds", default="11,22,33")
    ap.add_argument("--num-clients", type=int, default=11)
    ap.add_argument("--robust-f", type=int, default=2)
    ap.add_argument("--poison-frac", type=float, default=0.1818181818)
    ap.add_argument("--poison-scale", type=float, default=0.4)
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--local-epochs", type=int, default=2)
    ap.add_argument("--client-cpus", type=float, default=2.0)
    ap.add_argument("--client-gpus", type=float, default=0.0)
    args = ap.parse_args()

    py = args.python_bin
    suite = Path(args.suite_dir)
    out = suite / "fed_classic_robust_baselines"
    out.mkdir(parents=True, exist_ok=True)

    protocols = [x.strip() for x in str(args.protocols).split(",") if x.strip()]
    aggs = [x.strip() for x in str(args.aggregations).split(",") if x.strip()]
    seeds = [int(x.strip()) for x in str(args.seeds).split(",") if x.strip()]

    runs = []
    for proto in protocols:
        graph = suite / "protocol_graphs" / f"{proto}.pt"
        for agg in aggs:
            for seed in seeds:
                run_dir = out / f"{proto}_{agg}_s{seed}"
                run_dir.mkdir(parents=True, exist_ok=True)
                duration = run(
                    [
                        py,
                        "fed_pignn.py",
                        "--graph-file",
                        str(graph),
                        "--model-file",
                        str(run_dir / "model.pt"),
                        "--results-file",
                        str(run_dir / "results.json"),
                        "--num-clients",
                        str(args.num_clients),
                        "--rounds",
                        str(args.rounds),
                        "--local-epochs",
                        str(args.local_epochs),
                        "--aggregation",
                        agg,
                        "--simulate-poison-frac",
                        str(args.poison_frac),
                        "--poison-scale",
                        str(args.poison_scale),
                        "--robust-f",
                        str(args.robust_f),
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
                        str(args.client_cpus),
                        "--client-gpus",
                        str(args.client_gpus),
                        "--force-cpu",
                    ],
                    run_dir / "run.log",
                )
                result = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
                metrics = result.get("global_metrics", {}).get("test_temporal") or result.get("global_metrics", {}).get("test_random") or {}
                runs.append(
                    {
                        "protocol": proto,
                        "aggregation": agg,
                        "seed": seed,
                        "duration_sec": duration,
                        "f1": float(metrics.get("f1", 0.0)),
                        "recall": float(metrics.get("recall", 0.0)),
                        "fpr": float(metrics.get("fpr", 0.0)),
                    }
                )

    summary: dict[str, object] = {"config": vars(args), "runs": runs, "stats": {}, "p_values": {}}
    for proto in protocols:
        summary["stats"][proto] = {}
        proto_runs = [r for r in runs if r["protocol"] == proto]
        fedavg_f1 = [float(r["f1"]) for r in proto_runs if r["aggregation"] == "fedavg"]
        for agg in aggs:
            agg_runs = [r for r in proto_runs if r["aggregation"] == agg]
            summary["stats"][proto][agg] = {
                "f1": mean_std([float(r["f1"]) for r in agg_runs]),
                "recall": mean_std([float(r["recall"]) for r in agg_runs]),
                "fpr": mean_std([float(r["fpr"]) for r in agg_runs]),
                "duration_sec": mean_std([float(r["duration_sec"]) for r in agg_runs]),
            }
            if agg != "fedavg" and fedavg_f1:
                vals = [float(r["f1"]) for r in agg_runs]
                summary["p_values"][f"{proto}_{agg}_vs_fedavg_f1"] = pval_signflip(vals, fedavg_f1)

    fedavg_pooled = [float(r["f1"]) for r in runs if r["aggregation"] == "fedavg"]
    for agg in aggs:
        if agg == "fedavg":
            continue
        vals = [float(r["f1"]) for r in runs if r["aggregation"] == agg]
        if fedavg_pooled and vals:
            summary["p_values"][f"pooled_{agg}_vs_fedavg_f1"] = pval_signflip(vals, fedavg_pooled)

    out_file = out / "fed_classic_robust_baselines_summary.json"
    out_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[DONE] {out_file}")


if __name__ == "__main__":
    main()
