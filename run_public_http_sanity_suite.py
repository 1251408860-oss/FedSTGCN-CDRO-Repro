#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any


DATASET_CONFIG = {
    "csic2010": {
        "prep_script": "prepare_public_http_csic2010.py",
        "prep_output_subdir": "public_http_csic2010",
        "bundle_name": "public_http_csic2010_bundle.pt",
        "summary_name": "public_http_csic2010_summary.json",
        "suite_output_dir": "/home/user/FedSTGCN/cdro_suite/public_http_csic2010_s3_v1",
        "protocol_name": "public_http_csic2010",
    },
    "biblio_us17": {
        "prep_script": "prepare_public_http_biblio_us17.py",
        "prep_output_subdir": "public_http_biblio_us17",
        "bundle_name": "public_http_biblio_us17_bundle.pt",
        "summary_name": "public_http_biblio_us17_summary.json",
        "suite_output_dir": "/home/user/FedSTGCN/cdro_suite/public_http_biblio_us17_s3_v1",
        "protocol_name": "public_http_biblio_us17",
    },
}


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


def tail_text(path: Path, lines: int = 20) -> str:
    if not path.exists():
        return ""
    text_lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if not text_lines:
        return ""
    return "\n".join(text_lines[-lines:])


def main() -> None:
    ap = argparse.ArgumentParser(description="Run compact public HTTP sanity suite")
    ap.add_argument("--project-dir", default="/home/user/FedSTGCN")
    ap.add_argument("--python-bin", default="/home/user/miniconda3/envs/DL/bin/python")
    ap.add_argument("--dataset", choices=sorted(DATASET_CONFIG), default="biblio_us17")
    ap.add_argument("--output-dir", default=None)
    ap.add_argument("--methods", default="noisy_ce,posterior_ce,cdro_fixed,cdro_ug")
    ap.add_argument("--seeds", default="11,22,33")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--patience", type=int, default=8)
    ap.add_argument("--hidden-dim", type=int, default=128)
    ap.add_argument("--dropout", type=float, default=0.20)
    ap.add_argument("--lambda-dro", type=float, default=0.50)
    ap.add_argument("--biblio-tarball", default="/home/user/FedSTGCN/biblio_us17/Biblio-US17.tar.gz")
    ap.add_argument("--force-cpu", action="store_true")
    args = ap.parse_args()

    project = Path(args.project_dir).resolve()
    py = str(args.python_bin)
    dataset_cfg = DATASET_CONFIG[str(args.dataset)]
    out_dir = Path(args.output_dir or dataset_cfg["suite_output_dir"]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    methods = [s.strip() for s in args.methods.split(",") if s.strip()]
    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]

    prep_cmd = [
        py,
        dataset_cfg["prep_script"],
        "--output-dir",
        str(project / dataset_cfg["prep_output_subdir"]),
    ]
    if str(args.dataset) == "biblio_us17":
        prep_cmd.extend(["--tarball", str(args.biblio_tarball)])
    prep_log = out_dir / "logs" / "prepare_public_http.log"
    rc, sec = run_cmd(prep_cmd, cwd=project, log_file=prep_log)
    if rc != 0:
        tail = tail_text(prep_log)
        raise RuntimeError(
            f"public HTTP benchmark preparation failed; see {prep_log}\n{tail}".rstrip()
        )

    bundle_file = project / dataset_cfg["prep_output_subdir"] / dataset_cfg["bundle_name"]
    prep_summary = project / dataset_cfg["prep_output_subdir"] / dataset_cfg["summary_name"]

    summary: dict[str, Any] = {
        "config": vars(args),
        "dataset": str(args.dataset),
        "timestamps": {"start": time.strftime("%Y-%m-%d %H:%M:%S")},
        "public_bundle": {
            "bundle_file": str(bundle_file),
            "summary_json": str(prep_summary),
            "duration_sec": sec,
        },
        "runs": [],
    }

    for method in methods:
        for seed in seeds:
            exp_id = f"public_http__{args.dataset}__{method}__seed{seed}"
            exp_dir = out_dir / "runs" / exp_id
            exp_dir.mkdir(parents=True, exist_ok=True)
            result_file = exp_dir / "results.json"
            cmd = [
                py,
                "train_tabular_cdro.py",
                "--bundle-file",
                str(bundle_file),
                "--model-file",
                str(exp_dir / "model.pt"),
                "--results-file",
                str(result_file),
                "--method",
                method,
                "--hidden-dim",
                str(args.hidden_dim),
                "--dropout",
                str(args.dropout),
                "--epochs",
                str(args.epochs),
                "--patience",
                str(args.patience),
                "--lambda-dro",
                str(args.lambda_dro),
                "--seed",
                str(seed),
            ]
            if bool(args.force_cpu):
                cmd.append("--force-cpu")
            run_log = exp_dir / "run.log"
            rc, sec = run_cmd(cmd, cwd=project, log_file=run_log)
            if rc != 0:
                tail = tail_text(run_log)
                raise RuntimeError(f"tabular training failed for {exp_id}; see {run_log}\n{tail}".rstrip())
            result = load_json(result_file)
            summary["runs"].append(
                {
                    "id": exp_id,
                    "protocol": dataset_cfg["protocol_name"],
                    "method": method,
                    "seed": seed,
                    "duration_sec": sec,
                    "result_file": str(result_file),
                    "metrics": result.get("final_eval", {}).get("test_temporal", {}),
                }
            )

    summary["timestamps"]["end"] = time.strftime("%Y-%m-%d %H:%M:%S")
    summary_path = out_dir / "public_summary.json"
    save_json(summary_path, summary)

    sig_path = out_dir / "public_significance.json"
    sig_cmd = [
        py,
        "run_cdro_significance.py",
        "--summary-json",
        str(summary_path),
        "--output-json",
        str(sig_path),
        "--compare",
        "cdro_ug,noisy_ce",
        "--compare",
        "cdro_ug,posterior_ce",
        "--compare",
        "cdro_ug,cdro_fixed",
    ]
    sig_log = out_dir / "logs" / "public_significance.log"
    rc, _ = run_cmd(sig_cmd, cwd=project, log_file=sig_log)
    if rc != 0:
        tail = tail_text(sig_log)
        raise RuntimeError(f"public significance computation failed; see {sig_log}\n{tail}".rstrip())

    print(summary_path)


if __name__ == "__main__":
    main()
