#!/usr/bin/env bash
set -euo pipefail

cd /home/user/FedSTGCN
PY=/home/user/miniconda3/envs/DL/bin/python
G=/home/user/FedSTGCN/top_conf_suite_v3/protocol_graphs/attack_strategy_ood.pt

for m in data physics; do
  for s in 11 22 33 44 55; do
    if [ "$m" = "data" ]; then
      a=0
      b=0
    else
      a=0.03
      b=0.02
    fi
    od="/home/user/FedSTGCN/tmp_poison60_${m}_s${s}"
    mkdir -p "$od"
    "$PY" training/pi_gnn_train_v2.py \
      --graph-file "$G" \
      --model-file "$od/m.pt" \
      --results-file "$od/r.json" \
      --epochs 140 \
      --alpha-flow "$a" \
      --beta-latency "$b" \
      --train-poison-frac 0.60 \
      --warmup-epochs 25 \
      --patience 35 \
      --seed "$s" \
      --force-cpu \
      > "$od/run.log" 2>&1
  done
done

python3 - <<'PY'
import glob, json, statistics
for m in ["data", "physics"]:
    f1 = []
    rc = []
    for p in glob.glob(f"/home/user/FedSTGCN/tmp_poison60_{m}_s*/r.json"):
        d = json.load(open(p, "r", encoding="utf-8"))
        mm = d.get("final_eval", {}).get("test_temporal") or d.get("final_eval", {}).get("test_random") or {}
        f1.append(float(mm.get("f1", 0.0)))
        rc.append(float(mm.get("recall", 0.0)))
    print(
        m,
        "F1", round(statistics.mean(f1), 4), "std", round(statistics.stdev(f1), 4),
        "Recall", round(statistics.mean(rc), 4), "std", round(statistics.stdev(rc), 4),
    )
PY
