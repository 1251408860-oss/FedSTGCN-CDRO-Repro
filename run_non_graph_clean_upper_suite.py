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


def main() -> None:
    ap = argparse.ArgumentParser(description="Run XGBoost weak baseline + clean-label PI-GNN upper bound")
    ap.add_argument("--project-dir", default="/home/user/FedSTGCN")
    ap.add_argument("--python-bin", default="/home/user/miniconda3/envs/DL/bin/python")
    ap.add_argument("--main-graph-dir", default="/home/user/FedSTGCN/cdro_suite/main_baselineplus_s3_v1/protocol_graphs")
    ap.add_argument("--external-graph-dir", default="/home/user/FedSTGCN/cdro_suite/batch2_baselineplus_s3_v1/protocol_graphs")
    ap.add_argument("--output-dir", default="/home/user/FedSTGCN/cdro_suite/non_graph_clean_upper_s3_v1")
    ap.add_argument("--protocols", default="weak_temporal_ood,weak_topology_ood,weak_attack_strategy_ood,label_prior_shift_ood")
    ap.add_argument("--seeds", default="11,22,33")
    ap.add_argument("--xgb-n-estimators", type=int, default=300)
    ap.add_argument("--xgb-max-depth", type=int, default=6)
    ap.add_argument("--xgb-learning-rate", type=float, default=0.05)
    ap.add_argument("--clean-epochs", type=int, default=40)
    ap.add_argument("--clean-warmup-epochs", type=int, default=10)
    ap.add_argument("--clean-patience", type=int, default=10)
    ap.add_argument("--capacity", type=float, default=120000.0)
    ap.add_argument("--alpha-flow", type=float, default=0.05)
    ap.add_argument("--beta-latency", type=float, default=0.05)
    ap.add_argument("--force-cpu", action="store_true")
    args = ap.parse_args()

    project = Path(args.project_dir).resolve()
    py = str(args.python_bin)
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    protocols = [s.strip() for s in args.protocols.split(",") if s.strip()]
    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    dataset_dirs = {
        "main": Path(args.main_graph_dir).resolve(),
        "external_j": Path(args.external_graph_dir).resolve(),
    }

    summary: dict[str, Any] = {
        "config": vars(args),
        "timestamps": {"start": time.strftime("%Y-%m-%d %H:%M:%S")},
        "runs": [],
    }

    for dataset_name, graph_dir in dataset_dirs.items():
        for protocol in protocols:
            graph_file = graph_dir / f"{protocol}.pt"
            if not graph_file.exists():
                raise RuntimeError(f"Protocol graph missing: {graph_file}")
            for seed in seeds:
                xgb_id = f"{dataset_name}__{protocol}__xgboost_weak__seed{seed}"
                xgb_dir = out_dir / "runs" / xgb_id
                xgb_dir.mkdir(parents=True, exist_ok=True)
                xgb_result = xgb_dir / "results.json"
                if not xgb_result.exists():
                    cmd = [
                        py,
                        "train_xgboost_baseline.py",
                        "--graph-file",
                        str(graph_file),
                        "--model-file",
                        str(xgb_dir / "model.json"),
                        "--results-file",
                        str(xgb_result),
                        "--n-estimators",
                        str(args.xgb_n_estimators),
                        "--max-depth",
                        str(args.xgb_max_depth),
                        "--learning-rate",
                        str(args.xgb_learning_rate),
                        "--seed",
                        str(seed),
                    ]
                    rc, run_sec = run_cmd(cmd, cwd=project, log_file=xgb_dir / "run.log")
                    if rc != 0:
                        raise RuntimeError(f"XGBoost baseline failed for {xgb_id}")
                else:
                    run_sec = 0.0
                xgb_metrics = load_json(xgb_result)
                summary["runs"].append(
                    {
                        "id": xgb_id,
                        "dataset": dataset_name,
                        "protocol": protocol,
                        "method": "xgboost_weak",
                        "seed": seed,
                        "duration_sec": run_sec,
                        "result_file": str(xgb_result),
                        "metrics": xgb_metrics.get("final_eval", {}).get("test_temporal", {}),
                    }
                )

                clean_id = f"{dataset_name}__{protocol}__pignn_clean__seed{seed}"
                clean_dir = out_dir / "runs" / clean_id
                clean_dir.mkdir(parents=True, exist_ok=True)
                clean_result = clean_dir / "results.json"
                if not clean_result.exists():
                    cmd = [
                        py,
                        "pi_gnn_train_v2.py",
                        "--graph-file",
                        str(graph_file),
                        "--model-file",
                        str(clean_dir / "model.pt"),
                        "--results-file",
                        str(clean_result),
                        "--epochs",
                        str(args.clean_epochs),
                        "--warmup-epochs",
                        str(args.clean_warmup_epochs),
                        "--patience",
                        str(args.clean_patience),
                        "--capacity",
                        str(args.capacity),
                        "--alpha-flow",
                        str(args.alpha_flow),
                        "--beta-latency",
                        str(args.beta_latency),
                        "--seed",
                        str(seed),
                    ]
                    if bool(args.force_cpu):
                        cmd.append("--force-cpu")
                    rc, run_sec = run_cmd(cmd, cwd=project, log_file=clean_dir / "run.log")
                    if rc != 0:
                        raise RuntimeError(f"Clean-label PI-GNN failed for {clean_id}")
                else:
                    run_sec = 0.0
                clean_metrics = load_json(clean_result)
                summary["runs"].append(
                    {
                        "id": clean_id,
                        "dataset": dataset_name,
                        "protocol": protocol,
                        "method": "pignn_clean",
                        "seed": seed,
                        "duration_sec": run_sec,
                        "result_file": str(clean_result),
                        "metrics": clean_metrics.get("final_eval", {}).get("test_temporal", {}),
                    }
                )

    summary["timestamps"]["end"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_json(out_dir / "non_graph_clean_summary.json", summary)
    print(out_dir / "non_graph_clean_summary.json")


if __name__ == "__main__":
    main()
