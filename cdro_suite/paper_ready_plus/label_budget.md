# Label-Budget Sweep

Settings: `weak_topology_ood + weak_attack_strategy_ood`, seeds `11/22/33`, methods `Noisy-CE / CDRO-Fixed / CDRO-UG(sw0)`.

Artifacts: `table16_label_budget.csv`, `fig9_label_budget.png`.

## Pooled Means

### main

| Budget | Effective | Noisy-CE F1 / FPR | CDRO-Fixed F1 / FPR | CDRO-UG(sw0) F1 / FPR |
|---:|---:|---:|---:|---:|
| 5% | 5.0% | 0.910 / 0.231 | 0.898 / 0.240 | 0.904 / 0.232 |
| 10% | 10.0% | 0.889 / 0.260 | 0.905 / 0.206 | 0.889 / 0.259 |
| 20% | 20.0% | 0.908 / 0.197 | 0.877 / 0.296 | 0.896 / 0.227 |
| 30% | 30.0% | 0.899 / 0.227 | 0.897 / 0.229 | 0.884 / 0.273 |
| 50% | 50.0% | 0.891 / 0.256 | 0.885 / 0.263 | 0.886 / 0.267 |
| 100% | 100.0% | 0.893 / 0.258 | 0.877 / 0.294 | 0.888 / 0.270 |

Low-budget readout (5%): `CDRO-UG(sw0)` F1 `0.904`, vs `Noisy-CE` `0.910` and `CDRO-Fixed` `0.898`.

### external_j

| Budget | Effective | Noisy-CE F1 / FPR | CDRO-Fixed F1 / FPR | CDRO-UG(sw0) F1 / FPR |
|---:|---:|---:|---:|---:|
| 5% | 5.0% | 0.908 / 0.203 | 0.916 / 0.164 | 0.907 / 0.210 |
| 10% | 10.0% | 0.902 / 0.208 | 0.912 / 0.159 | 0.912 / 0.223 |
| 20% | 20.0% | 0.905 / 0.215 | 0.900 / 0.191 | 0.906 / 0.220 |
| 30% | 30.0% | 0.897 / 0.206 | 0.901 / 0.197 | 0.899 / 0.208 |
| 50% | 50.0% | 0.910 / 0.228 | 0.906 / 0.184 | 0.904 / 0.207 |
| 100% | 100.0% | 0.910 / 0.220 | 0.907 / 0.210 | 0.901 / 0.197 |

Low-budget readout (10%): `CDRO-UG(sw0)` F1 `0.912`, vs `Noisy-CE` `0.902` and `CDRO-Fixed` `0.912`.
