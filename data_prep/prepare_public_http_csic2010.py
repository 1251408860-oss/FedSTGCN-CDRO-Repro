#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import requests
import torch


CSIC_URLS = {
    "normal_train": "https://gitlab.fing.edu.uy/gsi/web-application-attacks-datasets/-/raw/master/csic_2010/normalTrafficTraining.txt",
    "normal_test": "https://gitlab.fing.edu.uy/gsi/web-application-attacks-datasets/-/raw/master/csic_2010/normalTrafficTest.txt",
    "attack_test": "https://gitlab.fing.edu.uy/gsi/web-application-attacks-datasets/-/raw/master/csic_2010/anomalousTrafficTest.txt",
}
METHODS = {"GET": 0, "POST": 1, "HEAD": 2, "PUT": 3, "DELETE": 4, "OPTIONS": 5}
SQL_TOKENS = ["select", "union", "drop", "insert", "update", "delete", "or 1=1", "sleep(", "benchmark(", "information_schema"]
XSS_TOKENS = ["<script", "%3cscript", "javascript:", "onerror", "onload", "alert(", "<img", "%3cimg", "<svg", "%3csvg"]
TRAVERSAL_TOKENS = ["../", "..\\", "%2e%2e", "%2f", "%5c", "/etc/passwd", "win.ini", "%00", "%255c", "%252e"]
CMD_TOKENS = ["cmd=", "exec", "system(", "wget ", "curl ", "/bin/sh", "powershell", "bash -c"]
TOKEN_RE = re.compile(r"[A-Za-z0-9_/%\.-]+")
REQUEST_START_RE = re.compile(r"^(GET|POST|HEAD|PUT|DELETE|OPTIONS)\s+http", re.IGNORECASE)


