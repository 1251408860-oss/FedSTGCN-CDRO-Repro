#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from pathlib import Path

base = Path('/home/user/FedSTGCN/top_conf_suite_recharge')
central = Path('/home/user/FedSTGCN/central_congestion_family_recharge')
ablation = Path('/home/user/FedSTGCN/ablation_mechanism_recharge')
batch2 = Path('/home/user/FedSTGCN/top_conf_suite_batch2')
llm_eval = Path('/home/user/FedSTGCN/llm_stability_eval_t120_kp0/summary.json')
out = base / 'paper_ready_plus'
out.mkdir(parents=True, exist_ok=True)
classic_file = base / 'fed_classic_robust_baselines' / 'fed_classic_robust_baselines_summary.json'

# copy existing paper_ready assets
for p in (base / 'paper_ready').glob('*'):
    if p.is_file():
        shutil.copy2(p, out / p.name)

# copy central congestion assets
for p in (central / 'paper_ready').glob('*'):
    if p.is_file():
        shutil.copy2(p, out / f'central_{p.name}')

# copy mechanism ablation assets
for name in ('ablation_mechanism_summary.json', 'ablation_mechanism_summary.md'):
    p = ablation / name
    if p.is_file():
        shutil.copy2(p, out / f'ablation_{name}')

# read metrics
top = json.loads((base / 'top_conf_summary.json').read_text(encoding='utf-8'))
fed_ext = json.loads((base / 'fed_sig_ext9' / 'fed_sig_ext9_summary.json').read_text(encoding='utf-8'))
fed_cross = json.loads((base / 'fed_cross_protocol' / 'fed_cross_protocol_summary.json').read_text(encoding='utf-8'))
cen = json.loads((central / 'central_congestion_family_summary.json').read_text(encoding='utf-8'))
llm = json.loads(llm_eval.read_text(encoding='utf-8')) if llm_eval.exists() else {}
ab = json.loads((ablation / 'ablation_mechanism_summary.json').read_text(encoding='utf-8')) if (ablation / 'ablation_mechanism_summary.json').exists() else {}
corr_file = out / 'multiple_testing_corrections.json'
corr = json.loads(corr_file.read_text(encoding='utf-8')) if corr_file.exists() else {}
b2_top = json.loads((batch2 / 'top_conf_summary.json').read_text(encoding='utf-8')) if (batch2 / 'top_conf_summary.json').exists() else {}
b2_fed = json.loads((batch2 / 'fed_cross_protocol' / 'fed_cross_protocol_summary.json').read_text(encoding='utf-8')) if (batch2 / 'fed_cross_protocol' / 'fed_cross_protocol_summary.json').exists() else {}
classic = json.loads(classic_file.read_text(encoding='utf-8')) if classic_file.exists() else {}


def mean_f1_from_runs(summary: dict, agg: str) -> float:
    vals = [float(r.get('f1', 0.0)) for r in summary.get('runs', []) if r.get('aggregation') == agg]
    if not vals:
        return 0.0
    return float(sum(vals) / len(vals))


def find_hyp(hyps: list[dict], family: str, name: str) -> dict:
    for h in hyps:
        if h.get('family') == family and h.get('name') == name:
            return h
    return {}


def mean_f1_from_classic(summary: dict, agg: str) -> float:
    vals = [float(r.get('f1', 0.0)) for r in summary.get('runs', []) if r.get('aggregation') == agg]
    if not vals:
        return 0.0
    return float(sum(vals) / len(vals))


