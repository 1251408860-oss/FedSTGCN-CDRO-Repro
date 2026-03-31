#!/usr/bin/env python3
"""
Run 12 experiments across 4 phases:
  - Stage 1 (3): real-LLM payload generation variants
  - Stage 2 (3): graph construction delta_t ablation
  - Stage 3 (3): PI-GNN physics loss ablation
  - Stage 4 (3): federated robust aggregation / poisoning settings

Produces:
  experiments_12/
    <exp_id>/
      run.log
      artifacts...
    summary_12_experiments.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def shannon_entropy(items: list[str]) -> float:
    if not items:
        return 0.0
    c = Counter(items)
    n = len(items)
    return -sum((v / n) * math.log2(v / n) for v in c.values())


def run_cmd(cmd: list[str], cwd: Path, log_path: Path, env: dict[str, str]) -> tuple[int, float]:
    start = time.time()
    with log_path.open("w", encoding="utf-8") as f:
        proc = subprocess.run(cmd, cwd=str(cwd), env=env, stdout=f, stderr=subprocess.STDOUT)
    return int(proc.returncode), float(time.time() - start)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def summarize_payload_file(payload_file: Path) -> dict[str, Any]:
    data = load_json(payload_file)
    payloads = data.get("flat_payloads", []) if isinstance(data, dict) else []
    md = data.get("metadata", {}) if isinstance(data, dict) else {}
    sessions = data.get("sessions", []) if isinstance(data, dict) else []

    uris = [str(p.get("uri", "")) for p in payloads]
    uas = [str(p.get("user_agent", "")) for p in payloads]
    think_times = [float(p.get("think_time", 0.0)) for p in payloads]

    unique_uri_ratio = (len(set(uris)) / len(uris)) if uris else 0.0
    mean_think = (sum(think_times) / len(think_times)) if think_times else 0.0

    return {
        "total_payloads": int(len(payloads)),
        "total_sessions": int(len(sessions)),
        "llm_sessions": int(md.get("llm_sessions", 0)),
        "unique_uri_ratio": float(unique_uri_ratio),
        "ua_entropy": float(shannon_entropy(uas)),
        "mean_think_time": float(mean_think),
    }


def summarize_graph(graph_file: Path) -> dict[str, Any]:
    import torch

    graph = torch.load(graph_file, weights_only=False, map_location="cpu")
    flow_mask = (graph.window_idx >= 0) if hasattr(graph, "window_idx") else (torch.arange(graph.num_nodes) > 0)
    benign = int(((graph.y == 0) & flow_mask).sum().item())
    attack = int(((graph.y == 1) & flow_mask).sum().item())
    return {
        "nodes": int(graph.num_nodes),
        "edges": int(graph.num_edges),
        "features": int(graph.x.shape[1]),
        "windows": int(getattr(graph, "n_windows", 0)),
        "benign_flow_nodes": benign,
        "attack_flow_nodes": attack,
        "label_source": str(getattr(graph, "label_source", "unknown")),
    }


def pick_pignn_test_metrics(results: dict[str, Any]) -> dict[str, Any]:
    final_eval = results.get("final_eval", {})
    if "test_temporal" in final_eval and isinstance(final_eval["test_temporal"], dict):
        return {"split": "test_temporal", **final_eval["test_temporal"]}
    if "test_random" in final_eval and isinstance(final_eval["test_random"], dict):
        return {"split": "test_random", **final_eval["test_random"]}
    return {"split": "unknown"}


def pick_fed_test_metrics(results: dict[str, Any]) -> dict[str, Any]:
    gm = results.get("global_metrics", {})
    temporal = gm.get("test_temporal", {})
    random_test = gm.get("test_random", {})
    if isinstance(temporal, dict) and (temporal.get("recall", 0.0) > 0.0 or temporal.get("f1", 0.0) > 0.0):
        return {"split": "test_temporal", **temporal}
    if isinstance(random_test, dict):
        return {"split": "test_random", **random_test}
    return {"split": "unknown"}


def stage1_experiments() -> list[dict[str, Any]]:
    return [
        {"id": "S1_E1", "name": "llm_small", "num_total_payloads": 600, "num_llm_sessions": 2, "llm_target_steps": 8},
        {"id": "S1_E2", "name": "llm_medium", "num_total_payloads": 800, "num_llm_sessions": 4, "llm_target_steps": 10},
        {"id": "S1_E3", "name": "llm_large", "num_total_payloads": 1200, "num_llm_sessions": 6, "llm_target_steps": 12},
    ]


def stage2_experiments() -> list[dict[str, Any]]:
    return [
        {"id": "S2_E1", "name": "delta_t_0p5", "delta_t": 0.5},
        {"id": "S2_E2", "name": "delta_t_1p0", "delta_t": 1.0},
        {"id": "S2_E3", "name": "delta_t_2p0", "delta_t": 2.0},
    ]


def stage3_experiments() -> list[dict[str, Any]]:
    return [
        {"id": "S3_E1", "name": "data_only", "alpha_flow": 0.0, "beta_latency": 0.0},
        {"id": "S3_E2", "name": "flow_only", "alpha_flow": 0.05, "beta_latency": 0.0},
        {"id": "S3_E3", "name": "full_physics", "alpha_flow": 0.05, "beta_latency": 0.05},
    ]


def stage4_experiments() -> list[dict[str, Any]]:
    return [
        {
            "id": "S4_E1",
            "name": "fedavg_clean",
            "aggregation": "fedavg",
            "simulate_poison_frac": 0.0,
            "poison_scale": 0.0,
        },
        {
            "id": "S4_E2",
            "name": "trimmed_clean",
            "aggregation": "trimmed_mean",
            "simulate_poison_frac": 0.0,
            "poison_scale": 0.0,
        },
        {
            "id": "S4_E3",
            "name": "shapley_poison",
            "aggregation": "shapley_proxy",
            "simulate_poison_frac": 0.34,
            "poison_scale": 0.2,
        },
    ]


def run_all(args: argparse.Namespace) -> Path:
    project_dir = Path(args.project_dir).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    pcap_file = Path(args.pcap_file).resolve()
    manifest_file = Path(args.manifest_file).resolve()
    if not pcap_file.exists():
        raise FileNotFoundError(f"PCAP missing: {pcap_file}")
    if not manifest_file.exists():
        raise FileNotFoundError(f"Manifest missing: {manifest_file}")

    py = args.python_bin
    shared_env = os.environ.copy()
    deepseek_key = args.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("LLM_API_KEY")
    if deepseek_key:
        shared_env["DEEPSEEK_API_KEY"] = deepseek_key

    summary: dict[str, Any] = {
        "created_at": now_iso(),
        "project_dir": str(project_dir),
        "pcap_file": str(pcap_file),
        "manifest_file": str(manifest_file),
        "stage1_capture_mode": "replay_existing_pcap",
        "experiments": [],
        "auxiliary": {},
    }

    # -------------------- Stage 1 --------------------
    for exp in stage1_experiments():
        exp_dir = out_dir / exp["id"]
        exp_dir.mkdir(parents=True, exist_ok=True)
        payload_file = exp_dir / "llm_payloads.json"
        log_file = exp_dir / "run.log"

        env = shared_env.copy()
        env.update(
            {
                "REQUIRE_REAL_LLM": "1",
                "KEEP_PROXY": "1" if args.keep_proxy else "0",
                "LLM_TIMEOUT_SEC": str(args.llm_timeout_sec),
                "NUM_TOTAL_PAYLOADS": str(exp["num_total_payloads"]),
                "NUM_LLM_SESSIONS": str(exp["num_llm_sessions"]),
                "LLM_TARGET_STEPS": str(exp["llm_target_steps"]),
                "OUTPUT_FILE": str(payload_file),
            }
        )
        cmd = [py, "generate_llm_payloads.py"]
        rc, sec = run_cmd(cmd, cwd=project_dir, log_path=log_file, env=env)

        rec: dict[str, Any] = {
            "id": exp["id"],
            "stage": 1,
            "name": exp["name"],
            "config": exp,
            "status": "ok" if rc == 0 else "failed",
            "return_code": rc,
            "duration_sec": sec,
            "log_file": str(log_file),
            "payload_file": str(payload_file),
        }
        if rc == 0 and payload_file.exists():
            rec["metrics"] = summarize_payload_file(payload_file)
        summary["experiments"].append(rec)
        if rc != 0:
            raise RuntimeError(f"Stage1 failed: {exp['id']}")

    # -------------------- Stage 2 --------------------
    stage2_graphs: dict[str, Path] = {}
    for exp in stage2_experiments():
        exp_dir = out_dir / exp["id"]
        exp_dir.mkdir(parents=True, exist_ok=True)
        graph_file = exp_dir / "st_graph.pt"
        log_file = exp_dir / "run.log"
        cmd = [
            py,
            "build_graph_v2.py",
            "--pcap-file",
            str(pcap_file),
            "--manifest-file",
            str(manifest_file),
            "--output-file",
            str(graph_file),
            "--delta-t",
            str(exp["delta_t"]),
            "--target-ip",
            args.target_ip,
            "--seed",
            str(args.seed),
        ]
        rc, sec = run_cmd(cmd, cwd=project_dir, log_path=log_file, env=shared_env)
        rec = {
            "id": exp["id"],
            "stage": 2,
            "name": exp["name"],
            "config": exp,
            "status": "ok" if rc == 0 else "failed",
            "return_code": rc,
            "duration_sec": sec,
            "log_file": str(log_file),
            "graph_file": str(graph_file),
        }
        if rc == 0 and graph_file.exists():
            rec["metrics"] = summarize_graph(graph_file)
            stage2_graphs[exp["id"]] = graph_file
        summary["experiments"].append(rec)
        if rc != 0:
            raise RuntimeError(f"Stage2 failed: {exp['id']}")

    # Stage 3/4 use the baseline graph from S2_E2 (delta_t = 1.0)
    graph_baseline = stage2_graphs.get("S2_E2")
    if graph_baseline is None:
        raise RuntimeError("Missing baseline graph S2_E2")

    # -------------------- Stage 3 --------------------
    stage3_models: dict[str, Path] = {}
    stage3_results: dict[str, Path] = {}
    for exp in stage3_experiments():
        exp_dir = out_dir / exp["id"]
        exp_dir.mkdir(parents=True, exist_ok=True)
        model_file = exp_dir / "pi_gnn_model.pt"
        result_file = exp_dir / "phase3_results.json"
        log_file = exp_dir / "run.log"

        cmd = [
            py,
            "training/pi_gnn_train_v2.py",
            "--graph-file",
            str(graph_baseline),
            "--model-file",
            str(model_file),
            "--results-file",
            str(result_file),
            "--epochs",
            str(args.stage3_epochs),
            "--alpha-flow",
            str(exp["alpha_flow"]),
            "--beta-latency",
            str(exp["beta_latency"]),
            "--capacity",
            str(args.capacity),
            "--seed",
            str(args.seed),
            "--force-cpu",
        ]
        rc, sec = run_cmd(cmd, cwd=project_dir, log_path=log_file, env=shared_env)
        rec: dict[str, Any] = {
            "id": exp["id"],
            "stage": 3,
            "name": exp["name"],
            "config": exp,
            "status": "ok" if rc == 0 else "failed",
            "return_code": rc,
            "duration_sec": sec,
            "log_file": str(log_file),
            "model_file": str(model_file),
            "results_file": str(result_file),
        }
        if rc == 0 and result_file.exists():
            r = load_json(result_file)
            rec["metrics"] = {
                "best_val_f1": float(r.get("best_val_f1", 0.0)),
                "best_epoch": int(r.get("best_epoch", 0)),
                "per_ip_accuracy": float(r.get("per_ip_accuracy", 0.0)),
                "test_metrics": pick_pignn_test_metrics(r),
            }
            stage3_models[exp["id"]] = model_file
            stage3_results[exp["id"]] = result_file
        summary["experiments"].append(rec)
        if rc != 0:
            raise RuntimeError(f"Stage3 failed: {exp['id']}")

    full_physics_model = stage3_models.get("S3_E3")
    full_physics_results = stage3_results.get("S3_E3")
    if full_physics_model is None or full_physics_results is None:
        raise RuntimeError("Missing S3_E3 outputs for baseline/plotting")

    # -------------------- Stage 4 --------------------
    stage4_results: dict[str, Path] = {}
    for exp in stage4_experiments():
        exp_dir = out_dir / exp["id"]
        exp_dir.mkdir(parents=True, exist_ok=True)
        model_file = exp_dir / "fed_pignn_model.pt"
        result_file = exp_dir / "phase4_federated_results.json"
        log_file = exp_dir / "run.log"

        cmd = [
            py,
            "training/fed_pignn.py",
            "--graph-file",
            str(graph_baseline),
            "--model-file",
            str(model_file),
            "--results-file",
            str(result_file),
            "--num-clients",
            str(args.num_clients),
            "--rounds",
            str(args.fed_rounds),
            "--local-epochs",
            str(args.fed_local_epochs),
            "--aggregation",
            str(exp["aggregation"]),
            "--simulate-poison-frac",
            str(exp["simulate_poison_frac"]),
            "--poison-scale",
            str(exp["poison_scale"]),
            "--alpha-flow",
            str(args.alpha_flow_fed),
            "--beta-latency",
            str(args.beta_latency_fed),
            "--capacity",
            str(args.capacity),
            "--client-cpus",
            str(args.client_cpus),
            "--client-gpus",
            "0.0",
            "--seed",
            str(args.seed),
            "--force-cpu",
        ]
        rc, sec = run_cmd(cmd, cwd=project_dir, log_path=log_file, env=shared_env)
        rec: dict[str, Any] = {
            "id": exp["id"],
            "stage": 4,
            "name": exp["name"],
            "config": exp,
            "status": "ok" if rc == 0 else "failed",
            "return_code": rc,
            "duration_sec": sec,
            "log_file": str(log_file),
            "model_file": str(model_file),
            "results_file": str(result_file),
        }
        if rc == 0 and result_file.exists():
            r = load_json(result_file)
            rec["metrics"] = pick_fed_test_metrics(r)
            stage4_results[exp["id"]] = result_file
        summary["experiments"].append(rec)
        if rc != 0:
            raise RuntimeError(f"Stage4 failed: {exp['id']}")

    # -------------------- Auxiliary: baseline + figures --------------------
    baseline_out = out_dir / "baseline_eval_results.json"
    baseline_log = out_dir / "baseline_eval.log"
    rc, sec = run_cmd(
        [
            py,
            "training/evaluate_baselines.py",
            "--graph-file",
            str(graph_baseline),
            "--pi-model-file",
            str(full_physics_model),
            "--output-file",
            str(baseline_out),
            "--seed",
            str(args.seed),
            "--force-cpu",
        ],
        cwd=project_dir,
        log_path=baseline_log,
        env=shared_env,
    )
    if rc != 0:
        raise RuntimeError("Aux baseline evaluation failed")

    fig_log = out_dir / "plot_results.log"
    rc, sec_plot = run_cmd(
        [
            py,
            "plot_results_v2.py",
            "--results-file",
            str(full_physics_results),
            "--graph-file",
            str(graph_baseline),
            "--baseline-file",
            str(baseline_out),
            "--output-dir",
            str(out_dir),
            "--prefix",
            "final",
        ],
        cwd=project_dir,
        log_path=fig_log,
        env=shared_env,
    )
    if rc != 0:
        raise RuntimeError("Aux plotting failed")

    summary["auxiliary"] = {
        "baseline_results_file": str(baseline_out),
        "baseline_log": str(baseline_log),
        "plot_log": str(fig_log),
        "figures": [
            str(out_dir / "final_fig1_loss_landscape.png"),
            str(out_dir / "final_fig2_entropy_distribution.png"),
            str(out_dir / "final_fig3_roc_comparison.png"),
            str(out_dir / "final_fig4_recall_fpr.png"),
        ],
    }
    summary["finished_at"] = now_iso()

    summary_file = out_dir / "summary_12_experiments.json"
    save_json(summary_file, summary)
    return summary_file


def parse_args() -> argparse.Namespace:
    base = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Run 12 experiments across 4 phases")
    p.add_argument("--project-dir", default=str(base))
    p.add_argument("--output-dir", default=str(base / "experiments_12"))
    p.add_argument("--python-bin", default=sys.executable)

    p.add_argument("--pcap-file", default=str(base / "full_arena_v2.pcap"))
    p.add_argument("--manifest-file", default=str(base / "arena_manifest_v2.json"))
    p.add_argument("--target-ip", default="10.0.0.100")

    p.add_argument("--deepseek-api-key", default="")
    p.add_argument("--keep-proxy", action="store_true")
    p.add_argument("--llm-timeout-sec", type=float, default=70.0)

    p.add_argument("--stage3-epochs", type=int, default=120)
    p.add_argument("--capacity", type=float, default=500.0)
    p.add_argument("--num-clients", type=int, default=3)
    p.add_argument("--fed-rounds", type=int, default=3)
    p.add_argument("--fed-local-epochs", type=int, default=2)
    p.add_argument("--alpha-flow-fed", type=float, default=0.05)
    p.add_argument("--beta-latency-fed", type=float, default=0.05)
    p.add_argument("--client-cpus", type=float, default=2.0)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    summary_file = run_all(args)
    print(f"[DONE] 12 experiments completed. Summary: {summary_file}")


if __name__ == "__main__":
    main()
