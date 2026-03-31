#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

PROJECT = Path('/home/user/FedSTGCN')
PY = '/home/user/miniconda3/envs/DL/bin/python'
KEY = os.environ.get('LLM_KEY', '')
OUT = PROJECT / 'llm_stability_eval'
OUT.mkdir(parents=True, exist_ok=True)

RUNS = []
for keep_proxy in (1, 0):
    for i in range(1, 4):
        RUNS.append({'keep_proxy': keep_proxy, 'run_id': f'kp{keep_proxy}_r{i}'})

summary = {'config': {'num_llm_sessions': 3, 'num_total_payloads': 180, 'llm_timeout_sec': 25}, 'runs': []}

for r in RUNS:
    run_id = r['run_id']
    out_json = OUT / f'{run_id}.json'
    log_file = OUT / f'{run_id}.log'

    env = os.environ.copy()
    env['LLM_API_KEY'] = KEY
    env['REQUIRE_REAL_LLM'] = '1'
    env['NUM_LLM_SESSIONS'] = '3'
    env['NUM_TOTAL_PAYLOADS'] = '180'
    env['LLM_TARGET_STEPS'] = '15'
    env['LLM_TIMEOUT_SEC'] = '25'
    env['KEEP_PROXY'] = str(r['keep_proxy'])
    env['OUTPUT_FILE'] = str(out_json)

    cmd = [PY, 'generate_llm_payloads.py']
    t0 = time.time()
    with log_file.open('w', encoding='utf-8') as lf:
        try:
            p = subprocess.run(cmd, cwd=str(PROJECT), env=env, stdout=lf, stderr=subprocess.STDOUT, timeout=260)
            rc = int(p.returncode)
            timeout_hit = False
        except subprocess.TimeoutExpired:
            rc = 124
            timeout_hit = True
    dt = time.time() - t0

    llm_sessions = 0
    total_payloads = 0
    if out_json.exists():
        try:
            data = json.loads(out_json.read_text(encoding='utf-8'))
            md = data.get('metadata', {}) if isinstance(data, dict) else {}
            llm_sessions = int(md.get('llm_sessions', 0))
            total_payloads = int(md.get('total_payloads', 0))
        except Exception:
            pass

    log_txt = log_file.read_text(encoding='utf-8', errors='ignore') if log_file.exists() else ''
    conn_err = log_txt.count('Connection error')
    bal_err = log_txt.count('Insufficient Balance')
    timeout_err = log_txt.lower().count('timeout')

    summary['runs'].append({
        'run_id': run_id,
        'keep_proxy': int(r['keep_proxy']),
        'rc': rc,
        'timeout_hit': timeout_hit,
        'duration_sec': round(dt, 2),
        'llm_sessions': llm_sessions,
        'total_payloads': total_payloads,
        'conn_error_count': conn_err,
        'balance_error_count': bal_err,
        'timeout_error_count': timeout_err,
        'success_real_llm': bool(rc == 0 and llm_sessions > 0),
        'json_file': str(out_json),
        'log_file': str(log_file),
    })

# aggregate
for kp in (0, 1):
    rs = [x for x in summary['runs'] if x['keep_proxy'] == kp]
    ok = [x for x in rs if x['success_real_llm']]
    summary[f'agg_keep_proxy_{kp}'] = {
        'n': len(rs),
        'success_n': len(ok),
        'success_rate': (len(ok) / len(rs)) if rs else 0.0,
        'llm_sessions_mean': (sum(x['llm_sessions'] for x in rs) / len(rs)) if rs else 0.0,
        'duration_mean_sec': (sum(x['duration_sec'] for x in rs) / len(rs)) if rs else 0.0,
        'conn_error_total': sum(x['conn_error_count'] for x in rs),
        'timeout_total': sum(x['timeout_error_count'] for x in rs),
    }

summary_path = OUT / 'summary.json'
summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(summary_path)