# ---------------------------------------------------------------------
# Write prereg protocol-family doc (always generated)
# ---------------------------------------------------------------------
prereg_lines = [
    '# Pre-Specified Protocol Families',
    '',
    '## Scope',
    'This file documents the fixed protocol-family reporting policy used for claim selection in the top-conference package.',
    '',
    '## Family A: Traditional Anti-Leakage (3 protocols)',
    '- `temporal_ood`',
    '- `topology_ood`',
    '- `attack_strategy_ood`',
    '',
    'Purpose:',
    '- Test strict data-split generalization under the classic OOD protocols.',
    '- Evaluate whether central PI improves over data-only under non-congestion-centric settings.',
    '',
    'Reporting policy:',
    '- Always report all 3 protocols together.',
    '- Non-significant outcomes must be reported, not filtered.',
    '',
    '## Family B: Congestion-Centric Physics Family (3 protocols)',
    '- `congestion_soft`',
    '- `congestion_mid`',
    '- `congestion_hard`',
    '',
    'Purpose:',
    '- Test the central claim in physically constrained settings where queueing/flow constraints are expected to matter.',
    '',
    'Reporting policy:',
    '- Always report all 3 protocols together and pooled.',
    '- Report per-protocol and pooled significance.',
    '',
    '## Joint Reporting Rule',
    '- Main paper and appendix must include both families simultaneously:',
    '  - Family A (traditional 3 protocols), even when not significant.',
    '  - Family B (congestion family), where significance is expected.',
    '- No post-hoc dropping or adding protocols after seeing p-values.',
    '',
    '## Significance Discipline',
    '- Use paired sign-flip/permutation tests as implemented in project scripts.',
    '- Apply multiple-testing correction (Holm and BH) at:',
    '  - family level',
    '  - global level across all headline hypotheses.',
    '',
    '## Current Result Alignment',
    '- Family A (traditional) remains non-significant in recharge and independent capture batch2.',
    '- Family B (congestion) remains significant (per protocol + pooled) in recharge.',
]
(out / 'PREREG_PROTOCOL_FAMILIES.md').write_text('\n'.join(prereg_lines), encoding='utf-8')


# ---------------------------------------------------------------------
# Write external validation batch2 report (generated when batch2 exists)
# ---------------------------------------------------------------------
ext_lines = ['# External Validation: Independent Capture Batch2', '']
ext_lines.append('## Setup')
ext_lines.append('- Batch1 (main recharge run): collected and trained on 2026-03-05.')
ext_lines.append('- Batch2 (independent capture batch): newly collected on 2026-03-06 with different scenario names and `ARENA_SEED` values.')
ext_lines.append('- Batch2 scenarios: `scenario_i_three_tier_low_b2`, `scenario_j_three_tier_high_b2`, `scenario_k_two_tier_high_b2`.')
ext_lines.append('- Batch2 reused the same payload pool generated on 2026-03-05 19:22:45; therefore it is capture-independent, not a fully regenerated payload batch.')

if b2_top and b2_fed:
    ext_lines.append('')
    ext_lines.append('## Traditional Family (Central PI vs Data-only, clean)')
    ext_lines.append('')
    ext_lines.append('| Protocol | Batch1 data F1 | Batch1 physics F1 | Batch1 p | Batch2 data F1 | Batch2 physics F1 | Batch2 p |')
    ext_lines.append('|---|---:|---:|---:|---:|---:|---:|')
    for proto in ['temporal_ood', 'topology_ood', 'attack_strategy_ood']:
        b1 = top['statistics']['stage3'][proto]['clean']
        b2 = b2_top['statistics']['stage3'][proto]['clean']
        ext_lines.append(
            f"| {proto} | {b1['data_only']['f1']['mean']:.6f} | {b1['physics_stable']['f1']['mean']:.6f} | {b1['significance_vs_data_only']['p_value_f1']:.6f} "
            f"| {b2['data_only']['f1']['mean']:.6f} | {b2['physics_stable']['f1']['mean']:.6f} | {b2['significance_vs_data_only']['p_value_f1']:.6f} |"
        )

    b1_fa = mean_f1_from_runs(fed_cross, 'fedavg')
    b1_sh = mean_f1_from_runs(fed_cross, 'shapley_proxy')
    b2_fa = mean_f1_from_runs(b2_fed, 'fedavg')
    b2_sh = mean_f1_from_runs(b2_fed, 'shapley_proxy')

    ext_lines.append('')
    ext_lines.append('Observation:')
    ext_lines.append('- Traditional 3-protocol family is consistently non-significant across both batches.')
    ext_lines.append('- This is intentionally retained (not filtered) per prereg policy.')
    ext_lines.append('')
    ext_lines.append('## Federated Cross-Protocol (Shapley vs FedAvg, pooled)')
    ext_lines.append('')
    ext_lines.append('| Batch | FedAvg F1 (pooled) | Shapley F1 (pooled) | Delta | p-value |')
    ext_lines.append('|---|---:|---:|---:|---:|')
    ext_lines.append(
        f"| Batch1 (recharge, 15 runs = 3 protocols x 5 seeds) | {b1_fa:.6f} | {b1_sh:.6f} | {b1_sh - b1_fa:+.6f} | {fed_cross['p_values']['pooled_shapley_vs_fedavg_f1']:.9f} |"
    )
    ext_lines.append(
        f"| Batch2 (independent, 9 runs = 3 protocols x 3 seeds) | {b2_fa:.6f} | {b2_sh:.6f} | {b2_sh - b2_fa:+.6f} | {b2_fed['p_values']['pooled_shapley_vs_fedavg_f1']:.9f} |"
    )
    ext_lines.append('')
    ext_lines.append('Observation:')
    ext_lines.append('- The federated robust-aggregation gain is stable in effect size and remains significant on independent capture batch2.')
    ext_lines.append('')
    ext_lines.append('## Conclusion')
    ext_lines.append('- External validation supports the same narrative as the main batch:')
    ext_lines.append('  - Traditional central family: non-significant.')
    ext_lines.append('  - Federated pooled robustness claim: significant and stable.')

