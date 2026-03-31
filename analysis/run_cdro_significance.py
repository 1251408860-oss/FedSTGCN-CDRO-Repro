#!/usr/bin/env python3
"""
Compute paired sign-flip significance for CDRO suite summaries.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import statistics
from collections import defaultdict
from typing import Any


def pair_unit_key(run: dict[str, Any]) -> tuple[str, str, int]:
    # Merged summaries may contain the same protocol/seed from multiple source suites.
    # Include source identity so paired comparisons do not overwrite earlier runs.
    source = str(run.get("source_tag") or run.get("source_summary_json") or "")
    return source, str(run["protocol"]), int(run["seed"])


def paired_signflip(x: list[float], y: list[float], n_perm: int = 20000) -> float:
    if len(x) != len(y) or len(x) == 0:
        return 1.0
    d = [float(a - b) for a, b in zip(x, y)]
    obs = abs(sum(d) / len(d))
    if obs <= 1e-12:
        return 1.0

    n = len(d)
    total = 0
    extreme = 0
    if n <= 12:
        for bits in itertools.product([-1.0, 1.0], repeat=n):
            total += 1
            stat = abs(sum(di * si for di, si in zip(d, bits)) / n)
            if stat >= obs - 1e-12:
                extreme += 1
    else:
        import random

        rng = random.Random(42)
        for _ in range(n_perm):
            total += 1
            stat = abs(sum(di * (1.0 if rng.random() > 0.5 else -1.0) for di in d) / n)
            if stat >= obs - 1e-12:
                extreme += 1
    return float((extreme + 1) / (total + 1))


def mean_std(xs: list[float]) -> dict[str, float]:
    if not xs:
        return {"n": 0, "mean": 0.0, "std": 0.0}
    if len(xs) == 1:
        return {"n": 1, "mean": float(xs[0]), "std": 0.0}
    return {"n": len(xs), "mean": float(statistics.mean(xs)), "std": float(statistics.stdev(xs))}


def main() -> None:
    p = argparse.ArgumentParser(description="Run CDRO paired significance")
    p.add_argument("--summary-json", required=True)
    p.add_argument("--output-json", required=True)
    p.add_argument("--compare", action="append", default=[], help="Pair as method_a,method_b")
    p.add_argument("--metrics", default="f1,fpr,ece,brier")
    args = p.parse_args()

    with open(args.summary_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows: dict[tuple[str, str, int], dict[str, dict[str, float]]] = defaultdict(dict)
    for run in data.get("runs", []):
        rows[pair_unit_key(run)][str(run["method"])] = dict(run.get("metrics", {}))

    metrics = [s.strip() for s in args.metrics.split(",") if s.strip()]
    compares = []
    for raw in args.compare:
        a, b = [s.strip() for s in raw.split(",", 1)]
        compares.append((a, b))

    output: dict[str, Any] = {
        "summary_json": os.path.abspath(args.summary_json),
        "metrics": metrics,
        "comparisons": [],
    }

    for a, b in compares:
        pooled: dict[str, Any] = {"method_a": a, "method_b": b, "pooled": {}, "per_protocol": {}}
        for metric in metrics:
            xa: list[float] = []
            xb: list[float] = []
            for key in sorted(rows):
                d = rows[key]
                if a in d and b in d:
                    xa.append(float(d[a].get(metric, 0.0)))
                    xb.append(float(d[b].get(metric, 0.0)))
            pooled["pooled"][metric] = {
                "method_a": mean_std(xa),
                "method_b": mean_std(xb),
                "delta_mean": float(statistics.mean([u - v for u, v in zip(xa, xb)])) if xa else 0.0,
                "p_value": paired_signflip(xa, xb),
            }

        protocols = sorted({proto for _source, proto, _seed in rows})
        for proto in protocols:
            block = {}
            for metric in metrics:
                xa = []
                xb = []
                for (_source, row_proto, _seed), d in rows.items():
                    if row_proto != proto:
                        continue
                    if a in d and b in d:
                        xa.append(float(d[a].get(metric, 0.0)))
                        xb.append(float(d[b].get(metric, 0.0)))
                block[metric] = {
                    "method_a": mean_std(xa),
                    "method_b": mean_std(xb),
                    "delta_mean": float(statistics.mean([u - v for u, v in zip(xa, xb)])) if xa else 0.0,
                    "p_value": paired_signflip(xa, xb),
                }
            pooled["per_protocol"][proto] = block
        output["comparisons"].append(pooled)

    os.makedirs(os.path.dirname(os.path.abspath(args.output_json)), exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Saved significance summary to {args.output_json}")


if __name__ == "__main__":
    main()
