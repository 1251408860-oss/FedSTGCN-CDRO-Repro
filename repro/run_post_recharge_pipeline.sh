#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY_BIN="${PY_BIN:-/home/user/miniconda3/envs/DL/bin/python}"
BACKUP_SUFFIX="${BACKUP_SUFFIX:-20260310_1305}"

cd "$ROOT_DIR"

echo "[WAIT] waiting for run_oneclick_recharge.sh to finish"
while pgrep -af "run_oneclick_recharge.sh" >/dev/null 2>&1; do
  sleep 60
done

echo "[RUN] backing up existing batch2 outputs"
if [[ -d "$ROOT_DIR/top_conf_suite_batch2" && ! -d "$ROOT_DIR/top_conf_suite_batch2_backup_${BACKUP_SUFFIX}" ]]; then
  mv "$ROOT_DIR/top_conf_suite_batch2" "$ROOT_DIR/top_conf_suite_batch2_backup_${BACKUP_SUFFIX}"
fi

echo "[RUN] rerunning top_conf_suite_batch2"
"$PY_BIN" run_top_conference_suite.py \
  --project-dir "$ROOT_DIR" \
  --python-bin "$PY_BIN" \
  --output-dir "$ROOT_DIR/top_conf_suite_batch2" \
  --real-collection-dir "$ROOT_DIR/real_collection" \
  --seeds "11,22,33" \
  --scenario-low "scenario_i_three_tier_low_b2" \
  --scenario-high "scenario_j_three_tier_high_b2" \
  --scenario-two-tier "scenario_k_two_tier_high_b2"

echo "[RUN] batch2 baseline significance"
"$PY_BIN" run_baseline_significance.py \
  --python-bin "$PY_BIN" \
  --suite-dir "$ROOT_DIR/top_conf_suite_batch2" \
  --seeds "11,22,33"

echo "[RUN] batch2 federated cross-protocol significance"
"$PY_BIN" run_fed_cross_protocol_significance.py \
  --python-bin "$PY_BIN" \
  --suite-dir "$ROOT_DIR/top_conf_suite_batch2" \
  --seeds "11,22,33"

echo "[RUN] batch2 federated extended significance"
"$PY_BIN" run_fed_significance_ext_final.py \
  --python-bin "$PY_BIN" \
  --suite-dir "$ROOT_DIR/top_conf_suite_batch2" \
  --seeds "11,22,33"

echo "[RUN] batch2 paper tables/figures"
"$PY_BIN" make_paper_tables_figs.py --suite-dir "$ROOT_DIR/top_conf_suite_batch2"

echo "[RUN] supplemental classic robust baselines"
"$PY_BIN" run_fed_classic_robust_baselines.py --suite-dir "$ROOT_DIR/top_conf_suite_recharge"

echo "[RUN] multiple testing corrections"
"$PY_BIN" compute_multiple_testing_corrections.py

echo "[RUN] runtime cost summary"
"$PY_BIN" summarize_runtime_costs.py --suite-dir "$ROOT_DIR/top_conf_suite_recharge"

echo "[RUN] refresh recharge master summary"
"$PY_BIN" compile_recharge_master_summary.py

echo "[DONE] post-recharge pipeline complete"