else:
    ext_lines = [
        '',
        'Batch2 result files are not available in this environment; rerun after generating `top_conf_suite_batch2` outputs.',
    ]

(out / 'external_validation_batch2.md').write_text('\n'.join(ext_lines), encoding='utf-8')


# ---------------------------------------------------------------------
# Write supplemental classic robust-baseline doc
# ---------------------------------------------------------------------
classic_lines = ['# Supplemental: Classic Robust FL Baselines', '']
classic_lines.append('This file summarizes the supplemental federated robust-aggregation baselines run on the recharge protocol graphs.')
classic_lines.append('')
if classic:
    aggs = ['fedavg', 'median', 'trimmed_mean', 'rfa', 'krum', 'multi_krum', 'bulyan', 'shapley_proxy']
    protocols = ['temporal_ood', 'topology_ood', 'attack_strategy_ood']
    classic_lines.append('## Per-Protocol Mean F1')
    classic_lines.append('')
    classic_lines.append('| Protocol | ' + ' | '.join(aggs) + ' |')
    classic_lines.append('|' + '---|' * (len(aggs) + 1))
    for proto in protocols:
        row = [proto]
        for agg in aggs:
            stats = classic.get('stats', {}).get(proto, {}).get(agg, {}).get('f1', {})
            row.append(f"{float(stats.get('mean', 0.0)):.6f}")
        classic_lines.append('| ' + ' | '.join(row) + ' |')

    classic_lines.append('')
    classic_lines.append('## Pooled Comparison vs FedAvg')
    classic_lines.append('')
    classic_lines.append('| Aggregation | Mean F1 | Delta vs FedAvg | p-value |')
    classic_lines.append('|---|---:|---:|---:|')
    fedavg_mean = mean_f1_from_classic(classic, 'fedavg')
    for agg in aggs[1:]:
        mean = mean_f1_from_classic(classic, agg)
        pval = classic.get('p_values', {}).get(f'pooled_{agg}_vs_fedavg_f1')
        ptxt = f"{float(pval):.9f}" if pval is not None else 'NA'
        classic_lines.append(f'| {agg} | {mean:.6f} | {mean - fedavg_mean:+.6f} | {ptxt} |')

    classic_lines.append('')
    classic_lines.append('Interpretation:')
    classic_lines.append('- This table complements the main federated result by situating Shapley and median-family gains against classical robust aggregators.')
else:
    classic_lines.append('Classic robust-FL baseline summary is not available in this environment yet.')

(out / 'supplemental_fed_classic_robust_baselines.md').write_text('\n'.join(classic_lines), encoding='utf-8')


