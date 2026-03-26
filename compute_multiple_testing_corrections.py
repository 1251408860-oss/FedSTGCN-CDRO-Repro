#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def holm_adjust(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    prev = 0.0
    for rank, idx in enumerate(order, start=1):
        val = (m - rank + 1) * pvals[idx]
        val = max(val, prev)
        prev = val
        adj[idx] = min(1.0, val)
    return adj


def bh_adjust(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    next_val = 1.0
    for i in range(m - 1, -1, -1):
        idx = order[i]
        rank = i + 1
        val = pvals[idx] * m / rank
        val = min(val, next_val)
        next_val = val
        adj[idx] = min(1.0, val)
    return adj


def collect_hypotheses(root: Path) -> list[dict]:
    hyps: list[dict] = []

    # A) traditional stage3 physics vs data-only (3 protocols)
    top = json.loads((root / 'top_conf_suite_recharge' / 'top_conf_summary.json').read_text(encoding='utf-8'))
    for proto in ['temporal_ood', 'topology_ood', 'attack_strategy_ood']:
        p = float(top['statistics']['stage3'][proto]['clean']['significance_vs_data_only']['p_value_f1'])
        hyps.append({'family': 'central_traditional', 'name': f'{proto}_physics_vs_data_f1', 'p_raw': p})

    # B) central congestion-family (3 protocols + pooled)
    cen = json.loads((root / 'central_congestion_family_recharge' / 'central_congestion_family_summary.json').read_text(encoding='utf-8'))
    for proto in ['congestion_soft', 'congestion_mid', 'congestion_hard']:
        p = float(cen['stats'][proto]['p_value_f1'])
        hyps.append({'family': 'central_congestion', 'name': f'{proto}_physics_vs_data_f1', 'p_raw': p})
    hyps.append({'family': 'central_congestion', 'name': 'pooled_physics_vs_data_f1', 'p_raw': float(cen['pooled']['p_value_f1'])})

    # C) federated robustness
    fed_ext = json.loads((root / 'top_conf_suite_recharge' / 'fed_sig_ext9' / 'fed_sig_ext9_summary.json').read_text(encoding='utf-8'))
    hyps.append({'family': 'federated', 'name': 'high_poison_shapley_vs_fedavg_f1', 'p_raw': float(fed_ext['p_values']['shapley_vs_fedavg_f1'])})
    hyps.append({'family': 'federated', 'name': 'high_poison_median_vs_fedavg_f1', 'p_raw': float(fed_ext['p_values']['median_vs_fedavg_f1'])})

    fed_cross = json.loads((root / 'top_conf_suite_recharge' / 'fed_cross_protocol' / 'fed_cross_protocol_summary.json').read_text(encoding='utf-8'))
    hyps.append({'family': 'federated', 'name': 'cross_protocol_pooled_shapley_vs_fedavg_f1', 'p_raw': float(fed_cross['p_values']['pooled_shapley_vs_fedavg_f1'])})
    hyps.append({'family': 'federated', 'name': 'cross_protocol_pooled_median_vs_fedavg_f1', 'p_raw': float(fed_cross['p_values']['pooled_median_vs_fedavg_f1'])})

    return hyps


def main() -> None:
    root = Path('/home/user/FedSTGCN')
    out = root / 'top_conf_suite_recharge' / 'paper_ready_plus'
    out.mkdir(parents=True, exist_ok=True)

    hyps = collect_hypotheses(root)

    # global corrections (all hypotheses)
    p_all = [h['p_raw'] for h in hyps]
    holm_all = holm_adjust(p_all)
    bh_all = bh_adjust(p_all)
    for i, h in enumerate(hyps):
        h['p_holm_global'] = holm_all[i]
        h['p_bh_global'] = bh_all[i]

    # family-wise corrections
    fam_to_idx: dict[str, list[int]] = {}
    for i, h in enumerate(hyps):
        fam_to_idx.setdefault(h['family'], []).append(i)

    for fam, idxs in fam_to_idx.items():
        fam_p = [hyps[i]['p_raw'] for i in idxs]
        fam_h = holm_adjust(fam_p)
        fam_b = bh_adjust(fam_p)
        for k, i in enumerate(idxs):
            hyps[i]['p_holm_family'] = fam_h[k]
            hyps[i]['p_bh_family'] = fam_b[k]

    # write json
    (out / 'multiple_testing_corrections.json').write_text(json.dumps({'hypotheses': hyps}, indent=2), encoding='utf-8')

    # write markdown table
    lines = []
    lines.append('# Multiple Testing Corrections (Holm / BH)')
    lines.append('')
    lines.append('| family | hypothesis | p_raw | p_holm_family | p_bh_family | p_holm_global | p_bh_global |')
    lines.append('|---|---|---:|---:|---:|---:|---:|')
    for h in sorted(hyps, key=lambda x: (x['family'], x['p_raw'])):
        lines.append(
            f"| {h['family']} | {h['name']} | {h['p_raw']:.6g} | {h['p_holm_family']:.6g} | {h['p_bh_family']:.6g} | {h['p_holm_global']:.6g} | {h['p_bh_global']:.6g} |"
        )

    (out / 'multiple_testing_corrections.md').write_text('\n'.join(lines), encoding='utf-8')
    print(out / 'multiple_testing_corrections.md')


if __name__ == '__main__':
    main()
