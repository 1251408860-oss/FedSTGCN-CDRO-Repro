# Analyst-Facing Case Studies

Figure: `fig10_analyst_case_studies.png`.

## Benign FP Suppressed

- Protocol / seed: `weak_temporal_ood` / `22`
- IP / role: `10.0.0.26` / `benign_user`
- Truth / weak label: `0` / `weak_benign`
- Noisy-CE prob / verdict: `0.425` / `1` at threshold `0.40`
- CDRO-UG prob / verdict: `0.353` / `0` at threshold `0.40`
- Weak posterior attack / trust-adjusted target attack: `0.171` / `0.098`
- Agreement / uncertainty / trust: `1.000` / `0.660` / `0.428`
- Group: `low_rho_low_uncertainty`
- Analyst readout: Noisy-CE raises a false alert on a benign user, while CDRO-UG suppresses it despite strong rate/latency views.

## True Positive Recovered

- Protocol / seed: `weak_topology_ood` / `33`
- IP / role: `10.0.0.34` / `bot:slowburn`
- Truth / weak label: `1` / `weak_benign`
- Noisy-CE prob / verdict: `0.190` / `0` at threshold `0.20`
- CDRO-UG prob / verdict: `0.054` / `1` at threshold `0.05`
- Weak posterior attack / trust-adjusted target attack: `0.329` / `0.216`
- Agreement / uncertainty / trust: `0.750` / `0.914` / `0.345`
- Group: `low_rho_high_uncertainty`
- Analyst readout: CDRO-UG keeps a true positive that Noisy-CE misses in a high-uncertainty slowburn region.

## Mimic TP Preserved

- Protocol / seed: `weak_attack_strategy_ood` / `11`
- IP / role: `10.0.0.107` / `bot:mimic`
- Truth / weak label: `1` / `weak_benign`
- Noisy-CE prob / verdict: `0.744` / `1` at threshold `0.10`
- CDRO-UG prob / verdict: `0.868` / `1` at threshold `0.05`
- Weak posterior attack / trust-adjusted target attack: `0.311` / `0.195`
- Agreement / uncertainty / trust: `1.000` / `0.895` / `0.374`
- Group: `low_rho_high_uncertainty`
- Analyst readout: Even under a misleading weak-benign label, CDRO-UG still keeps the mimic attack score high enough to alert.
