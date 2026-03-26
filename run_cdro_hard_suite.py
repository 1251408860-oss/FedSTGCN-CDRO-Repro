#!/usr/bin/env python3
"""
Run hard/camouflaged protocol variants on a weak-labeled graph.
"""

from __future__ import annotations

import argparse
import json
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
    ap = argparse.ArgumentParser(description="Run CDRO hard protocol suite")
    ap.add_argument("--project-dir", default="/home/user/FedSTGCN")
    ap.add_argument("--python-bin", default="/home/user/miniconda3/envs/DL/bin/python")
    ap.add_argument("--input-graph", required=True, help="Weak-labeled graph; masks will be overwritten")
    ap.add_argument("--manifest-file", default="")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--protocols", default="temporal_ood,topology_ood,attack_strategy_ood,congestion_ood")
    ap.add_argument("--methods", default="noisy_ce,cdro_fixed,cdro_ug")
    ap.add_argument("--seeds", default="11,22,33")
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--patience", type=int, default=4)
    ap.add_argument("--lambda-dro", type=float, default=0.50)
    ap.add_argument("--holdout-attack-type", default="mimic")
    ap.add_argument("--attack-trust", type=float, default=0.90)
    ap.add_argument("--benign-trust", type=float, default=0.55)
    ap.add_argument("--pseudo-attack-trust", type=float, default=0.85)
    ap.add_argument("--pseudo-benign-trust", type=float, default=0.80)
    ap.add_argument("--ug-temperature", type=float, default=0.35)
    ap.add_argument("--ug-priority-loss-scale", type=float, default=1.0)
    ap.add_argument("--ug-uncertainty-scale", type=float, default=0.20)
    ap.add_argument("--ug-disagreement-scale", type=float, default=0.10)
    ap.add_argument("--ug-sample-weight-scale", type=float, default=0.0)
    ap.add_argument("--hard-overlap", action="store_true")
    ap.add_argument("--train-keep-frac", type=float, default=0.80)
    ap.add_argument("--val-keep-frac", type=float, default=0.85)
    ap.add_argument("--test-keep-frac", type=float, default=0.95)
    ap.add_argument("--min-keep-per-class", type=int, default=64)
    ap.add_argument("--camouflage-test-attacks", action="store_true")
    ap.add_argument("--camouflage-noise-scale", type=float, default=0.35)
    ap.add_argument("--force-cpu", action="store_true")
    args = ap.parse_args()

    project = Path(args.project_dir).resolve()
    py = str(args.python_bin)
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    protocols = [s.strip() for s in args.protocols.split(",") if s.strip()]
    methods = [s.strip() for s in args.methods.split(",") if s.strip()]
    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]

    summary: dict[str, Any] = {
        "config": vars(args),
        "timestamps": {"start": time.strftime("%Y-%m-%d %H:%M:%S")},
        "protocol_graphs": {},
        "runs": [],
    }

    for proto in protocols:
        graph_out = out_dir / "protocol_graphs" / f"{proto}.pt"
        cmd = [
            py,
            "prepare_hard_protocol_graph.py",
            "--input-graph",
            str(Path(args.input_graph).resolve()),
            "--output-graph",
            str(graph_out),
            "--protocol",
            proto,
            "--manifest-file",
            str(args.manifest_file),
            "--holdout-attack-type",
            str(args.holdout_attack_type),
            "--train-keep-frac",
            str(args.train_keep_frac),
            "--val-keep-frac",
            str(args.val_keep_frac),
            "--test-keep-frac",
            str(args.test_keep_frac),
            "--min-keep-per-class",
            str(args.min_keep_per_class),
            "--camouflage-noise-scale",
            str(args.camouflage_noise_scale),
            "--seed",
            "42",
        ]
        if bool(args.hard_overlap):
            cmd.append("--hard-overlap")
        if bool(args.camouflage_test_attacks):
            cmd.append("--camouflage-test-attacks")
        rc, sec = run_cmd(cmd, cwd=project, log_file=out_dir / "logs" / f"{proto}_prepare.log")
        if rc != 0:
            raise RuntimeError(f"Hard protocol graph failed for {proto}")
        summary["protocol_graphs"][proto] = {
            "graph_file": str(graph_out),
            "duration_sec": sec,
        }

    for proto, info in summary["protocol_graphs"].items():
        for method in methods:
            for seed in seeds:
                exp_id = f"{proto}__{method}__seed{seed}"
                exp_dir = out_dir / "runs" / exp_id
                exp_dir.mkdir(parents=True, exist_ok=True)
                result_file = exp_dir / "results.json"
                cmd = [
                    py,
                    "pi_gnn_train_cdro.py",
                    "--graph-file",
                    info["graph_file"],
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
                        "method": method,
                        "seed": seed,
                        "duration_sec": sec,
                        "result_file": str(result_file),
                        "metrics": result.get("final_eval", {}).get("test_temporal", {}),
                    }
                )

    summary["timestamps"]["end"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_json(out_dir / "cdro_hard_summary.json", summary)
    print(out_dir / "cdro_hard_summary.json")


if __name__ == "__main__":
    main()
