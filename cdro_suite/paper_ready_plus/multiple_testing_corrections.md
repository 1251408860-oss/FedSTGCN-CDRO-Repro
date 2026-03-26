# Multiple Testing Corrections (Holm / BH)

| family | hypothesis | delta_mean | p_raw | p_holm_family | p_bh_family | p_holm_global | p_bh_global |
|---|---|---:|---:|---:|---:|---:|---:|
| core_results | batch2_pooled_cdro_ug_vs_noisy_ce_fpr | -0.043630 | 0.0051257 | 0.0205028 | 0.0205028 | 0.0563827 | 0.01794 |
| core_results | main_pooled_cdro_ug_vs_noisy_ce_fpr | -0.028020 | 0.553072 | 1 | 0.789846 | 1 | 0.637953 |
| core_results | batch2_pooled_cdro_ug_vs_noisy_ce_f1 | -0.002307 | 0.592385 | 1 | 0.789846 | 1 | 0.637953 |
| core_results | main_pooled_cdro_ug_vs_noisy_ce_f1 | +0.002374 | 0.99745 | 1 | 0.99745 | 1 | 0.99745 |
| mechanism | batch2_b035_vs_full_pooled_fpr | +0.011855 | 0.000732243 | 0.00146449 | 0.00146449 | 0.0102514 | 0.0102514 |
| mechanism | main_uniform_vs_full_pooled_f1 | -0.004083 | 0.0148889 | 0.0148889 | 0.0148889 | 0.148889 | 0.041689 |
| supplemental_baselines | main_pooled_cdro_ug_vs_cdro_ug_priorcorr_fpr | +0.011514 | 0.00219673 | 0.0175738 | 0.00878692 | 0.0285575 | 0.0102514 |
| supplemental_baselines | batch2_pooled_cdro_ug_vs_cdro_ug_priorcorr_fpr | -0.015160 | 0.00219673 | 0.0175738 | 0.00878692 | 0.0285575 | 0.0102514 |
| supplemental_baselines | batch2_pooled_cdro_ug_vs_cdro_ug_priorcorr_f1 | +0.003703 | 0.111057 | 0.666341 | 0.228948 | 0.999512 | 0.228948 |
| supplemental_baselines | main_pooled_cdro_ug_vs_posterior_ce_f1 | +0.011279 | 0.114474 | 0.666341 | 0.228948 | 0.999512 | 0.228948 |
| supplemental_baselines | main_pooled_cdro_ug_vs_posterior_ce_fpr | -0.036878 | 0.154503 | 0.666341 | 0.247205 | 1 | 0.270381 |
| supplemental_baselines | batch2_pooled_cdro_ug_vs_posterior_ce_f1 | +0.002084 | 0.345375 | 1 | 0.44883 | 1 | 0.537249 |
| supplemental_baselines | batch2_pooled_cdro_ug_vs_posterior_ce_fpr | +0.007281 | 0.392726 | 1 | 0.44883 | 1 | 0.549817 |
| supplemental_baselines | main_pooled_cdro_ug_vs_cdro_ug_priorcorr_f1 | -0.000941 | 0.58311 | 1 | 0.58311 | 1 | 0.637953 |
