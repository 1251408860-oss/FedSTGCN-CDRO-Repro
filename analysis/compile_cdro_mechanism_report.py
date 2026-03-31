#!/usr/bin/env python3
from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def pooled_method_stats(summary: dict[str, Any], methods: list[str]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for method in methods:
        rows = [r["metrics"] for r in summary.get("runs", []) if r["method"] == method]
        out[method] = {
            k: float(statistics.mean([row[k] for row in rows])) if rows else 0.0
            for k in ["f1", "recall", "fpr", "ece", "brier"]
        }
    return out


def find_comparison(sig: dict[str, Any], a: str, b: str) -> dict[str, Any]:
    for comp in sig.get("comparisons", []):
        if comp.get("method_a") == a and comp.get("method_b") == b:
            return comp
    return {}


def fmt(v: float) -> str:
    return f"{v:.4f}"


def main() -> None:
    root = Path("/home/user/FedSTGCN")
    main_summary = load_json(root / "cdro_suite/main_rewrite_sw0_s5_v1/cdro_summary.json")
    main_sig = load_json(root / "cdro_suite/main_rewrite_sw0_s5_v1/cdro_significance.json")
    batch2_summary = load_json(root / "cdro_suite/batch2_rewrite_sw0_s3_v2/cdro_summary.json")
    batch2_sig = load_json(root / "cdro_suite/batch2_rewrite_sw0_s3_v2/cdro_significance.json")
    mech_main = load_json(root / "cdro_suite/mechanism_main_s3_v1/mechanism_probe_summary.json")
    mech_batch2 = load_json(root / "cdro_suite/mechanism_batch2_s3_v1/mechanism_probe_summary.json")
    fp_main = load_json(root / "cdro_suite/main_rewrite_sw0_s5_v1/fp_sources_ug_vs_noisy.json")
    fp_batch2 = load_json(root / "cdro_suite/batch2_rewrite_sw0_s3_v2/fp_sources_ug_vs_noisy.json")
    q_main = load_json(root / "cdro_suite/main_rewrite_sw0_s5_v1/weak_label_quality_sw0.json")
    q_batch2 = load_json(root / "cdro_suite/batch2_rewrite_sw0_s3_v2/weak_label_quality_sw0.json")

    main_stats = pooled_method_stats(main_summary, ["noisy_ce", "cdro_fixed", "cdro_ug"])
    batch2_stats = pooled_method_stats(batch2_summary, ["noisy_ce", "cdro_fixed", "cdro_ug"])
    main_comp = find_comparison(main_sig, "cdro_ug", "noisy_ce")
    batch2_comp = find_comparison(batch2_sig, "cdro_ug", "noisy_ce")

    lines: list[str] = []
    lines.append("# CDRO Mechanism Report")
    lines.append("")
    lines.append("## Main Results")
    lines.append("")
    lines.append("### Main Batch (4 protocols x 5 seeds)")
    for method in ["noisy_ce", "cdro_fixed", "cdro_ug"]:
        s = main_stats[method]
        lines.append(
            f"- {method}: F1={fmt(s['f1'])}, Recall={fmt(s['recall'])}, "
            f"FPR={fmt(s['fpr'])}, ECE={fmt(s['ece'])}, Brier={fmt(s['brier'])}"
        )
    if main_comp:
        lines.append(
            f"- cdro_ug vs noisy_ce: "
            f"delta_F1={main_comp['pooled']['f1']['delta_mean']:+.6f} (p={main_comp['pooled']['f1']['p_value']:.6g}), "
            f"delta_FPR={main_comp['pooled']['fpr']['delta_mean']:+.6f} (p={main_comp['pooled']['fpr']['p_value']:.6g})"
        )
    lines.append("")
    lines.append("### Batch2 (4 protocols x 3 seeds)")
    for method in ["noisy_ce", "cdro_fixed", "cdro_ug"]:
        s = batch2_stats[method]
        lines.append(
            f"- {method}: F1={fmt(s['f1'])}, Recall={fmt(s['recall'])}, "
            f"FPR={fmt(s['fpr'])}, ECE={fmt(s['ece'])}, Brier={fmt(s['brier'])}"
        )
    if batch2_comp:
        lines.append(
            f"- cdro_ug vs noisy_ce: "
            f"delta_F1={batch2_comp['pooled']['f1']['delta_mean']:+.6f} (p={batch2_comp['pooled']['f1']['p_value']:.6g}), "
            f"delta_FPR={batch2_comp['pooled']['fpr']['delta_mean']:+.6f} (p={batch2_comp['pooled']['fpr']['p_value']:.6g})"
        )

    lines.append("")
    lines.append("## Mechanism Probe")
    lines.append("")
    lines.append("### Main Batch Probe (3 seeds)")
    for variant in mech_main["config"]["variants"]:
        s = mech_main["stats"]["pooled"][variant]
        lines.append(
            f"- {variant}: F1={fmt(s['f1']['mean'])}, Recall={fmt(s['recall']['mean'])}, "
            f"FPR={fmt(s['fpr']['mean'])}, ECE={fmt(s['ece']['mean'])}, Brier={fmt(s['brier']['mean'])}"
        )
    lines.append("- Key reading: uniform hurts pooled F1; loss-only stays close to full; benign-trust changes drive FPR tradeoffs.")
    lines.append("")
    lines.append("### Batch2 Probe (3 seeds)")
    for variant in mech_batch2["config"]["variants"]:
        s = mech_batch2["stats"]["pooled"][variant]
        lines.append(
            f"- {variant}: F1={fmt(s['f1']['mean'])}, Recall={fmt(s['recall']['mean'])}, "
            f"FPR={fmt(s['fpr']['mean'])}, ECE={fmt(s['ece']['mean'])}, Brier={fmt(s['brier']['mean'])}"
        )
    lines.append("- Key reading: very low benign trust hurts batch2 FPR; sw0_full remains the safest compromise.")

    lines.append("")
    lines.append("## FP Source Analysis")
    lines.append("")
    lines.append("### Main Batch Pooled (cdro_ug vs noisy_ce)")
    for bucket, info in fp_main["pooled"]["weak_bucket"].items():
        lines.append(
            f"- weak bucket {bucket}: delta_FPR={info['delta_fpr']:+.6f}, delta_FP={info['delta_fp']}, "
            f"ug_FPR={info['method_a']['fpr']:.6f}, noisy_FPR={info['method_b']['fpr']:.6f}"
        )
    lines.append("### Batch2 Pooled (cdro_ug vs noisy_ce)")
    for bucket, info in fp_batch2["pooled"]["weak_bucket"].items():
        lines.append(
            f"- weak bucket {bucket}: delta_FPR={info['delta_fpr']:+.6f}, delta_FP={info['delta_fp']}, "
            f"ug_FPR={info['method_a']['fpr']:.6f}, noisy_FPR={info['method_b']['fpr']:.6f}"
        )
    lines.append("- Key reading: FPR gains come mainly from benign `abstain` and `weak_benign` regions, not from `weak_attack` benign nodes.")
    lines.append("")
    lines.append("### Main Attack-Strategy Group Buckets")
    for bucket, info in fp_main["per_protocol"]["weak_attack_strategy_ood"]["group_bucket"].items():
        lines.append(
            f"- {bucket}: delta_FPR={info['delta_fpr']:+.6f}, delta_FP={info['delta_fp']}"
        )
    lines.append("### Batch2 Pooled Group Buckets")
    for bucket, info in fp_batch2["pooled"]["group_bucket"].items():
        lines.append(
            f"- {bucket}: delta_FPR={info['delta_fpr']:+.6f}, delta_FP={info['delta_fp']}"
        )
    lines.append("- Key reading: batch2 FPR reduction is strongest in high-rho benign groups.")

    lines.append("")
    lines.append("## Weak-Label Quality")
    lines.append("")
    lines.append("### Main Batch")
    for proto, block in q_main["protocols"].items():
        atk = block["buckets"]["weak_attack"]
        ben = block["buckets"]["weak_benign"]
        lines.append(
            f"- {proto}: weak_attack precision={atk['precision']:.4f}, trust={atk['effective_trust']['mean']:.4f}; "
            f"weak_benign precision={ben['precision']:.4f}, trust={ben['effective_trust']['mean']:.4f}"
        )
    lines.append("### Batch2")
    for proto, block in q_batch2["protocols"].items():
        atk = block["buckets"]["weak_attack"]
        ben = block["buckets"]["weak_benign"]
        lines.append(
            f"- {proto}: weak_attack precision={atk['precision']:.4f}, trust={atk['effective_trust']['mean']:.4f}; "
            f"weak_benign precision={ben['precision']:.4f}, trust={ben['effective_trust']['mean']:.4f}"
        )
    lines.append("- Key reading: weak_attack is consistently more precise than weak_benign, which justifies asymmetric trust.")

    out = root / "cdro_suite/mechanism_report_20260317.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
