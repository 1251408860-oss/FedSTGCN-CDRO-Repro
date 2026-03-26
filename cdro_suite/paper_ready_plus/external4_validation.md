# External 4-Batch Validation

## External-I / 3-tier low
- Noisy-CE: F1=0.9639, FPR=0.0749, ECE=0.3295
- Posterior-CE: F1=0.9835, FPR=0.0730, ECE=0.4822
- CDRO-Fixed: F1=0.9877, FPR=0.0402, ECE=0.4537
- CDRO-UG (sw0): F1=0.9653, FPR=0.0924, ECE=0.4307
- CDRO-UG + PriorCorr: F1=0.9920, FPR=0.0214, ECE=0.3861

## External-J / 3-tier high
- Noisy-CE: F1=0.8876, FPR=0.2695, ECE=0.1714
- Posterior-CE: F1=0.8832, FPR=0.2186, ECE=0.1975
- CDRO-Fixed: F1=0.8880, FPR=0.2368, ECE=0.2225
- CDRO-UG (sw0): F1=0.8852, FPR=0.2259, ECE=0.1826
- CDRO-UG + PriorCorr: F1=0.8815, FPR=0.2410, ECE=0.1700

## External-K / 2-tier high
- Noisy-CE: F1=0.8950, FPR=0.1745, ECE=0.1555
- Posterior-CE: F1=0.8760, FPR=0.1406, ECE=0.2232
- CDRO-Fixed: F1=0.8912, FPR=0.1485, ECE=0.2035
- CDRO-UG (sw0): F1=0.8914, FPR=0.1503, ECE=0.2173
- CDRO-UG + PriorCorr: F1=0.8844, FPR=0.1558, ECE=0.2057

## External-L / mimic-heavy
- Noisy-CE: F1=0.8677, FPR=0.2893, ECE=0.2257
- Posterior-CE: F1=0.8526, FPR=0.3138, ECE=0.2523
- CDRO-Fixed: F1=0.8591, FPR=0.3003, ECE=0.3002
- CDRO-UG (sw0): F1=0.8736, FPR=0.2839, ECE=0.2456
- CDRO-UG + PriorCorr: F1=0.8743, FPR=0.2852, ECE=0.2277

## Pooled external
- Noisy-CE: F1=0.9035, FPR=0.2020, ECE=0.2205
- Posterior-CE: F1=0.8988, FPR=0.1865, ECE=0.2888
- CDRO-Fixed: F1=0.9065, FPR=0.1815, ECE=0.2950
- CDRO-UG (sw0): F1=0.9039, FPR=0.1881, ECE=0.2691
- CDRO-UG + PriorCorr: F1=0.9081, FPR=0.1759, ECE=0.2474

## Reading
- Pooled external 4-batch comparison: CDRO-UG vs Noisy-CE has delta_F1=+0.000353, p=0.941503; delta_FPR=-0.013916, p=0.20834.
- Pooled external 4-batch comparison against Posterior-CE: delta_F1=+0.005053, p=0.167192; delta_FPR=+0.001634, p=0.947103.
- The strongest scenario-level FPR drop against Noisy-CE appears in External-J / 3-tier high with delta_FPR=-0.043630.
