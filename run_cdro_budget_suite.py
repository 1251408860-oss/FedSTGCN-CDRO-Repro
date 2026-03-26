#!/usr/bin/env python3
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
    with log_file.open("w", encoding="utf-8") as fh:
        proc = subprocess.run(cmd, cwd=str(cwd), stdout=fh, stderr=subprocess.STDOUT)
    return int(proc.returncode), float(time.time() - t0)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def maybe_run_prepare(
    py: str,
    project: Path,
    base_graph: Path,
    stress_graph: Path,
    budget: float,
    seed: int,
    log_file: Path,
) -> tuple[dict[str, Any], float]:
    meta_file = stress_graph.with_name(stress_graph.stem + "_stress.json")
    if stress_graph.exists() and meta_file.exists():
        meta = load_json(meta_file)
        return meta, 0.0
    drop_frac = max(0.0, min(1.0, 1.0 - float(budget)))
    cmd = [
        py,
        "prepare_weak_label_stress_graph.py",
        "--input-graph",
        str(base_graph),
        "--output-graph",
        str(stress_graph),
        "--flip-frac",
        "0.0",
        "--drop-frac",
        f"{drop_frac:.6f}",
        "--seed",
        str(seed),
    ]
    rc, sec = run_cmd(cmd, cwd=project, log_file=log_file)
    if rc != 0:
        raise RuntimeError(f"budget graph generation failed: {stress_graph.name}")
    return load_json(meta_file), sec


def main() -> None:
    ap = argparse.ArgumentParser(description="Run label-budget sweeps for main + external-J")
    ap.add_argument("--project-dir", default="/home/user/FedSTGCN")
    ap.add_argument("--python-bin", default="/home/user/miniconda3/envs/DL/bin/python")
    ap.add_argument("--main-graph-dir", default="/home/user/FedSTGCN/cdro_suite/main_baselineplus_s3_v1/protocol_graphs")
    ap.add_argument("--external-graph-dir", default="/home/user/FedSTGCN/cdro_suite/batch2_baselineplus_s3_v1/protocol_graphs")
    ap.add_argument("--output-dir", default="/home/user/FedSTGCN/cdro_suite/label_budget_s3_v1")
    ap.add_argument("--protocols", default="weak_topology_ood,weak_attack_strategy_ood")
    ap.add_argument("--methods", default="noisy_ce,cdro_fixed,cdro_ug")
    ap.add_argument("--budgets", default="0.05,0.10,0.20,0.30,0.50,1.00")
    ap.add_argument("--seeds", default="11,22,33")
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
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    protocols = [s.strip() for s in args.protocols.split(",") if s.strip()]
    methods = [s.strip() for s in args.methods.split(",") if s.strip()]
    budgets = [float(s.strip()) for s in args.budgets.split(",") if s.strip()]
    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    dataset_dirs = {
        "main": Path(args.main_graph_dir).resolve(),
        "external_j": Path(args.external_graph_dir).resolve(),
    }

    summary: dict[str, Any] = {
        "config": vars(args),
        "timestamps": {"start": time.strftime("%Y-%m-%d %H:%M:%S")},
        "budget_graphs": {},
        "runs": [],
    }

    for dataset_name, graph_dir in dataset_dirs.items():
        for protocol in protocols:
            base_graph = graph_dir / f"{protocol}.pt"
            if not base_graph.exists():
                raise RuntimeError(f"Protocol graph missing: {base_graph}")
            for budget in budgets:
                budget_tag = f"b{int(round(100 * budget)):03d}"
                budget_id = f"{dataset_name}__{protocol}__{budget_tag}"
                stress_graph = out_dir / "budget_graphs" / f"{budget_id}.pt"
                stress_meta, prep_sec = maybe_run_prepare(
                    py=py,
                    project=project,
                    base_graph=base_graph,
                    stress_graph=stress_graph,
                    budget=budget,
                    seed=42,
                    log_file=out_dir / "logs" / f"{budget_id}_prepare.log",
                )
                summary["budget_graphs"][budget_id] = {
                    "dataset": dataset_name,
                    "protocol": protocol,
                    "budget": float(budget),
                    "graph_file": str(stress_graph),
                    "summary_file": str(stress_graph.with_name(stress_graph.stem + "_stress.json")),
                    "duration_sec": prep_sec,
                    "stress_meta": stress_meta,
                }

                for method in methods:
                    for seed in seeds:
                        exp_id = f"{budget_id}__{method}__seed{seed}"
                        exp_dir = out_dir / "runs" / exp_id
                        exp_dir.mkdir(parents=True, exist_ok=True)
                        result_file = exp_dir / "results.json"
                        if not result_file.exists():
                            cmd = [
                                py,
                                "pi_gnn_train_cdro.py",
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
                            rc, run_sec = run_cmd(cmd, cwd=project, log_file=exp_dir / "run.log")
                            if rc != 0:
                                raise RuntimeError(f"training failed for {exp_id}")
                        else:
                            run_sec = 0.0
                        result = load_json(result_file)
                        summary["runs"].append(
                            {
                                "id": exp_id,
                                "dataset": dataset_name,
                                "protocol": protocol,
                                "budget": float(budget),
                                "method": method,
                                "seed": seed,
                                "duration_sec": run_sec,
                                "result_file": str(result_file),
                                "metrics": result.get("final_eval", {}).get("test_temporal", {}),
                            }
                        )

    summary["timestamps"]["end"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_json(out_dir / "budget_summary.json", summary)
    print(out_dir / "budget_summary.json")


if __name__ == "__main__":
    main()
