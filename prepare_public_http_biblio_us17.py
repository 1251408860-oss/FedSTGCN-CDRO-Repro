#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import heapq
import io
import json
import math
import re
import tarfile
import urllib.parse
from collections import Counter
from pathlib import Path
from typing import Any

import torch

from prepare_public_http_csic2010 import (
    build_feature_vector,
    build_normal_profile,
    bounded,
    safe_div,
)


DAY_RE = re.compile(r"biblio-2017-(\d{2})-(\d{2})\.(?:cl|att|lbl)$", re.IGNORECASE)
GZIP_MAGIC = b"\x1f\x8b"


def stable_u64(text: str) -> int:
    digest = hashlib.blake2b(text.encode("utf-8", errors="ignore"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False)


def validate_biblio_tarball(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Biblio-US17 tarball not found: {path}")
    with path.open("rb") as fh:
        head = fh.read(512)
    if head.startswith(b"<!DOCTYPE html") or b"<title>idUS :: Acceso</title>" in head:
        raise RuntimeError(
            "The local Biblio-US17.tar.gz is an idUS login HTML page, not the dataset tarball. "
            "Place the real tarball at the same path and rerun."
        )
    if not head.startswith(GZIP_MAGIC):
        raise RuntimeError(
            "The local Biblio-US17.tar.gz is not a valid gzip archive. "
            "Place the real dataset tarball and rerun."
        )
    try:
        with gzip.open(path, "rb") as fh:
            fh.read(2)
        with tarfile.open(path, "r:gz") as tf:
            members = tf.getmembers()
        if not members:
            raise RuntimeError("empty tar archive")
    except Exception as exc:  # pragma: no cover - defensive validation
        raise RuntimeError(f"Invalid Biblio-US17 tarball: {exc}") from exc


def iter_tar_lines(tf: tarfile.TarFile, member: tarfile.TarInfo):
    fh = tf.extractfile(member)
    if fh is None:
        return
    with io.TextIOWrapper(fh, encoding="utf-8", errors="ignore", newline="") as text_fh:
        for line in text_fh:
            line = line.rstrip("\r\n")
            if line.strip():
                yield line


def extract_day_key(name: str) -> str | None:
    match = DAY_RE.search(name)
    if not match:
        return None
    mm, dd = match.groups()
    return f"{mm}-{dd}"


def classify_member(name: str) -> str | None:
    lower = name.lower()
    if lower.endswith(".cl"):
        return "clean"
    if lower.endswith(".att"):
        return "attack"
    if lower.endswith(".lbl"):
        return "label"
    return None


def extract_partition_split(name: str) -> str | None:
    lower = name.lower()
    if "partitions/ti/tr/" in lower:
        return "train"
    if "partitions/ti/val/" in lower:
        return "val"
    if "partitions/ti/test/" in lower:
        return "test"
    return None


def sort_day_keys(day_keys: list[str]) -> list[str]:
    return sorted(day_keys, key=lambda day: tuple(int(part) for part in day.split("-")))


def assign_day_splits(day_keys: list[str]) -> dict[str, str]:
    ordered = sort_day_keys(day_keys)
    n = len(ordered)
    if n < 3:
        raise RuntimeError("Biblio-US17 fallback split requires at least 3 daily files")
    n_train = max(1, int(round(0.60 * n)))
    n_val = max(1, int(round(0.10 * n)))
    n_train = min(n_train, n - 2)
    n_val = min(n_val, n - n_train - 1)
    train_days = ordered[:n_train]
    val_days = ordered[n_train:n_train + n_val]
    test_days = ordered[n_train + n_val:]
    split_map: dict[str, str] = {}
    for day in train_days:
        split_map[day] = "train"
    for day in val_days:
        split_map[day] = "val"
    for day in test_days:
        split_map[day] = "test"
    return split_map


def parse_record_line(line: str, label: str) -> tuple[str, dict[str, Any]]:
    parts = [part for part in line.split("\t") if part]
    if len(parts) < 6:
        parts = line.split()
    if len(parts) < 6:
        raise RuntimeError(f"Malformed Biblio-US17 record line: {line[:200]}")
    rec_id, method, uri, protocol, resp_code, resp_size = parts[:6]
    parsed = urllib.parse.urlsplit(uri)
    record = {
        "id": rec_id,
        "method": method.upper(),
        "url": uri,
        "protocol": protocol,
        "path": parsed.path or "/",
        "query": parsed.query or "",
        "host": "",
        "headers": {
            "x-biblio-resp-code": str(resp_code),
            "x-biblio-resp-size": str(resp_size),
        },
        "body": "",
        "raw": line,
        "source_split": label,
        "y": 1 if label == "attack" else 0,
    }
    return rec_id, record


def parse_label_line(line: str) -> tuple[str, dict[str, int]]:
    parts = [part for part in line.split("\t") if part]
    if len(parts) < 8:
        parts = line.split()
    if len(parts) < 8:
        raise RuntimeError(f"Malformed Biblio-US17 label line: {line[:200]}")
    rec_id = parts[0]
    ints = [int(part) for part in parts[1:8]]
    return rec_id, {
        "il_m2": ints[0],
        "il_nem": ints[1],
        "ms_pl1": ints[2],
        "ms_pl2": ints[3],
        "manual_tp": ints[4],
        "phase2_tp": ints[5],
        "oos": ints[6],
    }


def select_member_records(
    tf: tarfile.TarFile,
    member: tarfile.TarInfo,
    quota: int,
    label: str,
    split: str,
    day_key: str | None,
) -> tuple[list[dict[str, Any]], int]:
    total_lines = 0
    if quota <= 0:
        return [], total_lines

    heap: list[tuple[int, str, dict[str, Any]]] = []
    for line in iter_tar_lines(tf, member):
        total_lines += 1
        rec_id, record = parse_record_line(line=line, label=label)
        record["benchmark_split"] = split
        record["day_key"] = day_key
        record["source_member"] = member.name
        rank = stable_u64(rec_id)
        item = (-rank, rec_id, record)
        if len(heap) < quota:
            heapq.heappush(heap, item)
        elif rank < -heap[0][0]:
            heapq.heapreplace(heap, item)
    selected = [item[2] for item in heap]
    selected.sort(key=lambda row: stable_u64(row["id"]))
    return selected, total_lines


def build_biblio_weak_supervision(
    aux: dict[str, float],
    label_info: dict[str, int],
) -> tuple[torch.Tensor, int, float, float]:
    det_probs = torch.tensor(
        [
            0.90 if label_info["il_m2"] else 0.08,
            0.88 if label_info["il_nem"] else 0.08,
            0.84 if label_info["ms_pl1"] else 0.10,
            0.86 if label_info["ms_pl2"] else 0.10,
            bounded(0.14 + 0.20 * float(label_info["oos"])),
            bounded(max(aux["total_suspicion"], 0.85 * aux["encoding_score"], 0.80 * aux["sql_score"], 0.78 * aux["xss_score"])),
            bounded(max(aux["profile_ood"], 0.92 * aux["schema_ood"], 0.90 * aux["value_ood"])),
            bounded(max(0.80 * (1.0 - aux["popularity"]), 0.72 * aux["path_ood"])),
        ],
        dtype=torch.float,
    )
    det_count = int(label_info["il_m2"] + label_info["il_nem"] + label_info["ms_pl1"] + label_info["ms_pl2"])
    detector_prob = bounded(
        0.18 * float(label_info["il_m2"])
        + 0.18 * float(label_info["il_nem"])
        + 0.15 * float(label_info["ms_pl1"])
        + 0.17 * float(label_info["ms_pl2"])
        + 0.16 * float(det_count >= 2)
        + 0.16 * float(det_count >= 3)
    )
    oos_prob = bounded(0.22 * min(max(label_info["oos"], 0), 4))
    heuristic_prob = bounded(max(aux["total_suspicion"], 0.82 * aux["encoding_score"], 0.78 * aux["profile_ood"]))
    structure_prob = bounded(max(aux["profile_ood"], 0.90 * aux["schema_ood"], 0.88 * aux["value_ood"]))
    rarity_prob = bounded(max(1.0 - aux["popularity"], 0.75 * aux["path_ood"]))
    posterior_attack = bounded(
        0.38 * detector_prob
        + 0.18 * oos_prob
        + 0.20 * heuristic_prob
        + 0.14 * structure_prob
        + 0.10 * rarity_prob
    )
    benign_prob = 0.36
    if det_count == 0 and label_info["oos"] == 0 and aux["total_suspicion"] <= 0.10 and aux["profile_ood"] <= 0.10:
        benign_prob = bounded(0.68 + 0.24 * aux["popularity"])
    elif det_count == 0 and label_info["oos"] == 0 and aux["total_suspicion"] <= 0.16 and aux["profile_ood"] <= 0.16:
        benign_prob = bounded(0.50 + 0.22 * aux["popularity"])

    weights = torch.tensor([1.10, 1.10, 1.00, 1.00, 1.20, 1.00, 1.25, 0.90], dtype=torch.float)
    weighted_prob = float((det_probs * weights).sum().item() / weights.sum().item())
    posterior_attack = bounded(0.62 * posterior_attack + 0.38 * weighted_prob)

    votes = torch.full((det_probs.numel(),), fill_value=-1, dtype=torch.long)
    votes[det_probs >= 0.56] = 1
    votes[det_probs <= 0.24] = 0
    valid = votes >= 0
    attack_votes = int((votes == 1).sum().item())
    benign_votes = int((votes == 0).sum().item())
    num_votes = int(valid.sum().item())
    agreement = float(max(attack_votes, benign_votes) / max(num_votes, 1)) if num_votes > 0 else 0.0

    p = min(max(posterior_attack, 1e-6), 1.0 - 1e-6)
    entropy = -(p * math.log(p) + (1.0 - p) * math.log(1.0 - p)) / math.log(2.0)

    weak_label = -1
    if det_count >= 2 and posterior_attack >= 0.42:
        weak_label = 1
    elif label_info["oos"] >= 2 and posterior_attack >= 0.45:
        weak_label = 1
    elif posterior_attack >= 0.70:
        weak_label = 1
    elif det_count == 0 and label_info["oos"] == 0 and benign_votes >= 3 and posterior_attack <= 0.22 and aux["profile_ood"] <= 0.12:
        weak_label = 0

    posterior = torch.tensor([1.0 - posterior_attack, posterior_attack], dtype=torch.float)
    return posterior, weak_label, agreement, float(entropy)


def load_label_map(tf: tarfile.TarFile, label_members: list[tarfile.TarInfo]) -> dict[str, dict[str, int]]:
    label_map: dict[str, dict[str, int]] = {}
    for member in label_members:
        for line in iter_tar_lines(tf, member):
            rec_id, info = parse_label_line(line)
            label_map[rec_id] = info
    return label_map


def cap_map(args: argparse.Namespace) -> dict[str, dict[str, int]]:
    return {
        "train": {"clean": int(args.train_benign_cap), "attack": int(args.train_attack_cap)},
        "val": {"clean": int(args.val_benign_cap), "attack": int(args.val_attack_cap)},
        "test": {"clean": int(args.test_benign_cap), "attack": int(args.test_attack_cap)},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Prepare a compact Biblio-US17 weak-supervision public HTTP benchmark")
    ap.add_argument("--tarball", default="/home/user/FedSTGCN/biblio_us17/Biblio-US17.tar.gz")
    ap.add_argument("--output-dir", default="/home/user/FedSTGCN/public_http_biblio_us17")
    ap.add_argument("--hash-dim", type=int, default=128)
    ap.add_argument("--train-benign-cap", type=int, default=60000)
    ap.add_argument("--train-attack-cap", type=int, default=12000)
    ap.add_argument("--val-benign-cap", type=int, default=10000)
    ap.add_argument("--val-attack-cap", type=int, default=4000)
    ap.add_argument("--test-benign-cap", type=int, default=30000)
    ap.add_argument("--test-attack-cap", type=int, default=8000)
    args = ap.parse_args()

    tarball = Path(args.tarball).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    validate_biblio_tarball(tarball)

    with tarfile.open(tarball, "r:gz") as tf:
        members = [member for member in tf.getmembers() if member.isfile()]
        member_groups: dict[str, list[tarfile.TarInfo]] = {"clean": [], "attack": [], "label": []}
        day_keys: set[str] = set()
        explicit_partition_members = 0
        for member in members:
            group = classify_member(member.name)
            if group is None:
                continue
            member_groups[group].append(member)
            if group in {"clean", "attack"} and extract_partition_split(member.name) is not None:
                explicit_partition_members += 1
            day_key = extract_day_key(member.name)
            if day_key is not None and group in {"clean", "attack"}:
                day_keys.add(day_key)

        if not member_groups["clean"] or not member_groups["attack"] or not member_groups["label"]:
            raise RuntimeError("Expected CLEAN / ATTACK / LABEL files were not found in the Biblio-US17 tarball")

        use_official_ti_partition = explicit_partition_members > 0
        split_by_day = assign_day_splits(list(day_keys))
        label_map = load_label_map(tf=tf, label_members=member_groups["label"])
        caps = cap_map(args)
        remaining_caps = {split: dict(values) for split, values in caps.items()}

        selected_records: list[dict[str, Any]] = []
        selected_counts: dict[str, Counter[str]] = {split: Counter() for split in ["train", "val", "test"]}
        processed_counts: dict[str, Counter[str]] = {split: Counter() for split in ["train", "val", "test"]}
        member_lists: dict[str, dict[str, list[tarfile.TarInfo]]] = {
            split: {"clean": [], "attack": []} for split in ["train", "val", "test"]
        }
        for label in ["clean", "attack"]:
            for member in member_groups[label]:
                if use_official_ti_partition:
                    split = extract_partition_split(member.name)
                    if split is None:
                        continue
                    member_lists[split][label].append(member)
                else:
                    day_key = extract_day_key(member.name)
                    if day_key is None or day_key not in split_by_day:
                        continue
                    member_lists[split_by_day[day_key]][label].append(member)
            for split in ["train", "val", "test"]:
                member_lists[split][label].sort(key=lambda item: item.name)

        for split in ["train", "val", "test"]:
            for label in ["clean", "attack"]:
                members_for_split = member_lists[split][label]
                remaining_members = len(members_for_split)
                for member in members_for_split:
                    if remaining_members <= 0:
                        break
                    quota = int(math.ceil(remaining_caps[split][label] / max(remaining_members, 1)))
                    picked, total_lines = select_member_records(
                        tf=tf,
                        member=member,
                        quota=quota,
                        label=label,
                        split=split,
                        day_key=extract_day_key(member.name),
                    )
                    processed_counts[split][label] += int(total_lines)
                    selected_counts[split][label] += int(len(picked))
                    selected_records.extend(picked)
                    remaining_caps[split][label] = max(0, remaining_caps[split][label] - len(picked))
                    remaining_members -= 1

    if not selected_records:
        raise RuntimeError("No records were selected from the Biblio-US17 tarball")

    train_clean_records = [
        record
        for record in selected_records
        if record["y"] == 0 and record.get("benchmark_split") == "train"
    ]
    if not train_clean_records:
        train_clean_records = [record for record in selected_records if record["y"] == 0][: max(1, min(5000, len(selected_records)))]

    popularity_counter: Counter[str] = Counter(record["path"] for record in train_clean_records)
    max_pop = max(popularity_counter.values()) if popularity_counter else 1
    popularity = {path: safe_div(count, max_pop) for path, count in popularity_counter.items()}
    normal_profile = build_normal_profile(train_clean_records)

    xs: list[torch.Tensor] = []
    ys: list[int] = []
    weak_posterior: list[torch.Tensor] = []
    weak_label: list[int] = []
    weak_agreement: list[float] = []
    weak_uncertainty: list[float] = []
    rho_proxy: list[float] = []
    aux_rows: list[torch.Tensor] = []
    train_mask_values: list[bool] = []
    val_mask_values: list[bool] = []
    test_mask_values: list[bool] = []
    aux_feature_names = [
        "popularity",
        "sql_score",
        "xss_score",
        "traversal_score",
        "encoding_score",
        "total_suspicion",
        "path_ood",
        "host_ood",
        "method_ood",
        "schema_ood",
        "value_ood",
        "profile_ood",
    ]

    for record in sorted(selected_records, key=lambda row: (str(row.get("benchmark_split", "test")), row["y"], stable_u64(row["id"]))):
        split = str(record.get("benchmark_split", "test"))
        x, aux = build_feature_vector(record, popularity=popularity, profile=normal_profile, hash_dim=int(args.hash_dim))
        label_info = label_map.get(
            record["id"],
            {"il_m2": 0, "il_nem": 0, "ms_pl1": 0, "ms_pl2": 0, "manual_tp": -1, "phase2_tp": -1, "oos": 0},
        )
        posterior, label, agreement, uncertainty = build_biblio_weak_supervision(aux=aux, label_info=label_info)
        xs.append(x)
        ys.append(int(record["y"]))
        weak_posterior.append(posterior)
        weak_label.append(int(label))
        weak_agreement.append(float(agreement))
        weak_uncertainty.append(float(uncertainty))
        rho_proxy.append(float(0.45 * posterior[1].item() + 0.35 * aux["profile_ood"] + 0.20 * (1.0 - aux["popularity"])))
        aux_rows.append(torch.tensor([float(aux[name]) for name in aux_feature_names], dtype=torch.float))
        train_mask_values.append(split == "train")
        val_mask_values.append(split == "val")
        test_mask_values.append(split == "test")

    x = torch.stack(xs, dim=0)
    y = torch.tensor(ys, dtype=torch.long)
    weak_posterior_t = torch.stack(weak_posterior, dim=0)
    weak_label_t = torch.tensor(weak_label, dtype=torch.long)
    weak_agreement_t = torch.tensor(weak_agreement, dtype=torch.float)
    weak_uncertainty_t = torch.tensor(weak_uncertainty, dtype=torch.float)
    rho_proxy_t = torch.tensor(rho_proxy, dtype=torch.float)
    aux_features_t = torch.stack(aux_rows, dim=0)
    x_mean = x.mean(dim=0, keepdim=True)
    x_std = x.std(dim=0, keepdim=True).clamp(min=1e-6)
    x_norm = (x - x_mean) / x_std

    train_mask = torch.tensor(train_mask_values, dtype=torch.bool)
    val_mask = torch.tensor(val_mask_values, dtype=torch.bool)
    test_mask = torch.tensor(test_mask_values, dtype=torch.bool)
    covered_train = train_mask & (weak_label_t >= 0)
    covered_test = test_mask & (weak_label_t >= 0)
    attack_mask = weak_label_t == 1
    benign_mask = weak_label_t == 0

    bundle = {
        "x": x,
        "x_norm": x_norm,
        "y": y,
        "train_mask": train_mask,
        "val_mask": val_mask,
        "test_mask": test_mask,
        "temporal_test_mask": test_mask.clone(),
        "flow_mask": torch.ones_like(y, dtype=torch.bool),
        "weak_label": weak_label_t,
        "weak_posterior": weak_posterior_t,
        "weak_agreement": weak_agreement_t,
        "weak_uncertainty": weak_uncertainty_t,
        "rho_proxy": rho_proxy_t,
        "aux_features": aux_features_t,
        "aux_feature_names": aux_feature_names,
        "metadata": {
            "dataset": "Biblio-US17",
            "dataset_label": "Biblio-US17",
            "dataset_description": "Large real HTTP URI corpus from University of Seville logs, converted into a compact weak-supervision tabular benchmark.",
            "kind": "public_http_sanity",
            "source_access": "request-gated original tarball",
            "protocol": "official_ti_partition" if use_official_ti_partition else "chronological_day_fallback_60_10_30",
            "using_official_ti_partition": bool(use_official_ti_partition),
            "num_features": int(x.shape[1]),
            "hash_dim": int(args.hash_dim),
            "profile_paths": int(len(normal_profile["paths"])),
            "profile_path_methods": int(len(normal_profile["path_methods"])),
        },
    }
    bundle_path = out_dir / "public_http_biblio_us17_bundle.pt"
    torch.save(bundle, bundle_path)

    def precision(mask: torch.Tensor, target: int) -> float:
        if int(mask.sum().item()) == 0:
            return 0.0
        return float((y[mask] == int(target)).float().mean().item())

    summary = {
        "bundle_file": str(bundle_path),
        "source_counts": {split: dict(counter) for split, counter in processed_counts.items()},
        "selected_counts": {split: dict(counter) for split, counter in selected_counts.items()},
        "num_nodes": int(y.numel()),
        "class_counts": {
            "benign": int((y == 0).sum().item()),
            "attack": int((y == 1).sum().item()),
        },
        "split_counts": {
            "train": int(train_mask.sum().item()),
            "val": int(val_mask.sum().item()),
            "test": int(test_mask.sum().item()),
        },
        "weak_supervision": {
            "covered_train_nodes": int(covered_train.sum().item()),
            "covered_test_nodes": int(covered_test.sum().item()),
            "train_coverage": safe_div(int(covered_train.sum().item()), int(train_mask.sum().item())),
            "test_coverage": safe_div(int(covered_test.sum().item()), int(test_mask.sum().item())),
            "weak_attack_nodes": int(attack_mask.sum().item()),
            "weak_benign_nodes": int(benign_mask.sum().item()),
            "weak_attack_precision_train": precision(covered_train & attack_mask, 1),
            "weak_benign_precision_train": precision(covered_train & benign_mask, 0),
        },
        "metadata": bundle["metadata"],
    }
    summary_path = out_dir / "public_http_biblio_us17_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(summary_path)


if __name__ == "__main__":
    main()