def download_file(url: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists() and out_path.stat().st_size > 0:
        return
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with out_path.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    fh.write(chunk)


def normalize_text(raw: bytes) -> str:
    text = raw.decode("latin1", errors="ignore")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def split_requests(text: str) -> list[str]:
    parts = re.split(r"\n{2,}(?=(?:GET|POST|HEAD|PUT|DELETE|OPTIONS)\s+http)", text)
    return [part.strip() for part in parts if part.strip()]


def parse_request(block: str) -> dict[str, Any]:
    parts = block.split("\n\n", 1)
    head = parts[0]
    body = parts[1] if len(parts) > 1 else ""
    lines = [line.strip() for line in head.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("empty request block")
    request_line = lines[0]
    toks = request_line.split()
    if len(toks) < 3:
        raise RuntimeError(f"bad request line: {request_line}")
    method, raw_url, protocol = toks[0].upper(), toks[1], toks[2]
    parsed = urllib.parse.urlparse(raw_url)
    query = parsed.query or ""
    path = parsed.path or "/"
    host = parsed.netloc or ""
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()
    return {
        "method": method,
        "url": raw_url,
        "protocol": protocol,
        "path": path,
        "query": query,
        "host": host,
        "headers": headers,
        "body": body.strip(),
        "raw": block,
    }


def safe_div(a: float, b: float) -> float:
    return float(a / b) if b > 0 else 0.0


def bounded(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


def count_hits(text: str, patterns: list[str]) -> int:
    text_l = text.lower()
    return sum(text_l.count(pattern) for pattern in patterns)


def extract_params(record: dict[str, Any]) -> list[tuple[str, str]]:
    return urllib.parse.parse_qsl(record["query"], keep_blank_values=True) + urllib.parse.parse_qsl(record["body"], keep_blank_values=True)


def characterize_value(value: str) -> dict[str, float]:
    text = urllib.parse.unquote_plus(value)
    n = max(len(text), 1)
    return {
        "len": float(len(text)),
        "digit_ratio": safe_div(sum(ch.isdigit() for ch in text), n),
        "alpha_ratio": safe_div(sum(ch.isalpha() for ch in text), n),
        "special_ratio": safe_div(sum(not ch.isalnum() for ch in text), n),
        "has_angle": 1.0 if ("<" in text or ">" in text) else 0.0,
        "has_quote": 1.0 if ("'" in text or '"' in text) else 0.0,
        "has_slash": 1.0 if ("/" in text or "\\" in text) else 0.0,
        "has_tilde": 1.0 if "~" in text else 0.0,
        "has_percent": 1.0 if "%" in text else 0.0,
    }


def build_normal_profile(records: list[dict[str, Any]]) -> dict[str, Any]:
    path_counts: Counter[str] = Counter()
    host_counts: Counter[str] = Counter()
    path_methods: set[tuple[str, str]] = set()
    schema_counts: dict[tuple[str, str], Counter[tuple[str, ...]]] = defaultdict(Counter)
    param_stats_raw: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for record in records:
        path_counts[record["path"]] += 1
        host_counts[record["host"]] += 1
        path_methods.add((record["path"], record["method"]))
        keys = tuple(sorted({k for k, _ in extract_params(record)}))
        schema_counts[(record["path"], record["method"])][keys] += 1
        for key, value in extract_params(record):
            for stat_name, stat_val in characterize_value(value).items():
                param_stats_raw[(record["path"], key)][stat_name].append(float(stat_val))

    param_stats: dict[tuple[str, str], dict[str, float]] = {}
    for stat_key, stat_map in param_stats_raw.items():
        summary: dict[str, float] = {}
        for stat_name, vals in stat_map.items():
            vals_sorted = sorted(float(v) for v in vals)
            n = len(vals_sorted)
            q10 = vals_sorted[min(n - 1, max(0, int(round(0.10 * (n - 1)))))]
            q90 = vals_sorted[min(n - 1, max(0, int(round(0.90 * (n - 1)))))]
            summary[f"{stat_name}_min"] = float(vals_sorted[0])
            summary[f"{stat_name}_q10"] = float(q10)
            summary[f"{stat_name}_q90"] = float(q90)
            summary[f"{stat_name}_max"] = float(vals_sorted[-1])
        param_stats[stat_key] = summary

    return {
        "paths": set(path_counts),
        "hosts": set(host_counts),
        "path_methods": path_methods,
        "dominant_schema": {key: counter.most_common(1)[0][0] for key, counter in schema_counts.items()},
        "path_popularity": dict(path_counts),
        "param_stats": param_stats,
    }


def value_anomaly_score(record: dict[str, Any], profile: dict[str, Any]) -> float:
    param_scores: list[float] = []
    for key, value in extract_params(record):
        ref = profile["param_stats"].get((record["path"], key))
        if ref is None:
            continue
        obs = characterize_value(value)
        score = 0.0
        score += 0.40 * float(obs["len"] > ref["len_max"] + 1.0 or obs["len"] < max(0.0, ref["len_min"] - 1.0))
        score += 0.18 * float(obs["digit_ratio"] > ref["digit_ratio_q90"] + 0.18 or obs["digit_ratio"] < ref["digit_ratio_q10"] - 0.18)
        score += 0.18 * float(obs["alpha_ratio"] > ref["alpha_ratio_q90"] + 0.18 or obs["alpha_ratio"] < ref["alpha_ratio_q10"] - 0.18)
        score += 0.24 * float(obs["special_ratio"] > ref["special_ratio_q90"] + 0.10 or obs["special_ratio"] < max(0.0, ref["special_ratio_q10"] - 0.10))
        for flag_name, weight in [
            ("has_angle", 0.30),
            ("has_quote", 0.26),
            ("has_slash", 0.24),
            ("has_tilde", 0.24),
            ("has_percent", 0.12),
        ]:
            score += weight * float(obs[flag_name] > ref[f"{flag_name}_max"] + 1e-9)
        param_scores.append(bounded(score))
    return float(max(param_scores)) if param_scores else 0.0


def profile_deviation_score(record: dict[str, Any], profile: dict[str, Any]) -> dict[str, float]:
    path_ood = 1.0 if record["path"] not in profile["paths"] else 0.0
    host_ood = 1.0 if record["host"] not in profile["hosts"] else 0.0
    method_ood = 1.0 if (record["path"], record["method"]) not in profile["path_methods"] else 0.0

    key_set = {k for k, _ in extract_params(record)}
    expected = profile["dominant_schema"].get((record["path"], record["method"]))
    if expected is None:
        schema_ood = 0.0 if path_ood >= 1.0 else 0.85
    else:
        expected_set = set(expected)
        extra_frac = safe_div(len(key_set - expected_set), max(len(key_set), 1))
        missing_frac = safe_div(len(expected_set - key_set), max(len(expected_set), 1))
        schema_ood = bounded(0.70 * extra_frac + 0.45 * missing_frac + 0.20 * float(len(key_set) != len(expected_set)))

    value_ood = value_anomaly_score(record, profile)
    profile_ood = bounded(0.70 * path_ood + 0.42 * method_ood + 0.55 * schema_ood + 0.68 * value_ood + 0.35 * host_ood)
    return {
        "path_ood": float(path_ood),
        "host_ood": float(host_ood),
        "method_ood": float(method_ood),
        "schema_ood": float(schema_ood),
        "value_ood": float(value_ood),
        "profile_ood": float(profile_ood),
    }


def suspicious_score(record: dict[str, Any], profile: dict[str, Any]) -> dict[str, float]:
    uri = urllib.parse.unquote_plus(record["url"]).lower()
    body = urllib.parse.unquote_plus(record["body"]).lower()
    full = f"{uri} {body}"
    sql_hits = count_hits(full, SQL_TOKENS)
    xss_hits = count_hits(full, XSS_TOKENS)
    traversal_hits = count_hits(full, TRAVERSAL_TOKENS)
    cmd_hits = count_hits(full, CMD_TOKENS)
    pct_count = full.count("%")
    quote_count = full.count("'") + full.count('"')
    angle_count = full.count("<") + full.count(">")
    semi_count = full.count(";")
    weird_ratio = safe_div(sum(ch in "<>\"'%;(){}[]|~`" for ch in full), max(len(full), 1))
    profile_scores = profile_deviation_score(record, profile)
    sql_score = bounded(0.34 * sql_hits + 0.08 * quote_count + 0.05 * semi_count)
    xss_score = bounded(0.38 * xss_hits + 0.07 * angle_count + 0.03 * pct_count)
    traversal_score = bounded(0.36 * traversal_hits + 0.05 * pct_count)
    encoding_score = bounded(
        0.04 * pct_count
        + 0.12 * float(quote_count > 2)
        + 0.14 * float(len(uri) > 180)
        + 0.12 * cmd_hits
        + 0.32 * weird_ratio
        + 0.18 * profile_scores["value_ood"]
    )
    total = bounded(
        0.20 * sql_score
        + 0.16 * xss_score
        + 0.14 * traversal_score
        + 0.12 * encoding_score
        + 0.30 * profile_scores["profile_ood"]
        + 0.16 * profile_scores["schema_ood"]
    )
    return {
        "sql_score": sql_score,
        "xss_score": xss_score,
        "traversal_score": traversal_score,
        "encoding_score": encoding_score,
        "total_suspicion": total,
        **profile_scores,
    }


def request_tokens(record: dict[str, Any]) -> list[str]:
    text = " ".join([record["path"], record["query"], record["body"]]).lower()
    return [tok for tok in TOKEN_RE.findall(text) if tok]


def stable_hash(token: str, dim: int) -> int:
    val = 2166136261
    for ch in token.encode("utf-8", errors="ignore"):
        val ^= ch
        val = (val * 16777619) & 0xFFFFFFFF
    return int(val % dim)


def build_feature_vector(
    record: dict[str, Any],
    popularity: dict[str, float],
    profile: dict[str, Any],
    hash_dim: int,
) -> tuple[torch.Tensor, dict[str, float]]:
    suspicion = suspicious_score(record, profile=profile)
    path = urllib.parse.unquote_plus(record["path"])
    query = urllib.parse.unquote_plus(record["query"])
    body = urllib.parse.unquote_plus(record["body"])
    full = f"{path}?{query} {body}".strip()
    tokens = request_tokens(record)

    hashed = torch.zeros(hash_dim, dtype=torch.float)
    for token in tokens:
        hashed[stable_hash(token, hash_dim)] += 1.0
    if int(hashed.sum().item()) > 0:
        hashed = hashed / hashed.sum().clamp(min=1.0)

    method_idx = METHODS.get(record["method"], len(METHODS))
    method_onehot = torch.zeros(len(METHODS) + 1, dtype=torch.float)
    method_onehot[method_idx] = 1.0

    alnum = sum(ch.isalnum() for ch in full)
    digits = sum(ch.isdigit() for ch in full)
    uppers = sum(ch.isupper() for ch in full)
    specials = len(full) - alnum
    params = urllib.parse.parse_qsl(record["query"], keep_blank_values=True)
    body_params = urllib.parse.parse_qsl(record["body"], keep_blank_values=True)
    param_count = len(params) + len(body_params)
    path_depth = record["path"].count("/")
    pct_count = full.count("%")
    pop = float(popularity.get(record["path"], 0.0))
    numeric = torch.tensor(
        [
            len(record["path"]),
            len(record["query"]),
            len(record["body"]),
            len(full),
            param_count,
            path_depth,
            pct_count,
            specials,
            safe_div(digits, max(len(full), 1)),
            safe_div(uppers, max(len(full), 1)),
            1.0 if "cookie" in record["headers"] else 0.0,
            1.0 if record["headers"].get("content-type", "").startswith("application/x-www-form-urlencoded") else 0.0,
            suspicion["sql_score"],
            suspicion["xss_score"],
            suspicion["traversal_score"],
            suspicion["encoding_score"],
            suspicion["total_suspicion"],
            pop,
            suspicion["path_ood"],
            suspicion["host_ood"],
            suspicion["method_ood"],
            suspicion["schema_ood"],
            suspicion["value_ood"],
            suspicion["profile_ood"],
        ],
        dtype=torch.float,
    )
    x = torch.cat([method_onehot, numeric, hashed], dim=0)
    aux = {
        "popularity": pop,
        **suspicion,
    }
    return x, aux


def build_weak_supervision(aux: dict[str, float]) -> tuple[torch.Tensor, int, float, float]:
    sql_prob = bounded(0.08 + 0.92 * aux["sql_score"])
    xss_prob = bounded(0.06 + 0.94 * aux["xss_score"])
    traversal_prob = bounded(0.06 + 0.94 * aux["traversal_score"])
    encoding_prob = bounded(0.10 + 0.90 * max(aux["encoding_score"], 0.72 * aux["total_suspicion"]))
    structure_prob = bounded(max(aux["profile_ood"], 0.92 * aux["schema_ood"], 0.92 * aux["value_ood"], 0.86 * aux["path_ood"]))
    rarity_prob = bounded(max(0.82 * (1.0 - aux["popularity"]), 0.75 * aux["profile_ood"]))
    benign_prob = 0.40
    if aux["total_suspicion"] <= 0.08 and aux["profile_ood"] <= 0.06:
        benign_prob = bounded(0.65 + 0.30 * aux["popularity"])
    elif aux["total_suspicion"] <= 0.14 and aux["profile_ood"] <= 0.12:
        benign_prob = bounded(0.46 + 0.20 * aux["popularity"])
    view_attack_probs = torch.tensor(
        [
            sql_prob,
            xss_prob,
            traversal_prob,
            encoding_prob,
            structure_prob,
            rarity_prob,
            1.0 - benign_prob,
        ],
        dtype=torch.float,
    )
    weights = torch.tensor([1.15, 1.10, 1.00, 0.85, 1.40, 1.05, 0.75], dtype=torch.float)
    weighted_prob = float((view_attack_probs * weights).sum().item() / weights.sum().item())
    posterior_attack = bounded(0.55 * weighted_prob + 0.30 * structure_prob + 0.15 * max(sql_prob, xss_prob, traversal_prob, encoding_prob))
    votes = torch.full((view_attack_probs.numel(),), fill_value=-1, dtype=torch.long)
    votes[view_attack_probs >= 0.56] = 1
    votes[view_attack_probs <= 0.24] = 0
    valid = votes >= 0
    attack_votes = int((votes == 1).sum().item())
    benign_votes = int((votes == 0).sum().item())
    num_votes = int(valid.sum().item())
    agreement = float(max(attack_votes, benign_votes) / max(num_votes, 1)) if num_votes > 0 else 0.0
    entropy = 0.0
    p = min(max(posterior_attack, 1e-6), 1.0 - 1e-6)
    entropy = -(p * math.log(p) + (1.0 - p) * math.log(1.0 - p)) / math.log(2.0)
    weak_label = -1
    max_payload = max(sql_prob, xss_prob, traversal_prob, encoding_prob)
    if attack_votes >= 2 and posterior_attack >= 0.42:
        weak_label = 1
    elif max_payload >= 0.88:
        weak_label = 1
    elif structure_prob >= 0.80:
        weak_label = 1
    elif benign_votes >= 3 and posterior_attack <= 0.24 and aux["profile_ood"] <= 0.08 and aux["total_suspicion"] <= 0.10:
        weak_label = 0
    posterior = torch.tensor([1.0 - posterior_attack, posterior_attack], dtype=torch.float)
    return posterior, weak_label, agreement, float(entropy)


def stratified_masks(y: torch.Tensor, seed: int, train_frac: float, val_frac: float) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    gen = torch.Generator().manual_seed(int(seed))
    train_mask = torch.zeros_like(y, dtype=torch.bool)
    val_mask = torch.zeros_like(y, dtype=torch.bool)
    test_mask = torch.zeros_like(y, dtype=torch.bool)
    for cls in [0, 1]:
        idx = (y == cls).nonzero(as_tuple=False).view(-1)
        perm = idx[torch.randperm(int(idx.numel()), generator=gen)]
        n = int(perm.numel())
        n_train = int(round(float(train_frac) * n))
        n_val = int(round(float(val_frac) * n))
        n_train = min(max(n_train, 1), n - 2)
        n_val = min(max(n_val, 1), n - n_train - 1)
        train_mask[perm[:n_train]] = True
        val_mask[perm[n_train:n_train + n_val]] = True
        test_mask[perm[n_train + n_val:]] = True
    return train_mask, val_mask, test_mask


def main() -> None:
    ap = argparse.ArgumentParser(description="Prepare a compact public HTTP sanity benchmark from CSIC 2010")
    ap.add_argument("--output-dir", default="/home/user/FedSTGCN/public_http_csic2010")
    ap.add_argument("--hash-dim", type=int, default=128)
    ap.add_argument("--split-seed", type=int, default=42)
    ap.add_argument("--train-frac", type=float, default=0.60)
    ap.add_argument("--val-frac", type=float, default=0.20)
    args = ap.parse_args()

    out_dir = Path(args.output_dir).resolve()
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    local_files: dict[str, Path] = {}
    for key, url in CSIC_URLS.items():
        path = raw_dir / Path(urllib.parse.urlparse(url).path).name
        download_file(url, path)
        local_files[key] = path

    records: list[dict[str, Any]] = []
    normal_train_records: list[dict[str, Any]] = []
    popularity_counter: Counter[str] = Counter()
    source_counts: dict[str, int] = {}
    for key, path in local_files.items():
        text = normalize_text(path.read_bytes())
        blocks = split_requests(text)
        source_counts[key] = len(blocks)
        for block in blocks:
            record = parse_request(block)
            y = 1 if key == "attack_test" else 0
            record["source_split"] = key
            record["y"] = y
            records.append(record)
            if key == "normal_train":
                normal_train_records.append(record)
                popularity_counter[record["path"]] += 1

    max_pop = max(popularity_counter.values()) if popularity_counter else 1
    popularity = {path: safe_div(count, max_pop) for path, count in popularity_counter.items()}
    normal_profile = build_normal_profile(normal_train_records)

    xs: list[torch.Tensor] = []
    ys: list[int] = []
    weak_posterior: list[torch.Tensor] = []
    weak_label: list[int] = []
    weak_agreement: list[float] = []
    weak_uncertainty: list[float] = []
    rho_proxy: list[float] = []
    aux_rows: list[torch.Tensor] = []
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
    for record in records:
        x, aux = build_feature_vector(record, popularity=popularity, profile=normal_profile, hash_dim=int(args.hash_dim))
        posterior, label, agreement, uncertainty = build_weak_supervision(aux)
        xs.append(x)
        ys.append(int(record["y"]))
        weak_posterior.append(posterior)
        weak_label.append(int(label))
        weak_agreement.append(float(agreement))
        weak_uncertainty.append(float(uncertainty))
        rho_proxy.append(float(0.55 * aux["total_suspicion"] + 0.45 * (1.0 - aux["popularity"])))
        aux_rows.append(torch.tensor([float(aux[name]) for name in aux_feature_names], dtype=torch.float))

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

    train_mask, val_mask, test_mask = stratified_masks(
        y=y,
        seed=int(args.split_seed),
        train_frac=float(args.train_frac),
        val_frac=float(args.val_frac),
    )
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
            "dataset": "CSIC-2010",
            "kind": "public_http_sanity",
            "source_counts": source_counts,
            "num_features": int(x.shape[1]),
            "hash_dim": int(args.hash_dim),
            "split_seed": int(args.split_seed),
            "profile_paths": int(len(normal_profile["paths"])),
            "profile_path_methods": int(len(normal_profile["path_methods"])),
        },
    }
    bundle_path = out_dir / "public_http_csic2010_bundle.pt"
    torch.save(bundle, bundle_path)

    def precision(mask: torch.Tensor, target: int) -> float:
        if int(mask.sum().item()) == 0:
            return 0.0
        return float((y[mask] == int(target)).float().mean().item())

    summary = {
        "bundle_file": str(bundle_path),
        "source_counts": source_counts,
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
    summary_path = out_dir / "public_http_csic2010_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(summary_path)


if __name__ == "__main__":
    main()
