# Non-Graph Baseline And Clean-Label Upper Bound

Weak-label graph-family references are pooled from the existing `main_baselineplus_s3_v1` and `batch2_baselineplus_s3_v1` summaries; new runs add `XGBoost(weak)` and `PI-GNN(clean)`.

Artifact table: `table17_non_graph_clean_upper.csv`.

## main

| Method | F1 | FPR | ECE |
|---|---:|---:|---:|
| Noisy-CE | 0.872 +- 0.031 | 0.182 +- 0.093 | 0.178 +- 0.046 |
| CDRO-Fixed | 0.858 +- 0.038 | 0.208 +- 0.126 | 0.171 +- 0.071 |
| CDRO-UG(sw0) | 0.866 +- 0.031 | 0.183 +- 0.106 | 0.195 +- 0.056 |
| XGBoost(weak) | 0.813 +- 0.044 | 0.265 +- 0.061 | 0.180 +- 0.040 |
| PI-GNN(clean) | 0.995 +- 0.003 | 0.000 +- 0.000 | 0.000 +- 0.000 |

Graph-vs-tabular readout: `CDRO-UG(sw0)` vs `XGBoost(weak)` = delta F1 `+0.053`, delta FPR `-0.082`.
Weak-vs-clean gap: `PI-GNN(clean)` minus `CDRO-UG(sw0)` = delta F1 `+0.129`, delta FPR `-0.183`.

## external_j

| Method | F1 | FPR | ECE |
|---|---:|---:|---:|
| Noisy-CE | 0.888 +- 0.028 | 0.270 +- 0.077 | 0.171 +- 0.051 |
| CDRO-Fixed | 0.888 +- 0.029 | 0.237 +- 0.070 | 0.223 +- 0.080 |
| CDRO-UG(sw0) | 0.885 +- 0.025 | 0.226 +- 0.050 | 0.183 +- 0.054 |
| XGBoost(weak) | 0.838 +- 0.055 | 0.113 +- 0.046 | 0.210 +- 0.092 |
| PI-GNN(clean) | 0.993 +- 0.004 | 0.000 +- 0.000 | 0.000 +- 0.000 |

Graph-vs-tabular readout: `CDRO-UG(sw0)` vs `XGBoost(weak)` = delta F1 `+0.047`, delta FPR `+0.113`.
Weak-vs-clean gap: `PI-GNN(clean)` minus `CDRO-UG(sw0)` = delta F1 `+0.108`, delta FPR `-0.226`.
