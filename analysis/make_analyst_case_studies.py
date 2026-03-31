#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch


VIEW_NAMES = ["rate_view", "entropy_view", "port_view", "latency_view", "physics_view"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def suite_output_dir(summary: dict[str, Any]) -> Path:
    return Path(summary["config"]["output_dir"]).resolve()


def weak_label_name(v: int) -> str:
    return {-1: "abstain", 0: "weak_benign", 1: "weak_attack"}.get(int(v), "unknown")


def compute_trust(graph: Any, idx: int, attack_trust: float = 0.90, benign_trust: float = 0.55) -> tuple[float, float]:
    posterior_attack = float(graph.weak_posterior[idx, 1].item())
    confidence = abs(posterior_attack - 0.5) * 2.0
    agreement = float(graph.weak_agreement[idx].item())
    uncertainty = float(graph.weak_uncertainty[idx].item())
    weak_label = int(graph.weak_label[idx].item())
    if weak_label == 1:
        trust = float(attack_trust) * (0.70 + 0.30 * agreement) * (0.80 + 0.20 * confidence)
    elif weak_label == 0:
        trust = float(benign_trust) * (0.75 + 0.25 * agreement) * (0.80 + 0.20 * confidence) * (1.0 - 0.25 * uncertainty)
    else:
        trust = 0.0
    trust = max(0.0, min(0.97, trust))
    if weak_label == 1:
        hybrid_attack = trust + (1.0 - trust) * posterior_attack
    elif weak_label == 0:
        hybrid_attack = (1.0 - trust) * posterior_attack
    else:
        hybrid_attack = posterior_attack
    return float(trust), float(hybrid_attack)


def case_rows(
    graph: Any,
    roles: dict[str, str],
    noisy_result: dict[str, Any],
    ug_result: dict[str, Any],
    noisy_logits: dict[str, Any],
    ug_logits: dict[str, Any],
) -> list[dict[str, Any]]:
    out = []
    noisy_prob = noisy_logits["probs"][:, 1].float()
    ug_prob = ug_logits["probs"][:, 1].float()
    noisy_thr = float(noisy_result["best_threshold"])
    ug_thr = float(ug_result["best_threshold"])
    test_mask = noisy_logits["temporal_test_mask"].bool()
    y_true = noisy_logits["y_true"].long()
    group_thresholds = ug_result.get("group_thresholds", {})
    u_mid = float(group_thresholds.get("uncertainty_mid", 0.0))
    r_mid = float(group_thresholds.get("rho_mid", 0.0))
    group_names = {int(k): v for k, v in ug_result.get("group_names", {0: "all"}).items()}

    for idx in torch.nonzero(test_mask, as_tuple=False).view(-1).tolist():
        ip = graph.source_ips[int(graph.ip_idx[idx])]
        role = roles.get(ip, "unknown")
        trust, hybrid_attack = compute_trust(graph, idx)
        group_id = int((float(graph.rho_proxy[idx].item()) >= r_mid)) * 2 + int((float(graph.weak_uncertainty[idx].item()) >= u_mid))
        out.append(
            {
                "idx": idx,
                "ip": ip,
                "role": role,
                "window": int(graph.window_idx[idx].item()),
                "truth": int(y_true[idx].item()),
                "weak_label": int(graph.weak_label[idx].item()),
                "weak_label_name": weak_label_name(int(graph.weak_label[idx].item())),
                "posterior_attack": float(graph.weak_posterior[idx, 1].item()),
                "agreement": float(graph.weak_agreement[idx].item()),
                "uncertainty": float(graph.weak_uncertainty[idx].item()),
                "rho_proxy": float(graph.rho_proxy[idx].item()),
                "trust": trust,
                "hybrid_attack": hybrid_attack,
                "group_id": group_id,
                "group_name": group_names.get(group_id, str(group_id)),
                "view_probs": [float(v) for v in graph.weak_view_probs[idx].tolist()],
                "noisy_prob": float(noisy_prob[idx].item()),
                "ug_prob": float(ug_prob[idx].item()),
                "noisy_threshold": noisy_thr,
                "ug_threshold": ug_thr,
                "noisy_pred": int(noisy_prob[idx].item() >= noisy_thr),
                "ug_pred": int(ug_prob[idx].item() >= ug_thr),
            }
        )
    return out


def select_case(rows: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool], score: Callable[[dict[str, Any]], tuple]) -> dict[str, Any]:
    candidates = [row for row in rows if predicate(row)]
    if not candidates:
        raise RuntimeError("No candidate case found for requested predicate")
    return sorted(candidates, key=score, reverse=True)[0]


