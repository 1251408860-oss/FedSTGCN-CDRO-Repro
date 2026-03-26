#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


STALE_IFACE_RE = re.compile(r"^(s\d+-eth\d+|user\d+-eth\d+|bot\d+-eth\d+|target-eth\d+)$")
PROCESS_PATTERNS = [
    ("mininet_arena_v2.py", ["pkill", "-9", "-f", "mininet_arena_v2.py"]),
    ("bot_attack.py", ["pkill", "-9", "-f", "bot_attack.py"]),
    ("benign_traffic.py", ["pkill", "-9", "-f", "benign_traffic.py"]),
    ("locust", ["pkill", "-9", "-f", "locust"]),
    ("tcpdump", ["pkill", "-INT", "-f", "tcpdump"]),
    ("target_server.py", ["pkill", "-9", "-f", "target_server.py"]),
]


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def scenario_needs_repair(manifest: dict[str, Any]) -> bool:
    topology = manifest.get("topology", {}) if isinstance(manifest, dict) else {}
    run_config = manifest.get("run_config", {}) if isinstance(manifest, dict) else {}
    target_ip = str(topology.get("target_ip", "10.0.0.100"))
    roles = manifest.get("roles", {}) if isinstance(manifest.get("roles"), dict) else {}
    ip_labels = manifest.get("ip_labels", {}) if isinstance(manifest.get("ip_labels"), dict) else {}
    bots = int(topology.get("bots", 0))

    return bots >= 71 or str(roles.get(target_ip, "")) != "target" or int(ip_labels.get(target_ip, 0)) != 0


def collect_scenarios(real_collection_dir: Path, selected: list[str]) -> list[Path]:
    scenario_dirs = [p for p in sorted(real_collection_dir.iterdir()) if p.is_dir()]
    if selected:
        wanted = set(selected)
        return [p for p in scenario_dirs if p.name in wanted]

    out: list[Path] = []
    for scenario_dir in scenario_dirs:
        manifest = scenario_dir / "arena_manifest_v2.json"
        if not manifest.exists():
            continue
        if scenario_needs_repair(load_manifest(manifest)):
            out.append(scenario_dir)
    return out


def backup_existing_files(scenario_dir: Path, backup_root: Path) -> None:
    backup_dir = backup_root / scenario_dir.name
    backup_dir.mkdir(parents=True, exist_ok=True)
    for name in ("arena_manifest_v2.json", "full_arena_v2.pcap", "mininet.log", "mininet_repair.log"):
        src = scenario_dir / name
        if src.exists():
            shutil.copy2(src, backup_dir / src.name)


def append_log(log_file: Path, message: str) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(message.rstrip() + "\n")


def run_cmd(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    log_file: Path,
    *,
    append: bool = True,
    timeout_sec: int | None = None,
    allowed_rcs: set[int] | None = None,
) -> int:
    mode = "a" if append else "w"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open(mode, encoding="utf-8") as fh:
        fh.write(f"\n[CMD] {' '.join(cmd)}\n")
        fh.flush()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(cwd),
                env=env,
                stdout=fh,
                stderr=subprocess.STDOUT,
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired as exc:
            fh.write(f"[TIMEOUT] exceeded {timeout_sec}s: {' '.join(cmd)}\n")
            raise RuntimeError(f"command timed out after {timeout_sec}s: {' '.join(cmd)}") from exc

    allowed = allowed_rcs if allowed_rcs is not None else {0}
    if proc.returncode not in allowed:
        raise RuntimeError(f"command failed rc={proc.returncode}: {' '.join(cmd)}")
    return int(proc.returncode)


