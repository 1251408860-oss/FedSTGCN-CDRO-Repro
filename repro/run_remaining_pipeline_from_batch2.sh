#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY_BIN="${PY_BIN:-/home/user/miniconda3/envs/DL/bin/python}"

cd "$ROOT_DIR"

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

echo "[DONE] remaining pipeline complete"