def main() -> None:
    ap = argparse.ArgumentParser(description="Build analyst-facing case-study artifacts")
    ap.add_argument("--external-summary", default="/home/user/FedSTGCN/cdro_suite/batch2_baselineplus_s3_v1/cdro_summary.json")
    ap.add_argument("--output-dir", default="/home/user/FedSTGCN/cdro_suite/analyst_case_studies_s3_v1")
    ap.add_argument("--paper-dir", default="/home/user/FedSTGCN/cdro_suite/paper_ready_plus")
    args = ap.parse_args()

    external_summary = load_json(Path(args.external_summary).resolve())
    out_dir = Path(args.output_dir).resolve()
    paper_dir = Path(args.paper_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    paper_dir.mkdir(parents=True, exist_ok=True)

    roles = load_json(Path(external_summary["config"]["manifest_file"]).resolve()).get("roles", {})
    suite_dir = suite_output_dir(external_summary)
    spec = [
        {
            "title": "Benign FP Suppressed",
            "protocol": "weak_temporal_ood",
            "seed": 22,
            "predicate": lambda row: row["truth"] == 0 and row["noisy_pred"] == 1 and row["ug_pred"] == 0 and row["weak_label"] >= 0,
            "score": lambda row: (row["noisy_prob"] - row["ug_prob"], row["uncertainty"]),
            "why": "Noisy-CE raises a false alert on a benign user, while CDRO-UG suppresses it despite strong rate/latency views.",
        },
        {
            "title": "True Positive Recovered",
            "protocol": "weak_topology_ood",
            "seed": 33,
            "predicate": lambda row: row["truth"] == 1 and row["noisy_pred"] == 0 and row["ug_pred"] == 1 and row["weak_label"] >= 0,
            "score": lambda row: (row["uncertainty"], row["agreement"]),
            "why": "CDRO-UG keeps a true positive that Noisy-CE misses in a high-uncertainty slowburn region.",
        },
        {
            "title": "Mimic TP Preserved",
            "protocol": "weak_attack_strategy_ood",
            "seed": 11,
            "predicate": lambda row: row["truth"] == 1 and row["noisy_pred"] == 1 and row["ug_pred"] == 1 and row["weak_label"] == 0,
            "score": lambda row: (row["uncertainty"], row["ug_prob"]),
            "why": "Even under a misleading weak-benign label, CDRO-UG still keeps the mimic attack score high enough to alert.",
        },
    ]

    cases: list[dict[str, Any]] = []
    for item in spec:
        proto = item["protocol"]
        seed = int(item["seed"])
        graph = torch.load(suite_dir / "protocol_graphs" / f"{proto}.pt", map_location="cpu", weights_only=False)
        noisy_result = load_json(suite_dir / "runs" / f"{proto}__noisy_ce__seed{seed}" / "results.json")
        ug_result = load_json(suite_dir / "runs" / f"{proto}__cdro_ug__seed{seed}" / "results.json")
        noisy_logits = torch.load(suite_dir / "runs" / f"{proto}__noisy_ce__seed{seed}" / "results_logits.pt", map_location="cpu", weights_only=False)
        ug_logits = torch.load(suite_dir / "runs" / f"{proto}__cdro_ug__seed{seed}" / "results_logits.pt", map_location="cpu", weights_only=False)
        rows = case_rows(graph, roles, noisy_result, ug_result, noisy_logits, ug_logits)
        chosen = select_case(rows, item["predicate"], item["score"])
        chosen["title"] = item["title"]
        chosen["protocol"] = proto
        chosen["seed"] = seed
        chosen["narrative"] = item["why"]
        cases.append(chosen)

    (out_dir / "analyst_case_studies.json").write_text(json.dumps({"cases": cases}, indent=2), encoding="utf-8")

    fig_path = paper_dir / "fig10_analyst_case_studies.png"
    fig, axes = plt.subplots(len(cases), 2, figsize=(12, 10))
    for row_i, case in enumerate(cases):
        ax_l = axes[row_i, 0]
        ax_r = axes[row_i, 1]
        ax_l.barh(VIEW_NAMES, case["view_probs"], color="#c96f53")
        ax_l.set_xlim(0.0, 1.0)
        ax_l.set_title(case["title"])
        ax_l.set_xlabel("Attack Probability")
        ax_l.grid(axis="x", alpha=0.2)

        labels = ["weak_posterior", "hybrid_target", "noisy_prob", "ug_prob"]
        values = [case["posterior_attack"], case["hybrid_attack"], case["noisy_prob"], case["ug_prob"]]
        colors = ["#7A8892", "#D68C45", "#444444", "#1F6E8C"]
        ax_r.barh(labels, values, color=colors)
        ax_r.axvline(case["noisy_threshold"], color="#444444", linestyle="--", linewidth=1, label="Noisy thr")
        ax_r.axvline(case["ug_threshold"], color="#1F6E8C", linestyle=":", linewidth=1.2, label="UG thr")
        ax_r.set_xlim(0.0, 1.0)
        ax_r.grid(axis="x", alpha=0.2)
        meta = (
            f"truth={case['truth']}  weak={case['weak_label_name']}\n"
            f"role={case['role']}  window={case['window']}\n"
            f"group={case['group_name']}\n"
            f"agreement={case['agreement']:.2f}  uncertainty={case['uncertainty']:.2f}\n"
            f"trust={case['trust']:.2f}  rho={case['rho_proxy']:.2f}"
        )
        ax_r.text(0.02, 0.02, meta, transform=ax_r.transAxes, fontsize=9, va="bottom", ha="left", bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "#cccccc"})
        if row_i == 0:
            ax_r.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(fig_path, dpi=220, bbox_inches="tight")
    plt.close(fig)

    lines = [
        "# Analyst-Facing Case Studies",
        "",
        f"Figure: `{fig_path.name}`.",
        "",
    ]
    for case in cases:
        lines.extend(
            [
                f"## {case['title']}",
                "",
                f"- Protocol / seed: `{case['protocol']}` / `{case['seed']}`",
                f"- IP / role: `{case['ip']}` / `{case['role']}`",
                f"- Truth / weak label: `{case['truth']}` / `{case['weak_label_name']}`",
                f"- Noisy-CE prob / verdict: `{case['noisy_prob']:.3f}` / `{case['noisy_pred']}` at threshold `{case['noisy_threshold']:.2f}`",
                f"- CDRO-UG prob / verdict: `{case['ug_prob']:.3f}` / `{case['ug_pred']}` at threshold `{case['ug_threshold']:.2f}`",
                f"- Weak posterior attack / trust-adjusted target attack: `{case['posterior_attack']:.3f}` / `{case['hybrid_attack']:.3f}`",
                f"- Agreement / uncertainty / trust: `{case['agreement']:.3f}` / `{case['uncertainty']:.3f}` / `{case['trust']:.3f}`",
                f"- Group: `{case['group_name']}`",
                f"- Analyst readout: {case['narrative']}",
                "",
            ]
        )
    (paper_dir / "analyst_case_studies.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
