#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any


def run_cmd(cmd: list[str], cwd: Path, log_file: Path, skip_if_exists: Path | None = None) -> tuple[int, float, bool]:
    if skip_if_exists is not None and skip_if_exists.exists():
        return 0, 0.0, True
    t0 = time.time()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("w", encoding="utf-8") as f:
        p = subprocess.run(cmd, cwd=str(cwd), stdout=f, stderr=subprocess.STDOUT)
    return int(p.returncode), float(time.time() - t0), False


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def summary_stats(vals: list[float]) -> dict[str, float]:
    if not vals:
        return {"n": 0, "mean": 0.0, "std": 0.0}
    if len(vals) == 1:
        return {"n": 1, "mean": float(vals[0]), "std": 0.0}
    return {"n": len(vals), "mean": float(statistics.mean(vals)), "std": float(statistics.stdev(vals))}


def paired_signflip_pvalue(x: list[float], y: list[float], n_perm: int = 4096) -> float:
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


def parse_int_list(s: str) -> list[int]:
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def parse_ab_grid(s: str) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for item in [x.strip() for x in s.split(",") if x.strip()]:
        a, b = item.split(":")
        out.append((float(a), float(b)))
    return out


def pick_test_metrics(phase3: dict[str, Any]) -> dict[str, float]:
    fe = phase3.get("final_eval", {})
    m = None
    if isinstance(fe.get("test_temporal"), dict):
        m = fe["test_temporal"]
    elif isinstance(fe.get("test_random"), dict):
        m = fe["test_random"]
    else:
        m = {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "tp": 0, "fp": 0, "fn": 0, "tn": 0}

    tp, fp, fn, tn = int(m.get("tp", 0)), int(m.get("fp", 0)), int(m.get("fn", 0)), int(m.get("tn", 0))
    fpr = float(fp / max(fp + tn, 1))
    out = dict(m)
    out["fpr"] = fpr
    return out


