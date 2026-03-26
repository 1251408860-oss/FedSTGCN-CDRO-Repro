# Supplemental Baseline Family

## Main (3 seeds)
- Noisy-CE: F1=0.8722, FPR=0.1822, ECE=0.1784, Brier=0.1218
- Posterior-CE: F1=0.8548, FPR=0.2203, ECE=0.2010, Brier=0.1434
- CDRO-Fixed: F1=0.8583, FPR=0.2080, ECE=0.1709, Brier=0.1384
- CDRO-UG (sw0): F1=0.8661, FPR=0.1834, ECE=0.1951, Brier=0.1335
- CDRO-UG + PriorCorr: F1=0.8671, FPR=0.1719, ECE=0.1935, Brier=0.1327

- CDRO-UG vs Posterior-CE: delta_F1=+0.011279, p=0.114474; delta_FPR=-0.036878, p=0.154503.
- CDRO-UG vs PriorCorr: delta_F1=-0.000941, p=0.58311; delta_FPR=+0.011514, p=0.00219673.

## Batch2 (3 seeds)
- Noisy-CE: F1=0.8876, FPR=0.2695, ECE=0.1714, Brier=0.1181
- Posterior-CE: F1=0.8832, FPR=0.2186, ECE=0.1975, Brier=0.1351
- CDRO-Fixed: F1=0.8880, FPR=0.2368, ECE=0.2225, Brier=0.1545
- CDRO-UG (sw0): F1=0.8852, FPR=0.2259, ECE=0.1826, Brier=0.1305
- CDRO-UG + PriorCorr: F1=0.8815, FPR=0.2410, ECE=0.1700, Brier=0.1229

- CDRO-UG vs Posterior-CE: delta_F1=+0.002084, p=0.345375; delta_FPR=+0.007281, p=0.392726.
- CDRO-UG vs PriorCorr: delta_F1=+0.003703, p=0.111057; delta_FPR=-0.015160, p=0.00219673.

## Reading
- Posterior-CE does not overtake CDRO-UG in either setting, so the final method is not simply benefiting from replacing hard labels with posterior soft labels.
- PriorCorr is unstable across datasets: it improves main pooled FPR slightly, but loses the key batch2 FPR advantage. This supports keeping raw sw0 as the locked main version.
