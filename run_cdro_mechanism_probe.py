#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
import statistics
import subprocess
from pathlib import Path
from typing import Any


VARIANT_ORDER = [
    "sw0_full",
    "sw0_lossonly",
    "sw0_uniform",
    "sw0_b035",
    "sw0_b075",
]


def run(cmd: list[str], cwd: Path, log: Path, done: Path | None = None) -> None:
    if done is not None and done.exists():
        return
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as f:
        proc = subprocess.run(cmd, cwd=str(cwd), stdout=f, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        raise RuntimeError(f"failed: {cmd} log={log}")


def signflip_p(x: list[float], y: list[float]) -> float:
    if len(x) != len(y) or len(x) == 0:
        return 1.0
    d = [a - b for a, b in zip(x, y)]
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
        for _ in range(4096):
            total += 1
            stat = abs(sum(di * (1.0 if rng.random() > 0.5 else -1.0) for di in d) / n)
            if stat >= obs - 1e-12:
                extreme += 1
    return float((extreme + 1) / (total + 1))


def stats(v: list[float]) -> dict[str, float]:
    if not v:
        return {"n": 0, "mean": 0.0, "std": 0.0}
    if len(v) == 1:
        return {"n": 1, "mean": float(v[0]), "std": 0.0}
    return {"n": len(v), "mean": float(statistics.mean(v)), "std": float(statistics.stdev(v))}


def read_metrics(path: Path) -> dict[str, float]:
    data = json.loads(path.read_text(encoding="utf-8"))
    metrics = data.get("final_eval", {}).get("test_temporal") or data.get("final_eval", {}).get("test_random") or {}
    return {
        "f1": float(metrics.get("f1", 0.0)),
        "recall": float(metrics.get("recall", 0.0)),
        "fpr": float(metrics.get("fpr", 0.0)),
        "ece": float(metrics.get("ece", 0.0)),
        "brier": float(metrics.get("brier", 0.0)),
    }


def build_variants() -> dict[str, dict[str, Any]]:
    return {
        "sw0_full": {
            "attack_trust": 0.90,
            "benign_trust": 0.55,
            "ug_priority_loss_scale": 1.0,
            "ug_uncertainty_scale": 0.20,
            "ug_disagreement_scale": 0.10,
            "ug_temperature": 0.35,
        },
        "sw0_lossonly": {
            "attack_trust": 0.90,
            "benign_trust": 0.55,
            "ug_priority_loss_scale": 1.0,
            "ug_uncertainty_scale": 0.0,
            "ug_disagreement_scale": 0.0,
            "ug_temperature": 0.35,
        },
        "sw0_uniform": {
            "attack_trust": 0.90,
            "benign_trust": 0.55,
            "ug_priority_loss_scale": 0.0,
            "ug_uncertainty_scale": 0.0,
            "ug_disagreement_scale": 0.0,
            "ug_temperature": 1.0,
        },
        "sw0_b035": {
            "attack_trust": 0.90,
            "benign_trust": 0.35,
            "ug_priority_loss_scale": 1.0,
            "ug_uncertainty_scale": 0.20,
            "ug_disagreement_scale": 0.10,
            "ug_temperature": 0.35,
        },
        "sw0_b075": {
            "attack_trust": 0.90,
            "benign_trust": 0.75,
            "ug_priority_loss_scale": 1.0,
            "ug_uncertainty_scale": 0.20,
            "ug_disagreement_scale": 0.10,
            "ug_temperature": 0.35,
        },
        "sw0_a080": {
            "attack_trust": 0.80,
            "benign_trust": 0.55,
            "ug_priority_loss_scale": 1.0,
            "ug_uncertainty_scale": 0.20,
            "ug_disagreement_scale": 0.10,
            "ug_temperature": 0.35,
        },
        "sw0_a095": {
            "attack_trust": 0.95,
            "benign_trust": 0.55,
            "ug_priority_loss_scale": 1.0,
            "ug_uncertainty_scale": 0.20,
            "ug_disagreement_scale": 0.10,
            "ug_temperature": 0.35,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Run CDRO sw0 mechanism probe on existing protocol graphs")
    ap.add_argument("--project-dir", default="/home/user/FedSTGCN")
    ap.add_argument("--python-bin", default="/home/user/miniconda3/envs/DL/bin/python")
    ap.add_argument("--protocol-graph-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--seeds", default="11,22,33")
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--patience", type=int, default=4)
    ap.add_argument("--force-cpu", action="store_true")
    ap.add_argument("--variants", default=",".join(VARIANT_ORDER))
    ap.add_argument("--protocols", default="weak_temporal_ood,weak_topology_ood,weak_attack_strategy_ood,label_prior_shift_ood")
    args = ap.parse_args()

    project = Path(args.project_dir)
    py = str(args.python_bin)
    protocol_dir = Path(args.protocol_graph_dir)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    seeds = [int(x.strip()) for x in str(args.seeds).split(",") if x.strip()]
    protocols = [x.strip() for x in str(args.protocols).split(",") if x.strip()]
    variant_names = [x.strip() for x in str(args.variants).split(",") if x.strip()]
    variants_all = build_variants()
    variants = {k: variants_all[k] for k in variant_names}

    rows: list[dict[str, Any]] = []
    for proto in protocols:
        g = protocol_dir / f"{proto}.pt"
        if not g.exists():
            raise FileNotFoundError(g)
        for seed in seeds:
            for vname, cfg in variants.items():
                exp = out / "runs" / f"{proto}__{vname}__s{seed}"
                exp.mkdir(parents=True, exist_ok=True)
                result_file = exp / "results.json"
                cmd = [
                    py,
                    "pi_gnn_train_cdro.py",
                    "--graph-file",
                    str(g),
                    "--model-file",
                    str(exp / "model.pt"),
                    "--results-file",
                    str(result_file),
                    "--method",
                    "cdro_ug",
                    "--epochs",
                    str(args.epochs),
                    "--patience",
                    str(args.patience),
                    "--lambda-dro",
                    "0.50",
                    "--attack-trust",
                    str(cfg["attack_trust"]),
                    "--benign-trust",
                    str(cfg["benign_trust"]),
                    "--ug-temperature",
                    str(cfg["ug_temperature"]),
                    "--ug-priority-loss-scale",
                    str(cfg["ug_priority_loss_scale"]),
                    "--ug-uncertainty-scale",
                    str(cfg["ug_uncertainty_scale"]),
                    "--ug-disagreement-scale",
                    str(cfg["ug_disagreement_scale"]),
                    "--ug-sample-weight-scale",
                    "0.0",
                    "--seed",
                    str(seed),
                ]
                if bool(args.force_cpu):
                    cmd.append("--force-cpu")
                run(cmd, cwd=project, log=exp / "run.log", done=result_file)
                rows.append(
                    {
                        "protocol": proto,
                        "seed": seed,
                        "variant": vname,
                        "result_file": str(result_file),
                        "metrics": read_metrics(result_file),
                    }
                )

    summary: dict[str, Any] = {
        "config": {
            "project_dir": str(project),
            "python_bin": py,
            "protocol_graph_dir": str(protocol_dir),
            "output_dir": str(out),
            "seeds": seeds,
            "protocols": protocols,
            "variants": variant_names,
        },
        "rows": rows,
        "stats": {},
        "p_values": {},
    }

    metrics = ["f1", "recall", "fpr", "ece", "brier"]
    for proto in protocols:
        summary["stats"][proto] = {}
        for vname in variant_names:
            summary["stats"][proto][vname] = {
                m: stats([r["metrics"][m] for r in rows if r["protocol"] == proto and r["variant"] == vname]) for m in metrics
            }

    summary["stats"]["pooled"] = {}
    for vname in variant_names:
        summary["stats"]["pooled"][vname] = {
            m: stats([r["metrics"][m] for r in rows if r["variant"] == vname]) for m in metrics
        }

    ref = "sw0_full"
    for vname in variant_names:
        if vname == ref:
            continue
        summary["p_values"][vname] = {"pooled": {}, "per_protocol": {}}
        for metric in metrics:
            x = [r["metrics"][metric] for r in rows if r["variant"] == vname]
            y = [r["metrics"][metric] for r in rows if r["variant"] == ref]
            summary["p_values"][vname]["pooled"][metric] = {
                "delta_mean": float(statistics.mean([a - b for a, b in zip(x, y)])) if x else 0.0,
                "p_value": signflip_p(x, y),
            }
        for proto in protocols:
            summary["p_values"][vname]["per_protocol"] = summary["p_values"][vname].get("per_protocol", {})
            summary["p_values"][vname]["per_protocol"][proto] = {}
            for metric in metrics:
                x = [r["metrics"][metric] for r in rows if r["variant"] == vname and r["protocol"] == proto]
                y = [r["metrics"][metric] for r in rows if r["variant"] == ref and r["protocol"] == proto]
                summary["p_values"][vname]["per_protocol"][proto][metric] = {
                    "delta_mean": float(statistics.mean([a - b for a, b in zip(x, y)])) if x else 0.0,
                    "p_value": signflip_p(x, y),
                }

    out_json = out / "mechanism_probe_summary.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = ["# CDRO sw0 Mechanism Probe", ""]
    lines.append("## Pooled")
    for vname in variant_names:
        s = summary["stats"]["pooled"][vname]
        lines.append(
            f"- {vname}: "
            f"F1={s['f1']['mean']:.4f}, Recall={s['recall']['mean']:.4f}, "
            f"FPR={s['fpr']['mean']:.4f}, ECE={s['ece']['mean']:.4f}, Brier={s['brier']['mean']:.4f}"
        )
    lines.append("")
    for proto in protocols:
        lines.append(f"## {proto}")
        for vname in variant_names:
            s = summary["stats"][proto][vname]
            lines.append(
                f"- {vname}: "
                f"F1={s['f1']['mean']:.4f}, Recall={s['recall']['mean']:.4f}, "
                f"FPR={s['fpr']['mean']:.4f}, ECE={s['ece']['mean']:.4f}"
            )
        lines.append("")
    (out / "mechanism_probe_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(out_json)


if __name__ == "__main__":
    main()