def run_stage3_once(
    py: str,
    project: Path,
    out_dir: Path,
    protocol: str,
    seed: int,
    model_name: str,
    graph_file: Path,
    epochs: int,
    alpha: float,
    beta: float,
    capacity: float,
    physics_context: bool = False,
) -> dict[str, Any]:
    exp_id = f"{protocol}__{model_name}__seed{seed}"
    exp_dir = out_dir / "stage3" / exp_id
    exp_dir.mkdir(parents=True, exist_ok=True)

    model_file = exp_dir / "pi_gnn_model.pt"
    result_file = exp_dir / "phase3_results.json"
    log_file = exp_dir / "run.log"

    cmd = [
        py,
        "training/pi_gnn_train_v2.py",
        "--graph-file",
        str(graph_file),
        "--model-file",
        str(model_file),
        "--results-file",
        str(result_file),
        "--epochs",
        str(epochs),
        "--alpha-flow",
        str(alpha),
        "--beta-latency",
        str(beta),
        "--capacity",
        str(capacity),
        "--warmup-epochs",
        "25",
        "--patience",
        "35",
        "--seed",
        str(seed),
        "--force-cpu",
    ]
    if physics_context:
        cmd.append("--physics-context")
    rc, sec, skipped = run_cmd(cmd, cwd=project, log_file=log_file, skip_if_exists=result_file)
    if rc != 0:
        raise RuntimeError(f"stage3 failed: {exp_id} (log={log_file})")

    result = load_json(result_file)
    metrics = pick_test_metrics(result)
    return {
        "protocol": protocol,
        "seed": seed,
        "model": model_name,
        "alpha": alpha,
        "beta": beta,
        "capacity": capacity,
        "metrics": metrics,
        "result_file": str(result_file),
        "log": str(log_file),
        "duration_sec": sec,
        "skipped": skipped,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Central PI-boost suite with hard overlap protocols")
    ap.add_argument("--project-dir", default="/home/user/FedSTGCN")
    ap.add_argument("--python-bin", default="/home/user/miniconda3/envs/DL/bin/python")
    ap.add_argument("--scenario-dir", default="/home/user/FedSTGCN/real_collection/scenario_h_mimic_heavy_overlap")
    ap.add_argument("--output-dir", default="/home/user/FedSTGCN/central_boost_suite")

    ap.add_argument("--delta-t", type=float, default=1.0)
    ap.add_argument("--capacity", type=float, default=120000.0)
    ap.add_argument("--epochs", type=int, default=140)

    ap.add_argument("--search-seeds", default="11,22,33")
    ap.add_argument("--full-seeds", default="11,22,33,44,55,66,77,88,99")
    ap.add_argument("--ab-grid", default="0.01:0.01,0.02:0.01,0.03:0.02,0.05:0.03")

    ap.add_argument("--train-keep-frac", type=float, default=0.75)
    ap.add_argument("--val-keep-frac", type=float, default=0.85)
    ap.add_argument("--test-keep-frac", type=float, default=0.95)
    ap.add_argument("--min-keep-per-class", type=int, default=64)
    ap.add_argument("--holdout-attack-type", default="mimic")
    ap.add_argument("--protocols", default="temporal_ood,topology_ood,attack_strategy_ood")
    ap.add_argument("--camouflage-test-attacks", action="store_true")
    ap.add_argument("--camouflage-noise-scale", type=float, default=0.35)
    ap.add_argument("--physics-context", action="store_true")

    args = ap.parse_args()

    project = Path(args.project_dir).resolve()
    scenario = Path(args.scenario_dir).resolve()
    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    py = args.python_bin
    search_seeds = parse_int_list(args.search_seeds)
    full_seeds = parse_int_list(args.full_seeds)
    ab_grid = parse_ab_grid(args.ab_grid)

    summary: dict[str, Any] = {
        "config": vars(args),
        "timestamps": {"start": time.strftime("%Y-%m-%d %H:%M:%S")},
        "graph": {},
        "protocol_graphs": {},
        "search": {},
        "runs": [],
        "statistics": {},
    }

    # A) Build graph from scenario capture
    pcap = scenario / "full_arena_v2.pcap"
    manifest = scenario / "arena_manifest_v2.json"
    graph_file = out / "graphs" / "scenario_h_graph.pt"
    graph_file.parent.mkdir(parents=True, exist_ok=True)

    cmd_build = [
        py,
        "build_graph_v2.py",
        "--pcap-file",
        str(pcap),
        "--manifest-file",
        str(manifest),
        "--output-file",
        str(graph_file),
        "--target-ip",
        "10.0.0.100",
        "--delta-t",
        str(args.delta_t),
        "--seed",
        "42",
    ]
    rc, sec, skipped = run_cmd(cmd_build, cwd=project, log_file=out / "logs" / "build_graph.log", skip_if_exists=graph_file)
    if rc != 0:
        raise RuntimeError("build_graph_v2 failed")
    summary["graph"] = {"graph_file": str(graph_file), "duration_sec": sec, "skipped": skipped}

    # B) Prepare hard-overlap protocol graphs
    protocols = [x.strip() for x in str(args.protocols).split(",") if x.strip()]
    for proto in protocols:
        g = out / "protocol_graphs" / f"{proto}.pt"
        g.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            py,
            "data_prep/prepare_hard_protocol_graph.py",
            "--input-graph",
            str(graph_file),
            "--output-graph",
            str(g),
            "--protocol",
            proto,
            "--manifest-file",
            str(manifest),
            "--holdout-attack-type",
            args.holdout_attack_type,
            "--seed",
            "42",
            "--hard-overlap",
            "--train-keep-frac",
            str(args.train_keep_frac),
            "--val-keep-frac",
            str(args.val_keep_frac),
            "--test-keep-frac",
            str(args.test_keep_frac),
            "--min-keep-per-class",
            str(args.min_keep_per_class),
        ]
        if bool(args.camouflage_test_attacks):
            cmd += ["--camouflage-test-attacks", "--camouflage-noise-scale", str(args.camouflage_noise_scale)]
        rc, sec, skipped = run_cmd(cmd, cwd=project, log_file=out / "logs" / f"prep_{proto}.log", skip_if_exists=g)
        if rc != 0:
            raise RuntimeError(f"prepare_hard_protocol_graph failed: {proto}")
        summary["protocol_graphs"][proto] = {"graph_file": str(g), "duration_sec": sec, "skipped": skipped}

    # C) Small alpha/beta search over hard protocols (paired delta vs data-only)
    data_baseline: dict[tuple[str, int], float] = {}
    for proto in protocols:
        g = Path(summary["protocol_graphs"][proto]["graph_file"])
        for seed in search_seeds:
            run = run_stage3_once(
                py=py,
                project=project,
                out_dir=out / "search",
                protocol=proto,
                seed=seed,
                model_name="data_only",
                graph_file=g,
                epochs=max(100, args.epochs - 20),
                alpha=0.0,
                beta=0.0,
                capacity=args.capacity,
                physics_context=False,
            )
            data_baseline[(proto, seed)] = float(run["metrics"]["f1"])

    best_ab = None
    best_delta = -1e9
    ab_rows = []
    for alpha, beta in ab_grid:
        deltas = []
        for proto in protocols:
            g = Path(summary["protocol_graphs"][proto]["graph_file"])
            for seed in search_seeds:
                run = run_stage3_once(
                    py=py,
                    project=project,
                    out_dir=out / "search",
                    protocol=proto,
                    seed=seed,
                    model_name=f"physics_a{alpha}_b{beta}",
                    graph_file=g,
                    epochs=max(100, args.epochs - 20),
                    alpha=alpha,
                    beta=beta,
                    capacity=args.capacity,
                    physics_context=bool(args.physics_context),
                )
                f1 = float(run["metrics"]["f1"])
                deltas.append(f1 - data_baseline[(proto, seed)])

        row = {
            "alpha": alpha,
            "beta": beta,
            "delta_f1_mean": float(statistics.mean(deltas)) if deltas else 0.0,
            "delta_f1_std": float(statistics.stdev(deltas)) if len(deltas) > 1 else 0.0,
            "n": len(deltas),
        }
        ab_rows.append(row)
        if row["delta_f1_mean"] > best_delta:
            best_delta = row["delta_f1_mean"]
            best_ab = (alpha, beta)

    if best_ab is None:
        best_ab = (0.03, 0.02)
    summary["search"] = {
        "rows": ab_rows,
        "best_alpha": best_ab[0],
        "best_beta": best_ab[1],
        "best_delta_f1_mean": best_delta,
    }

    # D) Full-seed evaluation
    for proto in protocols:
        g = Path(summary["protocol_graphs"][proto]["graph_file"])
        for seed in full_seeds:
            r_data = run_stage3_once(
                py=py,
                project=project,
                out_dir=out,
                protocol=proto,
                seed=seed,
                model_name="data_only",
                graph_file=g,
                epochs=args.epochs,
                alpha=0.0,
                beta=0.0,
                capacity=args.capacity,
                physics_context=False,
            )
            summary["runs"].append(r_data)

            r_phy = run_stage3_once(
                py=py,
                project=project,
                out_dir=out,
                protocol=proto,
                seed=seed,
                model_name="physics_boost",
                graph_file=g,
                epochs=args.epochs,
                alpha=float(best_ab[0]),
                beta=float(best_ab[1]),
                capacity=args.capacity,
                physics_context=bool(args.physics_context),
            )
            summary["runs"].append(r_phy)

    # E) Stats + significance
    stats: dict[str, Any] = {}
    pooled_data_f1 = []
    pooled_phy_f1 = []

    for proto in protocols:
        proto_runs = [r for r in summary["runs"] if r["protocol"] == proto]
        ds = [r for r in proto_runs if r["model"] == "data_only"]
        ps = [r for r in proto_runs if r["model"] == "physics_boost"]
        ds = sorted(ds, key=lambda x: x["seed"])
        ps = sorted(ps, key=lambda x: x["seed"])

        f1_d = [float(r["metrics"]["f1"]) for r in ds]
        f1_p = [float(r["metrics"]["f1"]) for r in ps]
        rc_d = [float(r["metrics"]["recall"]) for r in ds]
        rc_p = [float(r["metrics"]["recall"]) for r in ps]
        fpr_d = [float(r["metrics"]["fpr"]) for r in ds]
        fpr_p = [float(r["metrics"]["fpr"]) for r in ps]

        pooled_data_f1.extend(f1_d)
        pooled_phy_f1.extend(f1_p)

        stats[proto] = {
            "data_only": {
                "f1": summary_stats(f1_d),
                "recall": summary_stats(rc_d),
                "fpr": summary_stats(fpr_d),
            },
            "physics_boost": {
                "f1": summary_stats(f1_p),
                "recall": summary_stats(rc_p),
                "fpr": summary_stats(fpr_p),
            },
            "significance_vs_data_only": {
                "p_value_f1": paired_signflip_pvalue(f1_p, f1_d),
                "p_value_recall": paired_signflip_pvalue(rc_p, rc_d),
                "p_value_fpr": paired_signflip_pvalue(fpr_p, fpr_d),
                "mean_delta_f1": float(statistics.mean([a - b for a, b in zip(f1_p, f1_d)])) if f1_d else 0.0,
            },
        }

    summary["statistics"] = {
        "per_protocol": stats,
        "pooled": {
            "p_value_f1": paired_signflip_pvalue(pooled_phy_f1, pooled_data_f1),
            "mean_delta_f1": float(statistics.mean([a - b for a, b in zip(pooled_phy_f1, pooled_data_f1)])) if pooled_data_f1 else 0.0,
            "data_only": summary_stats(pooled_data_f1),
            "physics_boost": summary_stats(pooled_phy_f1),
        },
    }

    summary["timestamps"]["end"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_json(out / "central_boost_summary.json", summary)

    print("=== central_boost done ===")
    print("best alpha/beta:", best_ab)
    print("pooled p(F1):", summary["statistics"]["pooled"]["p_value_f1"])
    print("pooled delta F1:", summary["statistics"]["pooled"]["mean_delta_f1"])
    print("summary:", out / "central_boost_summary.json")


if __name__ == "__main__":
    main()
