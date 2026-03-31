#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--python-bin", default="/home/user/miniconda3/envs/DL/bin/python")
    p.add_argument("--graph-file", required=True)
    p.add_argument("--output-dir", default="/home/user/FedSTGCN/phys_search")
    p.add_argument("--seeds", default="11,22,33")
    p.add_argument("--epochs", type=int, default=120)
    p.add_argument("--train-poison-frac", type=float, default=0.35)
    args = p.parse_args()

    combos = [(0.01, 0.01), (0.02, 0.01), (0.03, 0.02), (0.05, 0.02), (0.08, 0.03), (0.02, 0.05)]
    seeds = [int(x.strip()) for x in args.seeds.split(",") if x.strip()]
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    summary: dict[str, list[dict[str, float]]] = {}
    for alpha, beta in combos:
        key = f"a{alpha}_b{beta}"
        summary[key] = []
        for seed in seeds:
            d = out / f"{key}_s{seed}"
            d.mkdir(parents=True, exist_ok=True)
            cmd = [
                args.python_bin,
                "training/pi_gnn_train_v2.py",
                "--graph-file",
                args.graph_file,
                "--model-file",
                str(d / "model.pt"),
                "--results-file",
                str(d / "results.json"),
                "--epochs",
                str(args.epochs),
                "--alpha-flow",
                str(alpha),
                "--beta-latency",
                str(beta),
                "--train-poison-frac",
                str(args.train_poison_frac),
                "--warmup-epochs",
                "25",
                "--patience",
                "30",
                "--seed",
                str(seed),
                "--force-cpu",
            ]
            with (d / "run.log").open("w", encoding="utf-8") as f:
                r = subprocess.run(cmd, cwd="/home/user/FedSTGCN", stdout=f, stderr=subprocess.STDOUT)
            if r.returncode != 0:
                raise RuntimeError(f"run failed: {key} seed={seed}")
            data = json.loads((d / "results.json").read_text(encoding="utf-8"))
            m = data.get("final_eval", {}).get("test_temporal") or data.get("final_eval", {}).get("test_random") or {}
            summary[key].append({"f1": float(m.get("f1", 0.0)), "recall": float(m.get("recall", 0.0))})

    print("=== Physics hyperparam search ===")
    for key, vals in summary.items():
        f1 = [v["f1"] for v in vals]
        rec = [v["recall"] for v in vals]
        f1_std = statistics.stdev(f1) if len(f1) > 1 else 0.0
        rec_std = statistics.stdev(rec) if len(rec) > 1 else 0.0
        print(
            key,
            "F1",
            round(statistics.mean(f1), 4),
            "+-",
            round(f1_std, 4),
            "Recall",
            round(statistics.mean(rec), 4),
            "+-",
            round(rec_std, 4),
        )


if __name__ == "__main__":
    main()
