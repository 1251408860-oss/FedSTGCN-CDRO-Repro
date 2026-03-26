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
OUT = PROJECT / 'llm_stability_eval_requests'
OUT.mkdir(parents=True, exist_ok=True)

summary = {'runs': []}
for i in range(1, 6):
    run_id = f'req_r{i}'
    out_json = OUT / f'{run_id}.json'
    log_file = OUT / f'{run_id}.log'

    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    env['LLM_API_KEY'] = KEY
    env['LLM_TRANSPORT'] = 'requests'
    env['REQUIRE_REAL_LLM'] = '1'
    env['NUM_LLM_SESSIONS'] = '2'
    env['NUM_TOTAL_PAYLOADS'] = '120'
    env['LLM_TARGET_STEPS'] = '12'
    env['LLM_TIMEOUT_SEC'] = '25'
    env['KEEP_PROXY'] = '1'
    env['OUTPUT_FILE'] = str(out_json)

    cmd = [PY, '-u', 'generate_llm_payloads.py']
    t0 = time.time()
    with log_file.open('w', encoding='utf-8') as lf:
        try:
            p = subprocess.run(cmd, cwd=str(PROJECT), env=env, stdout=lf, stderr=subprocess.STDOUT, timeout=220)
            rc = int(p.returncode)
            timeout_hit = False
        except subprocess.TimeoutExpired:
            rc = 124
            timeout_hit = True
    dt = time.time() - t0

    llm_sessions = 0
    if out_json.exists():
        try:
            data = json.loads(out_json.read_text(encoding='utf-8'))
            llm_sessions = int(data.get('metadata', {}).get('llm_sessions', 0))
        except Exception:
            pass

    txt = log_file.read_text(encoding='utf-8', errors='ignore') if log_file.exists() else ''
    summary['runs'].append({
        'run_id': run_id,
        'rc': rc,
        'timeout_hit': timeout_hit,
        'duration_sec': round(dt, 2),
        'llm_sessions': llm_sessions,
        'success_real_llm': bool(rc == 0 and llm_sessions > 0),
        'conn_timeout_count': txt.count('Request timed out') + txt.count('Read timed out') + txt.count('ConnectTimeout'),
        'log_file': str(log_file),
        'json_file': str(out_json),
    })

ok = [r for r in summary['runs'] if r['success_real_llm']]
summary['aggregate'] = {
    'n': len(summary['runs']),
    'success_n': len(ok),
    'success_rate': (len(ok) / len(summary['runs'])) if summary['runs'] else 0.0,
    'llm_sessions_mean': (sum(r['llm_sessions'] for r in summary['runs']) / len(summary['runs'])) if summary['runs'] else 0.0,
    'duration_mean_sec': (sum(r['duration_sec'] for r in summary['runs']) / len(summary['runs'])) if summary['runs'] else 0.0,
}

sp = OUT / 'summary.json'
sp.write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(sp)
