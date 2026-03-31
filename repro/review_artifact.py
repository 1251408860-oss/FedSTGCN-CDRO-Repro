#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

LEGACY_PREFIX = "/home/user/FedSTGCN/"
CORE_METHODS = ["noisy_ce", "cdro_fixed", "cdro_ug"]
ROLE_MANIFESTS = {
    "main_baselineplus_s3_v1": "repro/artifact_manifests/main_roles_manifest.json",
    "main_rewrite_sw0_s5_v1": "repro/artifact_manifests/main_roles_manifest.json",
    "batch2_baselineplus_s3_v1": "repro/artifact_manifests/external_j_roles_manifest.json",
    "batch2_rewrite_sw0_s3_v2": "repro/artifact_manifests/external_j_roles_manifest.json",
}
TRAIN_KEY_MAP = {
    "hidden_dim": "--hidden-dim",
    "heads": "--heads",
    "dropout": "--dropout",
    "lr": "--lr",
    "weight_decay": "--weight-decay",
    "epochs": "--epochs",
    "patience": "--patience",
    "lambda_dro": "--lambda-dro",
    "pseudo_attack_thr": "--pseudo-attack-thr",
    "pseudo_benign_thr": "--pseudo-benign-thr",
    "pseudo_weight": "--pseudo-weight",
    "attack_trust": "--attack-trust",
    "benign_trust": "--benign-trust",
    "pseudo_attack_trust": "--pseudo-attack-trust",
    "pseudo_benign_trust": "--pseudo-benign-trust",
    "ug_temperature": "--ug-temperature",
    "ug_priority_loss_scale": "--ug-priority-loss-scale",
    "ug_uncertainty_scale": "--ug-uncertainty-scale",
    "ug_disagreement_scale": "--ug-disagreement-scale",
    "ug_sample_weight_scale": "--ug-sample-weight-scale",
    "gce_q": "--gce-q",
    "sce_alpha": "--sce-alpha",
    "sce_beta": "--sce-beta",
    "bootstrap_beta": "--bootstrap-beta",
    "elr_lambda": "--elr-lambda",
    "elr_beta": "--elr-beta",
    "temp_scale_min": "--temp-scale-min",
    "temp_scale_max": "--temp-scale-max",
    "temp_scale_steps": "--temp-scale-steps",
    "train_mask_name": "--train-mask-name",
    "val_mask_name": "--val-mask-name",
    "test_mask_name": "--test-mask-name",
    "temporal_test_mask_name": "--temporal-test-mask-name",
    "seed": "--seed",
    "capacity": "--capacity",
}
BOOL_KEYS = {
    "force_cpu": "--force-cpu",
    "physics_context": "--physics-context",
    "posthoc_temperature_scaling": "--posthoc-temperature-scaling",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_text_auto(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "gb18030", "gbk", "latin-1"):
        try:
            text = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        if "\x00" in text and not enc.startswith("utf-16"):
            continue
        return text
    return raw.decode("latin-1", errors="replace")


def csv_equal(path_a: Path, path_b: Path) -> bool:
    rows_a = list(csv.reader(read_text_auto(path_a).splitlines()))
    rows_b = list(csv.reader(read_text_auto(path_b).splitlines()))
    return rows_a == rows_b


def resolve_path(repo_root: Path, raw: str | Path) -> Path:
    text = str(raw)
    if text.startswith(LEGACY_PREFIX):
        return (repo_root / text[len(LEGACY_PREFIX):]).resolve()
    path = Path(text)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def repo_rel(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def ensure_imports(repo_root: Path):
    analysis_dir = repo_root / "analysis"
    for path in (repo_root, analysis_dir):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from make_cdro_paper_ready import aggregate_cdro_summary, find_comparison, plot_pooled_results, METHOD_LABELS
    return aggregate_cdro_summary, find_comparison, plot_pooled_results, METHOD_LABELS


def rebind_summary(repo_root: Path, source_summary_path: Path, output_dir: Path, python_bin: str) -> tuple[Path, Path]:
    summary = load_json(source_summary_path)
    suite_name = source_summary_path.parent.name
    rebound = {
        "config": dict(summary.get("config", {})),
        "timestamps": dict(summary.get("timestamps", {})),
        "weak_label": dict(summary.get("weak_label", {})),
        "protocol_graphs": dict(summary.get("protocol_graphs", {})),
        "runs": [],
    }
    rebound["config"]["project_dir"] = "."
    rebound["config"]["python_bin"] = python_bin
    rebound["config"]["manifest_file"] = ROLE_MANIFESTS[suite_name]
    rebound["config"]["output_dir"] = repo_rel(repo_root, output_dir)
    for key in ["pt_file", "json_file"]:
        if key in rebound["weak_label"]:
            rebound["weak_label"][key] = repo_rel(repo_root, resolve_path(repo_root, rebound["weak_label"][key]))
    for proto, block in rebound["protocol_graphs"].items():
        for key in ["graph_file", "summary_file"]:
            if key in block:
                block[key] = repo_rel(repo_root, resolve_path(repo_root, block[key]))
    for run in summary["runs"]:
        rebound["runs"].append(
            {
                **run,
                "result_file": repo_rel(repo_root, resolve_path(repo_root, run["result_file"])),
            }
        )
    summary_path = output_dir / "cdro_summary.json"
    sig_path = output_dir / "cdro_significance.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    save_json(summary_path, rebound)
    subprocess.run(
        [
            python_bin,
            "analysis/run_cdro_significance.py",
            "--summary-json",
            repo_rel(repo_root, summary_path),
            "--output-json",
            repo_rel(repo_root, sig_path),
            "--compare",
            "cdro_ug,noisy_ce",
            "--compare",
            "cdro_ug,cdro_fixed",
        ],
        cwd=str(repo_root),
        check=True,
    )
    return summary_path, sig_path


def build_train_cmd(repo_root: Path, python_bin: str, graph_rel: str, out_run_dir: Path, result_cfg: dict[str, Any], suite_cfg: dict[str, Any]) -> list[str]:
    cmd = [
        python_bin,
        "training/pi_gnn_train_cdro.py",
        "--graph-file",
        graph_rel,
        "--model-file",
        repo_rel(repo_root, out_run_dir / "model.pt"),
        "--results-file",
        repo_rel(repo_root, out_run_dir / "results.json"),
        "--logits-file",
        repo_rel(repo_root, out_run_dir / "results_logits.pt"),
        "--method",
        str(result_cfg["method"]),
    ]
    merged = dict(suite_cfg)
    merged.update(result_cfg)
    for key, flag in TRAIN_KEY_MAP.items():
        if key in merged:
            cmd.extend([flag, str(merged[key])])
    for key, flag in BOOL_KEYS.items():
        if bool(merged.get(key)):
            cmd.append(flag)
    return cmd


def replay_suite(repo_root: Path, source_summary_path: Path, output_dir: Path, python_bin: str) -> tuple[Path, Path]:
    source = load_json(source_summary_path)
    suite_name = source_summary_path.parent.name
    replay = {
        "config": dict(source.get("config", {})),
        "timestamps": {"start": time.strftime("%Y-%m-%d %H:%M:%S")},
        "weak_label": dict(source.get("weak_label", {})),
        "protocol_graphs": dict(source.get("protocol_graphs", {})),
        "runs": [],
        "replay_source_summary": repo_rel(repo_root, source_summary_path),
    }
    replay["config"]["project_dir"] = "."
    replay["config"]["python_bin"] = python_bin
    replay["config"]["manifest_file"] = ROLE_MANIFESTS[suite_name]
    replay["config"]["output_dir"] = repo_rel(repo_root, output_dir)
    for key in ["pt_file", "json_file"]:
        if key in replay["weak_label"]:
            replay["weak_label"][key] = repo_rel(repo_root, resolve_path(repo_root, replay["weak_label"][key]))
    for proto, block in replay["protocol_graphs"].items():
        for key in ["graph_file", "summary_file"]:
            if key in block:
                block[key] = repo_rel(repo_root, resolve_path(repo_root, block[key]))

    for run in source["runs"]:
        ref_result = load_json(resolve_path(repo_root, run["result_file"]))
        graph_rel = repo_rel(repo_root, resolve_path(repo_root, ref_result["config"]["graph_file"]))
        out_run_dir = output_dir / "runs" / str(run["id"])
        out_run_dir.mkdir(parents=True, exist_ok=True)
        cmd = build_train_cmd(repo_root, python_bin, graph_rel, out_run_dir, ref_result["config"], source.get("config", {}))
        log_path = out_run_dir / "run.log"
        t0 = time.time()
        with log_path.open("w", encoding="utf-8") as log_f:
            subprocess.run(cmd, cwd=str(repo_root), stdout=log_f, stderr=subprocess.STDOUT, check=True)
        result_path = out_run_dir / "results.json"
        replay_result = load_json(result_path)
        replay["runs"].append(
            {
                "id": run["id"],
                "protocol": run["protocol"],
                "method": run["method"],
                "seed": int(run["seed"]),
                "duration_sec": float(time.time() - t0),
                "result_file": repo_rel(repo_root, result_path),
                "metrics": replay_result["final_eval"]["test_temporal"],
            }
        )

    replay["timestamps"]["end"] = time.strftime("%Y-%m-%d %H:%M:%S")
    summary_path = output_dir / "cdro_summary.json"
    sig_path = output_dir / "cdro_significance.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    save_json(summary_path, replay)
    subprocess.run(
        [
            python_bin,
            "analysis/run_cdro_significance.py",
            "--summary-json",
            repo_rel(repo_root, summary_path),
            "--output-json",
            repo_rel(repo_root, sig_path),
            "--compare",
            "cdro_ug,noisy_ce",
            "--compare",
            "cdro_ug,cdro_fixed",
        ],
        cwd=str(repo_root),
        check=True,
    )
    return summary_path, sig_path


def build_core_table(repo_root: Path, main_summary_path: Path, external_summary_path: Path, external_sig_path: Path, output_csv: Path) -> None:
    aggregate_cdro_summary, find_comparison, _plot, METHOD_LABELS = ensure_imports(repo_root)
    main_stats = aggregate_cdro_summary(load_json(main_summary_path))
    external_stats = aggregate_cdro_summary(load_json(external_summary_path))
    external_sig = load_json(external_sig_path)
    ug_vs_noisy = find_comparison(external_sig, "cdro_ug", "noisy_ce")
    rows = [[
        "method",
        "method_label",
        "main_pooled_f1",
        "main_pooled_fpr",
        "external_j_pooled_f1",
        "external_j_pooled_fpr",
        "external_j_delta_fpr_vs_noisy_ce",
        "external_j_p_fpr_vs_noisy_ce",
    ]]
    for method in CORE_METHODS:
        delta = ""
        p_value = ""
        if method == "cdro_ug":
            delta = f"{ug_vs_noisy['pooled']['fpr']['delta_mean']:.4f}"
            p_value = f"{ug_vs_noisy['pooled']['fpr']['p_value']:.4f}"
        rows.append(
            [
                method,
                METHOD_LABELS[method],
                f"{main_stats['pooled'][method]['f1']['mean']:.4f}",
                f"{main_stats['pooled'][method]['fpr']['mean']:.4f}",
                f"{external_stats['pooled'][method]['f1']['mean']:.4f}",
                f"{external_stats['pooled'][method]['fpr']['mean']:.4f}",
                delta,
                p_value,
            ]
        )
    write_csv(output_csv, rows)


def build_maintext_deploy(table18_csv: Path, output_csv: Path) -> None:
    rows = list(csv.DictReader(read_text_auto(table18_csv).splitlines()))
    out = [[
        "method",
        "method_label",
        "frozen_f1",
        "frozen_fpr",
        "frozen_attack_ip_detect_rate",
        "frozen_mean_first_alert_delay_windows",
        "frozen_false_alerts_per_run",
        "frozen_false_alerts_per_10k_benign",
    ]]
    method_labels = {
        "noisy_ce": "Noisy-CE",
        "cdro_fixed": "CDRO-Fixed",
        "cdro_ug": "CDRO-UG (sw0)",
    }
    for row in rows:
        method = row["method"]
        out.append(
            [
                method,
                method_labels[method],
                f"{float(row['frozen_f1_mean']):.3f}",
                f"{float(row['frozen_fpr_mean']):.3f}",
                f"{float(row['frozen_detect_rate_mean']):.3f}",
                f"{float(row['frozen_delay_mean']):.2f}",
                f"{float(row['frozen_fp_mean']):.1f}",
                f"{float(row['frozen_benign_per10k_mean']):.0f}",
            ]
        )
    write_csv(output_csv, out)


def compare_results(repo_root: Path, ref_summary_path: Path, new_summary_path: Path) -> dict[str, float]:
    ref_summary = load_json(ref_summary_path)
    new_summary = load_json(new_summary_path)
    ref_runs = {str(run['id']): run for run in ref_summary['runs']}
    max_metric_delta = 0.0
    max_threshold_delta = 0.0
    compared = 0
    for run in new_summary['runs']:
        ref_result = load_json(resolve_path(repo_root, ref_runs[str(run['id'])]['result_file']))
        new_result = load_json(resolve_path(repo_root, run['result_file']))
        for metric in ["f1", "recall", "fpr", "ece", "brier"]:
            max_metric_delta = max(max_metric_delta, abs(float(new_result['final_eval']['test_temporal'][metric]) - float(ref_result['final_eval']['test_temporal'][metric])))
        max_threshold_delta = max(max_threshold_delta, abs(float(new_result['best_threshold']) - float(ref_result['best_threshold'])))
        compared += 1
    return {
        "runs_compared": compared,
        "max_metric_delta": max_metric_delta,
        "max_threshold_delta": max_threshold_delta,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Reviewer-facing reproduction pipeline")
    ap.add_argument("--repo-root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--work-dir", default="review_artifact")
    ap.add_argument("--python-bin", default=sys.executable)
    ap.add_argument("--skip-rerun", action="store_true")
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    work_root = (repo_root / args.work_dir).resolve()
    mode = "reference" if args.skip_rerun else "rerun"
    out_root = work_root / mode
    out_root.mkdir(parents=True, exist_ok=True)

    ref_main = repo_root / "cdro_suite/main_rewrite_sw0_s5_v1/cdro_summary.json"
    ref_ext = repo_root / "cdro_suite/batch2_rewrite_sw0_s3_v2/cdro_summary.json"
    if args.skip_rerun:
        main_summary, main_sig = rebind_summary(repo_root, ref_main, out_root / "bound_main", args.python_bin)
        ext_summary, ext_sig = rebind_summary(repo_root, ref_ext, out_root / "bound_external_j", args.python_bin)
    else:
        main_summary, main_sig = replay_suite(repo_root, ref_main, out_root / "replayed_suites/main_rewrite_sw0_s5_v1", args.python_bin)
        ext_summary, ext_sig = replay_suite(repo_root, ref_ext, out_root / "replayed_suites/batch2_rewrite_sw0_s3_v2", args.python_bin)

    paper_dir = out_root / "paper_ready"
    deploy_dir = out_root / "deployment_checks"
    paper_dir.mkdir(parents=True, exist_ok=True)
    deploy_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            args.python_bin,
            "analysis/make_deployment_artifacts.py",
            "--main-summary",
            repo_rel(repo_root, main_summary),
            "--external-summary",
            repo_rel(repo_root, ext_summary),
            "--output-dir",
            repo_rel(repo_root, deploy_dir),
            "--paper-dir",
            repo_rel(repo_root, paper_dir),
        ],
        cwd=str(repo_root),
        check=True,
    )

    build_core_table(repo_root, main_summary, ext_summary, ext_sig, paper_dir / "table_maintext_core_results.csv")
    build_maintext_deploy(paper_dir / "table18_deployment_checks.csv", paper_dir / "table_maintext_deployment_transfer.csv")
    aggregate_cdro_summary, _find_comparison, plot_pooled_results, _method_labels = ensure_imports(repo_root)
    plot_pooled_results(
        paper_dir / "fig1_pooled_results.png",
        aggregate_cdro_summary(load_json(main_summary)),
        aggregate_cdro_summary(load_json(ext_summary)),
    )

    core_ref = repo_root / "cdro_suite/paper_ready_plus/table_maintext_core_results.csv"
    deploy_ref = repo_root / "cdro_suite/paper_ready_plus/table_maintext_deployment_transfer.csv"
    core_match = csv_equal(paper_dir / "table_maintext_core_results.csv", core_ref)
    deploy_match = csv_equal(paper_dir / "table_maintext_deployment_transfer.csv", deploy_ref)

    result_comparison = None
    if not args.skip_rerun:
        main_cmp = compare_results(repo_root, ref_main, main_summary)
        ext_cmp = compare_results(repo_root, ref_ext, ext_summary)
        result_comparison = {
            "runs_compared": int(main_cmp["runs_compared"] + ext_cmp["runs_compared"]),
            "max_metric_delta": max(main_cmp["max_metric_delta"], ext_cmp["max_metric_delta"]),
            "max_threshold_delta": max(main_cmp["max_threshold_delta"], ext_cmp["max_threshold_delta"]),
        }

    report = {
        "mode": mode,
        "main_summary": repo_rel(repo_root, main_summary),
        "external_summary": repo_rel(repo_root, ext_summary),
        "main_significance": repo_rel(repo_root, main_sig),
        "external_significance": repo_rel(repo_root, ext_sig),
        "generated_core_table": repo_rel(repo_root, paper_dir / "table_maintext_core_results.csv"),
        "generated_deployment_table": repo_rel(repo_root, paper_dir / "table_maintext_deployment_transfer.csv"),
        "core_table_exact_match": core_match,
        "deployment_table_exact_match": deploy_match,
        "result_comparison": result_comparison,
    }
    save_json(out_root / "repro_report.json", report)
    lines = [
        "# Reviewer Reproduction Report",
        "",
        f"- Mode: `{mode}`",
        f"- Core table exact match: `{core_match}`",
        f"- Deployment table exact match: `{deploy_match}`",
        f"- Main summary: `{report['main_summary']}`",
        f"- External summary: `{report['external_summary']}`",
        f"- Generated pooled figure: `{repo_rel(repo_root, paper_dir / 'fig1_pooled_results.png')}`",
    ]
    if result_comparison:
        lines.extend(
            [
                f"- Runs compared: `{result_comparison['runs_compared']}`",
                f"- Max per-run metric delta: `{result_comparison['max_metric_delta']:.10f}`",
                f"- Max threshold delta: `{result_comparison['max_threshold_delta']:.10f}`",
            ]
        )
    write_text(out_root / "REPRO_SUMMARY.md", "\n".join(lines))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()




