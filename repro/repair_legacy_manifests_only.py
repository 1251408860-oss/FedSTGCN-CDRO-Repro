#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_manifest(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def target_needs_fix(manifest: dict[str, Any], target_ip: str) -> bool:
    roles = manifest.get("roles", {}) if isinstance(manifest.get("roles"), dict) else {}
    ip_labels = manifest.get("ip_labels", {}) if isinstance(manifest.get("ip_labels"), dict) else {}
    return str(roles.get(target_ip, "")) != "target" or int(ip_labels.get(target_ip, 0)) != 0


def backup_manifest(src: Path, backup_root: Path) -> None:
    backup_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, backup_root / src.name)


def fix_manifest(manifest: dict[str, Any], target_ip: str, note: str) -> bool:
    roles = manifest.setdefault("roles", {})
    ip_labels = manifest.setdefault("ip_labels", {})
    if not isinstance(roles, dict) or not isinstance(ip_labels, dict):
        raise RuntimeError("manifest roles/ip_labels must be dicts")

    changed = False
    if str(roles.get(target_ip, "")) != "target":
        roles[target_ip] = "target"
        changed = True
    if int(ip_labels.get(target_ip, 0)) != 0:
        ip_labels[target_ip] = 0
        changed = True

    if changed:
        repair = manifest.setdefault("posthoc_repairs", [])
        if not isinstance(repair, list):
            repair = []
            manifest["posthoc_repairs"] = repair
        repair.append(
            {
                "date": "2026-03-10",
                "kind": "manifest_target_role_label_fix_only",
                "target_ip": target_ip,
                "note": note,
            }
        )
    return changed


def main() -> None:
    ap = argparse.ArgumentParser(description="Repair legacy capture manifests without re-capturing PCAPs.")
    ap.add_argument("--real-collection-dir", default="/home/user/FedSTGCN/real_collection")
    ap.add_argument("--scenarios", default="")
    ap.add_argument("--target-ip", default="10.0.0.100")
    ap.add_argument("--backup-dir", default="/home/user/FedSTGCN/repro/legacy_manifest_backups_20260310")
    ap.add_argument(
        "--note",
        default=(
            "Target role/label repaired post hoc so suite validation can rebuild graphs from legacy PCAPs. "
            "No new Mininet capture was produced in this step."
        ),
    )
    args = ap.parse_args()

    real_collection_dir = Path(args.real_collection_dir).resolve()
    selected = [x.strip() for x in str(args.scenarios).split(",") if x.strip()]
    scenario_dirs = [p for p in sorted(real_collection_dir.iterdir()) if p.is_dir()]
    if selected:
        wanted = set(selected)
        scenario_dirs = [p for p in scenario_dirs if p.name in wanted]

    changed = []
    for scenario_dir in scenario_dirs:
        manifest_file = scenario_dir / "arena_manifest_v2.json"
        if not manifest_file.exists():
            continue

        manifest = load_manifest(manifest_file)
        if not target_needs_fix(manifest, args.target_ip):
            continue

        backup_manifest(manifest_file, Path(args.backup_dir).resolve() / scenario_dir.name)
        if fix_manifest(manifest, args.target_ip, args.note):
            save_manifest(manifest_file, manifest)
            changed.append(scenario_dir.name)

    if changed:
        print("[DONE] repaired manifests:")
        for name in changed:
            print(f"  - {name}")
    else:
        print("[INFO] no manifest changes were needed")


if __name__ == "__main__":
    main()
