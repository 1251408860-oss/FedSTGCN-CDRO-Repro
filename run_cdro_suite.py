#!/usr/bin/env python3
"""
Run the weak-supervision CDRO suite.

Stages:
  1) Generate weak-label sidecar
  2) Prepare protocol graphs
  3) Train selected methods over protocols/seeds
  4) Save a machine-readable summary
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any


MAIN_PROTOCOLS = [
    "weak_temporal_ood",
    "weak_topology_ood",
    "weak_attack_strategy_ood",
    "label_prior_shift_ood",
]


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
    p = argparse.ArgumentParser(description="Run CDRO suite")
    p.add_argument("--project-dir", default="/home/user/FedSTGCN")
    p.add_argument("--python-bin", default="/home/user/miniconda3/envs/DL/bin/python")
    p.add_argument("--base-graph", default="/home/user/FedSTGCN/top_conf_suite_recharge/graphs/scenario_e_three_tier_high2.pt")
    p.add_argument("--manifest-file", default="/home/user/FedSTGCN/real_collection/scenario_e_three_tier_high2/arena_manifest_v2.json")
    p.add_argument("--output-dir", default="/home/user/FedSTGCN/cdro_suite/main_pilot")
    p.add_argument("--protocols", default=",".join(MAIN_PROTOCOLS))
    p.add_argument("--methods", default="noisy_ce,posterior_ce,cdro_fixed")
    p.add_argument("--seeds", default="11")
    p.add_argument("--epochs", type=int, default=12)
    p.add_argument("--patience", type=int, default=5)
    p.add_argument("--lambda-dro", type=float, default=0.50)
    p.add_argument("--force-cpu", action="store_true")
    p.add_argument("--physics-context", action="store_true")
    p.add_argument("--holdout-attack-type", default="mimic")
    p.add_argument("--pseudo-attack-thr", type=float, default=0.60)
    p.add_argument("--pseudo-benign-thr", type=float, default=0.25)
    p.add_argument("--pseudo-weight", type=float, default=0.60)
    p.add_argument("--attack-trust", type=float, default=0.90)
    p.add_argument("--benign-trust", type=float, default=0.55)
    p.add_argument("--pseudo-attack-trust", type=float, default=0.85)
    p.add_argument("--pseudo-benign-trust", type=float, default=0.80)
    p.add_argument("--ug-temperature", type=float, default=0.35)
    p.add_argument("--ug-priority-loss-scale", type=float, default=1.0)
    p.add_argument("--ug-uncertainty-scale", type=float, default=0.20)
    p.add_argument("--ug-disagreement-scale", type=float, default=0.10)
    p.add_argument("--ug-sample-weight-scale", type=float, default=0.20)
    p.add_argument("--posthoc-temperature-scaling", action="store_true")
    p.add_argument("--temp-scale-min", type=float, default=0.5)
    p.add_argument("--temp-scale-max", type=float, default=5.0)
    p.add_argument("--temp-scale-steps", type=int, default=31)
    args = p.parse_args()

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
        "weak_label": {},
        "protocol_graphs": {},
        "runs": [],
    }

    weak_dir = out_dir / "weak_labels"
    weak_prefix = Path(args.base_graph).stem
    weak_pt = weak_dir / f"{weak_prefix}_weak_labels.pt"
    weak_json = weak_dir / f"{weak_prefix}_weak_summary.json"

    cmd = [
        py,
        "generate_weak_supervision_views.py",
        "--input-graph",
        str(args.base_graph),
        "--manifest-file",
        str(args.manifest_file),
        "--output-dir",
        str(weak_dir),
        "--output-prefix",
        weak_prefix,
        "--seed",
        "42",
    ]
    rc, sec = run_cmd(cmd, cwd=project, log_file=out_dir / "logs" / "weak_labels.log")
    if rc != 0:
        raise RuntimeError("Weak label generation failed")
    summary["weak_label"] = {
        "pt_file": str(weak_pt),
        "json_file": str(weak_json),
        "duration_sec": sec,
    }

    for proto in protocols:
        graph_out = out_dir / "protocol_graphs" / f"{proto}.pt"
        cmd = [
            py,
            "prepare_label_shift_protocol_graph.py",
            "--input-graph",
            str(args.base_graph),
            "--weak-labels",
            str(weak_pt),
            "--manifest-file",
            str(args.manifest_file),
            "--output-graph",
            str(graph_out),
            "--protocol",
            proto,
            "--holdout-attack-type",
            str(args.holdout_attack_type),
            "--seed",
            "42",
        ]
        rc, sec = run_cmd(cmd, cwd=project, log_file=out_dir / "logs" / f"protocol_{proto}.log")
        if rc != 0:
            raise RuntimeError(f"Protocol graph failed for {proto}")
        summary["protocol_graphs"][proto] = {
            "graph_file": str(graph_out),
            "summary_file": str(graph_out.with_name(graph_out.stem + "_summary.json")),
            "duration_sec": sec,
        }

    for proto, pinfo in summary["protocol_graphs"].items():
        for method in methods:
            for seed in seeds:
                exp_id = f"{proto}__{method}__seed{seed}"
                exp_dir = out_dir / "runs" / exp_id
                exp_dir.mkdir(parents=True, exist_ok=True)
                model_file = exp_dir / "model.pt"
                result_file = exp_dir / "results.json"
                cmd = [
                    py,
                    "pi_gnn_train_cdro.py",
                    "--graph-file",
                    pinfo["graph_file"],
                    "--model-file",
                    str(model_file),
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
                    "--pseudo-attack-thr",
                    str(args.pseudo_attack_thr),
                    "--pseudo-benign-thr",
                    str(args.pseudo_benign_thr),
                    "--pseudo-weight",
                    str(args.pseudo_weight),
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
                    "--temp-scale-min",
                    str(args.temp_scale_min),
                    "--temp-scale-max",
                    str(args.temp_scale_max),
                    "--temp-scale-steps",
                    str(args.temp_scale_steps),
                    "--seed",
                    str(seed),
                ]
                if bool(args.force_cpu):
                    cmd.append("--force-cpu")
                if bool(args.physics_context):
                    cmd.append("--physics-context")
                if bool(args.posthoc_temperature_scaling):
                    cmd.append("--posthoc-temperature-scaling")

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
    save_json(out_dir / "cdro_summary.json", summary)
    print(f"Suite finished. Summary: {out_dir / 'cdro_summary.json'}")


if __name__ == "__main__":
    main()
