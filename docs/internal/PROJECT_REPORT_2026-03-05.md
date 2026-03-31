# FedSTGCN Project Report (Audited on Ubuntu1 `/home/user/FedSTGCN`)

- Report date: 2026-03-05
- Environment: WSL2 `Ubuntu1`
- Project path: `/home/user/FedSTGCN`
- Note: directory is not a Git repo; no top-level README/requirements file.

## 1. What This Project Does

This is a research-oriented security ML pipeline for network attack detection.

Main goals:
1. Build realistic e-commerce traffic in Mininet (benign users + multi-strategy bots).
2. Convert PCAP traffic into a spatiotemporal heterogeneous graph.
3. Train a physics-informed spatiotemporal GNN (PI-STGNN / PI-GNN).
4. Evaluate federated robustness under poisoning with multiple aggregators.
5. Run OOD protocols + multi-seed significance tests and export paper-ready figures/tables.

Important naming note:
- Project folder is `FedSTGCN`, but core models are implemented as dual-branch GAT + gating + physics regularization, not a classic STGCN block.

## 2. End-to-End Pipeline

Primary orchestrator: `run_top_conference_suite.py`

Pipeline stages:
1. Build graphs from real Mininet capture scenarios.
2. Build anti-leakage protocol graphs (`temporal_ood`, `topology_ood`, `attack_strategy_ood`).
3. Stage-3 centralized training: `data_only` vs `physics_stable` (multi-seed).
4. Stage-4 federated training: poison level grid x aggregation method x multi-seed.
5. Aggregate mean/std + paired sign-flip p-values.

Recorded full run summary:
- `top_conf_suite_final/top_conf_summary.json`
- timestamps: 2026-03-05 08:54:20 to 2026-03-05 09:26:45

Other experiment drivers:
- `run_12_experiments.py`
- `run_baseline_significance.py`
- `run_fed_cross_protocol_significance.py`
- `run_fed_significance_ext_final.py`
- `run_central_custom_significance.py`
- `make_paper_tables_figs.py`

## 3. Data Generation and Traffic Modeling

### 3.1 LLM Session-Chain Payload Generation

Script: `generate_llm_payloads.py`

Key design:
1. Session-chain generation (not independent random requests).
2. LLM generation (DeepSeek/OpenAI API format) with algorithmic fallback.
3. Rich URI/header/UA/referrer/cookie/think-time simulation.
4. Outputs `sessions`, `flat_payloads`, `metadata`.

Observed payload files:
- `llm_payloads.json`: total_payloads=800, total_sessions=131, llm_sessions=4
- `llm_payloads_boost.json`: total_payloads=4002, total_sessions=656, llm_sessions=0

Interpretation:
- Boost file indicates fallback generation dominated (real LLM not successfully used there).

### 3.2 Mininet Arena and Attack Traffic

Scripts:
- `mininet_arena_v2.py`
- `bot_attack.py`
- `benign_traffic.py`
- `benign_user.py`
- `target_server.py`

Mechanisms:
1. Topologies: `three_tier`, `two_tier`, `flat_star`
2. Load profiles: `low`, `medium`, `high`
3. Bot behaviors: `slowburn`, `burst`, `mimic` (plus `mimic_heavy` mode)
4. Attack engine: HTTP (urllib) or scapy crafted packets
5. Target server returns varied page sizes by URI to shape realistic bidirectional traffic
6. Exports `pcap` + `manifest` (labels, roles, bot profile, topology config)

Collected scenario set under `real_collection/`:
- 8 scenarios (`scenario_a` ... `scenario_h`)
- includes stress variants like `scenario_g_mimic_congest` and `scenario_h_mimic_heavy_overlap`

Example (`scenario_e_three_tier_high2`):
- users=25, bots=80, core bottleneck=8 Mbps, high load
- role counts: slowburn=52, burst=18, mimic=10, benign_user=20

## 4. Graph Construction and Protocol Splits

### 4.1 Graph Builder