def list_stale_interfaces() -> list[str]:
    proc = subprocess.run(["ip", "-o", "link", "show"], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return []

    out: list[str] = []
    for line in proc.stdout.splitlines():
        m = re.match(r"^\d+:\s+([^:@]+)", line)
        if not m:
            continue
        name = m.group(1)
        if STALE_IFACE_RE.match(name):
            out.append(name)
    return sorted(set(out))


def cleanup_mininet_state(project_dir: Path, env: dict[str, str], log_file: Path) -> None:
    append_log(log_file, f"[cleanup] start {time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        run_cmd(
            ["timeout", "-k", "5s", "90s", "mn", "-c"],
            cwd=project_dir,
            env=env,
            log_file=log_file,
            timeout_sec=100,
            allowed_rcs={0, 124},
        )
    except Exception as exc:
        append_log(log_file, f"[cleanup] mn -c raised: {exc}")

    for label, cmd in PROCESS_PATTERNS:
        try:
            run_cmd(
                cmd,
                cwd=project_dir,
                env=env,
                log_file=log_file,
                timeout_sec=15,
                allowed_rcs={0, 1},
            )
        except Exception as exc:
            append_log(log_file, f"[cleanup] process cleanup for {label} raised: {exc}")

    time.sleep(2)

    stale_ifaces = list_stale_interfaces()
    if stale_ifaces:
        append_log(log_file, "[cleanup] deleting stale interfaces: " + ", ".join(stale_ifaces))
    for iface in stale_ifaces:
        try:
            run_cmd(
                ["ip", "link", "del", iface],
                cwd=project_dir,
                env=env,
                log_file=log_file,
                timeout_sec=10,
                allowed_rcs={0, 1},
            )
        except Exception as exc:
            append_log(log_file, f"[cleanup] interface delete for {iface} raised: {exc}")

    time.sleep(2)
    remaining = list_stale_interfaces()
    if remaining:
        append_log(log_file, "[cleanup] interfaces still present: " + ", ".join(remaining))
        raise RuntimeError("stale Mininet interfaces remain after cleanup: " + ", ".join(remaining))

    append_log(log_file, "[cleanup] complete")


def rerun_scenario(
    project_dir: Path,
    python_bin: str,
    scenario_dir: Path,
    user_ip_start: str,
    bot_ip_start: str,
) -> None:
    manifest_file = scenario_dir / "arena_manifest_v2.json"
    manifest = load_manifest(manifest_file)

    topology = manifest.get("topology", {})
    run_cfg = manifest.get("run_config", {})

    env = os.environ.copy()
    env["TOPOLOGY_MODE"] = str(topology.get("type", "three_tier"))
    env["LOAD_PROFILE"] = str(run_cfg.get("load_profile", "medium"))
    env["BOT_TYPE_MODE"] = str(run_cfg.get("bot_type_mode", "mixed"))
    env["ARENA_SEED"] = str(run_cfg.get("arena_seed", 42))
    env["NUM_USERS"] = str(topology.get("users", 20))
    env["NUM_BOTS"] = str(topology.get("bots", 70))
    env["BENIGN_ENGINE"] = str(run_cfg.get("benign_engine", "locust"))
    env["ATTACK_ENGINE"] = str(run_cfg.get("attack_engine", "http"))
    env["REQUIRE_REAL_LLM"] = "1" if bool(run_cfg.get("require_real_llm", False)) else "0"
    env["PYTHON_BIN"] = python_bin
    env["PCAP_FILE"] = str(scenario_dir / "full_arena_v2.pcap")
    env["MANIFEST_FILE"] = str(manifest_file)
    env["USER_IP_START"] = str(run_cfg.get("user_ip_start", user_ip_start))
    env["BOT_IP_START"] = str(run_cfg.get("bot_ip_start", bot_ip_start))

    benign_pcap_file = str(run_cfg.get("benign_pcap_file", "")).strip()
    if benign_pcap_file:
        env["BENIGN_PCAP_FILE"] = benign_pcap_file

    duration_sec = int(run_cfg.get("duration_sec", 180))
    log_file = scenario_dir / "mininet_repair.log"
    if log_file.exists():
        log_file.unlink()

    cleanup_mininet_state(project_dir=project_dir, env=env, log_file=log_file)
    cmd = [python_bin, "mininet_arena_v2.py", str(duration_sec)]
    scenario_exc: Exception | None = None
    try:
        run_cmd(cmd, cwd=project_dir, env=env, log_file=log_file, append=True)
    except Exception as exc:
        scenario_exc = exc
        raise
    finally:
        try:
            cleanup_mininet_state(project_dir=project_dir, env=env, log_file=log_file)
        except Exception:
            if scenario_exc is None:
                raise


def main() -> None:
    ap = argparse.ArgumentParser(description="Rebuild affected capture scenarios after IP allocation repair.")
    ap.add_argument("--project-dir", default="/home/user/FedSTGCN")
    ap.add_argument("--python-bin", default="/home/user/miniconda3/envs/DL/bin/python")
    ap.add_argument("--real-collection-dir", default="/home/user/FedSTGCN/real_collection")
    ap.add_argument("--scenarios", default="", help="Comma-separated scenario names. Default: auto-detect affected scenarios.")
    ap.add_argument("--generate-payloads", action="store_true", help="Regenerate llm_payloads.json before rerunning scenarios.")
    ap.add_argument("--backup-dir", default="", help="Optional directory for manifest/pcap/log backups before overwrite.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--user-ip-start", default="10.0.0.10")
    ap.add_argument("--bot-ip-start", default="10.0.0.110")
    args = ap.parse_args()

    project_dir = Path(args.project_dir).resolve()
    real_collection_dir = Path(args.real_collection_dir).resolve()
    selected = [x.strip() for x in str(args.scenarios).split(",") if x.strip()]
    scenario_dirs = collect_scenarios(real_collection_dir, selected)
    if not scenario_dirs:
        print("[INFO] no scenarios selected for repair")
        return

    print("[INFO] scenarios selected for repair:")
    for scenario_dir in scenario_dirs:
        print(f"  - {scenario_dir.name}")

    if args.dry_run:
        return

    if hasattr(os, "geteuid") and os.geteuid() != 0:
        raise SystemExit("rerun_affected_captures.py must be run as root inside a Mininet-capable Linux environment.")

    if args.generate_payloads:
        env = os.environ.copy()
        run_cmd(
            [args.python_bin, "generate_llm_payloads.py"],
            cwd=project_dir,
            env=env,
            log_file=project_dir / "repro" / "rerun_generate_llm_payloads.log",
        )

    backup_root: Path | None = None
    if str(args.backup_dir).strip():
        backup_root = Path(args.backup_dir).resolve()
    if backup_root is not None:
        backup_root.mkdir(parents=True, exist_ok=True)

    start = time.time()
    for scenario_dir in scenario_dirs:
        if backup_root is not None:
            backup_existing_files(scenario_dir, backup_root)
        rerun_scenario(
            project_dir=project_dir,
            python_bin=args.python_bin,
            scenario_dir=scenario_dir,
            user_ip_start=args.user_ip_start,
            bot_ip_start=args.bot_ip_start,
        )

    elapsed = time.time() - start
    print(f"[DONE] repaired {len(scenario_dirs)} scenario(s) in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
