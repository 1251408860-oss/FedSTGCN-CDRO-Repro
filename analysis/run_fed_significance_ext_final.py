#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
import statistics
import subprocess
from pathlib import Path


def pval_signflip(x: list[float], y: list[float]) -> float:
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
        raise RuntimeError("command failed")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--python-bin", default="/home/user/miniconda3/envs/DL/bin/python")
    p.add_argument("--suite-dir", default="/home/user/FedSTGCN/top_conf_suite_final")
    p.add_argument("--seeds", default="11,22,33,44,55,66,77,88,99")
    p.add_argument("--aggregations", default="fedavg,shapley_proxy,median")
    p.add_argument("--robust-f", type=int, default=-1)
    args = p.parse_args()

    py = args.python_bin
    suite = Path(args.suite_dir)
    graph = str(suite / "protocol_graphs" / "temporal_ood.pt")
    out = suite / "fed_sig_ext9"
    out.mkdir(parents=True, exist_ok=True)
    seeds = [int(x.strip()) for x in str(args.seeds).split(",") if x.strip()]
    aggs = [x.strip() for x in str(args.aggregations).split(",") if x.strip()]

    raw: dict[str, list[dict[str, float]]] = {k: [] for k in aggs}
    for agg in aggs:
        for s in seeds:
            d = out / f"{agg}_s{s}"
            d.mkdir(parents=True, exist_ok=True)
            run(
                [
                    py,
                    "training/fed_pignn.py",
                    "--graph-file",
                    graph,
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
                    "0.03",
                    "--beta-latency",
                    "0.02",
                    "--capacity",
                    "120000",
                    "--warmup-rounds",
                    "2",
                    "--seed",
                    str(s),
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
            raw[agg].append(
                {"seed": s, "f1": float(m.get("f1", 0.0)), "recall": float(m.get("recall", 0.0)), "fpr": float(m.get("fpr", 0.0))}
            )

    summary: dict[str, object] = {"n": len(seeds), "raw": raw, "stats": {}, "p_values": {}}
    for agg in aggs:
        f1 = [x["f1"] for x in raw[agg]]
        rc = [x["recall"] for x in raw[agg]]
        fp = [x["fpr"] for x in raw[agg]]
        summary["stats"][agg] = {
            "f1_mean": statistics.mean(f1),
            "f1_std": statistics.stdev(f1),
            "recall_mean": statistics.mean(rc),
            "recall_std": statistics.stdev(rc),
            "fpr_mean": statistics.mean(fp),
            "fpr_std": statistics.stdev(fp),
        }

    pvals: dict[str, float] = {}
    fedavg = [x["f1"] for x in raw.get("fedavg", [])]
    for agg in aggs:
        if agg == "fedavg":
            continue
        vals = [x["f1"] for x in raw.get(agg, [])]
        if fedavg and vals:
            pval = pval_signflip(vals, fedavg)
            pvals[f"{agg}_vs_fedavg_f1"] = pval
            if agg == "shapley_proxy":
                pvals["shapley_vs_fedavg_f1"] = pval
            if agg == "median":
                pvals["median_vs_fedavg_f1"] = pval
    summary["p_values"] = pvals

    out_file = out / "fed_sig_ext9_summary.json"
    out_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[DONE] {out_file}")
    if "shapley_vs_fedavg_f1" in summary["p_values"]:
        print("p(shapley_vs_fedavg_f1)=", summary["p_values"]["shapley_vs_fedavg_f1"])


if __name__ == "__main__":
    main()