Script: `build_graph_v2.py`

Input:
- pcap + manifest

Output:
- `st_graph.pt`

Graph design:
1. One flow node per `(src_ip, time_window)` + one target aggregation node
2. Spatial edges: flow node -> target node
3. Temporal edges: same source IP across adjacent windows
4. 7D node features:
   - ln(N+1), ln(T+1), entropy, D_observed, pkt_rate, avg_pkt_size, port_diversity

### 4.2 Anti-Leakage Protocols

Scripts:
- `prepare_leakage_protocol_graph.py`
- `prepare_hard_protocol_graph.py`

Protocols:
1. `temporal_ood`: early windows train, later windows test
2. `topology_ood`: disjoint source groups by `ip_idx % 5`
3. `attack_strategy_ood`: hold out bot strategy type for testing
4. Extended script supports `congestion_ood`, overlap hardening, test camouflage

## 5. Model and Learning Design

### 5.1 Centralized Model (Stage-3)

Script: `pi_gnn_train_v2.py`

Architecture:
1. Input projection
2. Spatial GAT branch (2 layers)
3. Temporal GAT branch (2 layers)
4. Gated fusion + MLP classifier

Loss:
- `L_total = L_data + alpha * L_flow + beta * L_latency`
- `L_flow`: flow/capacity residual term
- `L_latency`: M/M/1-style latency violation term
- Warmup scales physics weights during early training

Robustness option:
- train label flipping (`train_poison_frac`, attack->benign)

### 5.2 Federated Model (Stage-4)

Script: `fed_pignn.py`

Framework:
- Flower + Ray simulation

Client partitioning:
- by `ip_idx % num_clients`

Poisoning simulation:
- poisoned clients upload noisy updates (Gaussian noise, `poison_scale`)

Aggregation methods:
1. `fedavg`
2. `median`
3. `trimmed_mean`
4. `shapley_proxy` (proxy score based on update alignment/distance/local F1; can isolate low-score clients)

## 6. Asset and Dataset Scale Snapshot

File sizes in current workspace:
- `full_arena_v2.pcap`: ~5.4 MB
- `st_graph.pt`: ~324 KB
- `llm_payloads.json`: ~1.5 MB
- `llm_payloads_boost.json`: ~7.2 MB

Graph stats (sampled):
1. `st_graph.pt`
   - nodes=1871, edges=2267, windows=155
   - flow labels: benign=337, attack=1533
2. `top_conf_suite_final/graphs/scenario_e_three_tier_high2.pt`
   - nodes=3077, edges=4381, windows=153
   - flow labels: benign=1772, attack=1304
3. Protocol masks on same base graph:
   - temporal_ood: train/val/test=1814/626/636 (test attack=282)
   - topology_ood: train/val/test=1924/618/534 (test attack=263)
   - attack_strategy_ood: train/val/test=2236/506/334 (test attack=63)

## 7. Key Experimental Results

Source: `top_conf_suite_final/top_conf_summary.json` and related summaries.

### 7.1 Run Scale

- Stage-3 runs: 50
- Federated runs: 60
- Stage-3 total duration: 669.73 s (mean 13.39 s)
- Federated total duration: 1244.87 s (mean 20.75 s)

### 7.2 Stage-3 (Clean): Physics vs Data-only

F1 means (physics - data):
1. temporal_ood: 0.974620 - 0.975738 = -0.001118, p=0.5152
2. topology_ood: 0.984887 - 0.983792 = +0.001095, p=0.2727
3. attack_strategy_ood: 0.973089 - 0.973089 = 0.000000, p=1.0000

Conclusion:
- No statistically significant gains from physics regularization in clean Stage-3 settings.

### 7.3 Stage-3 Attack-Strategy Poisoning Cases

- poison20 (avg flipped nodes ~217): data=physics=0.967992, p=1.0
- poison35 (avg flipped nodes ~379): data=physics=0.960397, p=1.0

Conclusion:
- Under this setup, physics/data-only remained nearly identical.