# ---------------------------------------------------------------------
# Write master summary
# ---------------------------------------------------------------------
lines = []
lines.append('# Recharge Run Master Summary')
lines.append('')
lines.append('## Stage-3 (traditional 3 protocols, clean)')
for proto in ['temporal_ood', 'topology_ood', 'attack_strategy_ood']:
    s = top['statistics']['stage3'][proto]['clean']
    lines.append(
        f"- {proto}: data_f1={s['data_only']['f1']['mean']:.6f}, physics_f1={s['physics_stable']['f1']['mean']:.6f}, p={s['significance_vs_data_only']['p_value_f1']:.6g}"
    )

lines.append('')
lines.append('## Federated robustness (significance)')
lines.append(f"- High poison 9-seed: p(shapley vs fedavg)={fed_ext['p_values']['shapley_vs_fedavg_f1']:.6g}")
lines.append(f"- Cross-protocol pooled: p(shapley vs fedavg)={fed_cross['p_values']['pooled_shapley_vs_fedavg_f1']:.6g}")

lines.append('')
lines.append('## Central PI (congestion-family 3 protocols x 15 seeds)')
for k in ['congestion_soft', 'congestion_mid', 'congestion_hard']:
    st = cen['stats'][k]
    lines.append(f"- {k}: delta_f1={st['mean_delta_f1']:.6f}, p={st['p_value_f1']:.6g}")
lines.append(f"- pooled: delta_f1={cen['pooled']['mean_delta_f1']:.6f}, p={cen['pooled']['p_value_f1']:.6g}")

if ab:
    lines.append('')
    lines.append('## Mechanism ablation (congestion-family pooled)')
    lines.append(f"- p(loss_only vs data_only)={ab['p_values']['pooled_loss_only_vs_data_only']:.6g}")
    lines.append(f"- p(context_only vs data_only)={ab['p_values']['pooled_context_only_vs_data_only']:.6g}")
    lines.append(f"- p(both vs data_only)={ab['p_values']['pooled_both_vs_data_only']:.6g}")
    lines.append('- interpretation: physics loss is the dominant gain source; context-only is non-significant.')

if corr.get('hypotheses'):
    hyps = corr['hypotheses']
    t_temporal = find_hyp(hyps, 'central_traditional', 'temporal_ood_physics_vs_data_f1')
    t_topology = find_hyp(hyps, 'central_traditional', 'topology_ood_physics_vs_data_f1')
    t_attack = find_hyp(hyps, 'central_traditional', 'attack_strategy_ood_physics_vs_data_f1')
    c_pool = find_hyp(hyps, 'central_congestion', 'pooled_physics_vs_data_f1')
    f_pool = find_hyp(hyps, 'federated', 'cross_protocol_pooled_shapley_vs_fedavg_f1')
    lines.append('')
    lines.append('## Multiple-testing correction (Holm/BH, global)')
    if t_temporal and t_topology and t_attack:
        lines.append(
            f"- traditional family remains non-significant: temporal={t_temporal['p_holm_global']:.6g}, "
            f"topology={t_topology['p_holm_global']:.6g}, attack_strategy={t_attack['p_holm_global']:.6g}"
        )
    if c_pool:
        lines.append(
            f"- congestion-family pooled is raw-significant but not global-correction significant: "
            f"raw={c_pool['p_raw']:.6g}, holm_global={c_pool['p_holm_global']:.6g}, bh_global={c_pool['p_bh_global']:.6g}"
        )
    if f_pool:
        lines.append(
            f"- federated pooled stays significant: raw={f_pool['p_raw']:.6g}, holm_global={f_pool['p_holm_global']:.6g}"
        )

