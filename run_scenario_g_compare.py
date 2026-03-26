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
        raise RuntimeError(f"failed: {' '.join(cmd)}")


def main() -> None:
    py = "/home/user/miniconda3/envs/DL/bin/python"
    base = Path("/home/user/FedSTGCN")
    out = base / "scenario_g_eval"
    out.mkdir(parents=True, exist_ok=True)

    graph = base / "scenario_g_graph.pt"
    manifest = base / "real_collection/scenario_g_mimic_congest/arena_manifest_v2.json"

    protocol_graphs = {}
    for proto in ["temporal_ood", "topology_ood"]:
        g = out / f"{proto}.pt"
        log = out / f"prep_{proto}.log"
        run(
            [
                py,
                "prepare_leakage_protocol_graph.py",
                "--input-graph",
                str(graph),
                "--output-graph",
                str(g),
                "--protocol",
                proto,
                "--manifest-file",
                str(manifest),
                "--holdout-attack-type",
                "mimic",
                "--seed",
                "42",
            ],
            log,
        )
        protocol_graphs[proto] = g

    seeds = [11, 22, 33, 44, 55]
    results = []
    for proto, g in protocol_graphs.items():
        for model, alpha, beta in [("data_only", 0.0, 0.0), ("physics", 0.03, 0.02)]:
            for s in seeds:
                d = out / f"{proto}_{model}_s{s}"
                d.mkdir(parents=True, exist_ok=True)
                run(
                    [
                        py,
                        "pi_gnn_train_v2.py",
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
                r = json.loads((d / "r.json").read_text(encoding="utf-8"))
                m = r.get("final_eval", {}).get("test_temporal") or r.get("final_eval", {}).get("test_random") or {}
                results.append({"protocol": proto, "model": model, "seed": s, "f1": float(m.get("f1", 0.0)), "recall": float(m.get("recall", 0.0))})

    print("=== scenario_g compare ===")
    for proto in ["temporal_ood", "topology_ood"]:
        print(proto)
        for model in ["data_only", "physics"]:
            vals = [r for r in results if r["protocol"] == proto and r["model"] == model]
            f1 = [v["f1"] for v in vals]
            rc = [v["recall"] for v in vals]
            print(
                " ",
                model,
                "F1",
                round(statistics.mean(f1), 4),
                "+-",
                round(statistics.stdev(f1), 4),
                "Recall",
                round(statistics.mean(rc), 4),
                "+-",
                round(statistics.stdev(rc), 4),
            )


if __name__ == "__main__":
    main()
