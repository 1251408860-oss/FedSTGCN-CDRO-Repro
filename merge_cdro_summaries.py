#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def infer_tag(summary: dict[str, Any], path: Path) -> str:
    cfg = summary.get("config", {})
    base_graph = str(cfg.get("base_graph", "")).strip()
    if base_graph:
        return Path(base_graph).stem
    return path.parent.name


def main() -> None:
    ap = argparse.ArgumentParser(description="Merge multiple CDRO summary JSON files")
    ap.add_argument("--summary-json", action="append", required=True)
    ap.add_argument("--output-json", required=True)
    ap.add_argument("--name", default="merged")
    args = ap.parse_args()

    merged_runs: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for raw in args.summary_json:
        path = Path(raw).resolve()
        summary = load_json(path)
        tag = infer_tag(summary, path)
        sources.append({"tag": tag, "summary_json": str(path)})
        for run in summary.get("runs", []):
            row = dict(run)
            row["source_tag"] = tag
            row["source_summary_json"] = str(path)
            merged_runs.append(row)

    out = {
        "name": str(args.name),
        "sources": sources,
        "runs": merged_runs,
        "config": {
            "summary_json": [str(Path(p).resolve()) for p in args.summary_json],
        },
    }
    save_json(Path(args.output_json).resolve(), out)
    print(os.path.abspath(args.output_json))


if __name__ == "__main__":
    main()
