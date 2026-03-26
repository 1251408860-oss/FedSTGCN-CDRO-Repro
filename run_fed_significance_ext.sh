#!/usr/bin/env bash
set -euo pipefail

cd /home/user/FedSTGCN
PY=/home/user/miniconda3/envs/DL/bin/python
GRAPH=/home/user/FedSTGCN/top_conf_suite_v3/protocol_graphs/temporal_ood.pt
OUT=/home/user/FedSTGCN/fed_sig_ext
mkdir -p "$OUT"

seeds=(11 22 33 44 55 66 77 88 99)
aggs=(fedavg shapley_proxy median)

for agg in "${aggs[@]}"; do
  for s in "${seeds[@]}"; do
    d="$OUT/${agg}_s${s}"
    mkdir -p "$d"
    "$PY" fed_pignn.py \
      --graph-file "$GRAPH" \
      --model-file "$d/model.pt" \
      --results-file "$d/results.json" \
      --num-clients 3 \
      --rounds 4 \
      --local-epochs 2 \
      --aggregation "$agg" \
      --simulate-poison-frac 0.4 \
      --poison-scale 0.4 \
      --alpha-flow 0.03 \
      --beta-latency 0.02 \
      --warmup-rounds 2 \
      --seed "$s" \
      --client-cpus 2.0 \
      --client-gpus 0.0 \
      --force-cpu \
      > "$d/run.log" 2>&1
  done
done

python3 - <<'PY'
import glob, json, itertools, statistics
base='/home/user/FedSTGCN/fed_sig_ext'
scores={}
for agg in ['fedavg','shapley_proxy','median']:
    vals=[]
    for p in sorted(glob.glob(f'{base}/{agg}_s*/results.json')):
        d=json.load(open(p,'r',encoding='utf-8'))
        m=d.get('global_metrics',{}).get('test_temporal') or d.get('global_metrics',{}).get('test_random') or {}
        vals.append(float(m.get('f1',0.0)))
    scores[agg]=vals
    print(agg,'F1 mean',round(statistics.mean(vals),4),'std',round(statistics.stdev(vals),4),'n',len(vals))

def pval(x,y):
    d=[a-b for a,b in zip(x,y)]
    n=len(d); obs=abs(sum(d)/n); ext=0; tot=0
    for bits in itertools.product([-1,1], repeat=n):
        tot+=1
        s=abs(sum(di*si for di,si in zip(d,bits))/n)
        if s>=obs-1e-12: ext+=1
    return (ext+1)/(tot+1)

print('p(shapley vs fedavg)=',pval(scores['shapley_proxy'],scores['fedavg']))
print('p(median vs fedavg)=',pval(scores['median'],scores['fedavg']))
PY
