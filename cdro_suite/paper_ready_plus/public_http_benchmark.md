# Public HTTP Benchmark

Dataset: `Biblio-US17` Large real HTTP URI corpus from University of Seville logs, converted into a compact weak-supervision tabular benchmark.

Train weak-label coverage: `94.6%`.
Weak attack precision on train-covered nodes: `1.000`.
Weak benign precision on train-covered nodes: `1.000`.

## Results

| Method | F1 | FPR | ECE | Brier |
|---|---:|---:|---:|---:|
| Noisy-CE | 0.842 +- 0.089 | 0.025 +- 0.006 | 0.084 +- 0.004 | 0.066 +- 0.010 |
| Posterior-CE | 0.631 +- 0.169 | 0.020 +- 0.010 | 0.138 +- 0.014 | 0.083 +- 0.010 |
| CDRO-Fixed | 0.660 +- 0.182 | 0.016 +- 0.005 | 0.133 +- 0.019 | 0.075 +- 0.009 |
| CDRO-UG(sw0) | 0.736 +- 0.106 | 0.023 +- 0.003 | 0.089 +- 0.023 | 0.068 +- 0.008 |

## Pairwise Readout

- `CDRO-UG(sw0)` vs `Noisy-CE`: delta F1 `-0.105`, delta FPR `-0.001`, delta ECE `+0.005`.
- `CDRO-UG(sw0)` vs `Posterior-CE`: delta F1 `+0.105`, delta FPR `+0.003`, delta ECE `-0.048`.
- `CDRO-UG(sw0)` vs `CDRO-Fixed`: delta F1 `+0.076`, delta FPR `+0.007`, delta ECE `-0.043`.

Artifact table: `table15_public_http_benchmark.csv`.