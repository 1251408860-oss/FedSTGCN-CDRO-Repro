#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "[ERROR] run_capture_batch2.sh must be run as root (sudo)."
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY_BIN="${PY_BIN:-/home/user/miniconda3/envs/DL/bin/python}"

NUM_LLM_SESSIONS="${NUM_LLM_SESSIONS:-60}"
NUM_TOTAL_PAYLOADS="${NUM_TOTAL_PAYLOADS:-8000}"
DURATION_SEC="${DURATION_SEC:-1200}"

export KEEP_PROXY="${KEEP_PROXY:-0}"
export LLM_TRANSPORT="${LLM_TRANSPORT:-requests}"
export LLM_TIMEOUT_SEC="${LLM_TIMEOUT_SEC:-120}"
export REQUIRE_REAL_LLM=1
export NUM_LLM_SESSIONS
export NUM_TOTAL_PAYLOADS
export USER_IP_START="${USER_IP_START:-10.0.0.10}"
export BOT_IP_START="${BOT_IP_START:-10.0.0.110}"

if [[ -z "${LLM_API_KEY:-${DEEPSEEK_API_KEY:-}}" ]]; then
  echo "[ERROR] missing LLM_API_KEY or DEEPSEEK_API_KEY in environment"
  exit 1
fi

run() {
  echo "[RUN] $*"
  "$@"
}

capture() {
  local name="$1"
  local topo="$2"
  local load="$3"
  local bot_mode="$4"
  local seed="$5"
  local users="$6"
  local bots="$7"

  local out_dir="$ROOT_DIR/real_collection/$name"
  mkdir -p "$out_dir"

  local pcap="$out_dir/full_arena_v2.pcap"
  local manifest="$out_dir/arena_manifest_v2.json"
  local log="$out_dir/mininet.log"

  echo "[SCENARIO] $name topo=$topo load=$load bot_mode=$bot_mode seed=$seed users=$users bots=$bots"

  set +e
  TOPOLOGY_MODE="$topo" \
  LOAD_PROFILE="$load" \
  BOT_TYPE_MODE="$bot_mode" \
  ARENA_SEED="$seed" \
  NUM_USERS="$users" \
  NUM_BOTS="$bots" \
  BENIGN_ENGINE=locust \
  ATTACK_ENGINE=http \
  REQUIRE_REAL_LLM=1 \
  PYTHON_BIN="$PY_BIN" \
  PCAP_FILE="$pcap" \
  MANIFEST_FILE="$manifest" \
  "$PY_BIN" "$ROOT_DIR/mininet_arena_v2.py" "$DURATION_SEC" > "$log" 2>&1
  local rc=$?
  set -e

  if [[ ! -s "$pcap" || ! -s "$manifest" ]]; then
    echo "[ERROR] capture artifacts missing for $name (rc=$rc)"
    exit 1
  fi

  echo "[OK] $name rc=$rc pcap=$(du -h "$pcap" | awk '{print $1}')"
}

cd "$ROOT_DIR"
run "$PY_BIN" generate_llm_payloads.py

# These values match the batch2 assets currently used by top_conf_suite_batch2.
capture "scenario_i_three_tier_low_b2"  "three_tier" "low"  "mixed"       "20260306" "20" "60"
capture "scenario_j_three_tier_high_b2" "three_tier" "high" "mixed"       "20260307" "25" "80"
capture "scenario_k_two_tier_high_b2"   "two_tier"   "high" "mixed"       "20260308" "25" "80"
capture "scenario_l_mimic_heavy_b2"     "three_tier" "high" "mimic_heavy" "20260309" "35" "70"

echo "[DONE] batch2 capture completed under $ROOT_DIR/real_collection"
