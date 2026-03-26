#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
    ap = argparse.ArgumentParser()
    ap.add_argument('--project-dir', default='/home/user/FedSTGCN')
    ap.add_argument('--python-bin', default='/home/user/miniconda3/envs/DL/bin/python')
    ap.add_argument('--output-dir', default='/home/user/FedSTGCN/central_congestion_family')
    ap.add_argument('--graph-file', default='')
    ap.add_argument('--manifest-file', default='/home/user/FedSTGCN/real_collection/scenario_h_mimic_heavy_overlap/arena_manifest_v2.json')
    ap.add_argument('--seeds', default='11,22,33,44,55,66,77,88,99,111,122,133,144,155,166')
    args = ap.parse_args()

    project = Path(args.project_dir)
    py = args.python_bin
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    graph = Path(args.graph_file) if str(args.graph_file).strip() else (project / 'central_boost_suite_h2/graphs/scenario_h_graph.pt')
    manifest = Path(args.manifest_file)

    seeds = [int(x.strip()) for x in str(args.seeds).split(',') if x.strip()]

    cfg = {
        'congestion_soft': {'tr': 0.80, 'va': 0.90, 'te': 0.85, 'alpha': 0.3, 'beta': 0.2},
        'congestion_mid': {'tr': 0.80, 'va': 0.90, 'te': 0.90, 'alpha': 0.3, 'beta': 0.2},
        'congestion_hard': {'tr': 0.80, 'va': 0.90, 'te': 0.96, 'alpha': 0.3, 'beta': 0.2},
    }

    for name, c in cfg.items():
        g = out / 'protocol_graphs' / f'{name}.pt'
        run(
            [
                py,
                'prepare_hard_protocol_graph.py',
                '--input-graph',
                str(graph),
                '--output-graph',
                str(g),
                '--protocol',
                'congestion_ood',
                '--manifest-file',
                str(manifest),
                '--hard-overlap',
                '--train-keep-frac',
                str(c['tr']),
                '--val-keep-frac',
                str(c['va']),
                '--test-keep-frac',
                str(c['te']),
                '--min-keep-per-class',
                '64',
                '--seed',
                '42',
            ],
            cwd=project,
            log=out / 'logs' / f'prep_{name}.log',
            done=g,
        )

    rows = []
    for name, c in cfg.items():
        g = out / 'protocol_graphs' / f'{name}.pt'
        for s in seeds:
            d0 = out / 'stage3' / f'{name}__data__s{s}'
            d0.mkdir(parents=True, exist_ok=True)
            r0 = d0 / 'r.json'
            run(
                [
                    py,
                    'pi_gnn_train_v2.py',
                    '--graph-file',
                    str(g),
                    '--model-file',
                    str(d0 / 'm.pt'),
                    '--results-file',
                    str(r0),
                    '--epochs',
                    '120',
                    '--alpha-flow',
                    '0',
                    '--beta-latency',
                    '0',
                    '--capacity',
                    '60000',
                    '--warmup-epochs',
                    '20',
                    '--patience',
                    '30',
                    '--seed',
                    str(s),
                    '--force-cpu',
                ],
                cwd=project,
                log=d0 / 'run.log',
                done=r0,
            )

            d1 = out / 'stage3' / f'{name}__physics__s{s}'
            d1.mkdir(parents=True, exist_ok=True)
            r1 = d1 / 'r.json'
            run(
                [
                    py,
                    'pi_gnn_train_v2.py',
                    '--graph-file',
                    str(g),
                    '--model-file',
                    str(d1 / 'm.pt'),
                    '--results-file',
                    str(r1),
                    '--epochs',
                    '120',
                    '--alpha-flow',
                    str(c['alpha']),
                    '--beta-latency',
                    str(c['beta']),
                    '--capacity',
                    '60000',
                    '--warmup-epochs',
                    '20',
                    '--patience',
                    '30',
                    '--seed',
                    str(s),
                    '--force-cpu',
                ],
                cwd=project,
                log=d1 / 'run.log',
                done=r1,
            )

            rows.append({'protocol': name, 'seed': s, 'model': 'data', 'f1': read_f1(r0)})
            rows.append({'protocol': name, 'seed': s, 'model': 'physics', 'f1': read_f1(r1)})

    summary = {'config': cfg, 'seeds': seeds, 'rows': rows, 'stats': {}, 'pooled': {}}
    pooled_d, pooled_p = [], []

    for name in cfg:
        d = sorted([r for r in rows if r['protocol'] == name and r['model'] == 'data'], key=lambda x: x['seed'])
        p = sorted([r for r in rows if r['protocol'] == name and r['model'] == 'physics'], key=lambda x: x['seed'])
        f1d = [x['f1'] for x in d]
        f1p = [x['f1'] for x in p]
        pooled_d.extend(f1d)
        pooled_p.extend(f1p)
        summary['stats'][name] = {
            'data': stats(f1d),
            'physics': stats(f1p),
            'mean_delta_f1': float(statistics.mean([a - b for a, b in zip(f1p, f1d)])),
            'p_value_f1': signflip_p(f1p, f1d),
        }

    summary['pooled'] = {
        'data': stats(pooled_d),
        'physics': stats(pooled_p),
        'mean_delta_f1': float(statistics.mean([a - b for a, b in zip(pooled_p, pooled_d)])),
        'p_value_f1': signflip_p(pooled_p, pooled_d),
    }

    out_json = out / 'central_congestion_family_summary.json'
    out_json.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print('done', out_json)
    print('pooled', summary['pooled'])


if __name__ == '__main__':
    main()
