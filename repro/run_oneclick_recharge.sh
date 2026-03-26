#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY_BIN="${PY_BIN:-/home/user/miniconda3/envs/DL/bin/python}"

OUT_DIR="${OUT_DIR:-$ROOT_DIR/top_conf_suite_recharge}"
SEEDS_STAGE3="${SEEDS_STAGE3:-11,22,33,44,55}"
SEEDS_FED9="${SEEDS_FED9:-11,22,33,44,55,66,77,88,99}"

SCENARIO_LOW="${SCENARIO_LOW:-scenario_d_three_tier_low2}"
SCENARIO_HIGH="${SCENARIO_HIGH:-scenario_e_three_tier_high2}"
SCENARIO_TWO_TIER="${SCENARIO_TWO_TIER:-scenario_f_two_tier_high2}"

run() {
  echo "[RUN] $*"
  "$@"
}

cd "$ROOT_DIR"

run "$PY_BIN" run_top_conference_suite.py \
  --project-dir "$ROOT_DIR" \
  --python-bin "$PY_BIN" \
  --output-dir "$OUT_DIR" \
  --real-collection-dir "$ROOT_DIR/real_collection" \
  --seeds "$SEEDS_STAGE3" \
  --scenario-low "$SCENARIO_LOW" \
  --scenario-high "$SCENARIO_HIGH" \
  --scenario-two-tier "$SCENARIO_TWO_TIER"

run "$PY_BIN" run_baseline_significance.py \
  --python-bin "$PY_BIN" \
  --suite-dir "$OUT_DIR" \
  --seeds "$SEEDS_STAGE3"

run "$PY_BIN" run_fed_significance_ext_final.py \
  --python-bin "$PY_BIN" \
  --suite-dir "$OUT_DIR" \
  --seeds "$SEEDS_FED9"

run "$PY_BIN" run_fed_cross_protocol_significance.py \
  --python-bin "$PY_BIN" \
  --suite-dir "$OUT_DIR" \
  --seeds "$SEEDS_STAGE3"

run "$PY_BIN" make_paper_tables_figs.py --suite-dir "$OUT_DIR"

run "$PY_BIN" run_central_congestion_family.py \
  --project-dir "$ROOT_DIR" \
  --python-bin "$PY_BIN" \
  --output-dir "$ROOT_DIR/central_congestion_family_recharge"

run "$PY_BIN" run_mechanism_ablation_recharge.py

run "$PY_BIN" compute_multiple_testing_corrections.py
run "$PY_BIN" summarize_runtime_costs.py --suite-dir "$OUT_DIR"
run "$PY_BIN" compile_recharge_master_summary.py

echo "[DONE] main suite: $OUT_DIR"
echo "[DONE] paper package: $OUT_DIR/paper_ready_plus"
echo "[DONE] central package: $ROOT_DIR/central_congestion_family_recharge/paper_ready"
