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


def mean_std(vals: list[float]) -> dict[str, float]:
    if not vals:
        return {"n": 0, "mean": 0.0, "std": 0.0}
    if len(vals) == 1:
        return {"n": 1, "mean": vals[0], "std": 0.0}
    return {"n": len(vals), "mean": float(statistics.mean(vals)), "std": float(statistics.stdev(vals))}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--python-bin", default="/home/user/miniconda3/envs/DL/bin/python")
    p.add_argument("--suite-dir", default="/home/user/FedSTGCN/top_conf_suite_v3")
    p.add_argument("--seeds", default="11,22,33,44,55")
    args = p.parse_args()

    py = args.python_bin
    suite = Path(args.suite_dir)
    seeds = [int(x.strip()) for x in args.seeds.split(",") if x.strip()]
    protocols = ["temporal_ood", "topology_ood", "attack_strategy_ood"]
    out_dir = suite / "baseline_significance"
    out_dir.mkdir(parents=True, exist_ok=True)

    runs = []
    for proto in protocols:
        graph = suite / "protocol_graphs" / f"{proto}.pt"
        for seed in seeds:
            model = suite / "stage3" / f"{proto}__clean__physics_stable__seed{seed}" / "pi_gnn_model.pt"
            out = out_dir / f"{proto}_seed{seed}.json"
            log = out_dir / f"{proto}_seed{seed}.log"
            cmd = [
                py,
                "training/evaluate_baselines.py",
                "--graph-file",
                str(graph),
                "--pi-model-file",
                str(model),
                "--output-file",
                str(out),
                "--seed",
                str(seed),
                "--force-cpu",
            ]
            with log.open("w", encoding="utf-8") as f:
                r = subprocess.run(cmd, cwd="/home/user/FedSTGCN", stdout=f, stderr=subprocess.STDOUT)
            if r.returncode != 0:
                raise RuntimeError(f"baseline eval failed: {proto} seed={seed}")
            d = json.loads(out.read_text(encoding="utf-8"))
            runs.append({"protocol": proto, "seed": seed, "metrics": d.get("metrics", {})})

    summary: dict[str, dict] = {"runs": runs, "stats": {}}
    for proto in protocols:
        summary["stats"][proto] = {}
        proto_runs = [r for r in runs if r["protocol"] == proto]
        for model in ["random_forest", "gcn", "pi_gnn"]:
            f1 = [float(r["metrics"].get(model, {}).get("f1", 0.0)) for r in proto_runs]
            fpr = [float(r["metrics"].get(model, {}).get("fpr", 0.0)) for r in proto_runs]
            rec = [float(r["metrics"].get(model, {}).get("recall", 0.0)) for r in proto_runs]
            summary["stats"][proto][model] = {"f1": mean_std(f1), "fpr": mean_std(fpr), "recall": mean_std(rec)}

        pi_f1 = [float(r["metrics"].get("pi_gnn", {}).get("f1", 0.0)) for r in proto_runs]
        gcn_f1 = [float(r["metrics"].get("gcn", {}).get("f1", 0.0)) for r in proto_runs]
        pi_fpr = [float(r["metrics"].get("pi_gnn", {}).get("fpr", 0.0)) for r in proto_runs]
        gcn_fpr = [float(r["metrics"].get("gcn", {}).get("fpr", 0.0)) for r in proto_runs]
        # For FPR, lower is better => compare -FPR.
        summary["stats"][proto]["significance_pi_vs_gcn"] = {
            "p_value_f1": pval_signflip(pi_f1, gcn_f1),
            "p_value_fpr": pval_signflip([-x for x in pi_fpr], [-y for y in gcn_fpr]),
        }

    out_file = out_dir / "baseline_significance_summary.json"
    out_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[DONE] {out_file}")


if __name__ == "__main__":
    main()