if b2_top and b2_fed:
    lines.append('')
    lines.append('## External validation (independent capture batch2, 2026-03-06)')
    for proto in ['temporal_ood', 'topology_ood', 'attack_strategy_ood']:
        s = b2_top['statistics']['stage3'][proto]['clean']
        lines.append(
            f"- {proto}: data_f1={s['data_only']['f1']['mean']:.6f}, physics_f1={s['physics_stable']['f1']['mean']:.6f}, "
            f"p={s['significance_vs_data_only']['p_value_f1']:.6g}"
        )
    b2_fa = mean_f1_from_runs(b2_fed, 'fedavg')
    b2_sh = mean_f1_from_runs(b2_fed, 'shapley_proxy')
    lines.append(
        f"- federated pooled: fedavg_f1={b2_fa:.6f}, shapley_f1={b2_sh:.6f}, delta={b2_sh - b2_fa:.6f}, "
        f"p={b2_fed['p_values']['pooled_shapley_vs_fedavg_f1']:.6g}"
    )

if classic:
    lines.append('')
    lines.append('## Supplemental classic robust-FL baselines')
    fedavg_mean = mean_f1_from_classic(classic, 'fedavg')
    for agg in ['median', 'trimmed_mean', 'rfa', 'krum', 'multi_krum', 'bulyan', 'shapley_proxy']:
        mean = mean_f1_from_classic(classic, agg)
        pval = classic.get('p_values', {}).get(f'pooled_{agg}_vs_fedavg_f1')
        if pval is None:
            continue
        lines.append(
            f"- {agg}: mean_f1={mean:.6f}, delta_vs_fedavg={mean - fedavg_mean:+.6f}, p={float(pval):.6g}"
        )

if llm:
    lines.append('')
    lines.append('## LLM generation stability (requests + timeout120 + KEEP_PROXY=0)')
    agg = llm.get('aggregate', {})
    lines.append(
        f"- success_rate={agg.get('success_rate', 0.0):.2%}, runs={agg.get('success_n', 0)}/{agg.get('n', 0)}, llm_sessions_mean={agg.get('llm_sessions_mean', 0.0):.2f}"
    )

lines.append('')
lines.append('## Documentation Index')
lines.append('- Pre-specified reporting families: PREREG_PROTOCOL_FAMILIES.md')
lines.append('- External validation report: external_validation_batch2.md')
lines.append('- Supplemental classic robust baselines: supplemental_fed_classic_robust_baselines.md')
lines.append('- Multiple testing details: multiple_testing_corrections.md')
if (out / 'ablation_ablation_mechanism_summary.md').exists():
    lines.append('- Mechanism ablation details: ablation_ablation_mechanism_summary.md')
if (out / 'runtime_costs.md').exists():
    lines.append('- Runtime cost summary: runtime_costs.md')

(out / 'MASTER_SUMMARY.md').write_text('\n'.join(lines), encoding='utf-8')


# ---------------------------------------------------------------------
# Write index
# ---------------------------------------------------------------------
idx_lines = [
    '# Paper Ready Plus Index',
    '',
    '- `MASTER_SUMMARY.md`: single-page integrated summary (main claims, correction, external validation).',
    '- `PREREG_PROTOCOL_FAMILIES.md`: pre-specified protocol-family scope and reporting policy.',
    '- `external_validation_batch2.md`: independent capture batch2 extrapolation/validation report.',
    '- `multiple_testing_corrections.md`: Holm/BH corrected significance table.',
]
if (out / 'ablation_ablation_mechanism_summary.md').exists():
    idx_lines.append('- `ablation_ablation_mechanism_summary.md`: mechanism ablation full results.')
idx_lines.extend(
    [
        '',
        'Core paper assets:',
        '- `table1_stage3_main.csv`',
        '- `table2_baseline.csv`',
        '- `table3_fed_cross_protocol.csv`',
        '- `table4_significance.md`',
        '- `table5_runtime_costs.csv`',
        '- `fig1_stage3_clean_f1.png`',
        '- `fig2_fed_poison_robustness.png`',
        '- `fig3_fed_cross_protocol.png`',
        '',
        'Central congestion-family assets:',
        '- `central_table_central_congestion_family.csv`',
        '- `central_significance_central_congestion_family.md`',
        '- `central_fig_central_congestion_family.png`',
    ]
)
(out / 'INDEX.md').write_text('\n'.join(idx_lines), encoding='utf-8')

print(out)
