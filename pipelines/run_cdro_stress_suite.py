#!/usr/bin/env python3
"""
Run weak-label stress sweeps over existing protocol graphs.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any


def run_cmd(cmd: list[str], cwd: Path, log_file: Path) -> tuple[int, float]:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with log_file.open("w", encoding="utf-8") as f:
        proc = subprocess.run(cmd, cwd=str(cwd), stdout=f, stderr=subprocess.STDOUT)
    return int(proc.returncode), float(time.time() - t0)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def main() -> None:
    ap = argparse.ArgumentParser(description="Run CDRO stress sweep")
    ap.add_argument("--project-dir", default="/home/user/FedSTGCN")
    ap.add_argument("--python-bin", default="/home/user/miniconda3/envs/DL/bin/python")
    ap.add_argument("--protocol-graph-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--protocols", default="weak_topology_ood,weak_attack_strategy_ood")
    ap.add_argument("--methods", default="noisy_ce,posterior_ce,cdro_ug")
    ap.add_argument("--seeds", default="11,22,33")
    ap.add_argument("--stress-kind", choices=["noise", "coverage"], required=True)
    ap.add_argument("--levels", default="0.00,0.15,0.30,0.45")
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--patience", type=int, default=4)
    ap.add_argument("--lambda-dro", type=float, default=0.50)
    ap.add_argument("--attack-trust", type=float, default=0.90)
    ap.add_argument("--benign-trust", type=float, default=0.55)
    ap.add_argument("--pseudo-attack-trust", type=float, default=0.85)
    ap.add_argument("--pseudo-benign-trust", type=float, default=0.80)
    ap.add_argument("--ug-temperature", type=float, default=0.35)
    ap.add_argument("--ug-priority-loss-scale", type=float, default=1.0)
    ap.add_argument("--ug-uncertainty-scale", type=float, default=0.20)
    ap.add_argument("--ug-disagreement-scale", type=float, default=0.10)
    ap.add_argument("--ug-sample-weight-scale", type=float, default=0.0)
    ap.add_argument("--force-cpu", action="store_true")
    args = ap.parse_args()

    project = Path(args.project_dir).resolve()
    py = str(args.python_bin)
    proto_dir = Path(args.protocol_graph_dir).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    protocols = [s.strip() for s in args.protocols.split(",") if s.strip()]
    methods = [s.strip() for s in args.methods.split(",") if s.strip()]
    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    levels = [float(s.strip()) for s in args.levels.split(",") if s.strip()]

    summary: dict[str, Any] = {
        "config": vars(args),
        "timestamps": {"start": time.strftime("%Y-%m-%d %H:%M:%S")},
        "stress_graphs": {},
        "runs": [],
    }

    for proto in protocols:
        base_graph = proto_dir / f"{proto}.pt"
        if not base_graph.exists():
            raise RuntimeError(f"Protocol graph missing: {base_graph}")
        for level in levels:
            level_tag = f"{int(round(level * 100)):02d}"
            stress_id = f"{proto}__{args.stress_kind}{level_tag}"
            stress_graph = out_dir / "stress_graphs" / f"{stress_id}.pt"
            cmd = [
                py,
                "data_prep/prepare_weak_label_stress_graph.py",
                "--input-graph",
                str(base_graph),
                "--output-graph",
                str(stress_graph),
                "--seed",
                "42",
            ]
            if args.stress_kind == "noise":
                cmd.extend(["--flip-frac", f"{level:.6f}", "--drop-frac", "0.0"])
            else:
                cmd.extend(["--flip-frac", "0.0", "--drop-frac", f"{level:.6f}"])
            rc, sec = run_cmd(cmd, cwd=project, log_file=out_dir / "logs" / f"{stress_id}_prepare.log")
            if rc != 0:
                raise RuntimeError(f"Stress graph generation failed for {stress_id}")
            stress_meta = load_json(stress_graph.with_suffix("").with_name(stress_graph.stem + "_stress.json"))
            summary["stress_graphs"][stress_id] = {
                "protocol": proto,
                "stress_kind": args.stress_kind,
                "stress_level": level,
                "graph_file": str(stress_graph),
                "summary_file": str(stress_graph.with_suffix("").with_name(stress_graph.stem + "_stress.json")),
                "duration_sec": sec,
                "stress_meta": stress_meta,
            }

            for method in methods:
                for seed in seeds:
                    exp_id = f"{stress_id}__{method}__seed{seed}"
                    exp_dir = out_dir / "runs" / exp_id
                    exp_dir.mkdir(parents=True, exist_ok=True)
                    result_file = exp_dir / "results.json"
                    cmd = [
                        py,
                        "training/pi_gnn_train_cdro.py",
                        "--graph-file",
                        str(stress_graph),
                        "--model-file",
                        str(exp_dir / "model.pt"),
                        "--results-file",
                        str(result_file),
                        "--method",
                        method,
                        "--epochs",
                        str(args.epochs),
                        "--patience",
                        str(args.patience),
                        "--lambda-dro",
                        str(args.lambda_dro),
                        "--attack-trust",
                        str(args.attack_trust),
                        "--benign-trust",
                        str(args.benign_trust),
                        "--pseudo-attack-trust",
                        str(args.pseudo_attack_trust),
                        "--pseudo-benign-trust",
                        str(args.pseudo_benign_trust),
                        "--ug-temperature",
                        str(args.ug_temperature),
                        "--ug-priority-loss-scale",
                        str(args.ug_priority_loss_scale),
                        "--ug-uncertainty-scale",
                        str(args.ug_uncertainty_scale),
                        "--ug-disagreement-scale",
                        str(args.ug_disagreement_scale),
                        "--ug-sample-weight-scale",
                        str(args.ug_sample_weight_scale),
                        "--seed",
                        str(seed),
                    ]
                    if bool(args.force_cpu):
                        cmd.append("--force-cpu")
                    rc, sec = run_cmd(cmd, cwd=project, log_file=exp_dir / "run.log")
                    if rc != 0:
                        raise RuntimeError(f"Training failed for {exp_id}")
                    result = load_json(result_file)
                    summary["runs"].append(
                        {
                            "id": exp_id,
                            "protocol": proto,
                            "stress_kind": args.stress_kind,
                            "stress_level": level,
                            "method": method,
                            "seed": seed,
                            "duration_sec": sec,
                            "result_file": str(result_file),
                            "metrics": result.get("final_eval", {}).get("test_temporal", {}),
                        }
                    )

    summary["timestamps"]["end"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_json(out_dir / "cdro_stress_summary.json", summary)
    print(out_dir / "cdro_stress_summary.json")


if __name__ == "__main__":
    main()