### 7.4 Stage-4 Federated Robustness

F1 mean over 5 seeds:
1. clean:
   - fedavg=0.9494, median=0.9494, trimmed_mean=0.9494, shapley_proxy=0.9494
2. poison_mid:
   - fedavg=0.9380, median=0.9514, trimmed_mean=0.9318, shapley_proxy=0.9502
3. poison_high:
   - fedavg=0.6467, median=0.9522, trimmed_mean=0.8216, shapley_proxy=0.9502

Conclusion:
- Under high poisoning, median/shapley are dramatically more robust than fedavg.

Shapley behavior evidence:
- Across 15 shapley runs x 4 rounds (60 rounds), client isolation happened in 40 rounds.

### 7.5 Baseline Model Comparison (RF / GCN / PI-GNN)

Source: `top_conf_suite_final/baseline_significance/baseline_significance_summary.json`

1. temporal_ood: GCN(0.9784) > PI-GNN(0.9743) > RF(0.9639)
2. topology_ood: GCN(0.9890) > PI-GNN(0.9844) > RF(0.9774)
3. attack_strategy_ood: PI-GNN(0.9761) approx GCN(0.9735) > RF(0.9333)

Conclusion:
- PI-GNN is competitive with GCN, but not consistently superior in this summary.

### 7.6 Cross-Protocol Federated Significance (High Poison)

Source: `fed_cross_protocol/fed_cross_protocol_summary.json`

- FedAvg F1 around 0.69-0.75 by protocol
- Median/Shapley around 0.95-0.98 by protocol
- pooled p-values:
  - p(shapley vs fedavg, F1) = 9.15499e-05
  - p(median vs fedavg, F1) = 9.15499e-05

9-seed extension (`fed_sig_ext9_summary.json`):
- fedavg F1 = 0.6706 +/- 0.2533
- shapley F1 = 0.9527 +/- 0.0058
- median F1 = 0.9531 +/- 0.0048
- p-values vs fedavg ~= 0.00585

## 8. LLM Stability Status

Script: `run_llm_stability_eval.py`
Summary: `llm_stability_eval/summary.json`

Observed:
- 6/6 runs timed out (rc=124)
- success_real_llm=0
- llm_sessions=0

Conclusion:
- Real LLM payload generation is currently unstable in this environment and is a major data-pipeline risk.

## 9. Engineering Assessment

Strengths:
1. Full-stack experimental pipeline from traffic to publication artifacts.
2. Clear anti-leakage OOD protocol handling.
3. Robust federated aggregation implementation with round-level debug traces.
4. Rich JSON summaries for secondary analysis.

Risks:
1. Missing repository hygiene (not Git-tracked, no top docs).
2. Naming mismatch (`FedSTGCN` vs actual PI-GAT implementation).
3. Real LLM dependency reliability is weak.
4. Physics gain claims should be conservative in centralized settings (weak significance).

## 10. Reproducibility and Environment

Conda env (DL):
- Python 3.10.19
- key libs: torch 2.10.0, torch-geometric 2.7.0, flwr 1.26.1, ray 2.51.1, scapy 2.7.0, mininet 2.3.1b4, locust 2.43.3, openai 2.24.0

Environment files:
- `DL_env_export.yml`
- `DL_conda_list.txt`
- `DL_pip_freeze.txt`

Recommended entry points:
1. `run_top_conference_suite.py`
2. `make_paper_tables_figs.py`
3. `run_baseline_significance.py`
4. `run_fed_cross_protocol_significance.py`
5. `run_fed_significance_ext_final.py`

## 11. Final Verdict

This project is a strong research prototype for attack detection under centralized and federated settings.

Most important empirical outcome:
- Federated robust aggregation (median/shapley_proxy) shows clear and statistically strong improvements over fedavg under high poisoning.

Most important caution:
- Physics regularization does not show stable significant gains in the currently recorded centralized summaries, and real-LLM data generation reliability is still a bottleneck.
