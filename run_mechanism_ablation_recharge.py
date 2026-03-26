#!/usr/bin/env python3
from __future__ import annotations

import itertools
import json
import statistics
import subprocess
from pathlib import Path


def run(cmd: list[str], cwd: Path, log: Path, done: Path | None = None):
    if done is not None and done.exists():
        return
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('w', encoding='utf-8') as f:
        r = subprocess.run(cmd, cwd=str(cwd), stdout=f, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        raise RuntimeError(f'failed: {cmd} log={log}')


def signflip_p(x: list[float], y: list[float]) -> float:
    if len(x) != len(y) or len(x) == 0:
        return 1.0
    d = [a - b for a, b in zip(x, y)]
    obs = abs(sum(d) / len(d))
    if obs <= 1e-12:
        return 1.0
    n = len(d)
    total = 0
    extreme = 0
    if n <= 12:
        for bits in itertools.product([-1.0, 1.0], repeat=n):
            total += 1
            stat = abs(sum(di * si for di, si in zip(d, bits)) / n)
            if stat >= obs - 1e-12:
                extreme += 1
    else:
        import random

        rng = random.Random(42)
        for _ in range(4096):
            total += 1
            stat = abs(sum(di * (1.0 if rng.random() > 0.5 else -1.0) for di in d) / n)
            if stat >= obs - 1e-12:
                extreme += 1
    return float((extreme + 1) / (total + 1))


def read_f1(path: Path) -> float:
    j = json.loads(path.read_text(encoding='utf-8'))
    m = j.get('final_eval', {}).get('test_temporal') or j.get('final_eval', {}).get('test_random') or {}
    return float(m.get('f1', 0.0))


def stats(v: list[float]) -> dict:
    if not v:
        return {'n': 0, 'mean': 0.0, 'std': 0.0}
    if len(v) == 1:
        return {'n': 1, 'mean': float(v[0]), 'std': 0.0}
    return {'n': len(v), 'mean': float(statistics.mean(v)), 'std': float(statistics.stdev(v))}


def main() -> None:
    project = Path('/home/user/FedSTGCN')
    py = '/home/user/miniconda3/envs/DL/bin/python'
    base = project / 'central_congestion_family_recharge'
    out = project / 'ablation_mechanism_recharge'
    out.mkdir(parents=True, exist_ok=True)

    seeds = [11, 22, 33, 44, 55, 66, 77, 88, 99]
    protocols = ['congestion_soft', 'congestion_mid', 'congestion_hard']

    variants = {
        'data_only': {'alpha': 0.0, 'beta': 0.0, 'context': False},
        'loss_only': {'alpha': 0.3, 'beta': 0.2, 'context': False},
        'context_only': {'alpha': 0.0, 'beta': 0.0, 'context': True},
        'both': {'alpha': 0.3, 'beta': 0.2, 'context': True},
    }

    rows = []
    for proto in protocols:
        g = base / 'protocol_graphs' / f'{proto}.pt'
        for seed in seeds:
            for vname, cfg in variants.items():
                d = out / 'runs' / f'{proto}__{vname}__s{seed}'
                d.mkdir(parents=True, exist_ok=True)
                rfile = d / 'r.json'
                cmd = [
                    py,
                    'pi_gnn_train_v2.py',
                    '--graph-file',
                    str(g),
                    '--model-file',
                    str(d / 'm.pt'),
                    '--results-file',
                    str(rfile),
                    '--epochs',
                    '120',
                    '--alpha-flow',
                    str(cfg['alpha']),
                    '--beta-latency',
                    str(cfg['beta']),
                    '--capacity',
                    '60000',
                    '--warmup-epochs',
                    '20',
                    '--patience',
                    '30',
                    '--seed',
                    str(seed),
                    '--force-cpu',
                ]
                if cfg['context']:
                    cmd.append('--physics-context')
                run(cmd, cwd=project, log=d / 'run.log', done=rfile)
                rows.append({'protocol': proto, 'seed': seed, 'variant': vname, 'f1': read_f1(rfile)})

    summary = {'seeds': seeds, 'protocols': protocols, 'variants': list(variants.keys()), 'rows': rows, 'stats': {}, 'p_values': {}}

    for proto in protocols:
        summary['stats'][proto] = {}
        for vname in variants:
            vals = [r['f1'] for r in rows if r['protocol'] == proto and r['variant'] == vname]
            summary['stats'][proto][vname] = stats(vals)

        # paired tests vs data_only
        d = [r['f1'] for r in sorted([x for x in rows if x['protocol'] == proto and x['variant'] == 'data_only'], key=lambda y: y['seed'])]
        for vname in ['loss_only', 'context_only', 'both']:
            x = [r['f1'] for r in sorted([x for x in rows if x['protocol'] == proto and x['variant'] == vname], key=lambda y: y['seed'])]
            summary['p_values'][f'{proto}_{vname}_vs_data_only'] = signflip_p(x, d)

    # pooled paired tests vs data-only
    pooled_data = [r['f1'] for r in rows if r['variant'] == 'data_only']
    for vname in ['loss_only', 'context_only', 'both']:
        pooled_x = [r['f1'] for r in rows if r['variant'] == vname]
        summary['p_values'][f'pooled_{vname}_vs_data_only'] = signflip_p(pooled_x, pooled_data)

    out_json = out / 'ablation_mechanism_summary.json'
    out_json.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    # markdown
    lines = ['# Mechanism Ablation (Recharge)', '']
    for proto in protocols:
        lines.append(f'## {proto}')
        for vname in variants:
            s = summary['stats'][proto][vname]
            lines.append(f"- {vname}: F1={s['mean']:.6f}±{s['std']:.6f} (n={s['n']})")
        for vname in ['loss_only', 'context_only', 'both']:
            lines.append(f"- p({vname} vs data_only)={summary['p_values'][f'{proto}_{vname}_vs_data_only']:.6g}")
        lines.append('')
    lines.append('## Pooled')
    for vname in ['loss_only', 'context_only', 'both']:
        lines.append(f"- p({vname} vs data_only)={summary['p_values'][f'pooled_{vname}_vs_data_only']:.6g}")

    (out / 'ablation_mechanism_summary.md').write_text('\n'.join(lines), encoding='utf-8')
    print(out_json)


if __name__ == '__main__':
    main()
