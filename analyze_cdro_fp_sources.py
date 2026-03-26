#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F


def load_json(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def summarize_bucket(fp: int, benign_total: int, prob_sum: float) -> dict[str, float]:
    return {
        "benign_total": int(benign_total),
        "fp": int(fp),
        "fpr": float(fp / benign_total) if benign_total > 0 else 0.0,
        "mean_prob_attack": float(prob_sum / benign_total) if benign_total > 0 else 0.0,
    }


def aggregate_bucket_rows(rows: list[dict[str, float]]) -> dict[str, float]:
    benign_total = sum(int(r["benign_total"]) for r in rows)
    fp = sum(int(r["fp"]) for r in rows)
    prob_sum = sum(float(r["mean_prob_attack"]) * int(r["benign_total"]) for r in rows)
    return summarize_bucket(fp=fp, benign_total=benign_total, prob_sum=prob_sum)


def build_group_bucket_names() -> dict[int, str]:
    return {
        0: "low_rho_low_uncertainty",
        1: "low_rho_high_uncertainty",
        2: "high_rho_low_uncertainty",
        3: "high_rho_high_uncertainty",
    }


def analyze_run(run: dict[str, Any]) -> dict[str, dict[str, dict[str, float]]]:
    result = load_json(run["result_file"])
    logits_path = str(run["result_file"]).replace("results.json", "results_logits.pt")
    logits_bundle = torch.load(logits_path, map_location="cpu", weights_only=False)
    graph = torch.load(result["config"]["graph_file"], map_location="cpu", weights_only=False)

    threshold = float(result.get("best_threshold", 0.5))
    probs = F.softmax(logits_bundle["logits"].float(), dim=1)[:, 1]
    test_mask = logits_bundle["temporal_test_mask"].bool()
    benign_mask = test_mask & (logits_bundle["y_true"].long() == 0)
    pred_attack = probs >= threshold

    weak_label = logits_bundle["weak_label"].long()
    weak_bucket_map = {
        -1: "abstain",
        0: "weak_benign",
        1: "weak_attack",
    }

    group_thresholds = result.get("group_thresholds", {})
    u_mid = float(group_thresholds.get("uncertainty_mid", 0.0))
    r_mid = float(group_thresholds.get("rho_mid", 0.0))
    uncertainty = graph.weak_uncertainty.float().cpu()
    rho = graph.rho_proxy.float().cpu()
    group_ids = (rho >= r_mid).long() * 2 + (uncertainty >= u_mid).long()
    group_names = result.get("group_names", build_group_bucket_names())

    weak_rows: dict[str, dict[str, float]] = {}
    for raw_label, label_name in weak_bucket_map.items():
        mask = benign_mask & (weak_label == raw_label)
        benign_total = int(mask.sum().item())
        fp = int((pred_attack & mask).sum().item())
        prob_sum = float(probs[mask].sum().item()) if benign_total > 0 else 0.0
        weak_rows[label_name] = summarize_bucket(fp=fp, benign_total=benign_total, prob_sum=prob_sum)

    group_rows: dict[str, dict[str, float]] = {}
    for gid, name in sorted(group_names.items(), key=lambda x: int(x[0])):
        gid_int = int(gid)
        mask = benign_mask & (group_ids == gid_int)
        benign_total = int(mask.sum().item())
        fp = int((pred_attack & mask).sum().item())
        prob_sum = float(probs[mask].sum().item()) if benign_total > 0 else 0.0
        group_rows[str(name)] = summarize_bucket(fp=fp, benign_total=benign_total, prob_sum=prob_sum)

    return {"weak_bucket": weak_rows, "group_bucket": group_rows}


def main() -> None:
    ap = argparse.ArgumentParser(description="Analyze benign false-positive sources for CDRO suites")
    ap.add_argument("--summary-json", required=True)
    ap.add_argument("--method-a", required=True)
    ap.add_argument("--method-b", required=True)
    ap.add_argument("--output-json", required=True)
    args = ap.parse_args()

    summary = load_json(args.summary_json)
    runs = summary.get("runs", [])

    by_key: dict[tuple[str, int, str], dict[str, Any]] = {}
    for run in runs:
        key = (str(run["protocol"]), int(run["seed"]), str(run["method"]))
        by_key[key] = run

    keys = sorted({(proto, seed) for proto, seed, _method in by_key})
    rows: list[dict[str, Any]] = []
    weak_pooled: dict[str, dict[str, list[dict[str, float]]]] = defaultdict(lambda: defaultdict(list))
    group_pooled: dict[str, dict[str, list[dict[str, float]]]] = defaultdict(lambda: defaultdict(list))
    weak_by_proto: dict[str, dict[str, dict[str, list[dict[str, float]]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    group_by_proto: dict[str, dict[str, dict[str, list[dict[str, float]]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for proto, seed in keys:
        run_a = by_key.get((proto, seed, args.method_a))
        run_b = by_key.get((proto, seed, args.method_b))
        if run_a is None or run_b is None:
            continue
        a_stats = analyze_run(run_a)
        b_stats = analyze_run(run_b)
        rows.append({"protocol": proto, "seed": seed, "method_a": a_stats, "method_b": b_stats})

        for bucket_name, bucket_rows in a_stats["weak_bucket"].items():
            weak_pooled["method_a"][bucket_name].append(bucket_rows)
            weak_by_proto[proto]["method_a"][bucket_name].append(bucket_rows)
        for bucket_name, bucket_rows in b_stats["weak_bucket"].items():
            weak_pooled["method_b"][bucket_name].append(bucket_rows)
            weak_by_proto[proto]["method_b"][bucket_name].append(bucket_rows)
        for bucket_name, bucket_rows in a_stats["group_bucket"].items():
            group_pooled["method_a"][bucket_name].append(bucket_rows)
            group_by_proto[proto]["method_a"][bucket_name].append(bucket_rows)
        for bucket_name, bucket_rows in b_stats["group_bucket"].items():
            group_pooled["method_b"][bucket_name].append(bucket_rows)
            group_by_proto[proto]["method_b"][bucket_name].append(bucket_rows)

    def build_bucket_summary(bucket_pool: dict[str, dict[str, list[dict[str, float]]]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        bucket_names = sorted(set(bucket_pool["method_a"]) | set(bucket_pool["method_b"]))
        for bucket_name in bucket_names:
            sa = aggregate_bucket_rows(bucket_pool["method_a"].get(bucket_name, []))
            sb = aggregate_bucket_rows(bucket_pool["method_b"].get(bucket_name, []))
            out[bucket_name] = {
                "method_a": sa,
                "method_b": sb,
                "delta_fpr": float(sa["fpr"] - sb["fpr"]),
                "delta_fp": int(sa["fp"] - sb["fp"]),
                "delta_mean_prob_attack": float(sa["mean_prob_attack"] - sb["mean_prob_attack"]),
            }
        return out

    output: dict[str, Any] = {
        "summary_json": str(Path(args.summary_json).resolve()),
        "method_a": args.method_a,
        "method_b": args.method_b,
        "rows": rows,
        "pooled": {
            "weak_bucket": build_bucket_summary(weak_pooled),
            "group_bucket": build_bucket_summary(group_pooled),
        },
        "per_protocol": {},
    }

    for proto in sorted(weak_by_proto):
        output["per_protocol"][proto] = {
            "weak_bucket": build_bucket_summary(weak_by_proto[proto]),
            "group_bucket": build_bucket_summary(group_by_proto[proto]),
        }

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
